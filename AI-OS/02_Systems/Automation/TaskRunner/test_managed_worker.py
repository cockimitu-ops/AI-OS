"""Managed web conversations keep chat behavior without a second transcript."""
import contextlib
import os
import subprocess
from unittest import mock

from test_taskrunner import TaskRunnerTestCase


class TestManagedWorkerHistory(TaskRunnerTestCase):
    def setUp(self):
        # The base fixture stubs all model execution. Import-time catalogue
        # probes are also forbidden so this suite never touches an account.
        with mock.patch.object(subprocess, "Popen", side_effect=FileNotFoundError("offline test")):
            super().setUp()
        self.runner.MODEL_CHAIN = [self.runner._chain_entry("offline-test-model")]
        self.runner.ROUTING_ENABLED = False
        self.runner.CLAUDE_ESCALATION_ENABLED = False
        self.runner._attempt = mock.Mock(return_value="Answer")
        self.runner._system_prompt_for = mock.Mock(return_value="System")
        self.runner._rewrite_in_his_voice = mock.Mock(side_effect=lambda output, *_: output)
        self.budgets = []

        @contextlib.contextmanager
        def timed(seconds):
            self.budgets.append(seconds)
            yield

        self.runner._time_limit = timed
        self.memory_mocks = {}
        for name, value in (("last_agent", None), ("as_messages", [{"role": "user", "content": "old"}]),
                            ("save_turn", None)):
            patcher = mock.patch.object(self.runner.memory, name, return_value=value)
            self.memory_mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)

    def _run(self, text):
        path = self.queue("managed.md", text)
        self.runner._run_task(path, "managed.md")
        self.assertEqual(self.log_of("managed.md"), "Answer")

    def test_managed_history_keeps_interactive_identity_without_duplicate_memory(self):
        """Shared memory must not turn a chat into a slower, voiceless batch task."""
        thread = "web_conv_codex_20260903_123456_123456"
        self._run(f"<!-- thread: {thread} -->\n<!-- shared-history -->\n"
                  "Shared recent conversation\n\nCurrent request")
        for call in self.memory_mocks.values():
            call.assert_not_called()
        attempt = self.runner._attempt.call_args
        self.assertIsNone(attempt.args[3])
        self.assertEqual(attempt.args[1], "Shared recent conversation\n\nCurrent request")
        self.runner._system_prompt_for.assert_called_once_with(None, thread)
        self.assertEqual(self.runner._rewrite_in_his_voice.call_args.args[1], thread)
        self.assertEqual(self.budgets[-1], self.runner.CHAT_ATTEMPT_TIMEOUT_S)

    def test_explicit_agent_survives_managed_directive(self):
        """The marker must be stripped before the existing agent/model parsers."""
        thread = "web_conv_aios_20260903_123456_123456"
        with mock.patch.object(self.runner.agents, "parse_directive", return_value=("Chosen_Agent", "Question")) as parse, \
                mock.patch.object(self.runner.agents, "model_preference", return_value=None):
            self._run(f"<!-- thread: {thread} -->\n<!-- shared-history -->\n"
                      "<!-- agent: Chosen_Agent -->\nQuestion")
        self.assertTrue(parse.call_args.args[0].startswith("<!-- agent:"))
        self.runner._system_prompt_for.assert_called_once_with("Chosen_Agent", thread)
        self.memory_mocks["last_agent"].assert_not_called()

    def test_legacy_web_thread_keeps_worker_memory(self):
        """Unmanaged callers keep their existing history and successful-turn save."""
        self._run("<!-- thread: web_legacy -->\nQuestion")
        self.memory_mocks["last_agent"].assert_called_once_with("web_legacy")
        self.memory_mocks["as_messages"].assert_called_once_with("web_legacy")
        self.memory_mocks["save_turn"].assert_called_once_with("web_legacy", "Question", "Answer", None)
        self.assertEqual(self.budgets[-1], self.runner.CHAT_ATTEMPT_TIMEOUT_S)

    def test_directive_requires_leading_managed_web_thread(self):
        """Quoted markers or Telegram text cannot disable the existing memory."""
        marker = "<!-- shared-history -->\nQuestion"
        for thread, text in ((None, marker), ("tg_123", marker), ("web_legacy", marker),
                             ("web_conv_codex_123", "Question\n" + marker)):
            with self.subTest(thread=thread, text=text):
                active, remaining = self.runner._parse_shared_history(text, thread)
                self.assertFalse(active)
                self.assertEqual(remaining, text)


if __name__ == "__main__":
    import unittest
    unittest.main()
