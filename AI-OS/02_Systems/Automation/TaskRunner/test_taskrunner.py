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
import importlib
import importlib.util
import os
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def _install_stubs():
    """aios_runner imports open-interpreter and python-dotenv at module level.
    Neither is needed to test the queue mechanics, and open-interpreter is a
    multi-second import that only exists inside one venv. Stub both."""
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = dotenv

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


class TestFreellmapiIntegration(TaskRunnerTestCase):
    """Added 2026-08-30: FreeLLMAPI (a self-hosted router in front of ~34 free
    providers) became the primary tier, with the original direct Groq/Gemini
    chain kept as fallback rather than replaced. MODEL_CHAIN is built at import
    time from FREELLMAPI_BASE_URL/FREELLMAPI_API_KEY, so these tests set those
    env vars before the fresh import setUp() already does."""

    def setUp(self):
        # Base setUp imports aios_runner fresh; do that AFTER setting the env
        # vars each test needs, so MODEL_CHAIN is built under the right config.
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["AIOS_WORKSPACE"] = self.tmp.name

    def _import_with_freellmapi(self, base_url, api_key):
        if base_url is None:
            os.environ.pop("FREELLMAPI_BASE_URL", None)
        else:
            os.environ["FREELLMAPI_BASE_URL"] = base_url
        if api_key is None:
            os.environ.pop("FREELLMAPI_API_KEY", None)
        else:
            os.environ["FREELLMAPI_API_KEY"] = api_key
        self.addCleanup(os.environ.pop, "FREELLMAPI_BASE_URL", None)
        self.addCleanup(os.environ.pop, "FREELLMAPI_API_KEY", None)

        self.fake = _install_stubs()
        sys.path.insert(0, HERE)
        self.addCleanup(lambda: sys.path.remove(HERE))
        sys.modules.pop("aios_runner", None)
        self.runner = importlib.import_module("aios_runner")
        self.addCleanup(lambda: sys.modules.pop("aios_runner", None))

    def test_freellmapi_is_prepended_when_both_env_vars_are_set(self):
        self._import_with_freellmapi("http://localhost:3001/v1", "freellmapi-testkey")
        first = self.runner.MODEL_CHAIN[0]
        self.assertEqual(first["model"], "openai/auto")
        self.assertEqual(first["api_base"], "http://localhost:3001/v1")
        self.assertEqual(first["api_key"], "freellmapi-testkey")
        # the original direct chain must still be present, unmodified, after it
        self.assertEqual(self.runner.MODEL_CHAIN[1]["model"], self.runner.PRIMARY_MODEL)
        self.assertEqual(len(self.runner.MODEL_CHAIN), 6)  # 1 freellmapi + 5 direct

    def test_falls_back_to_direct_chain_only_when_either_var_is_missing(self):
        for base_url, api_key in [(None, "key"), ("http://x", None), (None, None)]:
            with self.subTest(base_url=base_url, api_key=api_key):
                self._import_with_freellmapi(base_url, api_key)
                self.assertEqual(len(self.runner.MODEL_CHAIN), 5)
                self.assertEqual(self.runner.MODEL_CHAIN[0]["model"],
                                 self.runner.PRIMARY_MODEL)

    def test_direct_chain_entries_have_no_custom_endpoint(self):
        """A freellmapi call's api_base must never leak into a direct-provider
        attempt - each direct entry explicitly carries api_base=None,
        api_key=None rather than omitting the keys."""
        self._import_with_freellmapi("http://localhost:3001/v1", "freellmapi-testkey")
        for entry in self.runner.MODEL_CHAIN[1:]:
            self.assertIsNone(entry["api_base"], entry["model"])
            self.assertIsNone(entry["api_key"], entry["model"])

    def test_attempt_sets_and_resets_api_base_between_calls(self):
        """End to end through _attempt: the freellmapi entry's endpoint must be
        gone from interpreter.llm by the time a direct-provider entry runs -
        not just correct in the MODEL_CHAIN data, but actually applied."""
        self._import_with_freellmapi("http://localhost:3001/v1", "freellmapi-testkey")
        self.runner.time.sleep = lambda s: None  # skip the 20s cooldown entry
        seen_api_bases = []

        real_chat = self.fake.chat
        def spy_chat(*a, **k):
            seen_api_bases.append(self.fake.llm.api_base)
            return []  # empty -> _attempt raises, loop moves to the next entry
        self.fake.chat = spy_chat

        self.queue("t.md", "do a thing")
        try:
            self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        except Exception:
            pass  # every entry "fails" (empty output) by design of spy_chat above

        self.assertEqual(seen_api_bases[0], "http://localhost:3001/v1")
        self.assertTrue(all(b is None for b in seen_api_bases[1:]),
                        seen_api_bases)


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
        correct behaviour but silent - so assert the four real agents are wired,
        or a broken marker would go unnoticed until someone reads a bad answer."""
        found = self.agents.available()
        self.assertEqual(len(found), 4, found)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
