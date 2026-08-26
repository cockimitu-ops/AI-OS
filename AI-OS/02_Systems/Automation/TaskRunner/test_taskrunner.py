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
        self.runner._attempt = lambda model, instr: f"done by {model}"
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        self.assertEqual(self.log_of("t.md"),
                         f"done by {self.runner.MODEL_CHAIN[0][0]}")
        self.assert_quarantined("t.md")

    def test_falls_through_to_a_later_model(self):
        calls = []

        def flaky(model, instr):
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
        def dead(model, instr):
            raise RuntimeError("quota exhausted")

        self.runner._attempt = dead
        self.runner.time.sleep = lambda s: None
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        log = self.log_of("t.md")
        self.assertIn("All models failed", log)
        self.assertIn("quota exhausted", log)
        for model, _ in self.runner.MODEL_CHAIN:
            self.assertIn(model, log)
        self.assert_quarantined("t.md")

    def test_escalation_disabled_is_stated_in_the_failure_log(self):
        """CLAUDE_ESCALATION_ENABLED is off pending a ToS decision. If it is off,
        the log must say so - otherwise the failure looks like the escalation
        tier ran and also failed."""
        self.runner._attempt = lambda m, i: (_ for _ in ()).throw(RuntimeError("x"))
        self.runner.time.sleep = lambda s: None
        self.queue("t.md", "do a thing")
        self.runner._run_task(os.path.join(self.runner.INBOX, "t.md"), "t.md")
        if not self.runner.CLAUDE_ESCALATION_ENABLED:
            self.assertIn("Escalation: disabled", self.log_of("t.md"))


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
        self.runner._attempt = lambda model, instr: "fine"
        self.queue("good.md", "do a thing")
        self._run_one_pass()
        self.assertEqual(self.log_of("good.md"), "fine")
        self.assert_quarantined("good.md")

    def test_tasks_are_processed_in_filename_order(self):
        order = []
        self.runner._attempt = lambda model, instr: order.append(instr) or "ok"
        self.queue("task_b.md", "second")
        self.queue("task_a.md", "first")
        self._run_one_pass()
        self.assertEqual(order, ["first", "second"])


class TestOutputFormatting(TaskRunnerTestCase):
    def test_assistant_message_and_command_output_both_survive(self):
        out = self.runner.format_interpreter_output([
            {"role": "assistant", "type": "message", "content": "Here you go"},
            {"role": "assistant", "type": "code", "format": "shell",
             "content": "ls -la"},
            {"role": "computer", "type": "console", "content": "file.txt\n"},
        ])
        self.assertIn("Here you go", out)
        self.assertIn("ls -la", out)
        self.assertIn("file.txt", out)

    def test_empty_message_list_never_yields_an_empty_log(self):
        self.assertEqual(self.runner.format_interpreter_output([]),
                         "Task completed.")


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
