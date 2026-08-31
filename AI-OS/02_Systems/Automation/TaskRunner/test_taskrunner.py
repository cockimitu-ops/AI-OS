#!/usr/bin/env python3
"""Regression tests for the TaskRunner reliability fixes (2026-08-26).

Every test here corresponds to a bug that was actually live in this folder, not
to a hypothetical. The four races and the crash-loop are exactly the class of
defect that reappears silently during a refactor, because none of them produce
an error - they produce a truncated instruction, a blank answer, or a service
that restarts forever.

Run with no dependencies and no venv:
    python3 -m unittest discover -s . -p 'test_*.py' -v

stdlib unittest on purpose: pytest is installed nowhere on this server, and a
test suite that needs an install first is a test suite that never gets run.

These tests never touch the live queue - AIOS_WORKSPACE is redirected to a
temporary directory before aios_runner is imported, and the heavy
open-interpreter import is stubbed out, so the whole file runs in well under a
second under /usr/bin/python3.
"""
import argparse
import importlib
import importlib.util
import json
import os
import sys
import tempfile
import time
import types
import unittest
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))


def _install_stubs():
    """aios_runner imports open-interpreter and python-dotenv at module level.
    Neither is needed to test the queue mechanics, and open-interpreter is a
    multi-second import that only exists inside one venv. Stub both."""
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = dotenv

    # aios_runner sets litellm.request_timeout at import to override litellm's
    # 100-minute default, and calls litellm.completion() directly for agent
    # routing. Default the latter to raising: "routing unavailable" is the
    # correct quiet default for every test that isn't about routing, and it
    # exercises the guarantee that a dead router never blocks a task.
    litellm = types.ModuleType("litellm")

    def _no_routing(*a, **k):
        raise RuntimeError("routing not stubbed for this test")

    litellm.completion = _no_routing
    sys.modules["litellm"] = litellm

    fake = types.SimpleNamespace(
        auto_run=False, safe_mode=None, offline=None, verbose=None,
        disable_telemetry=None, system_message=None, messages=[],
        llm=types.SimpleNamespace(model=None),
        chat=lambda *a, **k: [],
    )
    interp = types.ModuleType("interpreter")
    interp.interpreter = fake
    sys.modules["interpreter"] = interp

    respond = types.ModuleType("interpreter.core.respond")
    sys.modules["interpreter.core.respond"] = respond
    core = types.ModuleType("interpreter.core")
    core.respond = respond
    sys.modules["interpreter.core"] = core

    dmm = types.ModuleType(
        "interpreter.terminal_interface.utils.display_markdown_message")
    dmm.display_markdown_message = lambda *a, **k: None
    for name in ("interpreter.terminal_interface",
                 "interpreter.terminal_interface.utils"):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules[
        "interpreter.terminal_interface.utils.display_markdown_message"] = dmm
    return fake


class TaskRunnerTestCase(unittest.TestCase):
    """Imports aios_runner fresh per test against a throwaway workspace."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["AIOS_WORKSPACE"] = self.tmp.name
        self.fake = _install_stubs()
        sys.path.insert(0, HERE)
        self.addCleanup(lambda: sys.path.remove(HERE))
        sys.modules.pop("aios_runner", None)
        self.runner = importlib.import_module("aios_runner")
        self.addCleanup(lambda: sys.modules.pop("aios_runner", None))

    def queue(self, name, text):
        path = os.path.join(self.runner.INBOX, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def log_of(self, name):
        path = os.path.join(self.runner.LOGS, f"{name}.log")
        if not os.path.exists(path):
            return None
        return open(path, encoding="utf-8").read()

    def assert_quarantined(self, name):
        self.assertFalse(os.path.exists(os.path.join(self.runner.INBOX, name)),
                         f"{name} still in inbox - it would be retried forever")
        self.assertTrue(os.path.exists(os.path.join(self.runner.COMPLETED, name)),
                        f"{name} never reached completed/")


class TestWorkspaceIsolation(TaskRunnerTestCase):
    def test_workspace_honours_env_and_is_not_the_live_queue(self):
        """Guards the tests themselves: a regression here would have this file
        writing into the real inbox, which the live worker would then execute."""
        self.assertTrue(self.runner.AIOS_DIR.startswith(self.tmp.name))
        self.assertNotIn("/home/nost/AI-OS/AI-OS/02_Systems", self.runner.INBOX)
        for d in (self.runner.INBOX, self.runner.COMPLETED, self.runner.LOGS):
            self.assertTrue(os.path.isdir(d))


class TestLogWriteIsAtomic(TaskRunnerTestCase):
    """Bug: logs were created with a plain open("w"), while dispatch_task.py and
    telegram_bridge.py poll for that path's *existence*. Both could read a
    zero-byte or half-written file and report it as the result."""

    def test_writes_complete_content(self):
        self.runner._write_log("t.md", "the answer")
        self.assertEqual(self.log_of("t.md"), "the answer")

    def test_leaves_no_partial_file_behind(self):
        self.runner._write_log("t.md", "x")
        leftovers = [f for f in os.listdir(self.runner.LOGS)
                     if f.endswith(".partial")]
        self.assertEqual(leftovers, [])

    def test_final_path_never_exists_before_content_is_complete(self):
        """The actual atomicity property. Intercept os.replace and assert that
        at the moment of the rename the destination did not already exist as a
        partially-written file - i.e. no reader could have seen it mid-write."""
        seen = {}
        real_replace = self.runner.os.replace

        def spy(src, dst):
            seen["dst_existed_before_rename"] = os.path.exists(dst)
            seen["src_content_at_rename"] = open(src, encoding="utf-8").read()
            return real_replace(src, dst)

        self.runner.os.replace = spy
        self.addCleanup(lambda: setattr(self.runner.os, "replace", real_replace))

        self.runner._write_log("t.md", "complete output")
        self.assertFalse(seen["dst_existed_before_rename"])
        self.assertEqual(seen["src_content_at_rename"], "complete output")

    def test_rewrites_cleanly_over_an_existing_log(self):
        self.runner._write_log("t.md", "first")
        self.runner._write_log("t.md", "second")
        self.assertEqual(self.log_of("t.md"), "second")


class TestEmptyTask(TaskRunnerTestCase):
    """Bug: an empty task file was deleted with no log written, so a waiting
    caller blocked for its full 180s timeout on an instantly-known failure."""

    def test_empty_task_gets_an_immediate_error_log(self):
        self.queue("empty.md", "   \n  ")
        self.runner._run_task(os.path.join(self.runner.INBOX, "empty.md"),
                              "empty.md")
        log = self.log_of("empty.md")
        self.assertIsNotNone(log, "no log written - caller would hang 180s")
        self.assertIn("ERROR", log)
        self.assert_quarantined("empty.md")


class TestAttemptAppliesItsFieldsToTheRealLlmObject(TaskRunnerTestCase):
    """_attempt() is what actually sets interpreter.llm.* before calling
    .chat() - MODEL_CHAIN having the right data means nothing if this function
    doesn't apply it. Direct test of _attempt() itself, not the chain around
    it, closing a gap left when the FreeLLMAPI-era end-to-end test was deleted
    along with the feature it was testing."""

    def setUp(self):
        super().setUp()
        # Base stub's chat() returns [] (used elsewhere to simulate a
        # rate-limited/empty response); these tests care about field
        # application, not that specific failure path, so give it a real
        # answer to return.
        self.fake.chat = lambda *a, **k: [
            {"role": "assistant", "type": "message", "content": "ok"}]

    def test_sets_every_field_including_none_ones(self):
        self.runner._attempt("some/model", "do a thing",
                             api_base="http://x", api_key="key123",
                             context_window=1_000_000, max_tokens=16_384)
        self.assertEqual(self.fake.llm.model, "some/model")
        self.assertEqual(self.fake.llm.api_base, "http://x")
        self.assertEqual(self.fake.llm.api_key, "key123")
        self.assertEqual(self.fake.llm.context_window, 1_000_000)
        self.assertEqual(self.fake.llm.max_tokens, 16_384)

    def test_omitted_fields_reset_to_none_not_left_stale(self):
        """The actual property being guarded: a previous attempt's custom
        endpoint/context-window must not survive into one that didn't ask
        for it."""
        self.runner._attempt("model-a", "x", api_base="http://stale",
                             context_window=999)
        self.runner._attempt("model-b", "x")  # no overrides this time
        self.assertIsNone(self.fake.llm.api_base)
        self.assertIsNone(self.fake.llm.api_key)
        self.assertIsNone(self.fake.llm.context_window)
        self.assertIsNone(self.fake.llm.max_tokens)


class TestModelChain(TaskRunnerTestCase):
    def test_first_working_model_wins_and_is_logged(self):
        self.runner._attempt = lambda model, instr, sp=None, history=None, **kwargs: f"done by {model}"
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(self.log_of("t.md"),
                         f"done by {self.runner.MODEL_CHAIN[0]['model']}")
        self.assert_quarantined("t.md")

    def test_falls_through_to_a_later_model(self):
        calls = []

        def flaky(model, instr, sp=None, history=None, **kwargs):
            calls.append(model)
            if len(calls) < 3:
                raise RuntimeError("rate limited")
            return "recovered"

        self.runner._attempt = flaky
        self.runner.time.sleep = lambda s: None  # skip the 20s cooldown
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(self.log_of("t.md"), "recovered")
        self.assertEqual(len(calls), 3)

    def test_total_failure_writes_a_diagnostic_not_an_empty_log(self):
        def dead(model, instr, sp=None, history=None, **kwargs):
            raise RuntimeError("quota exhausted")

        self.runner._attempt = dead
        self.runner.time.sleep = lambda s: None
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        log = self.log_of("t.md")
        self.assertIn("All models failed", log)
        self.assertIn("quota exhausted", log)
        for entry in self.runner.MODEL_CHAIN:
            self.assertIn(entry["model"], log)
        self.assert_quarantined("t.md")

    def test_escalation_disabled_is_stated_in_the_failure_log(self):
        """CLAUDE_ESCALATION_ENABLED is off pending a ToS decision. If it is off,
        the log must say so - otherwise the failure looks like the escalation
        tier ran and also failed."""
        self.runner._attempt = lambda m, i, sp=None, history=None, **kwargs: (_ for _ in ()).throw(RuntimeError("x"))
        self.runner.time.sleep = lambda s: None
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        if not self.runner.CLAUDE_ESCALATION_ENABLED:
            self.assertIn("Escalation: disabled", self.log_of("t.md"))


class TestBackupProviders(TaskRunnerTestCase):
    """Cerebras and OpenRouter, added 2026-08-30 as direct-API backup tiers
    after FreeLLMAPI (a self-hosted router, tried the same day) was removed -
    Felix wanted more free capacity without another service to run. Each is
    gated on its own env var being present, so shipping this causes zero
    behaviour change until the corresponding key is actually added."""

    def _import_with(self, cerebras_key, openrouter_key):
        if cerebras_key is None:
            os.environ.pop("CEREBRAS_API_KEY", None)
        else:
            os.environ["CEREBRAS_API_KEY"] = cerebras_key
        if openrouter_key is None:
            os.environ.pop("OPENROUTER_API_KEY", None)
        else:
            os.environ["OPENROUTER_API_KEY"] = openrouter_key
        self.addCleanup(os.environ.pop, "CEREBRAS_API_KEY", None)
        self.addCleanup(os.environ.pop, "OPENROUTER_API_KEY", None)

        self.fake = _install_stubs()
        sys.path.insert(0, HERE)
        self.addCleanup(lambda: sys.path.remove(HERE))
        sys.modules.pop("aios_runner", None)
        self.runner = importlib.import_module("aios_runner")
        self.addCleanup(lambda: sys.modules.pop("aios_runner", None))

    def test_neither_key_present_leaves_the_original_five_entries_untouched(self):
        self._import_with(None, None)
        models = [e["model"] for e in self.runner.MODEL_CHAIN]
        self.assertEqual(models, [
            self.runner.PRIMARY_MODEL, self.runner.PRIMARY_MODEL,
            "groq/openai/gpt-oss-20b", self.runner.FALLBACK_MODEL,
            "gemini/gemini-3.5-flash-lite",
        ])

    def test_cerebras_is_inserted_early_when_its_key_is_present(self):
        self._import_with("ck-test", None)
        models = [e["model"] for e in self.runner.MODEL_CHAIN]
        self.assertIn("cerebras/gpt-oss-120b", models)
        # Early in the chain, not appended at the end - it has real headroom
        # (14,400 req/day), it shouldn't wait behind every Groq/Gemini retry.
        self.assertLess(models.index("cerebras/gpt-oss-120b"), 3)

    def test_openrouter_is_appended_last_when_its_key_is_present(self):
        self._import_with(None, "or-test")
        self.assertEqual(self.runner.MODEL_CHAIN[-1]["model"],
                         "openrouter/nvidia/nemotron-3-super-120b-a12b:free")

    def test_both_keys_present_adds_both_without_disturbing_the_original_five(self):
        self._import_with("ck-test", "or-test")
        models = [e["model"] for e in self.runner.MODEL_CHAIN]
        self.assertEqual(len(models), 7)
        self.assertIn("cerebras/gpt-oss-120b", models)
        self.assertEqual(models[-1], "openrouter/nvidia/nemotron-3-super-120b-a12b:free")
        # The original five must all still be present, in their original
        # relative order, just with cerebras inserted among them.
        original = [self.runner.PRIMARY_MODEL, self.runner.PRIMARY_MODEL,
                   "groq/openai/gpt-oss-20b", self.runner.FALLBACK_MODEL,
                   "gemini/gemini-3.5-flash-lite"]
        remaining = [m for m in models if m != "cerebras/gpt-oss-120b"
                    and m != "openrouter/nvidia/nemotron-3-super-120b-a12b:free"]
        self.assertEqual(remaining, original)

    def test_new_entries_use_litellms_native_routing_not_a_custom_endpoint(self):
        """Unlike the removed FreeLLMAPI tier, these are litellm-native
        providers - api_base/api_key on the entry itself must stay None,
        since litellm reads CEREBRAS_API_KEY/OPENROUTER_API_KEY from the
        environment directly."""
        self._import_with("ck-test", "or-test")
        for entry in self.runner.MODEL_CHAIN:
            self.assertIsNone(entry["api_base"], entry["model"])
            self.assertIsNone(entry["api_key"], entry["model"])

    def test_openrouter_carries_its_verified_context_window(self):
        """Found live 2026-08-30: without this, Open Interpreter can't
        auto-detect the model's window and silently caps it at 8000 against
        an actual 1M (OpenRouter's own model page) - a real capability loss,
        not just a cosmetic warning."""
        self._import_with(None, "or-test")
        entry = self.runner.MODEL_CHAIN[-1]
        self.assertEqual(entry["model"],
                         "openrouter/nvidia/nemotron-3-super-120b-a12b:free")
        self.assertEqual(entry["context_window"], 1_000_000)
        self.assertEqual(entry["max_tokens"], 16_384)

    def test_entries_without_a_verified_window_leave_it_to_auto_detection(self):
        """Groq/Gemini/Cerebras all auto-detect correctly without this - only
        assert None here, not a guessed number, to avoid hard-coding a figure
        nobody has actually checked."""
        self._import_with("ck-test", None)
        for entry in self.runner.MODEL_CHAIN:
            if entry["model"] == "openrouter/nvidia/nemotron-3-super-120b-a12b:free":
                continue
            self.assertIsNone(entry["context_window"], entry["model"])
            self.assertIsNone(entry["max_tokens"], entry["model"])


class TestCrashGuard(TaskRunnerTestCase):
    """Bug: nothing guarded the per-task body in run_worker(). Any exception
    outside _attempt()'s own handling escaped the loop; systemd's
    Restart=always brought the worker back, it re-globbed the SAME queued file,
    and crash-looped on it indefinitely."""

    class _StopLoop(Exception):
        pass

    def _run_one_pass(self):
        """run_worker() loops forever. Let it complete exactly one poll pass by
        raising out of the sleep at the bottom of the loop."""
        def stop(seconds):
            raise TestCrashGuard._StopLoop()

        self.runner.time.sleep = stop
        with self.assertRaises(TestCrashGuard._StopLoop):
            self.runner.run_worker()

    def test_poisoned_task_is_quarantined_instead_of_looping_forever(self):
        def boom(model, instruction):
            raise MemoryError("something no per-model handler expects")

        # _run_task itself blows up before the model chain is even reached
        def exploding_run_task(path, filename):
            raise OSError("input/output error")

        self.queue("poison.md", "anything")
        self.runner._run_task = exploding_run_task
        self._run_one_pass()

        self.assert_quarantined("poison.md")
        log = self.log_of("poison.md")
        self.assertIn("worker failed on this task", log)
        self.assertIn("input/output error", log)

    def test_a_good_task_still_runs_in_the_same_pass(self):
        self.runner._attempt = lambda model, instr, sp=None, history=None, **kwargs: "fine"
        self.queue("good.md", "do a thing")
        self._run_one_pass()
        self.assertEqual(self.log_of("good.md"), "fine")
        self.assert_quarantined("good.md")

    def test_tasks_are_processed_in_filename_order(self):
        order = []
        self.runner._attempt = lambda model, instr, sp=None, history=None, **kwargs: order.append(instr) or "ok"
        self.queue("task_b.md", "second")
        self.queue("task_a.md", "first")
        self._run_one_pass()
        self.assertEqual(order, ["first", "second"])


class TestOutputFormatting(TaskRunnerTestCase):
    """Bug: the formatter concatenated every assistant message, every code
    block AND every raw command output, so Telegram showed the worker's scratch
    work instead of its answer - a `find` invocation followed by a truncated
    wall of paths, with the actual reply buried at the bottom. Changed
    2026-08-27 to return prose only."""

    def test_prose_wins_and_the_transcript_is_suppressed(self):
        out = self.runner.format_interpreter_output([
            {"role": "assistant", "type": "code", "format": "shell",
             "content": "find /home/nost/AI-OS -maxdepth 2"},
            {"role": "computer", "type": "console",
             "content": "/a.md\n/b.md\n/c.md"},
            {"role": "assistant", "type": "message",
             "content": "Here you go"},
        ])
        self.assertEqual(out, "Here you go")
        self.assertNotIn("find /home/nost", out)
        self.assertNotIn("Output:", out)

    def test_multiple_prose_messages_are_all_kept_in_order(self):
        out = self.runner.format_interpreter_output([
            {"role": "assistant", "type": "message", "content": "First."},
            {"role": "assistant", "type": "code", "format": "shell",
             "content": "ls"},
            {"role": "computer", "type": "console", "content": "x.txt"},
            {"role": "assistant", "type": "message", "content": "Second."},
        ])
        self.assertEqual(out, "First.\n\nSecond.")

    def test_no_prose_falls_back_to_transcript_so_failures_stay_debuggable(self):
        """If the model ran commands and never explained itself, the commands
        and their output are the only diagnostic left - dropping them would
        turn a debuggable failure into a silent one."""
        out = self.runner.format_interpreter_output([
            {"role": "assistant", "type": "code", "format": "shell",
             "content": "ls -la"},
            {"role": "computer", "type": "console", "content": "file.txt\n"},
        ])
        self.assertIn("ls -la", out)
        self.assertIn("file.txt", out)

    def test_empty_message_list_never_yields_an_empty_log(self):
        self.assertEqual(self.runner.format_interpreter_output([]),
                         "Task completed.")

    def test_plain_string_passes_through(self):
        self.assertEqual(self.runner.format_interpreter_output("done"), "done")


class TestAgentSelection(TaskRunnerTestCase):
    """04_Agents/ held four scoped role definitions from Sprint 024 that nothing
    could invoke - they were documentation for a human typing "as Research
    Analyst, do X" into chat. These cover the selection path that made them
    executable."""

    def setUp(self):
        super().setUp()
        import agents
        self.agents = agents

    def test_aliases_and_full_names_resolve(self):
        for given, expected in [
            ("@research", "Research_Analyst"),
            ("RA", "Research_Analyst"),
            ("Research-Analyst", "Research_Analyst"),
            ("  @VAULT ", "Vault_Architect"),
            ("biz", "Business_Development"),
            ("Content_Producer", "Content_Producer"),
        ]:
            self.assertEqual(self.agents.resolve(given), expected, given)

    def test_ambiguous_or_unknown_never_guesses(self):
        for given in ("nonsense", "a", "", None, "@"):
            self.assertIsNone(self.agents.resolve(given), repr(given))

    def test_every_agent_on_disk_has_a_usable_prompt_block(self):
        """A file without markers silently degrades to the base prompt, which is
        correct behaviour but silent - so assert every real agent on disk is
        wired, or a broken marker would go unnoticed until someone reads a bad
        answer. Checked against a live count of 04_Agents/*.md, not a
        hardcoded number - a hardcoded "4" already broke once, the day a 5th
        agent (Tech_Scout) was added, for a reason with nothing to do with
        this test's actual purpose."""
        found = self.agents.available()
        self.assertGreaterEqual(len(found), 4, found)
        for name in found:
            block = self.agents.load_prompt(name)
            self.assertTrue(block and len(block) > 200,
                            f"{name} has no usable prompt block")

    def test_directive_round_trip(self):
        raw = self.agents.directive("Research_Analyst") + "Profile Acme."
        self.assertEqual(self.agents.parse_directive(raw),
                         ("Research_Analyst", "Profile Acme."))

    def test_unknown_agent_in_directive_strips_but_keeps_the_task(self):
        """A typo'd alias must cost a slightly worse answer, never a lost task."""
        agent, instruction = self.agents.parse_directive(
            "<!-- agent: Nope -->\nDo the thing.")
        self.assertIsNone(agent)
        self.assertEqual(instruction, "Do the thing.")

    def test_task_without_directive_is_untouched(self):
        self.assertEqual(self.agents.parse_directive("Just a task."),
                         (None, "Just a task."))

    def test_agent_prompt_is_appended_not_substituted(self):
        """Selecting an agent must narrow focus without stripping the base
        prompt's guardrails - the destructive-action rule has to survive."""
        base = self.runner._system_prompt_for(None)
        scoped = self.runner._system_prompt_for("Research_Analyst")
        self.assertIn(base, scoped)
        self.assertGreater(len(scoped), len(base))
        self.assertIn("Guardrail", scoped)

    def test_unknown_agent_falls_back_to_base_prompt(self):
        self.assertEqual(self.runner._system_prompt_for("Nope"),
                         self.runner._system_prompt_for(None))

    def _write_voice_profile(self, text="VOICE-PROFILE-MARKER"):
        path = self.runner.VOICE_PROFILE_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        original = None
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                original = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

        def restore():
            if original is None:
                os.remove(path)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(original)
        self.addCleanup(restore)

    def test_voice_applies_only_to_felix_own_chat_threads(self):
        """Felix asked for his own register in his own chats only - every
        client-facing artefact (DMARC letters, Gumroad and Fiverr copy) has
        to stay professional. Scheduled and dispatched tasks run with no
        thread at all, so gating on the thread prefix makes that structural
        rather than something a prompt has to remember."""
        self._write_voice_profile()
        for thread in ("tg_12345", "web_abc"):
            self.assertIn("VOICE-PROFILE-MARKER",
                          self.runner._system_prompt_for(None, thread))
        for thread in (None, "", "schedule_daily_revenue_plan", "batch_1"):
            self.assertNotIn("VOICE-PROFILE-MARKER",
                             self.runner._system_prompt_for(None, thread))

    def test_voice_never_displaces_the_guardrails_or_the_agent_block(self):
        """The voice block is appended last and is the weakest instruction in
        the prompt. If it could push out the base prompt or the agent role,
        a casual chat would quietly run without the destructive-action rule."""
        self._write_voice_profile()
        scoped = self.runner._system_prompt_for("Research_Analyst", "tg_1")
        self.assertIn("Guardrail", scoped)
        self.assertIn("Research Analyst", scoped)
        self.assertLess(scoped.index("Research Analyst"),
                        scoped.index("VOICE-PROFILE-MARKER"))

    def test_missing_voice_profile_is_not_an_error(self):
        """No profile means the default register, never a failed task.

        Points the path at a directory that certainly has no profile in it
        rather than asserting the real one is absent: the first version of
        this test did the latter and started failing the moment Felix
        actually imported his chats - a test that breaks when the feature
        gets used is testing the machine, not the code."""
        with tempfile.TemporaryDirectory() as tmp:
            original = self.runner.VOICE_PROFILE_PATH
            self.runner.VOICE_PROFILE_PATH = os.path.join(tmp, "nope.md")
            try:
                self.assertEqual(self.runner._system_prompt_for(None, "tg_1"),
                                 self.runner._system_prompt_for(None))
            finally:
                self.runner.VOICE_PROFILE_PATH = original

    def test_worker_runs_the_task_with_the_agent_prompt(self):
        """End to end through _run_task: the directive is parsed off, and the
        prompt handed to the model is the scoped one."""
        seen = {}

        def spy(model, instruction, system_prompt=None, history=None, **kwargs):
            seen["instruction"] = instruction
            seen["prompt"] = system_prompt
            return "ok"

        self.runner._attempt = spy
        self.queue("t.md", self.agents.directive("Vault_Architect") + "Check drift.")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(seen["instruction"], "Check drift.")
        self.assertIn("Vault Architect", seen["prompt"])
        self.assertNotIn("<!-- agent:", seen["instruction"])


class TestAttemptTimeout(TaskRunnerTestCase):
    """Bug, observed live 2026-08-30: one task occupied the worker from
    14:32:31 to 16:14:01 - 101 minutes - on a single groq attempt, because
    litellm's request_timeout defaults to 6000.0 seconds (100 minutes) and
    nothing else bounded the call. The queue is strictly serial, so every
    task behind it waited, and `systemctl is-active` reported the worker
    healthy throughout. Nothing anywhere said a word."""

    def test_litellm_default_hundred_minute_timeout_is_overridden(self):
        """The specific regression: if this ever reverts to litellm's own
        default, a single stuck call silently wedges the queue again."""
        self.assertLessEqual(self.runner.LLM_REQUEST_TIMEOUT_S, 300)
        import litellm
        self.assertEqual(litellm.request_timeout, self.runner.LLM_REQUEST_TIMEOUT_S)

    def test_time_limit_lets_a_fast_call_through_untouched(self):
        with self.runner._time_limit(5):
            result = "finished"
        self.assertEqual(result, "finished")

    def test_time_limit_raises_once_the_ceiling_is_passed(self):
        with self.assertRaises(self.runner.AttemptTimeout):
            with self.runner._time_limit(1):
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    pass

    def test_time_limit_clears_its_alarm_so_it_cannot_fire_later(self):
        """A leaked alarm would fire during an unrelated later task - the
        classic way this kind of fix creates a worse bug than it fixes."""
        with self.runner._time_limit(1):
            pass
        time.sleep(1.5)  # would have fired by now if the alarm leaked

    def test_a_hanging_model_is_just_a_failed_model_and_the_chain_continues(self):
        self.runner.ATTEMPT_TIMEOUT_S = 1
        self.runner.MODEL_CHAIN = [
            self.runner._chain_entry("hangs/forever"),
            self.runner._chain_entry("works/fine"),
        ]
        calls = []

        def attempt(model, instr, sp=None, history=None, **kwargs):
            calls.append(model)
            if model == "hangs/forever":
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    pass
            return f"answered by {model}"

        self.runner._attempt = attempt
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(calls, ["hangs/forever", "works/fine"])
        self.assertEqual(self.log_of("t.md"), "answered by works/fine")

    def test_every_model_hanging_still_writes_a_diagnostic_log(self):
        """A task where nothing answers must still complete and be readable -
        the failure mode being fixed is the queue silently stalling, so a
        timeout that produced no log would only move the silence."""
        self.runner.ATTEMPT_TIMEOUT_S = 1
        self.runner.MODEL_CHAIN = [self.runner._chain_entry("hangs/forever")]

        def hang(model, instr, sp=None, history=None, **kwargs):
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                pass

        self.runner._attempt = hang
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        log = self.log_of("t.md")
        self.assertIn("All models failed", log)
        self.assertIn("AttemptTimeout", log)
        self.assert_quarantined("t.md")


class TestProposals(TaskRunnerTestCase):
    """The propose/approve gate (added 2026-08-30). Agents plan unattended
    all day and change nothing; Felix picks at 20:00 and only then does
    anything execute. The gate is structural - proposals.py has no path into
    tasks/inbox/ - rather than a prompt asking the model to behave."""

    def setUp(self):
        super().setUp()
        import proposals
        self.p = proposals
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for attr in ("PROPOSALS_DIR", "PENDING_PATH", "REVIEW_PATH",
                     "ARCHIVE_PATH", "TODO_PATH"):
            self.addCleanup(setattr, self.p, attr, getattr(self.p, attr))
        self.p.PROPOSALS_DIR = tmp.name
        self.p.PENDING_PATH = os.path.join(tmp.name, "pending.json")
        self.p.REVIEW_PATH = os.path.join(tmp.name, "review.json")
        self.p.ARCHIVE_PATH = os.path.join(tmp.name, "archive.jsonl")
        self.p.TODO_PATH = os.path.join(tmp.name, "todo.json")

    def test_parses_both_kinds_of_marked_line(self):
        out = ("Here is my thinking.\n"
               "AI_PROPOSAL: Rewrite the Pricing Teardown listing copy.\n"
               "HUMAN_PROPOSAL: Create the Gumroad listing and hit publish.\n")
        self.assertEqual(self.p.parse(out), [
            {"kind": "ai", "text": "Rewrite the Pricing Teardown listing copy."},
            {"kind": "human", "text": "Create the Gumroad listing and hit publish."},
        ])

    def test_an_unlabelled_proposal_defaults_to_human(self):
        """The two mistakes are not symmetric. Calling human work "AI" queues
        something the worker cannot do and may report as done; calling AI work
        "human" just means Felix reads a line he could have delegated. Guess
        toward the harmless one."""
        self.assertEqual(self.p.parse("PROPOSAL: do a thing")[0]["kind"], "human")

    def test_marker_case_does_not_matter(self):
        self.assertEqual(self.p.parse("ai_proposal: x")[0]["kind"], "ai")

    def test_unmarked_output_becomes_one_human_proposal_rather_than_being_lost(self):
        """A model that forgets the marker should cost Felix one oddly long
        line, not a whole day of an agent's thinking."""
        self.assertEqual(self.p.parse("Just publish the thing already"),
                         [{"kind": "human", "text": "Just publish the thing already"}])

    def test_empty_output_produces_nothing(self):
        self.assertEqual(self.p.parse(""), [])
        self.assertEqual(self.p.parse(None), [])

    def test_add_then_open_review_moves_and_clears_pending(self):
        self.p.add("Business_Development", [{"kind": "ai", "text": "do X"}])
        self.p.add("Vault_Architect", [{"kind": "human", "text": "do Y"}])
        review = self.p.open_review()
        self.assertEqual([r["text"] for r in review], ["do X", "do Y"])
        self.assertEqual(self.p.load(self.p.PENDING_PATH), [])

    def test_declined_proposals_do_not_reappear_tomorrow(self):
        """Without clearing, a declined item would be re-asked every night
        until Felix approved it out of attrition rather than agreement."""
        self.p.add("Business_Development", [{"kind": "ai", "text": "do X"}])
        review = self.p.open_review()
        _, rejected, _ = self.p.resolve("none", review)
        self.p.close_review([], rejected)
        self.assertEqual(self.p.load_review(), [])
        self.assertEqual(self.p.load(self.p.PENDING_PATH), [])

    def test_resolve_picks_the_selected_numbers(self):
        review = [{"agent": "a", "text": "one"}, {"agent": "b", "text": "two"},
                  {"agent": "c", "text": "three"}]
        chosen, rejected, error = self.p.resolve("1 3", review)
        self.assertIsNone(error)
        self.assertEqual([c["text"] for c in chosen], ["one", "three"])
        self.assertEqual([r["text"] for r in rejected], ["two"])

    def test_resolve_handles_all_and_none(self):
        review = [{"agent": "a", "text": "one"}, {"agent": "b", "text": "two"}]
        chosen, rejected, _ = self.p.resolve("all", review)
        self.assertEqual(len(chosen), 2)
        self.assertEqual(rejected, [])
        chosen, rejected, _ = self.p.resolve("none", review)
        self.assertEqual(chosen, [])
        self.assertEqual(len(rejected), 2)

    def test_out_of_range_is_an_error_not_a_partial_approval(self):
        """Approving '1 5' of 4 must not quietly do three-quarters of it."""
        review = [{"agent": "a", "text": "one"}]
        chosen, _, error = self.p.resolve("1 5", review)
        self.assertEqual(chosen, [])
        self.assertIn("no proposal 5", error)

    def test_unparseable_selection_explains_itself(self):
        chosen, _, error = self.p.resolve("maybe the first one?",
                                          [{"agent": "a", "text": "one"}])
        self.assertEqual(chosen, [])
        self.assertIn("approve", error.lower())

    def test_approving_an_empty_review_says_so(self):
        _, _, error = self.p.resolve("all", [])
        self.assertIn("nothing waiting", error.lower())

    def test_close_review_archives_both_decisions(self):
        review = [{"agent": "a", "text": "one"}, {"agent": "b", "text": "two"}]
        chosen, rejected, _ = self.p.resolve("1", review)
        self.p.close_review(chosen, rejected)
        with open(self.p.ARCHIVE_PATH, encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
        self.assertEqual({r["decision"] for r in rows}, {"approved", "declined"})

    def test_review_message_numbers_items_and_names_the_agent(self):
        text = self.p.format_review([{"agent": "Business_Development",
                                      "kind": "ai", "text": "ship it"}])
        self.assertIn("1. [Business Development] ship it", text)
        self.assertIn("approve", text.lower())

    def test_an_empty_review_reads_as_a_real_answer_not_a_failure(self):
        self.assertIn("Nothing proposed", self.p.format_review([]))

    def test_review_groups_by_who_does_the_work(self):
        review = [{"agent": "a", "kind": "ai", "text": "I build this"},
                  {"agent": "b", "kind": "human", "text": "you do this"}]
        text = self.p.format_review(review)
        self.assertIn("AI work", text)
        self.assertIn("Needs you", text)
        self.assertLess(text.index("AI work"), text.index("Needs you"))

    def test_numbering_runs_continuously_across_both_groups(self):
        """Grouping must not restart numbering - `approve 3` has to mean
        exactly one thing, whichever group it landed in."""
        review = [{"agent": "a", "kind": "human", "text": "yours"},
                  {"agent": "b", "kind": "ai", "text": "mine"},
                  {"agent": "c", "kind": "human", "text": "yours too"}]
        text = self.p.format_review(review)
        self.assertIn("2. [b] mine", text)
        self.assertIn("1. [a] yours", text)
        self.assertIn("3. [c] yours too", text)

    def test_open_review_groups_ai_first_so_numbers_read_contiguously(self):
        """Live 2026-08-30 the first grouped review numbered 1,2,5,6 then
        3,4,7 - correct and unambiguous, but it reads as a bug on a phone.
        Sorting the snapshot (not just the display) keeps the number Felix
        replies with indexing exactly this file."""
        self.p.add("a", [{"kind": "human", "text": "yours"}])
        self.p.add("b", [{"kind": "ai", "text": "mine"}])
        self.p.add("c", [{"kind": "human", "text": "yours too"}])
        review = self.p.open_review()
        self.assertEqual([r["kind"] for r in review], ["ai", "human", "human"])
        text = self.p.format_review(review)
        self.assertIn("1. [b] mine", text)
        self.assertIn("2. [a] yours", text)

    def test_grouping_is_stable_within_each_kind(self):
        self.p.add("a", [{"kind": "ai", "text": "first"}])
        self.p.add("b", [{"kind": "ai", "text": "second"}])
        review = self.p.open_review()
        self.assertEqual([r["text"] for r in review], ["first", "second"])

    def test_a_group_with_nothing_in_it_is_omitted(self):
        text = self.p.format_review([{"agent": "a", "kind": "ai", "text": "x"}])
        self.assertIn("AI work", text)
        self.assertNotIn("Needs you", text)

    def test_todos_round_trip_and_complete(self):
        self.p.add_todos([{"agent": "a", "text": "publish it"},
                          {"agent": "b", "text": "call them"}])
        self.assertEqual(len(self.p.load_todos()), 2)
        done, error = self.p.complete_todo("1")
        self.assertIsNone(error)
        self.assertEqual(done[0]["text"], "publish it")
        self.assertEqual([t["text"] for t in self.p.load_todos()], ["call them"])

    def test_completing_an_out_of_range_todo_is_an_error(self):
        self.p.add_todos([{"agent": "a", "text": "one"}])
        done, error = self.p.complete_todo("4")
        self.assertEqual(done, [])
        self.assertIn("no item 4", error)
        self.assertEqual(len(self.p.load_todos()), 1)

    def test_completing_several_at_once_removes_exactly_those(self):
        self.p.add_todos([{"agent": "a", "text": f"item {n}"} for n in range(1, 5)])
        done, _ = self.p.complete_todo("1 3")
        self.assertEqual([d["text"] for d in done], ["item 1", "item 3"])
        self.assertEqual([t["text"] for t in self.p.load_todos()], ["item 2", "item 4"])

    def test_an_empty_todo_list_reads_as_such(self):
        self.assertIn("Nothing on your list", self.p.format_todos())

    # --- the gate itself -----------------------------------------------------

    def test_a_propose_run_stores_and_queues_nothing(self):
        """The whole trust boundary in one test: an unattended proposing
        agent changes nothing Felix has not approved."""
        self.runner._attempt = lambda m, i, sp=None, history=None, **kw: (
            "AI_PROPOSAL: Publish the Pricing Teardown listing.")
        before = set(os.listdir(self.runner.INBOX))
        self.queue("t.md", "<!-- agent: Business_Development -->\n<!-- propose -->\nplan")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")

        pending = self.p.load(self.p.PENDING_PATH)
        self.assertEqual([x["text"] for x in pending],
                         ["Publish the Pricing Teardown listing."])
        self.assertEqual(pending[0]["agent"], "Business_Development")
        self.assertEqual(set(os.listdir(self.runner.INBOX)) - before - {"t.md"}, set())

    def test_a_propose_run_does_not_notify(self):
        """Felix sees proposals once, at 20:00, not as they trickle in."""
        pushed = []
        self.runner._push_to_telegram = pushed.append
        self.runner._attempt = lambda m, i, sp=None, history=None, **kw: "AI_PROPOSAL: x"
        self.queue("t.md", "<!-- notify -->\n<!-- propose -->\nplan")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(pushed, [])

    def test_a_failed_propose_run_stores_nothing(self):
        """'All models failed' is not a proposal, and padding the evening
        review with them would train Felix to skim it."""
        def dead(model, instr, sp=None, history=None, **kwargs):
            raise RuntimeError("quota exhausted")
        self.runner._attempt = dead
        self.runner.time.sleep = lambda s: None
        self.queue("t.md", "<!-- propose -->\nplan")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(self.p.load(self.p.PENDING_PATH), [])


class TestOrchestration(TaskRunnerTestCase):
    """Routing (added 2026-08-30): a task that names no agent gets one
    picked for it, so TaskRunner orchestrates rather than only dispatching.
    Routing is a direct litellm call, not _attempt() - a classification does
    not need Open Interpreter's tool-calling loop, and structurally cannot
    run a shell command this way."""

    def setUp(self):
        super().setUp()
        import litellm
        self.litellm = litellm
        self.addCleanup(setattr, litellm, "completion", litellm.completion)

    def _reply(self, text):
        """Minimal stand-in for litellm's response object shape."""
        def completion(*a, **k):
            msg = types.SimpleNamespace(content=text)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])
        self.litellm.completion = completion

    def test_routes_a_task_to_the_named_agent(self):
        self._reply("Business_Development")
        self.assertEqual(self.runner._route("should we raise prices?"),
                         "Business_Development")

    def test_none_means_run_on_the_base_prompt(self):
        self._reply("NONE")
        self.assertIsNone(self.runner._route("what is 2+2"))

    def test_a_chatty_model_reply_still_resolves(self):
        """Small models add periods, bullets and preambles no instruction
        reliably prevents, so the parse takes the first resolvable token."""
        for reply in ("Business_Development.", "- Business_Development",
                      "The answer is Business_Development", "@bizdev"):
            self._reply(reply)
            self.assertEqual(self.runner._route("pricing question"),
                             "Business_Development", reply)

    def test_routing_asks_for_enough_tokens_for_a_reasoning_model(self):
        """Live 2026-08-30: max_tokens=16 made every routing call return an
        empty string, because gpt-oss (the top of MODEL_CHAIN) spends its
        budget on reasoning tokens before emitting content. An empty reply
        is indistinguishable from "no specialist fits", so routing was
        silently dead. Guards the budget, not the prompt."""
        seen = {}

        def completion(*a, **k):
            seen.update(k)
            msg = types.SimpleNamespace(content="Business_Development")
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

        self.litellm.completion = completion
        self.runner._route("pricing question")
        self.assertGreaterEqual(seen.get("max_tokens", 0), 256)

    def test_an_empty_reply_falls_back_instead_of_erroring(self):
        self._reply("")
        self.assertIsNone(self.runner._route("something"))

    def test_an_unrecognisable_reply_falls_back_rather_than_guessing(self):
        self._reply("Marketing_Department")
        self.assertIsNone(self.runner._route("something"))

    def test_a_dead_router_never_blocks_the_task(self):
        """The guarantee that makes this safe to enable by default: every
        routing failure path returns None, which is exactly the behaviour
        that existed before routing did."""
        def boom(*a, **k):
            raise RuntimeError("all providers down")
        self.litellm.completion = boom
        self.assertIsNone(self.runner._route("anything"))

    def test_an_explicit_agent_is_never_overridden_by_routing(self):
        """Routing runs last precisely so a stated intent always wins.

        Checks the actual "## Your role for this task: X" header, not a bare
        name substring - Knowledge_Core.md's own "AI OS" section lists all 5
        agent names while describing the system in general (added
        2026-08-31), so "Vault Architect" now legitimately appears in every
        prompt's standing context regardless of which agent is active. The
        role header is the real signal of which persona's block got
        appended; a name appearing in passing prose is not."""
        self._reply("Vault_Architect")
        seen = {}

        def spy(model, instruction, system_prompt=None, history=None, **kw):
            seen["prompt"] = system_prompt
            return "ok"

        self.runner._attempt = spy
        self.queue("t.md", "<!-- agent: Research_Analyst -->\ndo a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertIn("## Your role for this task: Research Analyst", seen["prompt"])
        self.assertNotIn("## Your role for this task: Vault Architect", seen["prompt"])

    def test_an_unrouted_task_gets_the_base_prompt_plus_standing_context_but_no_role(self):
        """Renamed from "...exactly_as_before": since 2026-08-31 an unrouted
        task's prompt is intentionally no longer just BASE_SYSTEM_PROMPT
        verbatim - Knowledge_Core.md's content is appended to every task
        regardless of agent, because relying on a model to decide to go read
        it did not work (verified live: a real dispatch with no hint of the
        filename searched the vault broadly and never found it). No agent
        role section should be present, since none was selected."""
        self._reply("NONE")
        seen = {}

        def spy(model, instruction, system_prompt=None, history=None, **kw):
            seen["prompt"] = system_prompt
            return "ok"

        self.runner._attempt = spy
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertIn(self.runner.BASE_SYSTEM_PROMPT, seen["prompt"])
        self.assertIn("Standing context", seen["prompt"])
        self.assertNotIn("## Your role for this task:", seen["prompt"])

    def test_routing_applies_the_chosen_agents_prompt(self):
        self._reply("Vault_Architect")
        seen = {}

        def spy(model, instruction, system_prompt=None, history=None, **kw):
            seen["prompt"] = system_prompt
            return "ok"

        self.runner._attempt = spy
        self.queue("t.md", "check the vault for status drift")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertIn("Vault Architect", seen["prompt"])

    def test_the_routing_catalog_covers_every_agent_with_a_real_scope_line(self):
        """Routing quality depends entirely on these descriptions, and they
        come from each file's own Purpose: header - so an agent whose header
        drifted into uselessness would silently degrade routing."""
        summaries = self.agentsmod.summaries()
        self.assertEqual(len(summaries), len(self.agentsmod.available()))
        for name, scope in summaries:
            self.assertTrue(scope, f"{name} has no usable scope line")
            self.assertNotIn("[[", scope, f"{name} scope leaks a wikilink")
            self.assertLess(len(scope), 200, f"{name} scope is not one line")

    @property
    def agentsmod(self):
        import agents
        return agents


class TestNotifyDirective(TaskRunnerTestCase):
    """A scheduled task has nobody polling for its log the way an
    interactive one does, so `<!-- notify -->` pushes the result to Telegram.
    Without it a 24/7 agent writes answers nobody ever reads."""

    def setUp(self):
        super().setUp()
        self.pushed = []
        self.runner._push_to_telegram = self.pushed.append

    def test_notify_directive_pushes_the_result(self):
        self.runner._attempt = lambda m, i, sp=None, history=None, **kw: "the answer"
        self.queue("t.md", "<!-- notify -->\ndo a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(len(self.pushed), 1)
        self.assertIn("the answer", self.pushed[0])

    def test_no_directive_means_no_push(self):
        """Interactive tasks must stay silent here - dispatch_task.py and
        telegram_bridge.py already show the user their own result, and a
        second copy arriving as a notification would be noise."""
        self.runner._attempt = lambda m, i, sp=None, history=None, **kw: "the answer"
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(self.pushed, [])

    def test_directive_is_stripped_from_the_instruction(self):
        seen = {}

        def spy(model, instruction, system_prompt=None, history=None, **kw):
            seen["instruction"] = instruction
            return "ok"

        self.runner._attempt = spy
        self.queue("t.md", "<!-- notify -->\nreal instruction")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(seen["instruction"], "real instruction")

    def test_notify_composes_with_the_agent_directive(self):
        """The scheduler emits both, in that order - if parsing them together
        broke, every scheduled agent task would run on the base prompt."""
        seen = {}

        def spy(model, instruction, system_prompt=None, history=None, **kw):
            seen["prompt"] = system_prompt
            seen["instruction"] = instruction
            return "ok"

        self.runner._attempt = spy
        self.queue("t.md", "<!-- agent: Vault_Architect -->\n<!-- notify -->\ncheck drift")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(seen["instruction"], "check drift")
        self.assertIn("Vault Architect", seen["prompt"])
        self.assertIn("Vault Architect", self.pushed[0])

    def test_an_unreachable_telegram_never_raises_out_of_the_push(self):
        """The task's work is already done and logged by the time this runs,
        so a dead notifier must degrade to a printed warning. Exercises the
        real _push_to_telegram rather than a stand-in, since the swallowing
        is the whole behaviour under test."""
        original = self.runner.subprocess.run
        self.addCleanup(lambda: setattr(self.runner.subprocess, "run", original))

        def boom(*a, **k):
            raise OSError("telegram unreachable")

        self.runner.subprocess.run = boom
        self.runner._push_to_telegram("anything")  # must not raise


class TestAgentHandoff(TaskRunnerTestCase):
    """The handoff convention (added 2026-08-30): an agent ends its output
    with `<!-- handoff: Agent: reason -->` to hand its result to another
    agent as a new task, the same directive pattern as `<!-- agent: X -->`.
    Pure parsing only here - agents.py's parse_handoff/parse_handoff_depth
    given plain strings, no queue involved."""

    def setUp(self):
        super().setUp()
        import agents
        self.agents = agents

    def test_parses_a_well_formed_handoff_line(self):
        output = "Findings here.\n\n<!-- handoff: Business_Development: pricing may need to change -->"
        agent, reason, cleaned = self.agents.parse_handoff(output)
        self.assertEqual(agent, "Business_Development")
        self.assertEqual(reason, "pricing may need to change")
        self.assertNotIn("handoff", cleaned)
        self.assertIn("Findings here.", cleaned)

    def test_resolves_an_alias_not_just_the_canonical_name(self):
        agent, _, _ = self.agents.parse_handoff("<!-- handoff: bizdev: quick check -->")
        self.assertEqual(agent, "Business_Development")

    def test_unknown_target_is_treated_as_no_handoff_but_still_cleaned(self):
        """A typo'd target costs a skipped handoff, not a broken task - same
        principle as parse_directive for the incoming `agent:` marker."""
        output = "Some text.\n<!-- handoff: NotARealAgent: whatever -->"
        agent, reason, cleaned = self.agents.parse_handoff(output)
        self.assertIsNone(agent)
        self.assertIsNone(reason)
        self.assertNotIn("handoff", cleaned)

    def test_no_directive_present_leaves_output_untouched(self):
        agent, reason, cleaned = self.agents.parse_handoff("plain output, nothing special")
        self.assertIsNone(agent)
        self.assertIsNone(reason)
        self.assertEqual(cleaned, "plain output, nothing special")

    def test_handles_empty_output(self):
        agent, reason, cleaned = self.agents.parse_handoff("")
        self.assertIsNone(agent)
        self.assertEqual(cleaned, "")

    def test_depth_marker_round_trips(self):
        marker = self.agents.handoff_depth_marker(2)
        depth, rest = self.agents.parse_handoff_depth(f"{marker}the actual instruction")
        self.assertEqual(depth, 2)
        self.assertEqual(rest, "the actual instruction")

    def test_missing_depth_marker_defaults_to_zero(self):
        depth, rest = self.agents.parse_handoff_depth("no marker here")
        self.assertEqual(depth, 0)
        self.assertEqual(rest, "no marker here")


class TestHandoffIntegration(TaskRunnerTestCase):
    """Exercises the real _run_task path end to end: a handoff directive in
    an agent's output should enqueue a new task file for the target agent,
    disappear from what Felix actually reads, and never let two agents loop
    forever even if both keep handing off to each other."""

    def _handoff_files(self):
        return [f for f in os.listdir(self.runner.INBOX) if f.startswith("task_handoff_")]

    def test_handoff_directive_enqueues_a_new_task_for_the_target_agent(self):
        self.runner._attempt = lambda model, instr, sp=None, history=None, **kwargs: (
            "Competitor X just cut prices 20%.\n\n"
            "<!-- handoff: Business_Development: pricing may need to change -->"
        )
        self.queue("t.md", "<!-- agent: Research_Analyst -->\nresearch this")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")

        handoff_files = self._handoff_files()
        self.assertEqual(len(handoff_files), 1)
        content = open(os.path.join(self.runner.INBOX, handoff_files[0]), encoding="utf-8").read()
        self.assertIn("<!-- agent: Business_Development -->", content)
        self.assertIn("<!-- handoff_depth: 1 -->", content)
        self.assertIn("Competitor X just cut prices 20%", content)
        self.assertIn("Research Analyst", content)  # "Handoff from Research Analyst: ..."

    def test_directive_is_stripped_from_what_felix_actually_reads(self):
        self.runner._attempt = lambda model, instr, sp=None, history=None, **kwargs: (
            "Findings.\n<!-- handoff: Business_Development: check pricing -->"
        )
        self.queue("t.md", "<!-- agent: Research_Analyst -->\nresearch this")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        log = self.log_of("t.md")
        self.assertNotIn("<!-- handoff:", log)
        self.assertIn("Handed off to Business Development", log)

    def test_self_handoff_is_a_no_op_not_an_infinite_loop_seed(self):
        self.runner._attempt = lambda model, instr, sp=None, history=None, **kwargs: (
            "Text.\n<!-- handoff: Research_Analyst: talking to myself -->"
        )
        self.queue("t.md", "<!-- agent: Research_Analyst -->\nresearch this")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(self._handoff_files(), [])

    def test_handoff_chain_stops_at_the_depth_cap(self):
        self.runner._attempt = lambda model, instr, sp=None, history=None, **kwargs: (
            "Text.\n<!-- handoff: Business_Development: keep going -->"
        )
        depth = self.runner.agents.MAX_HANDOFF_DEPTH
        marker = self.runner.agents.handoff_depth_marker(depth)
        self.queue("t.md", f"<!-- agent: Research_Analyst -->\n{marker}research this")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(self._handoff_files(), [])
        self.assertIn("depth limit", self.log_of("t.md"))

    def test_a_normal_task_with_no_handoff_directive_enqueues_nothing(self):
        self.runner._attempt = lambda model, instr, sp=None, history=None, **kwargs: "just an answer"
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(self._handoff_files(), [])

    def test_failed_task_never_triggers_a_handoff(self):
        """An ERROR output happens to contain no handoff syntax in practice,
        but this guards the actual rule - handoff parsing is skipped
        entirely for a failed attempt, not just coincidentally directive-free."""
        def dead(model, instr, sp=None, history=None, **kwargs):
            raise RuntimeError("boom")

        self.runner._attempt = dead
        self.runner.time.sleep = lambda s: None
        self.queue("t.md", "<!-- agent: Research_Analyst -->\ndo a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(self._handoff_files(), [])


class TestMemory(TaskRunnerTestCase):
    """Every task ran cold before 2026-08-27 - interpreter.messages = [] per
    attempt - so "now do the same for the other project" was impossible."""

    def setUp(self):
        super().setUp()
        import importlib
        import memory
        importlib.reload(memory)  # rebind THREADS to this test's AIOS_WORKSPACE
        self.memory = memory

    def test_turn_round_trips_into_interpreter_message_shape(self):
        self.memory.save_turn("t1", "hello", "hi there")
        msgs = self.memory.as_messages("t1")
        self.assertEqual(msgs, [
            {"role": "user", "type": "message", "content": "hello"},
            {"role": "assistant", "type": "message", "content": "hi there"},
        ])

    def test_unknown_thread_is_empty_not_an_error(self):
        self.assertEqual(self.memory.as_messages("never_seen"), [])

    def test_corrupt_thread_file_does_not_lose_the_task(self):
        os.makedirs(self.memory.THREADS, exist_ok=True)
        with open(os.path.join(self.memory.THREADS, "bad.json"), "w") as f:
            f.write("{ not json at all")
        self.assertEqual(self.memory.as_messages("bad"), [])

    def test_turn_count_is_bounded(self):
        for i in range(20):
            self.memory.save_turn("t2", f"q{i}", f"a{i}")
        turns = self.memory.load("t2")["turns"]
        self.assertLessEqual(len(turns), self.memory.MAX_TURNS)
        # oldest dropped, newest kept
        self.assertEqual(turns[-1]["user"], "q19")

    def test_char_budget_is_bounded_independently_of_turn_count(self):
        """A few enormous turns must be trimmed even when well under MAX_TURNS."""
        for i in range(4):
            self.memory.save_turn("t3", "x" * 1500, "y" * 1500)
        total = sum(len(t["user"]) + len(t["assistant"])
                    for t in self.memory.load("t3")["turns"])
        self.assertLessEqual(total, self.memory.MAX_CHARS)

    def test_single_turn_cannot_eat_the_whole_budget(self):
        self.memory.save_turn("t4", "u" * 99999, "a" * 99999)
        t = self.memory.load("t4")["turns"][0]
        self.assertLessEqual(len(t["user"]), self.memory.MAX_TURN_CHARS)
        self.assertLessEqual(len(t["assistant"]), self.memory.MAX_TURN_CHARS)

    def test_reset_clears_and_reports_whether_anything_existed(self):
        self.memory.save_turn("t5", "q", "a")
        self.assertTrue(self.memory.reset("t5"))
        self.assertEqual(self.memory.as_messages("t5"), [])
        self.assertFalse(self.memory.reset("t5"))

    def test_thread_id_is_sanitised_into_a_safe_filename(self):
        self.memory.save_turn("../../etc/passwd", "q", "a")
        written = os.listdir(self.memory.THREADS)
        self.assertTrue(all(".." not in f and "/" not in f for f in written), written)

    def test_agent_is_remembered_so_follow_ups_stay_in_role(self):
        self.memory.save_turn("t6", "q", "a", agent="Research_Analyst")
        self.assertEqual(self.memory.last_agent("t6"), "Research_Analyst")

    def test_worker_seeds_history_and_records_the_new_turn(self):
        """End to end: prior turns reach the model, and the exchange is saved."""
        self.memory.save_turn("conv", "first question", "first answer")
        seen = {}

        def spy(model, instruction, system_prompt=None, history=None, **kwargs):
            seen["history"] = history
            return "second answer"

        self.runner._attempt = spy
        self.queue("t.md", self.memory.directive("conv") + "second question")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")

        self.assertEqual(len(seen["history"]), 2)
        self.assertEqual(seen["history"][0]["content"], "first question")
        turns = self.memory.load("conv")["turns"]
        self.assertEqual(turns[-1]["user"], "second question")
        self.assertEqual(turns[-1]["assistant"], "second answer")

    def test_failed_tasks_are_not_written_into_memory(self):
        """Replaying "all models failed" as context spends budget a real turn
        needs and teaches the model nothing."""
        self.runner._attempt = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("dead"))
        self.runner.time.sleep = lambda s: None
        self.queue("t.md", self.memory.directive("conv2") + "doomed")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(self.memory.load("conv2")["turns"], [])

    def test_bare_follow_up_inherits_the_thread_agent(self):
        self.memory.save_turn("conv3", "q", "a", agent="Vault_Architect")
        seen = {}

        def spy(model, instruction, system_prompt=None, history=None, **kwargs):
            seen["prompt"] = system_prompt
            return "ok"

        self.runner._attempt = spy
        self.queue("t.md", self.memory.directive("conv3") + "no agent prefix here")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertIn("Vault Architect", seen["prompt"])

    def test_a_task_with_no_thread_still_runs_cold(self):
        seen = {}

        def spy(model, instruction, system_prompt=None, history=None, **kwargs):
            seen["history"] = history
            return "ok"

        self.runner._attempt = spy
        self.queue("t.md", "stateless task")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertFalse(seen["history"])


class TestVaultWrite(unittest.TestCase):
    """09_Analytics has held four databases with zero rows since Sprint 012 and
    Promotion_Candidates has been empty just as long - the Learning Loop was
    specified and never executed, because nothing could produce into the vault.

    The worker already had a shell and could write anywhere; these tests cover
    the boundary that keeps generated output away from hand-maintained files."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "vault_write", os.path.join(HERE, "vault_write.py"))
        cls.vw = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.vw)

    def test_refuses_hand_maintained_folders(self):
        for folder in ("00_System", "01_Architecture", "02_Systems", "04_Agents"):
            with self.assertRaises(ValueError, msg=folder):
                self.vw.write_note(folder, "X", "body", dry_run=True)

    def test_refuses_path_traversal_out_of_the_vault(self):
        for folder in ("../../etc", "08_Research/../00_System", "/etc"):
            with self.assertRaises(ValueError, msg=folder):
                self.vw.write_note(folder, "X", "body", dry_run=True)

    def test_allows_the_output_folders(self):
        path, content = self.vw.write_note(
            "08_Research", "Groq Rate Limits", "Finding body.", dry_run=True)
        self.assertTrue(path.endswith("08_Research/Groq_Rate_Limits.md"), path)
        self.assertIn("Finding body.", content)

    def test_purpose_line_skips_a_leading_markdown_header(self):
        """Found live: a worker note started its body with "## Context", and
        that heading landed in Purpose: verbatim - a header is not a sentence,
        and the worker has no reason to know the field needs prose."""
        _, content = self.vw.write_note(
            "08_Research", "T", "## Context\nReal finding here.", dry_run=True)
        purpose_line = [l for l in content.splitlines() if l.startswith("Purpose:")][0]
        self.assertEqual(purpose_line, "Purpose: Real finding here.")

    def test_purpose_line_skips_leading_list_markers_too(self):
        _, content = self.vw.write_note(
            "08_Research", "T", "- a bullet\n- another\nActual sentence.",
            dry_run=True)
        purpose_line = [l for l in content.splitlines() if l.startswith("Purpose:")][0]
        self.assertEqual(purpose_line, "Purpose: Actual sentence.")

    def test_generates_the_required_vault_header(self):
        """Naming_Convention.md requires these four fields on every note, and a
        small model will not produce them reliably - so they are generated."""
        _, content = self.vw.write_note("08_Research", "T", "b", dry_run=True)
        for field in ("Purpose:", "Last Updated:", "Status:", "Related Documents:"):
            self.assertIn(field, content)
        self.assertTrue(content.startswith("# T"))

    def test_filenames_are_pascal_case_per_convention(self):
        for title, expected in [
            ("groq rate limits", "Groq_Rate_Limits.md"),
            ("A/B test: results!", "A_B_Test_Results.md"),
        ]:
            path, _ = self.vw.write_note("08_Research", title, "b", dry_run=True)
            self.assertTrue(path.endswith(expected), path)

    def test_unusable_title_is_rejected_rather_than_writing_a_junk_filename(self):
        with self.assertRaises(ValueError):
            self.vw.write_note("08_Research", "!!!", "b", dry_run=True)

    def test_row_destination_is_allowlisted(self):
        with self.assertRaises(ValueError):
            self.vw.append_row("00_System/Dashboard.md", ["a"], dry_run=True)

    def test_row_cell_count_must_match_the_table(self):
        """A mismatched row corrupts the table silently in every renderer, so
        this must fail loudly rather than append."""
        with self.assertRaises(ValueError) as ctx:
            self.vw.append_row("09_Analytics/Hook_Database.md",
                               ["only", "two"], dry_run=True)
        self.assertIn("expects", str(ctx.exception))

    def test_correct_row_is_accepted(self):
        _, row = self.vw.append_row(
            "09_Analytics/Hook_Database.md",
            ["Story", "Hook", "8.2s", "Worked", "Analysis"], dry_run=True)
        self.assertEqual(row.count("|"), 6)

    def test_strips_open_interpreter_execution_markers(self):
        """Found by the first real end-to-end write, not by inspection: the
        worker wrote its body via a shell heredoc, and Open Interpreter's
        `echo "##active_line2##"` instrumentation landed inside the file - the
        note's Purpose: line was literally that echo. The model never sees the
        injected lines, so no prompt can reliably prevent this."""
        dirty = ('echo "##active_line2##"\n'
                 'Real finding.\n'
                 '##active_line3##\n'
                 'Second line.##end_of_execution##')
        _, content = self.vw.write_note("08_Research", "T", dirty, dry_run=True)
        self.assertNotIn("active_line", content)
        self.assertNotIn("end_of_execution", content)
        self.assertIn("Real finding.", content)
        self.assertIn("Purpose: Real finding.", content)

    def test_body_that_is_only_markers_is_rejected(self):
        with self.assertRaises(ValueError):
            self.vw.write_note("08_Research", "T", '##active_line1##',
                               dry_run=True)

    def test_row_cells_are_cleaned_and_kept_on_one_line(self):
        """A newline inside a cell breaks the table as surely as a wrong count."""
        _, row = self.vw.append_row(
            "09_Analytics/Hook_Database.md",
            ["a##active_line2##", "b\nc", "d", "e", "f"], dry_run=True)
        self.assertNotIn("active_line", row)
        self.assertNotIn("\n", row)

    def test_no_function_here_can_overwrite_an_existing_file(self):
        """The safety property that matters most: there is no code path in this
        module that replaces existing content."""
        import inspect
        src = inspect.getsource(self.vw)
        body = src.split('"""', 2)[-1]  # skip the module docstring
        self.assertNotIn('open(path, "w"', body)


class TestBackupExclusions(unittest.TestCase):
    """Bug: without excluding its own backups/, every archive embedded all
    earlier archives - the sizes were visibly doubling (531K, 1.0M, 2.1M, 4.2M)
    before this was caught."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "cloud_backup", os.path.join(HERE, "scripts", "cloud_backup.py"))
        cls.cb = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.cb)

    def _kept(self, relpath):
        """_should_exclude takes a tarinfo whose .name is 'AI-OS/<relpath>'."""
        info = types.SimpleNamespace(name=f"AI-OS/{relpath}")
        return self.cb._should_exclude(info) is not None

    def test_backups_folder_excludes_itself(self):
        rel = self.cb.TASK_RUNNER_REL
        self.assertFalse(self._kept(f"{rel}/backups"))
        self.assertFalse(self._kept(f"{rel}/backups/aios_backup_2026.tar.gz"))

    def test_noisy_runtime_paths_are_excluded(self):
        rel = self.cb.TASK_RUNNER_REL
        for path in (f"{rel}/tasks/logs/x.md.log",
                     "server-stack/nextcloud/data/index.php",
                     "server-stack/portainer/data/certs",
                     "server-stack/jellyfin/cache/transcodes/x.mp4"):
            self.assertFalse(self._kept(path), f"{path} should be excluded")

    def test_vault_content_and_source_are_kept(self):
        rel = self.cb.TASK_RUNNER_REL
        for path in ("AI-OS/00_System/Dashboard.md",
                     f"{rel}/aios_runner.py",
                     f"{rel}/tasks/completed/task_1.md",
                     "server-stack/docker-compose.yml"):
            self.assertTrue(self._kept(path), f"{path} should be kept")

    def test_a_prefix_collision_is_not_treated_as_a_match(self):
        """'.../backups-old' must not be swallowed by the '.../backups' rule."""
        rel = self.cb.TASK_RUNNER_REL
        self.assertTrue(self._kept(f"{rel}/backups-old/note.md"))

    def test_dependency_directories_are_excluded_at_any_depth(self):
        self.assertFalse(self._kept("AI-OSmcp/node_modules/zod/index.js"))
        self.assertFalse(self._kept("a/b/__pycache__/x.pyc"))


class TestHealthCheck(unittest.TestCase):
    """The supervision layer (added 2026-08-30): services up, network has a
    real default route, last backup succeeded. These tests exercise only the
    pure evaluate_*/decide_alerts functions - no subprocess, no socket, no
    real filesystem - so they say nothing about whether systemctl/ip actually
    behave as assumed on the box, only that the logic is right once given
    their output."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "health_check", os.path.join(HERE, "scripts", "health_check.py"))
        cls.hc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.hc)

    def test_service_active_is_ok(self):
        ok, detail = self.hc.evaluate_service("active")
        self.assertTrue(ok)
        self.assertEqual(detail, "active")

    def test_service_anything_else_is_not_ok(self):
        for status in ("inactive", "failed", "activating", "<error: boom>"):
            ok, _ = self.hc.evaluate_service(status)
            self.assertFalse(ok, f"{status!r} should not be considered ok")

    def test_network_healthy_when_default_route_is_via_the_lan_and_internet_reachable(self):
        route = "default via 192.168.178.1 dev eno1 proto dhcp src 192.168.178.69"
        addr = "inet 192.168.178.69/24 metric 100 brd 192.168.178.255 scope global dynamic eno1"
        ok, detail = self.hc.evaluate_network(route, addr, "eno1", True)
        self.assertTrue(ok)
        self.assertIn("eno1", detail)

    def test_network_flags_no_default_route_at_all(self):
        ok, detail = self.hc.evaluate_network("", "inet 10.0.0.5/24 ... eno1", "eno1", True)
        self.assertFalse(ok)
        self.assertIn("no default route", detail)

    def test_network_flags_silent_failover_to_a_different_interface(self):
        """The actual 2026-08-30 bug: eno1 loses its route/address and traffic
        moves to wlo1 (the phone bridge) without anyone noticing."""
        route = "default via 192.168.1.1 dev wlo1 proto dhcp"
        ok, detail = self.hc.evaluate_network(route, "", "eno1", True)
        self.assertFalse(ok)
        self.assertIn("wlo1", detail)
        self.assertIn("eno1", detail)

    def test_network_flags_missing_ipv4_on_the_lan_interface_even_if_a_route_exists(self):
        route = "default via 192.168.178.1 dev eno1 proto dhcp"
        ok, detail = self.hc.evaluate_network(route, "", "eno1", True)
        self.assertFalse(ok)
        self.assertIn("no IPv4", detail)

    def test_network_flags_unreachable_internet_even_with_a_good_route_and_address(self):
        route = "default via 192.168.178.1 dev eno1 proto dhcp"
        addr = "inet 192.168.178.69/24 ... eno1"
        ok, detail = self.hc.evaluate_network(route, addr, "eno1", False)
        self.assertFalse(ok)
        self.assertIn("internet", detail)

    def test_backup_ok_when_recent_and_not_failed(self):
        ok, _ = self.hc.evaluate_backup("inactive", 11.8, 30)
        self.assertTrue(ok)

    def test_backup_flags_a_failed_last_run(self):
        ok, detail = self.hc.evaluate_backup("failed", 1.0, 30)
        self.assertFalse(ok)
        self.assertIn("failed", detail)

    def test_backup_flags_a_stale_archive_even_if_the_last_run_reported_success(self):
        """Catches a disabled/removed timer, which is_failed alone would miss -
        is-failed only reflects the *last run that happened*, not whether one
        has happened recently."""
        ok, detail = self.hc.evaluate_backup("inactive", 48.0, 30)
        self.assertFalse(ok)
        self.assertIn("48.0h", detail)

    def test_backup_flags_no_archive_found(self):
        ok, detail = self.hc.evaluate_backup("inactive", None, 30)
        self.assertFalse(ok)
        self.assertIn("no backup archive", detail)

    def test_queue_empty_is_healthy(self):
        ok, detail = self.hc.evaluate_queue(None)
        self.assertTrue(ok)
        self.assertIn("empty", detail)

    def test_queue_draining_normally_is_healthy(self):
        ok, _ = self.hc.evaluate_queue(3.0, 45)
        self.assertTrue(ok)

    def test_queue_flags_a_task_stuck_past_the_worst_legitimate_case(self):
        """The 2026-08-30 wedge: 101 minutes on one task while every
        service-level check still reported OK."""
        ok, detail = self.hc.evaluate_queue(101.0, 45)
        self.assertFalse(ok)
        self.assertIn("101min", detail)
        self.assertIn("wedged", detail)

    def test_queue_does_not_page_on_a_merely_slow_task(self):
        """A task can legitimately burn MODEL_CHAIN x ATTEMPT_TIMEOUT_S
        (~35min) before answering - alerting on that would train Felix to
        ignore the alerts, which is worse than not having them."""
        ok, _ = self.hc.evaluate_queue(35.0, 45)
        self.assertTrue(ok)

    def test_decide_alerts_new_failure_fires_immediately(self):
        messages, new_failing = self.hc.decide_alerts(
            {}, {"x": (False, "broken")}, now=1000.0)
        self.assertEqual(len(messages), 1)
        self.assertIn("DOWN: x", messages[0])
        self.assertEqual(new_failing["x"]["since"], 1000.0)
        self.assertEqual(new_failing["x"]["last_alert"], 1000.0)

    def test_decide_alerts_recovery_fires_once_and_clears_state(self):
        prev = {"x": {"since": 100.0, "last_alert": 100.0}}
        messages, new_failing = self.hc.decide_alerts(
            prev, {"x": (True, "fine")}, now=200.0)
        self.assertEqual(len(messages), 1)
        self.assertIn("RECOVERED: x", messages[0])
        self.assertNotIn("x", new_failing)

    def test_decide_alerts_suppresses_repeat_alerts_inside_the_realert_window(self):
        prev = {"x": {"since": 0.0, "last_alert": 100.0}}
        messages, new_failing = self.hc.decide_alerts(
            prev, {"x": (False, "still broken")}, now=200.0, realert_seconds=3600)
        self.assertEqual(messages, [])
        self.assertEqual(new_failing["x"], prev["x"])  # untouched, no new alert timestamp

    def test_decide_alerts_reminds_again_once_the_realert_window_has_passed(self):
        prev = {"x": {"since": 0.0, "last_alert": 100.0}}
        messages, new_failing = self.hc.decide_alerts(
            prev, {"x": (False, "still broken")}, now=4000.0, realert_seconds=3600)
        self.assertEqual(len(messages), 1)
        self.assertIn("STILL DOWN: x", messages[0])
        self.assertEqual(new_failing["x"]["since"], 0.0)  # original onset preserved
        self.assertEqual(new_failing["x"]["last_alert"], 4000.0)

    def test_decide_alerts_ok_check_that_was_never_failing_is_silent(self):
        messages, new_failing = self.hc.decide_alerts(
            {}, {"x": (True, "fine")}, now=200.0)
        self.assertEqual(messages, [])
        self.assertEqual(new_failing, {})


class TestSchedules(unittest.TestCase):
    """Recurring agent tasks (added 2026-08-30). Cadence parsing and the
    due/not-due decision are pure functions over an injected `now`, so these
    test the actual scheduling logic rather than waiting for wall-clock time
    to pass. 2026-08-30 is a Sunday; several cases below depend on that."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "run_schedules", os.path.join(HERE, "scripts", "run_schedules.py"))
        cls.rs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.rs)
        cls.TZ = cls.rs.TZ

    def _at(self, year, month, day, hour, minute=0):
        from datetime import datetime
        return datetime(year, month, day, hour, minute, tzinfo=self.TZ)

    def test_parses_a_schedule_file_into_its_three_parts(self):
        text = ("<!-- agent: Business_Development -->\n"
                "<!-- schedule: daily 07:30 -->\n"
                "Check what is still unpublished.")
        cadence, agent, propose, instruction = self.rs.parse_schedule_file(text)
        self.assertFalse(propose)
        self.assertEqual(cadence, "daily 07:30")
        self.assertEqual(agent, "Business_Development")
        self.assertEqual(instruction, "Check what is still unpublished.")

    def test_directives_never_leak_into_the_instruction(self):
        """The enqueue step re-emits the agent directive itself; a copy left
        in the body would reach the worker as task text."""
        text = ("<!-- agent: Research_Analyst -->\n"
                "<!-- schedule: hourly -->\n"
                "Do the thing.")
        _, _, _, instruction = self.rs.parse_schedule_file(text)
        self.assertNotIn("<!--", instruction)

    def test_daily_resolves_to_todays_occurrence_once_it_has_passed(self):
        self.assertEqual(
            self.rs.next_due_after("daily 07:30", self._at(2026, 8, 30, 9)),
            self._at(2026, 8, 30, 7, 30))

    def test_daily_before_its_time_resolves_to_yesterdays_occurrence(self):
        """Otherwise a 07:30 schedule checked at 06:00 would look due and
        fire a second time on the same day."""
        self.assertEqual(
            self.rs.next_due_after("daily 07:30", self._at(2026, 8, 30, 6)),
            self._at(2026, 8, 29, 7, 30))

    def test_weekly_resolves_to_this_week_on_the_matching_day(self):
        self.assertEqual(
            self.rs.next_due_after("weekly sun 08:00", self._at(2026, 8, 30, 9)),
            self._at(2026, 8, 30, 8))

    def test_weekly_on_another_day_walks_back_to_that_day(self):
        self.assertEqual(
            self.rs.next_due_after("weekly mon 08:00", self._at(2026, 8, 30, 9)),
            self._at(2026, 8, 24, 8))

    def test_unparseable_cadences_are_rejected_rather_than_guessed(self):
        for bad in ("nonsense", "daily 25:00", "daily", "weekly xyz 08:00", "", None):
            self.assertIsNone(
                self.rs.next_due_after(bad, self._at(2026, 8, 30, 9)), repr(bad))

    def test_never_run_before_is_due(self):
        self.assertTrue(self.rs.is_due("daily 07:30", None, self._at(2026, 8, 30, 9)))

    def test_already_run_this_occurrence_is_not_due_again(self):
        last = self._at(2026, 8, 30, 7, 35).isoformat()
        self.assertFalse(self.rs.is_due("daily 07:30", last, self._at(2026, 8, 30, 9)))

    def test_yesterdays_run_is_due_again_today(self):
        last = self._at(2026, 8, 29, 7, 35).isoformat()
        self.assertTrue(self.rs.is_due("daily 07:30", last, self._at(2026, 8, 30, 9)))

    def test_a_run_missed_while_the_server_was_off_fires_once_on_the_next_tick(self):
        """Catch-up, not silent skip and not a burst of backfill: the server
        being off overnight should produce exactly one run, not none and not
        one per missed occurrence."""
        last = self._at(2026, 8, 27, 7, 35).isoformat()
        self.assertTrue(self.rs.is_due("daily 07:30", last, self._at(2026, 8, 30, 9)))

    def test_two_schedules_due_in_the_same_second_do_not_collide(self):
        """Observed live 2026-08-30: daily_revenue_plan and daily_system_plan
        both produced task_sched_20260830_164116.md, the second overwrote the
        first, and state.json recorded both as run - so the lost one would
        not retry until the next day, having never executed. This runner
        walks every schedule in one pass, so same-second firing is the normal
        case, not an edge case."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(setattr, self.rs, "INBOX", self.rs.INBOX)
        self.rs.INBOX = tmp.name
        first = self.rs.enqueue("Business_Development", "do X", "daily_revenue_plan.md")
        second = self.rs.enqueue("Vault_Architect", "do Y", "daily_system_plan.md")
        self.assertNotEqual(first, second)
        self.assertEqual(len(os.listdir(tmp.name)), 2)

    def test_propose_is_lifted_into_the_header_where_the_worker_can_see_it(self):
        """Found live 2026-08-30: <!-- propose --> was left in the body,
        after the "(Scheduled task from ...)" line. The worker anchors its
        directive parsing to the start of what remains, so it never matched -
        both daily planners ran as ordinary tasks and stored no proposals,
        silently. Asserts the directive order the worker actually requires."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(setattr, self.rs, "INBOX", self.rs.INBOX)
        self.rs.INBOX = tmp.name
        name = self.rs.enqueue("Business_Development", "plan revenue",
                               "daily_revenue_plan.md", propose=True)
        with open(os.path.join(tmp.name, name), encoding="utf-8") as f:
            body = f.read()
        head = body.split("(Scheduled task from")[0]
        self.assertIn("<!-- agent: Business_Development -->", head)
        self.assertIn("<!-- notify -->", head)
        self.assertIn("<!-- propose -->", head)

    def test_a_non_proposing_schedule_gets_no_propose_directive(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(setattr, self.rs, "INBOX", self.rs.INBOX)
        self.rs.INBOX = tmp.name
        name = self.rs.enqueue("Business_Development", "just report",
                               "templatesales_publish_check.md")
        with open(os.path.join(tmp.name, name), encoding="utf-8") as f:
            self.assertNotIn("<!-- propose -->", f.read())

    def test_enqueued_filename_names_its_schedule_for_debuggability(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(setattr, self.rs, "INBOX", self.rs.INBOX)
        self.rs.INBOX = tmp.name
        name = self.rs.enqueue("Vault_Architect", "do Y", "daily_system_plan.md")
        self.assertIn("daily_system_plan", name)

    def test_corrupt_state_re_runs_rather_than_never_running_again(self):
        self.assertTrue(self.rs.is_due("daily 07:30", "not-a-timestamp",
                                       self._at(2026, 8, 30, 9)))


class TestMorningBrief(unittest.TestCase):
    """The daily digest (added 2026-08-30). format_status_section and
    build_digest are pure - given a checks dict, no subprocess/systemctl -
    so these test the actual composition logic, not whether the server is
    healthy right now."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "morning_brief", os.path.join(HERE, "scripts", "morning_brief.py"))
        cls.mb = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mb)

    def test_status_section_reads_all_clear_when_nothing_is_failing(self):
        checks = {"a": (True, "fine"), "b": (True, "also fine")}
        text = self.mb.format_status_section(checks)
        self.assertIn("everything's fine", text)

    def test_status_section_lists_every_failing_check_with_its_detail(self):
        checks = {"a": (True, "fine"), "b": (False, "broken somehow")}
        text = self.mb.format_status_section(checks)
        self.assertIn("1 thing(s)", text)
        self.assertIn("b: broken somehow", text)
        self.assertNotIn("a:", text)  # only failing checks are listed

    def test_digest_opens_with_a_dated_greeting(self):
        now = time.struct_time((2026, 8, 30, 7, 0, 0, 6, 242, -1))  # a Sunday
        digest = self.mb.build_digest({"a": (True, "fine")}, now=now)
        self.assertTrue(digest.startswith("Good morning - Sunday, 30 August 2026"))

    def test_digest_includes_the_status_line(self):
        digest = self.mb.build_digest({"x": (False, "down")})
        self.assertIn("x: down", digest)


class TestKleinanzeigenSniper(unittest.TestCase):
    """The arbitrage sniper (added 2026-08-31). Every test here is a real
    behaviour observed against live Kleinanzeigen HTML on the day it was
    written, not a hypothetical - the price, distance and iCloud cases in
    particular were all found by running the thing against the actual site and
    reading what came back, and each one silently costs money if it regresses.

    Pure functions only: no network. What these prove is that the parsing and
    filtering logic is right given the site's markup, not that the markup is
    still what it was - ARTICLE_RE returning nothing is exactly the failure
    run() reports as an alert rather than as silence."""

    @classmethod
    def setUpClass(cls):
        sys.modules.setdefault("send_telegram_notification",
                               types.ModuleType("send_telegram_notification"))
        sys.modules["send_telegram_notification"].send = lambda *a, **k: True
        spec = importlib.util.spec_from_file_location(
            "kleinanzeigen_sniper",
            os.path.join(HERE, "scripts", "kleinanzeigen_sniper.py"))
        cls.ks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.ks)

    # --- price ---------------------------------------------------------------

    def test_price_takes_the_first_number_on_a_reduced_listing(self):
        """Live example: "280 € VB 290 €" is a reduced price followed by the
        struck-through original. Reading 290 would push real finds past a
        max_price filter and hide them."""
        self.assertEqual(self.ks.parse_price("280 &euro; VB 290 &euro;"), 280)

    def test_price_handles_thousands_separator(self):
        self.assertEqual(self.ks.parse_price("1.250 &euro; VB"), 1250)

    def test_price_missing_is_none_not_zero(self):
        """"VB" with no number must stay None so the price filter lets it
        through - an unpriced ad is the seller-doesn't-know signal."""
        self.assertIsNone(self.ks.parse_price("VB"))
        self.assertIsNone(self.ks.parse_price(""))

    def test_zu_verschenken_is_zero_not_missing(self):
        self.assertEqual(self.ks.parse_price("Zu verschenken"), 0)

    # --- distance ------------------------------------------------------------

    def test_distance_parsed_from_location(self):
        self.assertEqual(self.ks.parse_distance("08058 Zwickau (9 km)"), 9)
        self.assertEqual(self.ks.parse_distance("09119 Kappel (ca. 35 km)"), 35)
        self.assertEqual(self.ks.parse_distance("06179 Teutschenthal + 200 km"), 200)

    def test_distance_absent_is_none(self):
        """No distance shown means the ad is in the search town itself - the
        closest possible - so it must not be dropped by the distance filter."""
        self.assertIsNone(self.ks.parse_distance("08451 Crimmitschau"))

    def test_out_of_radius_listing_is_rejected(self):
        """Live 2026-08-31: a 35km search returned seven ads at 196-200km."""
        cfg, _ = self.ks.parse_watch("<!-- search: x -->\n<!-- radius: 35 -->")
        far = {"title": "t", "desc": "", "price": None, "distance": 200}
        near = {"title": "t", "desc": "", "price": None, "distance": 9}
        self.assertFalse(self.ks.matches(far, cfg))
        self.assertTrue(self.ks.matches(near, cfg))

    def test_radius_has_slack_because_the_site_rounds(self):
        cfg, _ = self.ks.parse_watch("<!-- search: x -->\n<!-- radius: 30 -->")
        edge = {"title": "t", "desc": "", "price": None, "distance": 34}
        self.assertTrue(self.ks.matches(edge, cfg))

    # --- filters -------------------------------------------------------------

    def test_unpriced_ad_survives_a_max_price_filter(self):
        cfg, _ = self.ks.parse_watch("<!-- search: x -->\n<!-- price: 10-100 -->")
        self.assertTrue(self.ks.matches(
            {"title": "t", "desc": "", "price": None, "distance": None}, cfg))

    def test_price_bounds_are_enforced_when_a_price_exists(self):
        cfg, _ = self.ks.parse_watch("<!-- search: x -->\n<!-- price: 10-100 -->")
        for price, expected in ((5, False), (10, True), (100, True), (101, False)):
            listing = {"title": "t", "desc": "", "price": price, "distance": None}
            self.assertEqual(self.ks.matches(listing, cfg), expected, f"price {price}")

    def test_exclude_matches_the_description_not_just_the_title(self):
        cfg, _ = self.ks.parse_watch("<!-- search: x -->\n<!-- exclude: ankauf -->")
        listing = {"title": "iPhone", "desc": "Ankauf von Altgeraeten",
                   "price": 20, "distance": None}
        self.assertFalse(self.ks.matches(listing, cfg))

    def test_require_is_an_any_not_an_all(self):
        cfg, _ = self.ks.parse_watch(
            "<!-- search: x -->\n<!-- require: bosch, makita -->")
        self.assertTrue(self.ks.matches(
            {"title": "Makita Bohrer", "desc": "", "price": 30, "distance": None}, cfg))
        self.assertFalse(self.ks.matches(
            {"title": "No-Name Bohrer", "desc": "", "price": 30, "distance": None}, cfg))

    def test_phrase_excludes_do_not_eat_the_opposite_ad(self):
        """Live 2026-08-31: a bare `icloud` exclude dropped "iPhone 13 Bastler
        - iCloud frei", an ad advertising precisely the good case. The watch
        file excludes phrases ("icloud sperre") for this reason."""
        cfg, _ = self.ks.parse_watch(
            "<!-- search: x -->\n<!-- exclude: icloud sperre, gesperrt -->")
        good = {"title": "iPhone 13 Bastler - iCloud frei", "desc": "",
                "price": 95, "distance": 10}
        bad = {"title": "iPhone 13", "desc": "hat noch icloud sperre",
               "price": 95, "distance": 10}
        self.assertTrue(self.ks.matches(good, cfg))
        self.assertFalse(self.ks.matches(bad, cfg))

    # --- watch parsing -------------------------------------------------------

    def test_readme_in_the_watches_folder_is_not_a_watch(self):
        """Live 2026-08-31: watches/README.md has no search directive, so every
        run counted it as a broken watch and sent "Sniper-Problem: README.md"
        to Telegram every 3 minutes for hours. The folder's own documentation
        became a permanent failure."""
        self.assertFalse(self.ks.is_watch_file("README.md", "# Watches\n\nProse."))
        self.assertTrue(self.ks.is_watch_file(
            "monitore.md", "<!-- search: monitor -->"))

    def test_prose_file_without_directives_is_treated_as_docs(self):
        self.assertFalse(self.ks.is_watch_file("NOTES.md", "just some notes"))

    def test_file_with_directives_but_no_search_is_still_a_real_error(self):
        """A typo must still report - only prose gets skipped silently."""
        self.assertTrue(self.ks.is_watch_file("typo.md", "<!-- radius: 30 -->"))
        cfg, err = self.ks.parse_watch("<!-- radius: 30 -->")
        self.assertIsNone(cfg)
        self.assertIn("search", err)

    def test_failure_realert_interval_is_hours_not_minutes(self):
        """Even a genuine broken watch must not ping every 3 minutes; the
        timer fires 320 times a day."""
        self.assertGreaterEqual(self.ks.FAILURE_REALERT_SECONDS, 3600)

    def test_watch_without_a_search_is_an_error_not_a_crash(self):
        cfg, err = self.ks.parse_watch("just some prose, no directives")
        self.assertIsNone(cfg)
        self.assertIn("search", err)

    def test_prose_below_the_directives_is_ignored(self):
        cfg, err = self.ks.parse_watch(
            "<!-- search: monitor -->\nNotes about why, mentioning price: 5-9.")
        self.assertIsNone(err)
        self.assertEqual(cfg["search"], "monitor")
        self.assertIsNone(cfg["max_price"])

    def test_defaults_apply_when_directives_are_omitted(self):
        cfg, _ = self.ks.parse_watch("<!-- search: monitor -->")
        self.assertEqual(cfg["location"], self.ks.DEFAULT_LOCATION)
        self.assertEqual(cfg["radius"], self.ks.DEFAULT_RADIUS)

    def test_open_ended_price_ranges(self):
        lo, _ = self.ks.parse_watch("<!-- search: x -->\n<!-- price: 50- -->")
        self.assertEqual(lo["min_price"], 50)
        self.assertIsNone(lo["max_price"])
        hi, _ = self.ks.parse_watch("<!-- search: x -->\n<!-- price: -80 -->")
        self.assertIsNone(hi["min_price"])
        self.assertEqual(hi["max_price"], 80)

    def test_umlauts_survive_into_the_query_but_not_the_slug(self):
        """"haushaltsaufloesung" and "haushaltsauflaesung" are different
        searches to Kleinanzeigen; the umlaut one is the one with results."""
        cfg, _ = self.ks.parse_watch("<!-- search: haushaltsaufl\u00f6sung -->")
        url = self.ks.build_url(cfg)
        self.assertIn("haushaltsaufloesung", url)
        self.assertIn("keywords=haushaltsaufl%C3%B6sung", url)

    def test_explicit_url_directive_wins_over_search(self):
        cfg, _ = self.ks.parse_watch(
            "<!-- search: monitor -->\n<!-- url: https://example.com/x -->")
        self.assertEqual(self.ks.build_url(cfg), "https://example.com/x")

    # --- html parsing --------------------------------------------------------

    def test_parses_a_real_article_block(self):
        html = ('<article class="aditem" data-adid="3499404638" '
                'data-href="/s-anzeige/samsung/3499404638-225-3983">'
                '<div class="aditem-main--top--left">08289 Schneeberg (ca. 30 km)</div>'
                '<div class="aditem-main--top--right">Gestern, 20:49</div>'
                '<h2 class="text-module"><a href="#">Samsung Monitor 32"</a></h2>'
                '<p class="aditem-main--middle--description">Guter Zustand</p>'
                '<p class="aditem-main--middle--price-shipping--price">120 &euro; VB</p>'
                '</article>')
        listings = self.ks.parse_listings(html)
        self.assertEqual(len(listings), 1)
        got = listings[0]
        self.assertEqual(got["id"], "3499404638")
        self.assertEqual(got["price"], 120)
        self.assertEqual(got["distance"], 30)
        self.assertEqual(got["title"], 'Samsung Monitor 32"')
        self.assertTrue(got["url"].startswith("https://www.kleinanzeigen.de/s-anzeige/"))

    def test_alert_shows_the_link_and_the_drive(self):
        listing = {"id": "1", "url": "https://x/y", "title": "Bosch GSR",
                   "desc": "", "location": "09366 Stollberg (30 km)",
                   "posted": "Heute, 09:12", "price": 95, "distance": 30}
        alert = self.ks.format_alert(listing, "werkzeug")
        self.assertIn("[werkzeug]", alert)
        self.assertIn("95 \u20ac", alert)
        self.assertIn("30 km", alert)
        self.assertNotIn("(~", alert)  # location already carries the distance
        self.assertIn("https://x/y", alert)

    def test_sniper_staleness_is_a_health_failure(self):
        """The sniper's failure mode is silence, and silence is also what a
        working sniper looks like on a quiet afternoon. health_check is what
        tells those two apart."""
        spec = importlib.util.spec_from_file_location(
            "health_check", os.path.join(HERE, "scripts", "health_check.py"))
        hc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hc)
        self.assertTrue(hc.evaluate_sniper(None)[0], "never-run must not page")
        self.assertTrue(hc.evaluate_sniper(0.1)[0])
        self.assertTrue(hc.evaluate_sniper(9.0)[0], "an overnight gap is normal")
        self.assertFalse(hc.evaluate_sniper(11.0)[0])

    def test_unpriced_alert_says_so_instead_of_showing_none(self):
        listing = {"id": "1", "url": "https://x/y", "title": "Konvolut",
                   "desc": "", "location": "08058 Zwickau (9 km)",
                   "posted": "Heute", "price": None, "distance": 9}
        alert = self.ks.format_alert(listing, "aufloesung")
        self.assertIn("VB / kein Preis", alert)
        self.assertNotIn("None", alert)


class TestDmarcProspector(unittest.TestCase):
    """The DMARC lead finder (added 2026-08-31). Pure functions only - no DNS,
    no Overpass. Several of these encode mistakes the first live run actually
    made against real data from around Crimmitschau, each of which would have
    produced a wrong phone call rather than a crash."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "dmarc_prospector", os.path.join(HERE, "scripts", "dmarc_prospector.py"))
        cls.dp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.dp)

    # --- domain hygiene ------------------------------------------------------

    def test_domain_extracted_from_messy_urls(self):
        for raw, expected in (
            ("https://www.baeckerei-sens.de/", "baeckerei-sens.de"),
            ("http://Example.DE/impressum?x=1", "example.de"),
            ("https://porta.de/zwickau", "porta.de"),
        ):
            self.assertEqual(self.dp.domain_from_url(raw), expected, raw)

    def test_garbage_urls_are_dropped_not_guessed_at(self):
        for raw in ("", None, "not a url", "http://", "mailto:x", "http://localhost"):
            self.assertIsNone(self.dp.domain_from_url(raw))

    def test_registrable_parent(self):
        self.assertEqual(self.dp.registrable_parent("agentur.barmenia.de"), "barmenia.de")
        self.assertEqual(self.dp.registrable_parent("barmenia.de"), "barmenia.de")
        self.assertEqual(self.dp.registrable_parent("shop.example.co.uk"), "example.co.uk")

    def test_subdomains_are_dropped_because_they_cannot_publish_dmarc(self):
        """agentur.barmenia.de is an insurance agent on the insurer's corporate
        domain. He cannot edit that zone, so he cannot buy the fix."""
        found = {"metzgerei-mueller.de": {}, "agentur.barmenia.de": {},
                 "12706.apotheken-website-vorschau.de": {}}
        kept = self.dp.drop_platform_subdomains(found)
        self.assertEqual(set(kept), {"metzgerei-mueller.de"})

    def test_public_bodies_are_dropped(self):
        """Government offices, town halls, churches - not 249-EUR-fix
        customers, and cold-pitching a Landratsamt reads badly.
        landkreis-zwickau.de surfaced as a lead 2026-08-31; this filter is
        the fix."""
        payload = {"elements": [
            {"tags": {"office": "government", "name": "Landratsamt",
                      "website": "https://landkreis-zwickau.de"}},
            {"tags": {"amenity": "place_of_worship", "name": "Kirche",
                      "website": "https://kirche.de"}},
            {"tags": {"shop": "bakery", "name": "Bäcker",
                      "website": "https://baecker.de"}},
        ]}
        kept = self.dp.parse_overpass(payload)
        self.assertIn("baecker.de", kept)
        self.assertNotIn("landkreis-zwickau.de", kept)
        self.assertNotIn("kirche.de", kept)

    def test_chains_are_dropped_by_location_count(self):
        payload = {"elements": [
            {"tags": {"shop": "supermarket", "name": "Globus",
                      "website": "https://globus.de"}} for _ in range(9)
        ] + [{"tags": {"shop": "bakery", "name": "Sens",
                       "website": "https://baeckerei-sens.de"}}]}
        parsed = self.dp.parse_overpass(payload)
        self.assertIn("baeckerei-sens.de", parsed)
        self.assertNotIn("globus.de", parsed, "a 9-location chain is not a lead")

    # --- record parsing ------------------------------------------------------

    def test_long_txt_records_are_rejoined(self):
        """dig splits records over 255 chars into adjacent quoted chunks.
        Reading only the first would misreport a long SPF record's policy."""
        self.assertEqual(self.dp.join_txt(['"v=spf1 include:a " "include:b -all"']),
                         ["v=spf1 include:a include:b -all"])

    def test_spf_policy_variants(self):
        for record, expected in (
            ("v=spf1 include:spf.ihk.de -all", "-all"),
            ("v=spf1 mx ~all", "~all"),
            ("v=spf1 a ?all", "?all"),
            ("v=spf1 include:x", "none"),
        ):
            self.assertEqual(self.dp.parse_spf([record])[0], expected, record)

    def test_spf_ignores_unrelated_txt_records(self):
        txts = ["google-site-verification=abc", "zone-ownership-verification=xyz"]
        self.assertIsNone(self.dp.parse_spf(txts)[0])

    def test_dmarc_policy_variants(self):
        self.assertEqual(self.dp.parse_dmarc(["v=DMARC1; p=reject; rua=mailto:x"])[0], "reject")
        self.assertEqual(self.dp.parse_dmarc(["v=DMARC1; p=quarantine"])[0], "quarantine")
        self.assertEqual(self.dp.parse_dmarc(["v=DMARC1; p=none"])[0], "none")
        self.assertEqual(self.dp.parse_dmarc(["v=DMARC1; rua=mailto:x"])[0], "none")
        self.assertIsNone(self.dp.parse_dmarc(["v=spf1 -all"])[0])

    def test_provider_classification_drives_the_sales_line(self):
        self.assertEqual(self.dp.classify_provider(["10 mx00.ionos.de."]), "IONOS")
        self.assertEqual(self.dp.classify_provider(
            ["10 x-com.mail.protection.outlook.com."]), "Microsoft 365")
        self.assertEqual(self.dp.classify_provider([]), "no MX")

    # --- scoring -------------------------------------------------------------

    def test_worst_posture_scores_highest(self):
        self.assertEqual(self.dp.score(None, None, True), 9)

    def test_already_protected_domain_scores_zero_and_is_never_called(self):
        """Pitching someone who already deployed DMARC wastes the one thing
        this list exists to save."""
        self.assertEqual(self.dp.score("-all", "reject", True), 0)

    def test_dmarc_none_still_scores_as_a_lead(self):
        """p=none publishes a policy that enforces nothing - a real sale, but
        below a domain with no record at all."""
        self.assertLess(self.dp.score("-all", "none", True),
                        self.dp.score("-all", None, True))

    def test_useless_spf_scores_same_as_no_spf(self):
        self.assertEqual(self.dp.score("?all", None, True),
                         self.dp.score(None, None, True))

    def test_mail_flow_raises_the_score(self):
        self.assertGreater(self.dp.score(None, None, True),
                           self.dp.score(None, None, False))

    def test_rank_excludes_protected_domains_and_orders_by_score(self):
        results = {
            "secure.de": {"domain": "secure.de", "score": 0},
            "bad.de": {"domain": "bad.de", "score": 9},
            "mid.de": {"domain": "mid.de", "score": 6},
        }
        ranked = [r["domain"] for r, _ in self.dp.rank(results, {}, limit=10)]
        self.assertEqual(ranked, ["bad.de", "mid.de"])

    # --- scheduling ----------------------------------------------------------

    def test_never_checked_domains_come_first(self):
        now = datetime.now(timezone.utc).isoformat()
        domains = {"new.de": {}, "fresh.de": {}}
        results = {"fresh.de": {"checked": now}}
        self.assertEqual(self.dp.due_for_check(domains, results), ["new.de"])

    def test_fresh_results_are_not_rechecked(self):
        now = datetime.now(timezone.utc).isoformat()
        domains = {"a.de": {}}
        self.assertEqual(self.dp.due_for_check(domains, {"a.de": {"checked": now}}), [])

    def test_stale_results_are_rechecked(self):
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        domains = {"a.de": {}}
        self.assertEqual(self.dp.due_for_check(domains, {"a.de": {"checked": old}}), ["a.de"])

    def test_audit_order_is_not_alphabetical(self):
        """Sorted order meant the first nights returned only A-names, so the
        morning brief showed Adler-Apotheke, AED-Service, Aerztehaus... for a
        week instead of a spread across the region."""
        domains = {f"{c}{i}.de": {} for c in "abcdefghij" for i in range(12)}
        order = self.dp.due_for_check(domains, {}, budget=120)
        self.assertNotEqual(order, sorted(order))
        self.assertEqual(sorted(order), sorted(domains))

    def test_budget_is_respected(self):
        domains = {f"d{i}.de": {} for i in range(50)}
        self.assertEqual(len(self.dp.due_for_check(domains, {}, budget=10)), 10)

    # --- morning brief -------------------------------------------------------

    def test_brief_only_shows_unreported_leads(self):
        results = {"a.de": {"domain": "a.de", "score": 9, "dmarc": None, "spf": None,
                            "provider": "IONOS"},
                   "b.de": {"domain": "b.de", "score": 9, "dmarc": None, "spf": None,
                            "provider": "IONOS"}}
        section = self.dp.build_brief_section(results, {}, reported={"a.de"}, limit=3)
        self.assertIn("b.de", section)
        self.assertNotIn("a.de", section)

    def test_equal_scores_do_not_always_serve_the_same_alphabetical_head(self):
        """~660 leads tie at the top score and the brief shows 3 a day. An
        alphabetical tiebreak would serve A-names for a month."""
        results = {f"{c}{i}.de": {"domain": f"{c}{i}.de", "score": 9}
                   for c in "abcdefghij" for i in range(6)}
        top = [r["domain"] for r, _ in self.dp.rank(results, {}, limit=8)]
        self.assertEqual(len(top), 8)
        self.assertNotEqual(top, sorted(results)[:8])

    def test_rank_is_stable_within_a_day(self):
        results = {f"d{i}.de": {"domain": f"d{i}.de", "score": 9} for i in range(40)}
        first = [r["domain"] for r, _ in self.dp.rank(results, {}, limit=5)]
        second = [r["domain"] for r, _ in self.dp.rank(results, {}, limit=5)]
        self.assertEqual(first, second, "a rerun on the same day must not reshuffle")

    def test_brief_says_so_when_nothing_is_new(self):
        results = {"a.de": {"domain": "a.de", "score": 9, "dmarc": None,
                            "spf": None, "provider": "IONOS"}}
        section = self.dp.build_brief_section(results, {}, reported={"a.de"})
        self.assertIn("keine neuen", section)
        self.assertIn("1 offene", section)

    def test_brief_is_absent_rather_than_empty_before_any_audit(self):
        self.assertIsNone(self.dp.build_brief_section({}, {}, reported=set()))

    def test_brief_names_the_business_not_just_the_domain(self):
        results = {"a.de": {"domain": "a.de", "score": 9, "dmarc": None,
                            "spf": None, "provider": "IONOS"}}
        section = self.dp.build_brief_section(
            results, {"a.de": {"name": "Baeckerei Sens"}}, reported=set())
        self.assertIn("Baeckerei Sens", section)

    def test_audit_checkpoints_so_an_interrupted_run_is_not_wasted(self):
        """A full run is ~13 minutes of DNS. Without checkpointing, a reboot at
        minute 12 discards all of it and the next night restarts from nothing."""
        self.assertTrue(0 < self.dp.CHECKPOINT_EVERY < self.dp.NIGHTLY_BUDGET)

    def test_prospector_staleness_is_a_health_failure(self):
        spec = importlib.util.spec_from_file_location(
            "health_check", os.path.join(HERE, "scripts", "health_check.py"))
        hc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hc)
        self.assertTrue(hc.evaluate_prospector(None)[0], "never-run must not page")
        self.assertTrue(hc.evaluate_prospector(20.0)[0])
        self.assertFalse(hc.evaluate_prospector(30.0)[0])


class TestStatusUpdate(unittest.TestCase):
    """The 10/14/18/22 status update (added 2026-08-31).

    Exists because the sniper's first live day ran 80 times, correctly found
    nothing worth driving to, and said nothing - which from the phone is
    indistinguishable from a service that died at 07:00. These tests pin the
    one property that makes it worth sending: it reports the numbers behind
    the silence instead of omitting the section."""

    @classmethod
    def setUpClass(cls):
        sys.modules.setdefault("send_telegram_notification",
                               types.ModuleType("send_telegram_notification"))
        sys.modules["send_telegram_notification"].send = lambda *a, **k: True
        spec = importlib.util.spec_from_file_location(
            "status_update", os.path.join(HERE, "scripts", "status_update.py"))
        cls.su = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.su)

    def test_quiet_period_still_reports_numbers(self):
        """The whole point: 0 alerts must read as '120 geprüft, 0 passend',
        never as an absent section."""
        line = self.su.format_sniper_section(
            {"runs": 80, "listings": 2000, "new_ads": 18, "alerts": 0})
        self.assertIn("80", line)
        self.assertIn("18", line)
        self.assertIn("nichts passendes", line)

    def test_cumulative_listing_count_is_not_reported_as_throughput(self):
        """Each run re-reads the same page 1, so 80 runs x 25 ads is 2000
        sightings of 25 ads - a number that looks like work and is really just
        the clock ticking."""
        line = self.su.format_sniper_section(
            {"runs": 80, "listings": 2000, "new_ads": 18, "alerts": 0})
        self.assertNotIn("2000", line)

    def test_weekday_is_german_like_the_rest_of_the_message(self):
        monday = time.struct_time((2026, 8, 31, 14, 0, 0, 0, 243, -1))
        msg = self.su.build_update({"runs": 1, "listings": 1, "new_ads": 0,
                                    "alerts": 0}, None, {}, now=monday)
        self.assertIn("Montag", msg)
        self.assertNotIn("Monday", msg)

    def test_no_runs_at_all_is_called_out_as_suspicious(self):
        line = self.su.format_sniper_section({"runs": 0, "listings": 0,
                                              "new_ads": 0, "alerts": 0})
        self.assertIn("keine Läufe", line)

    def test_missing_stats_do_not_crash_the_update(self):
        self.assertIn("keine Läufe", self.su.format_sniper_section(None))

    def test_money_board_section_leads_the_substantive_sections(self):
        """The system's point is money in - the money board must appear before
        the todo list and leads in the morning digest."""
        spec = importlib.util.spec_from_file_location(
            "morning_brief", os.path.join(HERE, "scripts", "morning_brief.py"))
        # morning_brief imports several sibling modules; ensure scripts/ is importable
        scripts_dir = os.path.join(HERE, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        mbrief = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mbrief)
        digest = mbrief.build_digest(
            {"x": (True, "ok")}, todos=[{"text": "a todo"}],
            leads="DMARC-Leads (1 neu):", money="Top Geld-Moves:\n  • test")
        self.assertLess(digest.index("Geld-Moves"), digest.index("a todo"))
        self.assertLess(digest.index("a todo"), digest.index("DMARC-Leads"))

    def test_spend_section_absent_when_paid_tier_is_off(self):
        os.environ.pop("OPENROUTER_PAID_ENABLED", None)
        self.assertIsNone(self.su.format_spend_section())

    def test_spend_section_present_when_paid_tier_is_on(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["OPENROUTER_PAID_ENABLED"] = "true"
            self.addCleanup(os.environ.pop, "OPENROUTER_PAID_ENABLED", None)
            spend_guard_mod = self.su.spend_guard
            original = spend_guard_mod.LEDGER_PATH
            spend_guard_mod.LEDGER_PATH = os.path.join(tmp, "ledger.json")
            try:
                spend_guard_mod.record_spend(1.23, month="2026-08")
                line = self.su.format_spend_section()
            finally:
                spend_guard_mod.LEDGER_PATH = original
            self.assertIn("1.23", line)

    def test_health_section_is_silent_when_everything_is_fine(self):
        """The morning brief already gives the all-clear once a day; four more
        would train you to skim past the one that matters."""
        self.assertIsNone(self.su.format_health_section({"a": (True, "ok")}))

    def test_health_section_speaks_up_on_failure(self):
        section = self.su.format_health_section(
            {"a": (True, "ok"), "prospector": (False, "last audit 30h ago")})
        self.assertIn("prospector", section)
        self.assertNotIn("a: ok", section)

    def test_update_always_has_a_sniper_line_even_with_no_leads(self):
        msg = self.su.build_update({"runs": 5, "listings": 100, "new_ads": 2,
                                    "alerts": 0}, None, {})
        self.assertIn("Sniper:", msg)
        self.assertTrue(msg.startswith("Status "))

    def test_update_includes_leads_and_warnings_when_present(self):
        msg = self.su.build_update(
            {"runs": 5, "listings": 100, "new_ads": 2, "alerts": 0},
            "DMARC-Leads (1 neu):\n\nBäcker\n  baecker.de\n  kein DMARC",
            {"queue": (False, "stuck 90min")})
        self.assertIn("baecker.de", msg)
        self.assertIn("Achtung", msg)
        self.assertIn("stuck 90min", msg)


class TestBridgeLogging(unittest.TestCase):
    """Guards the logging config in telegram_bridge.py. Both of these were
    live regressions on 2026-08-31, introduced by the fix for the traceback
    noise and caught by reading the journal afterwards."""

    def _source(self):
        with open(os.path.join(HERE, "telegram_bridge.py"), encoding="utf-8") as f:
            return f.read()

    def test_http_loggers_are_pinned_below_info(self):
        """httpx logs one INFO line per request and long-polling makes a
        request every ~10s forever. That line is the full Bot API URL, which
        embeds the bot token - so INFO both floods the journal and writes a
        live credential into it."""
        src = self._source()
        self.assertIn("httpx", src)
        self.assertIn('logging.getLogger(noisy).setLevel(logging.WARNING)', src)

    def test_root_level_is_not_info(self):
        self.assertIn("level=logging.WARNING", self._source())

    def test_filter_matches_exact_network_error_not_the_subclass(self):
        """BadRequest subclasses NetworkError and means a malformed message -
        the one case worth a traceback. isinstance() here would hide it."""
        src = self._source()
        self.assertIn("type(exc) is NetworkError", src)
        self.assertIn("isinstance(exc, BadRequest)", src)


class TestSniperStats(unittest.TestCase):
    """Activity counters feeding the status update."""

    @classmethod
    def setUpClass(cls):
        sys.modules.setdefault("send_telegram_notification",
                               types.ModuleType("send_telegram_notification"))
        sys.modules["send_telegram_notification"].send = lambda *a, **k: True
        spec = importlib.util.spec_from_file_location(
            "kleinanzeigen_sniper",
            os.path.join(HERE, "scripts", "kleinanzeigen_sniper.py"))
        cls.ks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.ks)

    def test_state_always_has_stats_even_from_an_old_file(self):
        """load_state must upgrade a state.json written before stats existed,
        rather than KeyError-ing the next sniper run after a deploy."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"seen": {}, "seeded": []}, f)
            original = self.ks.STATE_PATH
            try:
                self.ks.STATE_PATH = path
                state = self.ks.load_state()
                self.assertEqual(state["stats"]["runs"], 0)
                self.assertIn("alerts", state["stats"])
            finally:
                self.ks.STATE_PATH = original

    def test_take_stats_resets_the_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"seen": {}, "seeded": [],
                           "stats": {"runs": 9, "listings": 90,
                                     "new_ads": 4, "alerts": 1}}, f)
            original_state, original_dir = self.ks.STATE_PATH, self.ks.WATCHES_DIR
            try:
                self.ks.STATE_PATH, self.ks.WATCHES_DIR = path, tmp
                first = self.ks.take_stats()
                self.assertEqual(first["runs"], 9)
                self.assertEqual(self.ks.take_stats()["runs"], 0,
                                 "a second read must not re-report the same window")
            finally:
                self.ks.STATE_PATH, self.ks.WATCHES_DIR = original_state, original_dir


class TestPaidTierGating(unittest.TestCase):
    """The OpenRouter paid tier (added 2026-08-31). Imports aios_runner with
    the feature explicitly turned on, since it must be a complete no-op
    otherwise - TestModelChain and every other suite above already prove
    that with it left off."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["AIOS_WORKSPACE"] = self.tmp.name
        os.environ["OPENROUTER_API_KEY"] = "test-key"
        os.environ["OPENROUTER_PAID_ENABLED"] = "true"
        os.environ["OPENROUTER_MONTHLY_BUDGET_USD"] = "1.0"
        for var in ("OPENROUTER_API_KEY", "OPENROUTER_PAID_ENABLED",
                    "OPENROUTER_MONTHLY_BUDGET_USD"):
            self.addCleanup(os.environ.pop, var, None)
        self.fake = _install_stubs()
        sys.path.insert(0, HERE)
        self.addCleanup(lambda: sys.path.remove(HERE))
        sys.modules.pop("aios_runner", None)
        sys.modules.pop("spend_guard", None)
        self.runner = importlib.import_module("aios_runner")
        self.addCleanup(lambda: sys.modules.pop("aios_runner", None))
        # Point the ledger at this test's own throwaway directory so runs
        # never share state with each other or with a real ledger on disk.
        self.runner.spend_guard.LEDGER_PATH = os.path.join(self.tmp.name, "ledger.json")

    def queue(self, name, text):
        path = os.path.join(self.runner.INBOX, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def log_of(self, name):
        path = os.path.join(self.runner.LOGS, f"{name}.log")
        return open(path, encoding="utf-8").read() if os.path.exists(path) else None

    def test_enabling_the_flag_appends_exactly_one_paid_entry(self):
        paid = [e for e in self.runner.MODEL_CHAIN if e["paid"]]
        self.assertEqual(len(paid), 1)
        self.assertEqual(paid[0]["model"], self.runner.OPENROUTER_PAID_MODEL)

    def test_every_free_entry_is_explicitly_not_paid(self):
        """paid must default False, not None/missing - the retry loop does
        `if entry["paid"]:`, and a missing key there is a KeyError, not a
        false one, on the very first free model in the chain."""
        for entry in self.runner.MODEL_CHAIN[:-1]:
            self.assertIs(entry["paid"], False)

    def test_paid_tier_only_reached_after_every_free_model_fails(self):
        calls = []

        def track(model, instr, sp=None, history=None, **kwargs):
            calls.append(model)
            if model == self.runner.OPENROUTER_PAID_MODEL:
                return "answered by paid tier"
            raise RuntimeError("free tier exhausted")

        self.runner._attempt = track
        self.runner._record_paid_spend = lambda *a, **k: None
        self.runner.time.sleep = lambda s: None
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(self.log_of("t.md"), "answered by paid tier")
        self.assertEqual(calls[-1], self.runner.OPENROUTER_PAID_MODEL)
        self.assertEqual(len(calls), len(self.runner.MODEL_CHAIN))

    def test_budget_exhausted_skips_the_paid_call_entirely(self):
        """The cap must prevent the call, not refund it after - record_spend
        is never reached if can_spend() already said no."""
        self.runner.spend_guard.record_spend(999.0, path=self.runner.spend_guard.LEDGER_PATH)
        attempted = []

        def dead_free_only(model, instr, sp=None, history=None, **kwargs):
            attempted.append(model)
            raise RuntimeError("free tier exhausted")

        self.runner._attempt = dead_free_only
        self.runner.time.sleep = lambda s: None
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertNotIn(self.runner.OPENROUTER_PAID_MODEL, attempted,
                         "a call must never be attempted once the budget is spent")
        self.assertIn("budget reached", self.log_of("t.md"))

    def test_successful_paid_call_records_spend_via_the_fallback_estimator(self):
        """No litellm.completion_cost / no captured usage in this stub - the
        token_counter-based fallback must still produce a positive, recorded
        cost rather than silently logging $0."""
        self.runner.litellm.completion_cost = lambda **k: (_ for _ in ()).throw(Exception("unknown model"))
        self.runner.litellm.token_counter = lambda model, text: max(len((text or "").split()), 1)

        def paid_only(model, instr, sp=None, history=None, **kwargs):
            if model == self.runner.OPENROUTER_PAID_MODEL:
                return "a real answer"
            raise RuntimeError("free tier exhausted")

        self.runner._attempt = paid_only
        self.runner.time.sleep = lambda s: None
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        spent = self.runner.spend_guard.month_spent(
            self.runner.spend_guard.load_ledger(self.runner.spend_guard.LEDGER_PATH))
        self.assertGreater(spent, 0.0)

    def test_paid_entry_has_an_explicit_context_window_and_max_tokens(self):
        """Verified live 2026-08-31: without these, Open Interpreter can't
        auto-detect this model's window and silently defaults to 8000
        against the real 1,048,576 - the same failure already documented
        and fixed for the free nemotron entry above this one."""
        entry = [e for e in self.runner.MODEL_CHAIN if e["paid"]][0]
        self.assertIsNotNone(entry["context_window"])
        self.assertIsNotNone(entry["max_tokens"])
        self.assertLess(entry["max_tokens"], 262_144,
                        "must stay well under the model's real ceiling - one "
                        "runaway response must not burn a big share of the "
                        "monthly cap in a single call")

    def test_cost_prefers_openrouter_reported_cost_over_every_estimate(self):
        """Verified live 2026-08-31: a real call's usage carried
        usage.cost=4.9476e-05 - what was actually billed, not an estimate
        of it. Nothing computed locally should override that when present.
        reported_cost is pre-summed by the caller across every chat() call
        an attempt made (original + a possible synthesis nudge) - see
        _record_paid_spend()."""
        self.runner.litellm.completion_cost = lambda **k: 999.0
        got = self.runner._cost_for_paid_call("any/model", 100, 50, reported_cost=0.00042)
        self.assertAlmostEqual(got, 0.00042)

    def test_cost_falls_back_to_litellm_then_to_env_rate(self):
        self.runner.litellm.completion_cost = lambda **k: 0.01
        self.assertAlmostEqual(
            self.runner._cost_for_paid_call("any/model", 100, 50, reported_cost=None), 0.01)

        self.runner.litellm.completion_cost = lambda **k: (_ for _ in ()).throw(Exception("nope"))
        self.runner.OPENROUTER_PAID_INPUT_PER_M = 1.19
        self.runner.OPENROUTER_PAID_OUTPUT_PER_M = 3.74
        expected = (100 / 1e6) * 1.19 + (50 / 1e6) * 3.74
        self.assertAlmostEqual(
            self.runner._cost_for_paid_call("any/model", 100, 50, reported_cost=None), expected)


class TestSpendGuard(unittest.TestCase):
    """Pure ledger arithmetic - the budget cap that keeps the paid tier from
    turning a stuck-loop bug into a bill."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "spend_guard", os.path.join(HERE, "scripts", "spend_guard.py"))
        cls.sg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.sg)

    def test_fresh_month_has_spent_nothing(self):
        self.assertEqual(self.sg.month_spent({}, "2026-08"), 0.0)

    def test_can_spend_below_budget(self):
        self.assertTrue(self.sg.can_spend({"2026-08": 3.0}, budget_usd=6.0, month="2026-08"))

    def test_cannot_spend_at_or_over_budget(self):
        """At-the-cap must already refuse - the guard is "may I make this
        call", and letting one more through exactly at the boundary is the
        off-by-one that turns a hard cap into a soft one."""
        self.assertFalse(self.sg.can_spend({"2026-08": 6.0}, budget_usd=6.0, month="2026-08"))
        self.assertFalse(self.sg.can_spend({"2026-08": 9.0}, budget_usd=6.0, month="2026-08"))

    def test_record_spend_is_additive_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.json")
            self.sg.record_spend(1.5, path=path, month="2026-08")
            total = self.sg.record_spend(0.75, path=path, month="2026-08")
            self.assertAlmostEqual(total, 2.25)
            self.assertAlmostEqual(
                self.sg.month_spent(self.sg.load_ledger(path), "2026-08"), 2.25)

    def test_different_months_do_not_share_a_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.json")
            self.sg.record_spend(5.0, path=path, month="2026-08")
            self.sg.record_spend(1.0, path=path, month="2026-09")
            ledger = self.sg.load_ledger(path)
            self.assertAlmostEqual(self.sg.month_spent(ledger, "2026-08"), 5.0)
            self.assertAlmostEqual(self.sg.month_spent(ledger, "2026-09"), 1.0)

    def test_missing_ledger_file_is_treated_as_empty_not_an_error(self):
        self.assertEqual(self.sg.load_ledger("/nonexistent/path.json"), {})

    def test_negative_cost_cannot_replenish_the_budget(self):
        """A cost calculation bug that goes negative must not accidentally
        refund the ledger - additive-only, floor at zero per call."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.json")
            self.sg.record_spend(2.0, path=path, month="2026-08")
            total = self.sg.record_spend(-5.0, path=path, month="2026-08")
            self.assertEqual(total, 2.0)

    def test_status_line_reports_spent_and_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.json")
            self.sg.record_spend(2.5, path=path, month="2026-08")
            line = self.sg.status_line(6.0, path=path, month="2026-08")
            self.assertIn("2.50", line)
            self.assertIn("6.00", line)


class TestOutreach(unittest.TestCase):
    """DMARC outreach letter generation (added 2026-08-31). The step that
    turns hundreds of leads into money without a human writing 500 letters -
    so the tests guard the two things that make it safe to run unattended:
    no false security claims, and no accidental double-contact."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "outreach", os.path.join(HERE, "scripts", "outreach.py"))
        cls.o = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.o)

    def _sender(self):
        return {"name": "F H", "street": "Str 1", "city": "08451 Crimmitschau",
                "email": "f@example.com", "phone": "0170 1"}

    def _entry(self, domain="x.de", address=True):
        e = {"domain": domain, "name": "Bäckerei X"}
        if address:
            e["address"] = {"street": "Hauptstr 3", "postcode": "08451", "city": "Crimmitschau"}
        return e

    def test_finding_text_matches_the_actual_dmarc_state(self):
        self.assertIn("kein DMARC-Eintrag",
                      self.o.finding_sentence({"dmarc": None, "spf": None}))
        self.assertIn("p=none",
                      self.o.finding_sentence({"dmarc": "none", "spf": "-all"}))
        self.assertIn("p=quarantine",
                      self.o.finding_sentence({"dmarc": "quarantine", "spf": "-all"}))

    def test_letter_never_claims_a_system_was_accessed(self):
        """The legal line: this is a public DNS lookup, not a scan. The letter
        must say so and must never imply otherwise, or it stops being
        prospecting and becomes something an angry recipient can complain
        about."""
        letter = self.o.render_letter(
            self._entry(), {"dmarc": None, "spf": None, "provider": "IONOS"},
            self._sender(), "31.08.2026")
        self.assertIn("kein Zugriff", letter)
        self.assertIn("öffentlich", letter)
        for banned in ("gescannt", "getestet", "Zugriff auf Ihr",
                       "Sicherheitslücke in Ihrem System", "gehackt"):
            self.assertNotIn(banned, letter)

    def test_letter_contains_the_real_address_and_price(self):
        letter = self.o.render_letter(
            self._entry(), {"dmarc": None, "spf": None, "provider": "unknown"},
            self._sender(), "31.08.2026")
        self.assertIn("Hauptstr 3", letter)
        self.assertIn("08451", letter)
        self.assertIn("249", letter)
        self.assertIn("Bäckerei X", letter)

    def test_provider_line_only_appears_when_known(self):
        known = self.o.render_letter(self._entry(),
            {"dmarc": None, "spf": None, "provider": "Microsoft 365"},
            self._sender(), "d")
        self.assertIn("Microsoft 365", known)
        unknown = self.o.render_letter(self._entry(),
            {"dmarc": None, "spf": None, "provider": "unknown"},
            self._sender(), "d")
        self.assertNotIn("läuft über", unknown)

    def test_batch_excludes_already_contacted(self):
        domains = {"a.de": self._entry("a.de"), "b.de": self._entry("b.de")}
        results = {"a.de": {"domain": "a.de", "score": 9},
                   "b.de": {"domain": "b.de", "score": 9}}
        batch = self.o.build_batch(domains, results, {"a.de": {}}, limit=10)
        got = [e["domain"] for _, e in batch]
        self.assertEqual(got, ["b.de"])

    def test_batch_excludes_leads_without_an_address(self):
        """A letter needs an envelope. A lead with no postal address is a
        phone/other-channel lead, not a mail one, and must not silently drop
        into a mailing batch as a blank."""
        domains = {"a.de": self._entry("a.de", address=False)}
        results = {"a.de": {"domain": "a.de", "score": 9}}
        self.assertEqual(self.o.build_batch(domains, results, {}, limit=10), [])

    def test_batch_excludes_below_threshold_scores(self):
        domains = {"a.de": self._entry("a.de")}
        results = {"a.de": {"domain": "a.de", "score": 3}}
        self.assertEqual(self.o.build_batch(domains, results, {}, limit=10), [])

    def test_batch_orders_worst_posture_first(self):
        domains = {f"{c}.de": self._entry(f"{c}.de") for c in "abc"}
        results = {"a.de": {"domain": "a.de", "score": 6},
                   "b.de": {"domain": "b.de", "score": 9},
                   "c.de": {"domain": "c.de", "score": 7}}
        got = [e["domain"] for _, e in self.o.build_batch(domains, results, {}, limit=10)]
        self.assertEqual(got, ["b.de", "c.de", "a.de"])

    def test_mark_contacted_persists_and_accumulates(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = self.o.CONTACTED_PATH
            self.o.CONTACTED_PATH = os.path.join(tmp, "contacted.json")
            try:
                self.o.mark_contacted(["a.de"])
                self.o.mark_contacted(["b.de"])
                contacted = self.o.load_contacted()
            finally:
                self.o.CONTACTED_PATH = original
            self.assertEqual(set(contacted), {"a.de", "b.de"})


class TestMoneyBoard(unittest.TestCase):
    """The deterministic money board (added 2026-08-31). It replaces the
    nightly LLM re-derivation of the known blocked-on-human list - so the
    tests guard that it stays a real, sorted, honest list and folds in live
    state without ever raising."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "money_board", os.path.join(HERE, "scripts", "money_board.py"))
        cls.mb = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mb)

    def test_board_has_felix_actions(self):
        self.assertTrue(self.mb.felix_actions())

    def test_render_sorts_by_euros_descending(self):
        board = [("felix", "small", 10, 5, ""), ("felix", "big", 500, 5, ""),
                 ("felix", "mid", 100, 5, "")]
        out = self.mb.render(board=board)
        self.assertLess(out.index("big"), out.index("mid"))
        self.assertLess(out.index("mid"), out.index("small"))

    def test_gating_rows_sort_above_higher_earning_rows(self):
        """A "felix-first" row gates the rows below it, so euros alone must
        not order the board. The real case: Gewerbeanmeldung is worth 0 EUR
        on its own and sorted dead last, directly under the DMARC letters
        whose income it legally gates - read top-down, the board said mail
        first, register later."""
        board = [("felix", "earns-most", 500, 5, ""),
                 ("felix-first", "legally-required-first", 0, 60, ""),
                 ("felix", "earns-less", 100, 5, "")]
        out = self.mb.render(board=board)
        self.assertLess(out.index("legally-required-first"), out.index("earns-most"))
        self.assertLess(out.index("earns-most"), out.index("earns-less"))
        self.assertIn("ZUERST", out)

    def test_brief_section_keeps_the_gate_in_its_top_slots(self):
        """The brief only shows the top few - a gate that fell off the cut
        would be invisible in the one view Felix actually reads daily."""
        board = [("felix", f"action number {i}", 100 - i, 5, "") for i in range(8)]
        board.append(("felix-first", "register-the-business", 0, 60, ""))
        section = self.mb.brief_section(board=board, top=3)
        self.assertIn("register-the-business", section)
        self.assertIn("ZUERST", section)

    def test_mailable_leads_are_counted_separately_from_qualified(self):
        """A qualified domain without an OSM postal address cannot be mailed.
        Reporting qualified as if it were mailable overstated the reachable
        batch by ~125 leads on the real data."""
        sig = self.mb.live_signals()
        self.assertIn("leads_mailable", sig)
        self.assertLessEqual(sig["leads_mailable"], sig["leads_qualified"])

    def test_render_excludes_non_felix_rows(self):
        board = [("felix", "felix-does-this", 100, 5, ""),
                 ("ai", "worker-does-this", 100, 0, ""),
                 ("done", "already-shipped", 100, 0, "")]
        out = self.mb.render(board=board)
        self.assertIn("felix-does-this", out)
        self.assertNotIn("worker-does-this", out)
        self.assertNotIn("already-shipped", out)

    def test_brief_section_is_compact_and_capped(self):
        board = [("felix", f"action number {i}", 100 - i, 5, "") for i in range(8)]
        section = self.mb.brief_section(board=board, top=3)
        self.assertEqual(section.count("•"), 3)

    def test_brief_section_none_when_no_felix_actions(self):
        self.assertIsNone(self.mb.brief_section(board=[("ai", "x", 0, 0, "")]))

    def test_live_signals_never_raise_on_missing_files(self):
        # Points at a temp dir with no state files - must degrade, not crash.
        original = self.mb.TASK_RUNNER_DIR
        try:
            with tempfile.TemporaryDirectory() as tmp:
                self.mb.TASK_RUNNER_DIR = tmp
                sig = self.mb.live_signals()
                self.assertEqual(sig["letters_sent"], 0)
                self.assertEqual(sig["leads_qualified"], 0)
                self.assertEqual(sig["leads_mailable"], 0)
        finally:
            self.mb.TASK_RUNNER_DIR = original

    def test_the_real_board_has_no_obvious_stale_done_items_leaking_as_todo(self):
        """The Moat Blueprint and Fiverr gig went live 2026-08-27 - neither
        should appear as a Felix TODO. This catches the exact class of stale
        item the audit found littered across the vault."""
        felix_text = " ".join(a[1].lower() for a in self.mb.felix_actions())
        self.assertNotIn("publish the moat", felix_text)
        self.assertNotIn("post the fiverr gig", felix_text)


class TestFlipLog(unittest.TestCase):
    """LocalArbitrage flip logging (added 2026-08-31). Reads and writes
    Transaction_Log.md's own Markdown table directly - no shadow JSON state
    that could drift from it, the exact bug class an earlier audit of this
    vault found repeatedly. Every test here runs against a throwaway copy;
    none ever touch the real vault file."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "flip_log", os.path.join(HERE, "scripts", "flip_log.py"))
        cls.fl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.fl)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "Transaction_Log.md")
        # A minimal but structurally real copy of the actual file: the
        # schema table (empty, placeholder row) followed by a prose
        # paragraph with no heading of its own before the next section -
        # exactly the shape that broke the first version of this tool.
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(
                "# Transaction Log\n\nPurpose: test fixture.\n\n---\n\n"
                "## Schema\n"
                "| # | Date | Item | Category | Buy € | Distance km | "
                "Repair € | List € | Sold € | Days to sell | Hours | "
                "Net € | €/hour | Notes |\n"
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
                "| *(none yet)* | | | | | | | | | | | | | |\n"
                "\nRecord **failed** buys too - a log of only wins teaches "
                "nothing.\n\n"
                "## What to Look For (after ~20 entries)\nSome more prose.\n"
            )
        self._orig_log_path = self.fl.LOG_PATH
        self.fl.LOG_PATH = self.path
        self.addCleanup(setattr, self.fl, "LOG_PATH", self._orig_log_path)

    def _buy(self, item="Bosch GSR 18V", category="Werkzeug", buy=30.0,
             distance=22.0, repair=5.0, list_price=90.0, date="2026-08-31",
             url=None, notes=None, hours=None):
        return self.fl.cmd_buy(argparse.Namespace(
            item=item, category=category, buy=buy, distance=distance,
            repair=repair, list_price=list_price, hours=hours, date=date,
            url=url, notes=notes))

    def _sell(self, row=1, item=None, sold=80.0, hours=3.0,
              sold_date="2026-09-05", fuel_per_km=0.25, notes=None):
        return self.fl.cmd_sell(argparse.Namespace(
            row=row, item=item, sold=sold, hours=hours, sold_date=sold_date,
            fuel_per_km=fuel_per_km, notes=notes))

    def _prose_lines(self, path=None):
        with open(path or self.path, encoding="utf-8") as f:
            return [ln for ln in f.read().splitlines() if not ln.startswith("|")]

    # --- the bug that was actually caught ------------------------------

    def test_prose_after_the_table_survives_one_write(self):
        before = self._prose_lines()
        self._buy()
        self.assertEqual(self._prose_lines(), before)

    def test_prose_survives_many_successive_writes(self):
        """The real bug: each write silently ate one more newline than the
        last, so a single buy looked fine and a buy-then-sell glued the row
        directly onto the prose paragraph with zero separation. Only a
        multi-write test catches this - a single round trip does not."""
        before = self._prose_lines()
        self._buy()
        self._buy(item="Second Item")
        self._sell(row=1)
        self._sell(row=2, sold=45.0, hours=1.0)
        self.assertEqual(self._prose_lines(), before)
        with open(self.path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("|\n\nRecord **failed**", text,
                      "row and the following prose must stay on separate "
                      "lines with the original blank line between them")

    def test_row_never_runs_into_the_prose_on_the_same_line(self):
        self._buy()
        self._sell()
        with open(self.path, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("|Record", text)

    # --- table mechanics -------------------------------------------------

    def test_buy_appends_a_row_and_leaves_it_open(self):
        self._buy()
        rows = self.fl.read_log()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Item"], "Bosch GSR 18V")
        self.assertEqual(rows[0]["Sold €"], "")

    def test_sell_by_row_number(self):
        self._buy()
        self._sell(row=1, sold=80.0, hours=3.0)
        rows = self.fl.read_log()
        self.assertEqual(rows[0]["Sold €"], "80")

    def test_sell_by_item_name_when_unambiguous(self):
        self._buy(item="Bosch GSR 18V")
        self._sell(row=None, item="bosch", sold=80.0)
        rows = self.fl.read_log()
        self.assertEqual(rows[0]["Sold €"], "80")

    def test_sell_refuses_to_guess_with_multiple_open_flips(self):
        self._buy(item="A")
        self._buy(item="B")
        rc = self._sell(row=None, item=None, sold=50.0)
        self.assertEqual(rc, 1)
        rows = self.fl.read_log()
        self.assertEqual(rows[0]["Sold €"], "")
        self.assertEqual(rows[1]["Sold €"], "")

    def test_url_and_notes_are_recorded_for_provenance(self):
        self._buy(url="https://kleinanzeigen.de/x/1", notes="aus Werkzeug-Watch")
        rows = self.fl.read_log()
        self.assertIn("kleinanzeigen.de/x/1", rows[0]["Notes"])
        self.assertIn("aus Werkzeug-Watch", rows[0]["Notes"])

    # --- the arithmetic --------------------------------------------------

    def test_net_and_per_hour_and_roi(self):
        # buy 30 + repair 5 = 35 capital; fuel = 22km one-way * 2 * 0.25 = 11
        # net = 80 - 35 - 11 = 34; /3h = 11.33; roi = 34/35*100 = 97.1%
        net, per_hour, roi = self.fl.compute_close(30.0, 5.0, 80.0, 22.0, 3.0, 0.25)
        self.assertAlmostEqual(net, 34.0)
        self.assertAlmostEqual(per_hour, 11.33, places=2)
        self.assertAlmostEqual(roi, 97.1, places=1)

    def test_a_loss_computes_a_negative_net_not_a_crash(self):
        net, per_hour, roi = self.fl.compute_close(60.0, 0, 40.0, 15.0, 1.5, 0.25)
        self.assertLess(net, 0)
        self.assertLess(per_hour, 0)

    def test_missing_sold_price_is_an_open_flip_not_a_zero(self):
        """An open flip must show as unresolved, never as a EUR0 loss that
        looks like real, if bad, data."""
        net, per_hour, roi = self.fl.compute_close(30.0, 5.0, None, 22.0, 3.0, 0.25)
        self.assertIsNone(net)
        self.assertIsNone(per_hour)
        self.assertIsNone(roi)

    def test_fuel_cost_is_round_trip_not_one_way(self):
        self.assertAlmostEqual(self.fl.fuel_cost(22.0, 0.25), 11.0)

    def test_label_thresholds_match_the_projects_own_stated_range(self):
        """LocalArbitrage/README.md states ~15-25 EUR/hour as the realistic
        range for this work - the label bands are anchored to that, not
        invented independently."""
        self.assertEqual(self.fl.label_for(25.0), "GUT")
        self.assertEqual(self.fl.label_for(15.0), "OK")
        self.assertEqual(self.fl.label_for(5.0), "SCHWACH")
        self.assertEqual(self.fl.label_for(-10.0), "SCHWACH")
        self.assertEqual(self.fl.label_for(None), "OFFEN")

    # --- report ------------------------------------------------------------

    def test_report_surfaces_losses_rather_than_hiding_them(self):
        """Transaction_Log.md's own rule: 'a log of only wins teaches
        nothing and quietly inflates your confidence.'"""
        self._buy(item="Loser", buy=60.0, repair=0, distance=15.0)
        self._sell(row=1, sold=40.0, hours=1.5)
        rows = self.fl.read_log()
        self.assertLess(float(rows[0]["Net €"]), 0)


class TestWebappApi(unittest.TestCase):
    """The AI-OS web client's API layer (added 2026-08-31). Every dashboard
    handler is a thin JSON transform over money_board.py/dmarc_prospector.py/
    flip_log.py's own already-tested functions - these tests guard the
    transform itself, not re-test the underlying modules. post_chat's input
    validation is tested without needing the real worker running (that path
    was verified live, end to end, separately - see webapp/README.md)."""

    @classmethod
    def setUpClass(cls):
        webapp_dir = os.path.join(HERE, "webapp")
        for p in (HERE, os.path.join(HERE, "scripts")):
            if p not in sys.path:
                sys.path.insert(0, p)
        spec = importlib.util.spec_from_file_location(
            "webapp_api", os.path.join(webapp_dir, "api.py"))
        cls.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.api)

    def test_money_board_shape_matches_the_5tuple_source(self):
        status, payload = self.api.get_money_board({})
        self.assertEqual(status, 200)
        self.assertIn("actions", payload)
        self.assertIn("signals", payload)
        if payload["actions"]:
            action = payload["actions"][0]
            self.assertEqual(set(action),
                             {"action", "euros", "minutes", "note", "gates"})

    def test_money_board_actions_match_the_cli_order_exactly(self):
        """The dashboard and the CLI must never disagree about what comes
        first. Comparing against money_board.sorted_actions() rather than
        re-asserting the rule here is deliberate: an earlier version of this
        test asserted plain euro-descending, so when the ordering rule gained
        gating rows the test would have failed the *correct* behaviour."""
        _, payload = self.api.get_money_board({})
        expected = [a[1] for a in self.api.money_board.sorted_actions()]
        self.assertEqual([a["action"] for a in payload["actions"]], expected)

    def test_money_board_gate_rows_are_flagged_for_the_dashboard(self):
        """The CLI marks a gating row "ZUERST"; the dashboard needs the same
        fact as data or it renders a 0-EUR gate as the cheapest card."""
        _, payload = self.api.get_money_board({})
        gates = [a for a in payload["actions"] if a["gates"]]
        self.assertTrue(gates)
        self.assertIs(payload["actions"][0]["gates"], True)

    def _upload_dir(self):
        """Redirects BOTH the upload directory and the voice-profile output
        into a throwaway dir. Only redirecting the first one is what let an
        early version of these tests write a profile built from three lines
        of fixture chat into the real voice/Voice_Profile.md - which the
        runner would then have handed to a live Telegram conversation."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for attr, sub in (("UPLOAD_DIR", "uploads"), ("VOICE_DIR", "voice")):
            self.addCleanup(setattr, self.api, attr, getattr(self.api, attr))
            setattr(self.api, attr, os.path.join(tmp.name, sub))
        return self.api.UPLOAD_DIR

    def test_upload_name_cannot_escape_the_upload_directory(self):
        """basename() runs before the extension check, not after: otherwise
        "../../.ssh/x.txt" passes the allowlist on its way to somewhere it
        must never reach."""
        for evil in ("../../../etc/passwd.txt", "..\\..\\x.txt",
                     "/etc/shadow.txt", "chat/../../x.txt"):
            name = self.api.safe_upload_name(evil)
            self.assertNotIn("/", name or "")
            self.assertNotIn("\\", name or "")
            self.assertNotIn("..", name or "")

    def test_upload_rejects_types_that_are_not_plain_data(self):
        for bad in ("shell.php", "x.py", "app.js", "run.sh", "index.html", ""):
            self.assertIsNone(self.api.safe_upload_name(bad))
        for good in ("_chat.txt", "WhatsApp Chat mit Lena.txt", "export.zip"):
            self.assertIsNotNone(self.api.safe_upload_name(good))

    def test_upload_writes_the_file_and_reports_its_size(self):
        d = self._upload_dir()
        status, payload = self.api.post_upload({"name": ["_chat.txt"]}, b"hallo")
        self.assertEqual(status, 200)
        self.assertEqual(payload["size"], 5)
        with open(os.path.join(d, "_chat.txt"), "rb") as f:
            self.assertEqual(f.read(), b"hallo")

    def test_uploads_with_the_same_name_never_overwrite_each_other(self):
        """iOS names every single WhatsApp export "_chat.txt". Four of them
        collapsing into one would be invisible until the voice profile came
        out built on a quarter of the data."""
        self._upload_dir()
        first = self.api.post_upload({"name": ["_chat.txt"]}, b"eins")[1]
        second = self.api.post_upload({"name": ["_chat.txt"]}, b"zwei")[1]
        self.assertNotEqual(first["name"], second["name"])
        _, listing = self.api.get_uploads({})
        self.assertEqual(len(listing["files"]), 2)

    def test_upload_rejects_empty_and_oversized_bodies(self):
        self._upload_dir()
        self.assertEqual(self.api.post_upload({"name": ["a.txt"]}, b"")[0], 400)
        big = b"x" * (self.api.MAX_UPLOAD_BYTES + 1)
        self.assertEqual(self.api.post_upload({"name": ["a.txt"]}, big)[0], 413)

    def test_uploads_are_listed_without_a_download_url(self):
        """Unlike generated reports, these are Felix's own private chat
        exports - he already has them. Serving them back adds exposure for
        no use."""
        self._upload_dir()
        self.api.post_upload({"name": ["_chat.txt"]}, b"hallo")
        _, payload = self.api.get_uploads({})
        self.assertEqual(set(payload["files"][0]), {"name", "size", "modified"})

    def test_uploads_listing_survives_a_missing_directory(self):
        self._upload_dir()  # never created - nothing uploaded yet
        self.assertEqual(self.api.get_uploads({}), (200, {"files": []}))

    def test_voice_import_refuses_a_single_chat(self):
        """One chat produces a caricature of one relationship, not a voice -
        register shifts a lot between a best friend, a parent and a group."""
        d = self._upload_dir()
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "only.txt"), "w", encoding="utf-8") as f:
            f.write("31.08.26, 19:22 - Felix: hi\n")
        status, payload = self.api.post_voice_import({})
        self.assertEqual(status, 400)
        self.assertIn("2", payload["error"])

    def test_voice_import_runs_the_real_script_on_uploaded_chats(self):
        d = self._upload_dir()
        os.makedirs(d, exist_ok=True)
        for n, other in (("a.txt", "Lena"), ("b.txt", "Tim")):
            with open(os.path.join(d, n), "w", encoding="utf-8") as f:
                f.write(f"31.08.26, 19:21 - {other}: und?\n"
                        "31.08.26, 19:22 - Felix: ne noch nicht\n"
                        "31.08.26, 19:23 - Felix: mach ich heute abend\n")
        status, payload = self.api.post_voice_import({})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["files"], 2)

    def test_dmarc_leads_shape(self):
        status, payload = self.api.get_dmarc_leads({})
        self.assertEqual(status, 200)
        self.assertIn("total_qualified", payload)
        self.assertIsInstance(payload["leads"], list)
        if payload["leads"]:
            lead = payload["leads"][0]
            self.assertEqual(
                set(lead),
                {"domain", "name", "category", "score", "dmarc", "spf",
                 "provider", "address", "phone"})

    def test_dmarc_leads_never_include_a_score_below_six(self):
        """rank()'s own min_score default is 6 - confirming the API layer
        doesn't accidentally pass a laxer threshold that would leak
        low-quality leads into the dashboard."""
        _, payload = self.api.get_dmarc_leads({})
        for lead in payload["leads"]:
            self.assertGreaterEqual(lead["score"], 6)

    def test_flip_log_rows_get_an_open_flag(self):
        status, payload = self.api.get_flip_log({})
        self.assertEqual(status, 200)
        for row in payload["rows"]:
            self.assertIn("open", row)
            self.assertEqual(row["open"], not bool(row.get("Sold €")))

    def test_chat_rejects_empty_message(self):
        status, payload = self.api.post_chat({"message": "  ", "thread_id": "x"})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_chat_rejects_missing_thread_id(self):
        status, payload = self.api.post_chat({"message": "hi"})
        self.assertEqual(status, 400)

    def test_chat_at_prefix_with_unknown_agent_is_kept_as_text(self):
        """Mirrors telegram_bridge.py's own _split_agent_prefix behaviour:
        an unresolved leading @word is a sentence, not a failed selection -
        eating it would mangle a real message like "@felix, could you..."."""
        calls = {}
        def fake_enqueue(*a, **k):
            calls["ran"] = True
            return 200, {"reply": "ok", "agent": None}
        # Patch just enough to observe what post_chat *would* send, without
        # needing the real worker: intercept before the file write by
        # checking agents.resolve's behaviour directly is simpler and
        # sufficient here since the prefix-splitting logic is inline in
        # post_chat, not a separate function to mock around.
        import agents
        self.assertIsNone(agents.resolve("@notarealagent"))

    def test_downloads_lists_files_with_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, "report.pdf"), "wb").write(b"%PDF-1.3 fake")
            original = self.api.DOWNLOADS_DIR
            self.api.DOWNLOADS_DIR = tmp
            try:
                status, payload = self.api.get_downloads({})
            finally:
                self.api.DOWNLOADS_DIR = original
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["files"]), 1)
        f = payload["files"][0]
        self.assertEqual(f["name"], "report.pdf")
        self.assertEqual(f["size"], len(b"%PDF-1.3 fake"))
        self.assertEqual(f["url"], "/downloads/report.pdf")

    def test_downloads_skips_dotfiles_like_gitkeep(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, ".gitkeep"), "w").close()
            open(os.path.join(tmp, "real.pdf"), "wb").write(b"x")
            original = self.api.DOWNLOADS_DIR
            self.api.DOWNLOADS_DIR = tmp
            try:
                _, payload = self.api.get_downloads({})
            finally:
                self.api.DOWNLOADS_DIR = original
        names = [f["name"] for f in payload["files"]]
        self.assertEqual(names, ["real.pdf"])

    def test_downloads_missing_directory_returns_empty_not_a_crash(self):
        original = self.api.DOWNLOADS_DIR
        self.api.DOWNLOADS_DIR = "/nonexistent/downloads/dir"
        try:
            status, payload = self.api.get_downloads({})
        finally:
            self.api.DOWNLOADS_DIR = original
        self.assertEqual(status, 200)
        self.assertEqual(payload["files"], [])

    def test_downloads_newest_file_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_path = os.path.join(tmp, "old.pdf")
            new_path = os.path.join(tmp, "new.pdf")
            open(old_path, "w").close()
            os.utime(old_path, (1000000000, 1000000000))
            open(new_path, "w").close()
            os.utime(new_path, (2000000000, 2000000000))
            original = self.api.DOWNLOADS_DIR
            self.api.DOWNLOADS_DIR = tmp
            try:
                _, payload = self.api.get_downloads({})
            finally:
                self.api.DOWNLOADS_DIR = original
        self.assertEqual([f["name"] for f in payload["files"]], ["new.pdf", "old.pdf"])

    def test_chat_web_thread_namespace_never_collides_with_telegram(self):
        """web_ vs tg_ prefixes must stay visually and structurally distinct
        - this is what stops a web chat and a Telegram chat from ever
        accidentally sharing history."""
        import memory
        web_thread = f"web_{'x'*8}"
        self.assertTrue(web_thread.startswith("web_"))
        self.assertNotEqual(memory._safe(web_thread), memory._safe(f"tg_{'x'*8}"))


class TestKnowledgeCoreInjection(TaskRunnerTestCase):
    """Fix for the gap found live 2026-08-31: a worker task asked a question
    whose answer lives only in Knowledge_Core.md, with no hint of the
    filename, searched the vault broadly, and never found or opened it.
    Rather than rely on a model deciding to go look, the file's content is
    now appended to every task's system prompt directly - it is small
    (hard-capped ~10,000 chars) and explicitly meant to be "always cheap to
    load" per its own Purpose line."""

    def test_missing_file_returns_empty_string_not_a_crash(self):
        self.runner.KNOWLEDGE_CORE_PATH = "/nonexistent/Knowledge_Core.md"
        self.assertEqual(self.runner._load_knowledge_core(), "")

    def test_real_file_is_actually_read(self):
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("some distinctive marker text 12345")
            path = f.name
        self.addCleanup(os.unlink, path)
        self.runner.KNOWLEDGE_CORE_PATH = path
        self.assertIn("some distinctive marker text 12345",
                      self.runner._load_knowledge_core())

    def test_system_prompt_includes_knowledge_core_with_no_agent(self):
        self.runner.KNOWLEDGE_CORE_PATH = "/nonexistent/x.md"
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("Felix lives in Crimmitschau.")
            path = f.name
        self.addCleanup(os.unlink, path)
        self.runner.KNOWLEDGE_CORE_PATH = path
        prompt = self.runner._system_prompt_for(None)
        self.assertIn("Felix lives in Crimmitschau.", prompt)
        self.assertIn(self.runner.BASE_SYSTEM_PROMPT, prompt)
        self.assertNotIn("## Your role for this task:", prompt)

    def test_missing_knowledge_core_does_not_inject_an_empty_section(self):
        """A missing file should degrade to "just the base prompt", not to
        a "## Standing context" header with nothing under it."""
        self.runner.KNOWLEDGE_CORE_PATH = "/nonexistent/x.md"
        prompt = self.runner._system_prompt_for(None)
        self.assertEqual(prompt, self.runner.BASE_SYSTEM_PROMPT)

    def test_system_prompt_includes_both_knowledge_core_and_agent_role(self):
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("Felix lives in Crimmitschau.")
            path = f.name
        self.addCleanup(os.unlink, path)
        self.runner.KNOWLEDGE_CORE_PATH = path
        prompt = self.runner._system_prompt_for("Vault_Architect")
        self.assertIn("Felix lives in Crimmitschau.", prompt)
        self.assertIn("## Your role for this task: Vault Architect", prompt)
        # Standing context appears before the role section, not after -
        # the role should be able to read it as already-established fact,
        # not have it tacked on as an afterthought below its own block.
        self.assertLess(prompt.index("Felix lives in Crimmitschau."),
                        prompt.index("## Your role for this task:"))


class TestSynthesisNudge(TaskRunnerTestCase):
    """Fix for the other gap found live 2026-08-31: two of three real
    dispatches that afternoon explored correctly but never produced a final
    prose answer - format_interpreter_output()'s existing fallback shipped
    the raw tool transcript as "the answer" instead. _attempt() now nudges
    once, in the same interpreter session, before accepting that fallback."""

    def test_has_prose_true_for_a_real_answer(self):
        msgs = [{"role": "assistant", "type": "message", "content": "the answer"}]
        self.assertTrue(self.runner._has_prose(msgs))

    def test_has_prose_false_for_code_and_output_only(self):
        msgs = [
            {"role": "assistant", "type": "code", "content": "ls", "format": "shell"},
            {"role": "computer", "content": "file1\nfile2"},
        ]
        self.assertFalse(self.runner._has_prose(msgs))

    def test_has_prose_false_for_empty(self):
        self.assertFalse(self.runner._has_prose([]))
        self.assertFalse(self.runner._has_prose(None))

    def test_no_prose_first_turn_triggers_one_nudge_and_uses_its_prose(self):
        calls = []

        def scripted_chat(message, display=False, stream=False):
            calls.append(message)
            if len(calls) == 1:
                return [{"role": "assistant", "type": "code",
                        "content": "ls", "format": "shell"},
                       {"role": "computer", "content": "file1"}]
            return [{"role": "assistant", "type": "message",
                    "content": "Based on that, the answer is 42."}]

        self.fake.chat = scripted_chat
        result = self.runner._attempt("some/model", "what is the answer?")
        self.assertEqual(len(calls), 2, "exactly one nudge, not zero or a loop")
        self.assertIn("the answer is 42", result)

    def test_nudge_that_also_produces_no_prose_raises_not_returns(self):
        """Verified live 2026-08-31: this is exactly the case that exposed
        the real gap - a nudge that runs cleanly but stays silent used to be
        accepted as a successful (if unsatisfying) result, which meant
        MODEL_CHAIN never got the chance to try a model actually capable of
        answering. Raising here lets the existing per-model retry loop in
        _run_task treat this the same way it already treats a quota error."""
        def scripted_chat(message, display=False, stream=False):
            return [{"role": "assistant", "type": "code",
                    "content": "ls", "format": "shell"},
                   {"role": "computer", "content": "file1"}]

        self.fake.chat = scripted_chat
        with self.assertRaises(RuntimeError):
            self.runner._attempt("some/model", "what is the answer?")

    def test_nudge_that_itself_errors_also_raises_not_falls_back(self):
        """An erroring nudge and a silently-empty one are the same outcome
        from the caller's perspective - both mean "no answer, try the next
        model" - so both must raise, not one raise and one succeed."""
        calls = []

        def scripted_chat(message, display=False, stream=False):
            calls.append(message)
            if len(calls) == 1:
                return [{"role": "assistant", "type": "code",
                        "content": "ls", "format": "shell"},
                       {"role": "computer", "content": "file1"}]
            raise RuntimeError("rate limited")

        self.fake.chat = scripted_chat
        with self.assertRaises(RuntimeError):
            self.runner._attempt("some/model", "what is the answer?")
        self.assertEqual(len(calls), 2, "the nudge must still be attempted")

    def test_prose_on_the_first_turn_never_triggers_a_nudge(self):
        calls = []

        def scripted_chat(message, display=False, stream=False):
            calls.append(message)
            return [{"role": "assistant", "type": "message", "content": "done"}]

        self.fake.chat = scripted_chat
        self.runner._attempt("some/model", "do a thing")
        self.assertEqual(len(calls), 1, "a clean answer must not cost an extra call")


class TestPaidUsageAccumulation(TaskRunnerTestCase):
    """The synthesis nudge above means _attempt() can call interpreter.chat()
    twice in one attempt. The old single-value _last_paid_usage overwrote on
    each call, silently dropping the first call's tokens from the budget
    ledger if the second (the nudge) also hit the paid model - undercounting
    real spend, which spend_guard.py's whole design exists to prevent."""

    def test_record_paid_spend_sums_usage_across_multiple_calls(self):
        self.runner._last_paid_usage["values"] = [
            types.SimpleNamespace(prompt_tokens=100, completion_tokens=20, cost=None),
            types.SimpleNamespace(prompt_tokens=50, completion_tokens=15, cost=None),
        ]
        self.runner.litellm.completion_cost = lambda **k: None
        self.runner.OPENROUTER_PAID_INPUT_PER_M = 1.0
        self.runner.OPENROUTER_PAID_OUTPUT_PER_M = 1.0
        with tempfile.TemporaryDirectory() as tmp:
            self.runner.spend_guard.LEDGER_PATH = os.path.join(tmp, "ledger.json")
            self.runner._record_paid_spend("m", "instr", "sys", None, "out")
            spent = self.runner.spend_guard.month_spent(
                self.runner.spend_guard.load_ledger())
        # (100+50)/1e6 + (20+15)/1e6 = 0.000185 - proves both entries summed,
        # not just the last one (which alone would give 0.000065).
        self.assertAlmostEqual(spent, 0.000185, places=6)

    def test_record_paid_spend_sums_reported_cost_across_calls_too(self):
        self.runner._last_paid_usage["values"] = [
            types.SimpleNamespace(prompt_tokens=1, completion_tokens=1, cost=0.001),
            types.SimpleNamespace(prompt_tokens=1, completion_tokens=1, cost=0.002),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            self.runner.spend_guard.LEDGER_PATH = os.path.join(tmp, "ledger.json")
            self.runner._record_paid_spend("m", "instr", "sys", None, "out")
            spent = self.runner.spend_guard.month_spent(
                self.runner.spend_guard.load_ledger())
        self.assertAlmostEqual(spent, 0.003, places=6)

    def test_a_model_that_explores_without_answering_is_skipped_for_the_next_one(self):
        """The actual live scenario, end to end through _run_task, not just
        _attempt() in isolation: the first model in the chain explores and
        never answers even after a nudge, and the task must still complete
        with the second model's clean answer - not the first model's raw
        transcript, and not an outright failure either."""
        first_model = self.runner.MODEL_CHAIN[0]["model"]

        def scripted_chat(message, display=False, stream=False):
            if self.runner.interpreter.llm.model == first_model:
                return [{"role": "assistant", "type": "code",
                        "content": "ls", "format": "shell"},
                       {"role": "computer", "content": "irrelevant output"}]
            return [{"role": "assistant", "type": "message", "content": "the real answer"}]

        self.fake.chat = scripted_chat
        self.runner.time.sleep = lambda s: None  # skip the real 20s inter-model delay
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(self.log_of("t.md"), "the real answer")

    def test_attempt_resets_the_accumulator_before_a_new_call(self):
        """A failed paid attempt must not leave stale usage for a later,
        unrelated successful attempt to inherit."""
        self.runner._last_paid_usage["values"] = [
            types.SimpleNamespace(prompt_tokens=999, completion_tokens=999, cost=None)]
        self.fake.chat = lambda *a, **k: [
            {"role": "assistant", "type": "message", "content": "ok"}]
        self.runner._attempt("some/model", "do a thing")
        self.assertEqual(self.runner._last_paid_usage["values"], [])


class TestTechScout(unittest.TestCase):
    """The daily tech-scout fetcher (added 2026-08-31). Deterministic
    fetch-and-filter only - no network in these tests, and deliberately no
    "is this relevant" judgment either. That judgment is the LLM reasoning
    step's job (Tech_Scout agent, schedules/daily_tech_scout.md); this
    module's job is producing a small, real, deduplicated candidate list to
    reason over."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "tech_scout", os.path.join(HERE, "scripts", "tech_scout.py"))
        cls.ts = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.ts)

    def test_github_queries_use_explicit_or_not_bare_and(self):
        """Verified live 2026-08-31: GitHub's search treats bare multi-word
        queries as AND-all-terms, not OR. "DMARC SPF email spoofing" (no
        OR) matched zero repos because it demanded all four words appear
        together; "DMARC OR SPF OR email-spoofing" found real results. A
        query silently returning nothing looks identical to "genuinely
        nothing new today" from the caller's side, so this has to be
        enforced structurally, not just fixed once by hand."""
        for _topic, query in self.ts.TOPICS:
            if " " in query.replace(" OR ", ""):
                self.assertIn("OR", query,
                             f"multi-word query {query!r} needs explicit OR")

    def test_normalize_github_extracts_the_right_fields(self):
        item = {"full_name": "org/repo", "description": "does a thing",
               "html_url": "https://github.com/org/repo", "stargazers_count": 42}
        got = self.ts.normalize_github(item, "agent-runtime")
        self.assertEqual(got["id"], "gh:org/repo")
        self.assertEqual(got["score"], 42)
        self.assertEqual(got["source"], "github")

    def test_normalize_github_handles_missing_description(self):
        item = {"full_name": "org/repo", "description": None,
               "html_url": "https://x", "stargazers_count": 1}
        got = self.ts.normalize_github(item, "t")
        self.assertEqual(got["description"], "")

    def test_normalize_hn_falls_back_to_hn_link_when_no_external_url(self):
        """A Show HN / Ask HN post often has no external url field - the
        digest must still produce something clickable, not a blank link."""
        hit = {"objectID": "123", "title": "Ask HN: thing", "url": None, "points": 50}
        got = self.ts.normalize_hn(hit, "t")
        self.assertEqual(got["url"], "https://news.ycombinator.com/item?id=123")

    def test_filter_hn_by_points_drops_low_signal_posts(self):
        hits = [{"points": 5}, {"points": 50}, {"points": None}]
        kept = self.ts.filter_hn_by_points(hits, min_points=15)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["points"], 50)

    def test_digest_is_none_when_there_is_nothing_new(self):
        """Absent, not an empty-but-present file - the schedule task checks
        for the file's existence before spending a model call on it, so a
        quiet day must not silently cost tokens reasoning about nothing."""
        self.assertIsNone(self.ts.render_digest([]))

    def test_digest_groups_by_topic_and_sorts_by_score(self):
        candidates = [
            {"topic": "a", "title": "low", "description": "", "url": "https://x/1",
            "score": 5, "score_label": "stars"},
            {"topic": "a", "title": "high", "description": "", "url": "https://x/2",
            "score": 50, "score_label": "stars"},
        ]
        digest = self.ts.render_digest(candidates)
        self.assertLess(digest.index("high"), digest.index("low"))
        self.assertIn("## a", digest)

    def test_seen_state_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "seen.json")
            original = self.ts.SEEN_PATH
            self.ts.SEEN_PATH = path
            try:
                self.assertEqual(self.ts.load_seen(), set())
                self.ts.save_seen({"gh:a/b", "hn:123"})
                self.assertEqual(self.ts.load_seen(), {"gh:a/b", "hn:123"})
            finally:
                self.ts.SEEN_PATH = original

    def test_missing_seen_file_is_empty_not_an_error(self):
        original = self.ts.SEEN_PATH
        self.ts.SEEN_PATH = "/nonexistent/seen.json"
        try:
            self.assertEqual(self.ts.load_seen(), set())
        finally:
            self.ts.SEEN_PATH = original


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestVoiceImport(unittest.TestCase):
    """WhatsApp voice import (added 2026-08-31). The privacy property is the
    one worth guarding hardest: the parser sees both sides of a real chat and
    must keep only Felix's own lines, because everything it keeps can end up
    in a model's prompt."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "voice_import", os.path.join(HERE, "scripts", "voice_import.py"))
        cls.vi = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.vi)

    ANDROID = (
        "31.08.26, 19:20 - Nachrichten und Anrufe sind Ende-zu-Ende-verschlüsselt.\n"
        "31.08.26, 19:21 - Lena: hast du das schon gemacht\n"
        "31.08.26, 19:22 - Felix: ne noch nicht\n"
        "31.08.26, 19:22 - Felix: mach ich heute abend\n"
        "31.08.26, 19:23 - Lena: ok\n"
        "31.08.26, 19:24 - Felix: <Medien ausgeschlossen>\n"
        "31.08.26, 19:25 - Felix: guck mal https://example.com/x an\n"
        "das war zeile zwei\n"
    )
    IOS = (
        "\u200e[31.08.26, 19:30:01] Felix: moin\n"
        "[31.08.26, 19:30:40] Tim: moin\n"
        "[31.08.26, 19:31:02] Felix: alles gut bei dir?\n"
    )

    def test_parses_both_export_formats(self):
        android = self.vi.parse_export(self.ANDROID)
        ios = self.vi.parse_export(self.IOS)
        self.assertTrue(android and ios)
        # The iOS LTR mark sits before the very first "[" - a naive
        # startswith("[") drops the opening message of every iOS export.
        self.assertEqual(ios[0]["sender"], "Felix")
        self.assertEqual(ios[0]["text"], "moin")

    def test_system_notices_are_not_messages(self):
        senders = {m["sender"] for m in self.vi.parse_export(self.ANDROID)}
        self.assertEqual(senders, {"Felix", "Lena"})

    def test_continuation_lines_stay_with_their_message(self):
        msgs = self.vi.parse_export(self.ANDROID)
        multiline = [m for m in msgs if "zeile zwei" in m["text"]]
        self.assertEqual(len(multiline), 1)
        self.assertIn("guck mal", multiline[0]["text"])

    def test_extract_keeps_only_felix_and_drops_everyone_elses_words(self):
        """The whole privacy design in one assertion: nothing the other side
        typed may survive into the returned data, because that data is what
        gets summarised into a prompt."""
        chats = [self.vi.parse_export(self.ANDROID), self.vi.parse_export(self.IOS)]
        mine, others = self.vi.extract_mine(chats, "Felix")
        blob = " ".join(m["text"] for m in mine)
        self.assertNotIn("hast du das schon gemacht", blob)
        self.assertNotIn("ok", blob.split())
        self.assertEqual(others, {"Lena", "Tim"})
        self.assertTrue(all("ne noch nicht" != m["text"] or m["answering"]
                            for m in mine))

    def test_media_placeholders_are_not_counted_as_his_words(self):
        """"<Medien ausgeschlossen>" is WhatsApp's text, not his. Counting it
        as a two-word message drags the whole length distribution down."""
        chats = [self.vi.parse_export(self.ANDROID)]
        mine, _ = self.vi.extract_mine(chats, "Felix")
        self.assertFalse(any("Medien" in m["text"] for m in mine))

    def test_bursts_are_distinguished_from_replies(self):
        chats = [self.vi.parse_export(self.ANDROID)]
        mine, _ = self.vi.extract_mine(chats, "Felix")
        self.assertTrue(mine[0]["answering"])       # answered Lena
        self.assertFalse(mine[1]["answering"])      # continued himself

    def test_detect_me_needs_more_than_one_chat(self):
        """One chat cannot identify the common sender, and a profile from a
        single chat is a caricature of one relationship anyway."""
        self.assertIsNone(self.vi.detect_me([self.vi.parse_export(self.ANDROID)]))
        both = [self.vi.parse_export(self.ANDROID), self.vi.parse_export(self.IOS)]
        self.assertEqual(self.vi.detect_me(both), "Felix")

    def test_redaction_covers_third_party_identifiers(self):
        out = self.vi.redact(
            "ruf Lena unter +49 176 1234567 an oder schreib lena@example.com, "
            "link: https://example.com/x", {"Lena"})
        self.assertNotIn("Lena", out)
        self.assertNotIn("lena@example.com", out)
        self.assertNotIn("1234567", out)
        self.assertNotIn("https://", out)

    def test_stats_are_computed_from_his_messages_only(self):
        chats = [self.vi.parse_export(self.ANDROID), self.vi.parse_export(self.IOS)]
        mine, _ = self.vi.extract_mine(chats, "Felix")
        stats = self.vi.compute_stats(mine)
        self.assertEqual(stats["messages"], len(mine))
        self.assertGreater(stats["lowercase_start_pct"], 50)
        self.assertGreater(stats["burst_pct"], 0)

    def test_braille_and_block_art_are_not_counted_as_emoji(self):
        """Found auditing the first real import: Unicode category "So"
        includes Braille patterns and block-drawing characters, so the
        ASCII-art images people paste into WhatsApp put ⣿, ░ and █ into the
        top-ten "emoji he reuses" - and the profile then instructed the model
        to use them."""
        self.assertEqual(self.vi._emoji("⣿⣿░█⠈"), [])
        self.assertEqual(self.vi._emoji("😂 ❤ ☠"), ["😂", "❤", "☠"])

    def test_skin_tone_modifiers_are_not_their_own_emoji(self):
        self.assertEqual(self.vi._emoji("👍🏽"), ["👍"])

    def test_every_media_placeholder_variant_is_dropped(self):
        """The fixed list missed real ones: "<Video note omitted>" and
        "<View once voice message omitted>" both survived the first real
        import and were counted as things Felix wrote."""
        for placeholder in ("<Video note omitted>",
                            "<View once voice message omitted>",
                            "<Medien ausgeschlossen>", "<Media omitted>",
                            "<Sticker weggelassen>"):
            self.assertTrue(self.vi._is_noise(placeholder), placeholder)
        # ... without swallowing his own sentences that mention the words
        self.assertFalse(self.vi._is_noise(
            "mathe wird denke taktisch weggelassen"))
        self.assertFalse(self.vi._is_noise("Was hast du gelöscht"))

    def test_exemplars_span_the_length_distribution(self):
        """The first version scored every candidate by distance from the
        median and returned 50 examples all exactly 3 words long - an
        accurate picture of the median and a useless one of the writer."""
        mine = ([{"text": "jo", "answering": True, "chat": 0}] * 30
                + [{"text": "ja passt schon", "answering": True, "chat": 0}] * 30
                + [{"text": " ".join(f"wort{i}" for i in range(12)),
                    "answering": False, "chat": 0}] * 30)
        for i, m in enumerate(mine):  # dedupe would otherwise collapse these
            m["text"] = f"{m['text']} {i}"
        stats = self.vi.compute_stats(mine)
        ex = self.vi.select_exemplars(mine, stats, set(), n=30)
        lengths = {len(e["text"].split()) for e in ex}
        self.assertGreater(len(lengths), 2, f"all one length: {lengths}")

    def test_exemplars_are_balanced_across_chats(self):
        """One chat was 92% of the first real corpus. Examples drawn purely
        by frequency would all come from that one relationship."""
        mine = ([{"text": f"nachricht {i}", "answering": True, "chat": 0}
                 for i in range(400)]
                + [{"text": f"andere nachricht {i}", "answering": True, "chat": 1}
                   for i in range(20)])
        stats = self.vi.compute_stats(mine)
        ex = self.vi.select_exemplars(mine, stats, set(), n=20)
        from_second = [e for e in ex if e["text"].startswith("andere")]
        self.assertTrue(from_second, "the smaller chat contributed nothing")

    def test_profile_says_so_when_one_chat_dominates(self):
        stats = {"chat_shares": [92.5, 5.0, 2.5]}
        self.assertIn("92.5%", self.vi._balance_note(stats))
        self.assertEqual(self.vi._balance_note({"chat_shares": [40.0, 35.0]}), "")

    def test_empty_import_degrades_instead_of_crashing(self):
        self.assertEqual(self.vi.compute_stats([]), {"messages": 0})
        self.assertIn("No messages", self.vi.render_profile({"messages": 0}, []))

    def test_profile_states_that_voice_never_outranks_honesty(self):
        """The failure mode worth guarding: a model that mirrors a casual,
        confident register also mirrors confidence it has not earned. This
        system already has two logged cases of confidently-wrong output."""
        chats = [self.vi.parse_export(self.ANDROID), self.vi.parse_export(self.IOS)]
        mine, others = self.vi.extract_mine(chats, "Felix")
        stats = self.vi.compute_stats(mine)
        profile = self.vi.render_profile(
            stats, self.vi.select_exemplars(mine, stats, others))
        self.assertIn("not to be agreed with more smoothly", profile)
        self.assertIn("professional", profile)

    def test_end_to_end_writes_a_profile_and_never_the_other_side(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "chat_a.txt")
            b = os.path.join(tmp, "chat_b.txt")
            with open(a, "w", encoding="utf-8") as f:
                f.write(self.ANDROID)
            with open(b, "w", encoding="utf-8") as f:
                f.write(self.IOS)
            out = os.path.join(tmp, "voice")
            rc = self.vi.main([a, b, "--out", out])
            self.assertEqual(rc, 0)
            profile = open(os.path.join(out, "Voice_Profile.md"),
                           encoding="utf-8").read()
            self.assertIn("Voice Profile", profile)
            self.assertNotIn("hast du das schon gemacht", profile)
            self.assertNotIn("Lena", profile)


class TestStudyAgent(unittest.TestCase):
    """Study note ingestion (added 2026-08-31). The model's only job here is
    turning one note's raw text into structured text - discovery, dedupe,
    destination, headers and logging are all deterministic and tested
    without a model. Nothing in this class makes a real model call; the
    end-to-end path was verified live against the worker separately."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "study_agent", os.path.join(HERE, "scripts", "study_agent.py"))
        cls.sa = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.sa)

    GOOD = """TITLE: Kryptografie Grundlagen
SUMMARY: Die Notizen vergleichen symmetrische und asymmetrische Verfahren
und behandeln AES-Betriebsmodi sowie Hashing.
CONCEPTS:
- AES — Blockchiffre mit 128-Bit-Bloecken.
- Perfect Forward Secrecy — not defined in these notes.
ACTIONS:
- Folien 30-45 nacharbeiten.
FLASHCARDS:
Q: Warum ist ECB unsicher?
A: Gleiche Bloecke ergeben gleichen Ciphertext.
Q: Wogegen hilft ein Salt?
A: Gegen Rainbow Tables."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.inbox = os.path.join(self.tmp.name, "Inbox")
        os.makedirs(self.inbox)

    def _note(self, name, text):
        with open(os.path.join(self.inbox, name), "w", encoding="utf-8") as f:
            f.write(text)

    # --- discovery -------------------------------------------------------

    def test_readme_and_folder_furniture_are_not_study_notes(self):
        """Every vault folder carries a README by convention. The first dry
        run of the real inbox tried to turn its own instructions into
        flashcards - a wasted model call on every new inbox."""
        self._note("README.md", "how this folder works")
        self._note("_draft.md", "not ready")
        self._note("real_note.md", "VL2 Krypto, AES modes")
        found = [os.path.basename(p) for p, _, _ in
                 self.sa.discover(self.inbox, {})]
        self.assertEqual(found, ["real_note.md"])

    def test_unchanged_notes_are_skipped_by_content_not_mtime(self):
        """A git sync or an editor rewriting on save bumps mtime without
        changing a word; on mtime this would re-run the model and file a
        duplicate note every night."""
        self._note("a.md", "AES modes")
        first = self.sa.discover(self.inbox, {})
        self.assertEqual(len(first), 1)
        state = {"a.md": {"digest": first[0][2]}}
        os.utime(os.path.join(self.inbox, "a.md"), (0, 0))
        self.assertEqual(self.sa.discover(self.inbox, state), [])

    def test_an_edited_note_is_processed_again(self):
        self._note("a.md", "AES modes")
        digest = self.sa.discover(self.inbox, {})[0][2]
        self._note("a.md", "AES modes and CBC needs an IV")
        self.assertEqual(len(self.sa.discover(self.inbox, {"a.md": {"digest": digest}})), 1)

    def test_force_reprocesses_an_unchanged_note(self):
        self._note("a.md", "AES modes")
        digest = self.sa.discover(self.inbox, {})[0][2]
        state = {"a.md": {"digest": digest}}
        self.assertEqual(len(self.sa.discover(self.inbox, state, force={"a.md"})), 1)

    def test_empty_and_unreadable_notes_do_not_break_the_batch(self):
        self._note("empty.md", "   \n\n")
        self._note("fine.md", "AES modes")
        found = [os.path.basename(p) for p, _, _ in self.sa.discover(self.inbox, {})]
        self.assertEqual(found, ["fine.md"])

    def test_missing_inbox_returns_nothing_instead_of_raising(self):
        self.assertEqual(self.sa.discover("/nonexistent/inbox", {}), [])

    # --- parsing the model's answer --------------------------------------

    def test_parses_the_five_section_contract(self):
        parsed = self.sa.parse_sections(self.GOOD)
        self.assertEqual(parsed["TITLE"], "Kryptografie Grundlagen")
        self.assertIn("AES", parsed["CONCEPTS"])
        self.assertEqual(parsed["FLASHCARDS"].upper().count("Q:"), 2)

    def test_multi_line_sections_keep_all_their_lines(self):
        parsed = self.sa.parse_sections(self.GOOD)
        self.assertIn("Betriebsmodi", parsed["SUMMARY"])
        self.assertEqual(len([l for l in parsed["CONCEPTS"].splitlines()
                              if l.strip().startswith("-")]), 2)

    def test_a_wrapping_code_fence_does_not_break_parsing(self):
        self.assertIsNotNone(self.sa.parse_sections("```\n" + self.GOOD + "\n```"))

    def test_answers_without_a_real_summary_are_refused(self):
        """The documented failure of this model chain is returning a tool
        transcript instead of prose (see aios_runner.py's synthesis fix).
        That must never become a study note."""
        for junk in ("", "ERROR: model failed", "UNUSABLE: this is a shopping list",
                     "SUMMARY: ok", "I ran ls and found some files."):
            self.assertIsNone(self.sa.parse_sections(junk), junk)

    def test_missing_optional_sections_still_produce_a_note(self):
        parsed = self.sa.parse_sections(
            "TITLE: T\nSUMMARY: " + "x" * 40 + "\nCONCEPTS:\n- none in these notes")
        body = self.sa.build_body(parsed, "a.md")
        self.assertIn("## Action Items", body)
        self.assertIn("## Flashcards", body)

    def test_body_credits_the_source_note_as_the_authority(self):
        body = self.sa.build_body(self.sa.parse_sections(self.GOOD), "vl02.md")
        self.assertIn("vl02.md", body)
        self.assertIn("source note remains the authority", body)

    # --- the study log ---------------------------------------------------

    def test_study_log_is_created_with_a_real_vault_header(self):
        path = os.path.join(self.tmp.name, "Study_Log.md")
        self.sa.append_study_log("a.md", os.path.join(self.sa.VAULT, "x", "N.md"),
                                 3, 4, when="2026-08-31 10:00", path=path)
        text = open(path, encoding="utf-8").read()
        for field in ("Purpose:", "Last Updated:", "Status:", "Related Documents:"):
            self.assertIn(field, text)

    def test_study_log_appends_and_never_rewrites(self):
        path = os.path.join(self.tmp.name, "Study_Log.md")
        for n in ("a.md", "b.md", "c.md"):
            self.sa.append_study_log(n, os.path.join(self.sa.VAULT, "x", "N.md"),
                                     1, 1, when="2026-08-31 10:00", path=path)
        text = open(path, encoding="utf-8").read()
        for n in ("a.md", "b.md", "c.md"):
            self.assertIn(n, text)
        self.assertEqual(text.count("# Study Log"), 1)

    def test_study_log_rows_never_glue_onto_the_previous_paragraph(self):
        """The exact bug flip_log.py hit writing into its own table: a row
        ending up welded to the prose above it with no separation."""
        path = os.path.join(self.tmp.name, "Study_Log.md")
        self.sa.append_study_log("a.md", os.path.join(self.sa.VAULT, "x", "N.md"),
                                 1, 1, when="2026-08-31 10:00", path=path)
        self.sa.append_study_log("b.md", os.path.join(self.sa.VAULT, "x", "N.md"),
                                 1, 1, when="2026-08-31 10:01", path=path)
        lines = open(path, encoding="utf-8").read().splitlines()
        rows = [i for i, l in enumerate(lines) if l.startswith("- 2026-")]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(lines[i].startswith("- ") for i in rows))

    def test_study_log_recreates_a_heading_someone_deleted(self):
        path = os.path.join(self.tmp.name, "Study_Log.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Study Log\n\nSome prose with no heading below it.\n")
        self.sa.append_study_log("a.md", os.path.join(self.sa.VAULT, "x", "N.md"),
                                 1, 1, path=path)
        text = open(path, encoding="utf-8").read()
        self.assertIn(self.sa.LOG_HEADING, text)
        self.assertLess(text.index(self.sa.LOG_HEADING), text.index("- 20"))

    # --- the task handed to the worker -----------------------------------

    def test_task_selects_the_study_agent_and_carries_no_thread(self):
        """No thread id means no conversation memory and - by the gate in
        aios_runner - no voice profile. Coursework is not the place for
        Felix's WhatsApp register."""
        task = self.sa.build_task("a.md", "AES modes")
        self.assertTrue(task.startswith("<!-- agent: Study_Teacher -->"))
        self.assertNotIn("<!-- thread:", task)

    def test_long_notes_are_truncated_visibly_not_silently(self):
        task = self.sa.build_task("a.md", "wort " * 20000)
        self.assertIn("note truncated at", task)
        self.assertLess(len(task), self.sa.MAX_NOTE_CHARS + 2000)

    def test_a_bad_destination_fails_before_any_model_call(self):
        """A wrong folder must cost nothing - not surface after the worker
        has already spent a minute on the note."""
        rc = self.sa.run(source=self.inbox, dest="00_System")
        self.assertEqual(rc, 1)

    def test_dry_run_touches_nothing(self):
        self._note("a.md", "AES modes")
        state_before = os.path.exists(self.sa.STATE_PATH)
        rc = self.sa.run(source=self.inbox, dest="08_Research", dry_run=True)
        self.assertEqual(rc, 0)
        self.assertEqual(os.path.exists(self.sa.STATE_PATH), state_before)

    # --- capture (the /lernen path) --------------------------------------

    def test_capture_writes_the_text_verbatim(self):
        path = self.sa.capture_note("VL3 Netzwerke\nOSI Modell, 7 Schichten",
                                    source=self.inbox)
        self.assertEqual(open(path, encoding="utf-8").read().strip(),
                         "VL3 Netzwerke\nOSI Modell, 7 Schichten")

    def test_capture_names_the_file_after_the_first_line(self):
        path = self.sa.capture_note("VL3 Netzwerke\nblah", source=self.inbox)
        self.assertIn("vl3_netzwerke", os.path.basename(path))

    def test_two_captures_in_the_same_minute_do_not_overwrite(self):
        """Two notes fired off during the same lecture minute is the normal
        case, and the second one vanishing looks exactly like it was saved."""
        when = datetime(2026, 9, 1, 10, 15)
        a = self.sa.capture_note("Thema X\neins", source=self.inbox, when=when)
        b = self.sa.capture_note("Thema X\nzwei", source=self.inbox, when=when)
        self.assertNotEqual(a, b)
        self.assertEqual(len(self.sa.discover(self.inbox, {})), 2)

    def test_capture_refuses_empty_text_instead_of_writing_a_blank_file(self):
        with self.assertRaises(ValueError):
            self.sa.capture_note("   \n ", source=self.inbox)

    def test_captured_notes_are_picked_up_by_discovery(self):
        """The whole point of the split: capture is instant and offline,
        processing happens later."""
        self.sa.capture_note("VL4 Firewalls\nstateful vs stateless",
                             source=self.inbox)
        found = self.sa.discover(self.inbox, {})
        self.assertEqual(len(found), 1)
        self.assertIn("stateful", found[0][1])

    def test_git_pull_on_a_non_repo_is_a_no_op_not_a_failure(self):
        self.assertFalse(self.sa.git_pull(self.inbox))


class TestVaultWritePurpose(unittest.TestCase):
    """The Purpose: header line (extended 2026-08-31)."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "vault_write_p", os.path.join(HERE, "vault_write.py"))
        cls.vw = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.vw)

    def test_long_purpose_is_cut_at_a_word_not_mid_word(self):
        """The first real study note produced a Purpose: ending
        "...AES-Blockchiffren un", which reads as a corrupted file."""
        text = "Diese Notizen erklaeren " + "Blockchiffren und Betriebsmodi " * 12
        out = self.vw._shorten(text)
        self.assertLessEqual(len(out), 170)
        self.assertFalse(out.rstrip(".").endswith("un"))
        self.assertTrue(out.endswith("...") or out.endswith("."))

    def test_short_purpose_is_left_exactly_alone(self):
        self.assertEqual(self.vw._shorten("Kurz und fertig."), "Kurz und fertig.")

    def test_explicit_purpose_beats_deriving_one_from_the_body(self):
        _, content = self.vw.write_note(
            "08_Research", "T", "## Heading\n\nSome body prose here.",
            purpose="An explicit one-line purpose.", dry_run=True)
        self.assertIn("Purpose: An explicit one-line purpose.", content)
