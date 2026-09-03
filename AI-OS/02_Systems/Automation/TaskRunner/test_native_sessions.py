"""Offline regressions for native Google/Codex conversation transport.

No test starts an engine, probes an account, or reads a real session store.
"""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock


SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def _module(name):
    spec = importlib.util.spec_from_file_location("_native_test_" + name,
                                                os.path.join(SCRIPTS, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    # The existing Codex catalogue probes model availability at import time.
    with mock.patch("subprocess.Popen", side_effect=FileNotFoundError("offline test")):
        spec.loader.exec_module(module)
    return module


class TestCodexNativeSessions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = _module("codex_chat")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        real_named = tempfile.NamedTemporaryFile
        patcher = mock.patch.object(self.engine.tempfile, "NamedTemporaryFile",
                                   side_effect=lambda *a, **kw: real_named(*a, dir=self.tmp.name, **kw))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _completed(self, argv, **kwargs):
        with open(argv[argv.index("-o") + 1], "w", encoding="utf-8") as handle:
            handle.write("Native answer")
        return SimpleNamespace(returncode=0, stderr=b"", stdout=(
            b'not json\n[]\n{"type":"thread.started","thread_id":"this-turn-id"}\n'
            b'{"type":"item.completed","item":{"text":"Not the final answer"}}\n'))

    def test_own_event_stream_identifies_session(self):
        """Concurrent chats cannot steal each other's native session IDs."""
        with mock.patch.object(self.engine.subprocess, "run", side_effect=self._completed) as run, \
                mock.patch.object(self.engine.shared_briefing, "prepend", return_value="Briefed") as brief:
            result = self.engine.ask("Question")
        self.assertEqual(result["session_id"], "this-turn-id")
        self.assertEqual(result["reply"], "Native answer")
        self.assertEqual(run.call_args.kwargs["input"], b"Briefed")
        self.assertIn("--json", run.call_args.args[0])
        brief.assert_called_once_with("Question")
        self.assertEqual(os.listdir(self.tmp.name), [])

    def test_resume_parent_options_and_managed_briefing(self):
        """Resume accepts exec's sandbox/cwd before, not after, the subcommand."""
        with mock.patch.object(self.engine.subprocess, "run", side_effect=self._completed) as run, \
                mock.patch.object(self.engine.shared_briefing, "prepend") as brief:
            self.engine.ask("Delta only", resume="old-id", model="chosen-model", cwd="/workspace",
                            read_only=True, include_briefing=False)
        argv = run.call_args.args[0]
        self.assertLess(argv.index("-s"), argv.index("resume"))
        self.assertLess(argv.index("-C"), argv.index("resume"))
        self.assertEqual(argv[argv.index("-s") + 1], "read-only")
        self.assertEqual(argv[argv.index("-C") + 1], "/workspace")
        self.assertEqual(argv[argv.index("resume") + 1], "old-id")
        self.assertEqual(argv[argv.index("-m") + 1], "chosen-model")
        self.assertEqual(run.call_args.kwargs["input"], b"Delta only")
        brief.assert_not_called()

    def test_partial_reply_on_nonzero_exit_is_failure(self):
        """A failed native turn must not advance the shared-memory cursor."""
        def fail(argv, **kwargs):
            result = self._completed(argv, **kwargs)
            result.returncode = 1
            result.stderr = b"quota exceeded"
            return result
        with mock.patch.object(self.engine.subprocess, "run", side_effect=fail):
            with self.assertRaisesRegex(self.engine.CodexError, "quota exceeded"):
                self.engine.ask("Question", include_briefing=False)
        self.assertEqual(os.listdir(self.tmp.name), [])

    def test_temp_file_is_removed_on_all_start_failures(self):
        """Timeouts and missing executables do not leave answer files behind."""
        for error in (subprocess.TimeoutExpired("codex", 1), FileNotFoundError("missing"),
                      PermissionError("denied")):
            with self.subTest(error=type(error).__name__), \
                    mock.patch.object(self.engine.subprocess, "run", side_effect=error):
                with self.assertRaises(self.engine.CodexError):
                    self.engine.ask("Question", include_briefing=False)
                self.assertEqual(os.listdir(self.tmp.name), [])

    def test_no_stream_id_uses_only_explicit_resume(self):
        """Missing events never cause a scan of another conversation's files."""
        def no_event(argv, **kwargs):
            result = self._completed(argv, **kwargs)
            result.stdout = b""
            return result
        with mock.patch.object(self.engine.subprocess, "run", side_effect=no_event):
            self.assertEqual(self.engine.ask("Question", resume="explicit-id", include_briefing=False)
                             ["session_id"], "explicit-id")
            self.assertIsNone(self.engine.ask("Question", include_briefing=False)["session_id"])

    def test_empty_final_file_is_not_success(self):
        """An event stream alone is not a completed final answer."""
        with mock.patch.object(self.engine.subprocess, "run", return_value=SimpleNamespace(
                returncode=0, stderr=b"", stdout=b"")):
            with self.assertRaises(self.engine.CodexError):
                self.engine.ask("Question", include_briefing=False)
        self.assertEqual(os.listdir(self.tmp.name), [])

    def test_cli_can_skip_duplicate_briefing(self):
        """The engine dispatcher can pass its already managed context unchanged."""
        with mock.patch.object(self.engine, "ask", return_value={"reply": "ok", "model": "auto"}) as ask, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.engine.main(["--no-briefing", "--resume", "saved", "hello"]), 0)
        self.assertFalse(ask.call_args.kwargs["include_briefing"])
        self.assertEqual(ask.call_args.kwargs["resume"], "saved")


class TestGoogleNativeSessions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = _module("antigravity_chat")

    @staticmethod
    def _completed():
        return SimpleNamespace(returncode=0, stderr=b"", stdout=json.dumps({
            "status": "SUCCESS", "response": "Google answer", "conversation_id": "google-native-id",
            "usage": {"input_tokens": 10}}).encode("utf-8"))

    def test_default_still_briefs_and_registers_project(self):
        """cwd alone is not an Antigravity workspace; add-dir makes it explicit."""
        with mock.patch.object(self.engine.subprocess, "run", return_value=self._completed()) as run, \
                mock.patch.object(self.engine.shared_briefing, "prepend", return_value="Briefed") as brief:
            result = self.engine.ask("Question")
        argv = run.call_args.args[0]
        self.assertEqual(argv[argv.index("-p") + 1], "Briefed")
        self.assertEqual(argv[argv.index("--add-dir") + 1], self.engine.PROJECT_DIR)
        self.assertEqual(result["session_id"], "google-native-id")
        brief.assert_called_once_with("Question")

    def test_resume_receives_native_id_and_delta_only(self):
        """A resumed native Google chat gets no duplicated standing briefing."""
        with mock.patch.object(self.engine.subprocess, "run", return_value=self._completed()) as run, \
                mock.patch.object(self.engine.shared_briefing, "prepend") as brief:
            self.engine.ask("New context", conversation="google-old", cwd="/workspace", read_only=True,
                            include_briefing=False)
        argv = run.call_args.args[0]
        self.assertEqual(argv[argv.index("-p") + 1], "New context")
        self.assertEqual(argv[argv.index("--conversation") + 1], "google-old")
        self.assertIn("--continue", argv)
        self.assertEqual(argv[argv.index("--add-dir") + 1], "/workspace")
        self.assertEqual(run.call_args.kwargs["cwd"], "/workspace")
        self.assertIn("--sandbox", argv)
        self.assertIn("--disable-slash-commands", argv)
        self.assertNotIn("--dangerously-skip-permissions", argv)
        brief.assert_not_called()

    def test_partial_response_on_failure_is_rejected(self):
        """Failed Google turns must not be persisted as completed replies."""
        result = self._completed()
        result.returncode = 1
        with mock.patch.object(self.engine.subprocess, "run", return_value=result):
            with self.assertRaises(self.engine.GoogleProError):
                self.engine.ask("Question", include_briefing=False)

    def test_cli_uses_conversation_without_wrapper_continue_flag(self):
        """The Python wrapper handles continuation internally for its CLI caller."""
        with mock.patch.object(self.engine, "ask", return_value={
                "reply": "ok", "model": "model", "usage": {}, "session_id": "saved"}) as ask, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.engine.main(["--no-briefing", "--conversation", "saved", "hello"]), 0)
        self.assertFalse(ask.call_args.kwargs["include_briefing"])
        self.assertEqual(ask.call_args.kwargs["conversation"], "saved")


if __name__ == "__main__":
    unittest.main()
