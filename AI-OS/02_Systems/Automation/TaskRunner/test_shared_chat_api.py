"""Shared conversation HTTP contracts, with all external engines replaced by fakes."""
import concurrent.futures
import importlib.util
from pathlib import Path
import re
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
NATIVE_ID = "12345678-1234-1234-1234-123456789abc"


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SharedChatApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load the real full API module, but never import account probes, devices,
        # notifications, or provider clients just to test a conversation route.
        cls.store = load_file("shared_api_store", HERE / "scripts" / "conversation_store.py")
        names = ("agents claude_chat cost_board engines gemini_chat knowledge_store memory "
                 "money_board dmarc_prospector flip_log notifications safety_controls phone "
                 "phone_root phone_stream pico proposals shared_briefing snipe_rank "
                 "study_agent vault_write watch_health").split()
        fakes = {name: types.ModuleType(name) for name in names}
        fakes["conversation_store"] = cls.store
        fakes["vault_write"].VAULT = "/offline-test-vault"
        fakes["engines"].ENGINES = {name: {} for name in ("claude", "google-pro", "codex", "aios")}
        fakes["claude_chat"].SESSION_ID_RE = re.compile(r"[0-9a-fA-F-]{36}")
        with patch.dict(sys.modules, fakes), patch("subprocess.Popen", side_effect=AssertionError("No processes in API tests")):
            cls.api = load_file("shared_chat_test_api", HERE / "webapp" / "api.py")

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        store_patch = patch.object(self.store, "CONVERSATIONS_DIR", temporary.name)
        store_patch.start()
        self.addCleanup(store_patch.stop)
        self.api.claude_chat.transcript = Mock(side_effect=AssertionError("Unexpected native transcript read"))
        self.api.engines.send = Mock(side_effect=AssertionError("No provider dispatch"))
        self.api.engines.result = Mock(side_effect=AssertionError("No provider collection"))
        self.api.shared_briefing.record_event = Mock()

    def attach(self, **changes):
        return self.api.post_conversations({"action": "attach", "engine": "claude", "session_id": NATIVE_ID, **changes})

    def native_fixture(self):
        return {"session_id": NATIVE_ID, "title": "Existing local conversation", "messages": [
            {"role": "user", "text": "Remember the decision"},
            {"role": "assistant", "text": "Tool trace must stay native", "tool": True},
            {"role": "assistant", "text": "We chose option two"},
        ]}

    def test_attach_imports_visible_turns_and_native_cursor(self):
        """Only actual conversation text crosses engines; tools remain in the native transcript."""
        self.api.claude_chat.transcript.side_effect = None
        self.api.claude_chat.transcript.return_value = self.native_fixture()
        status, payload = self.attach()
        self.assertEqual(status, 200)
        record = payload["conversation"]
        self.assertEqual([m["text"] for m in record["messages"]], ["Remember the decision", "We chose option two"])
        self.assertEqual(record["messages"][-1]["engine"], "claude")
        self.assertEqual(record["sessions"]["claude"]["id"], NATIVE_ID)
        self.assertEqual(record["sessions"]["claude"]["seen_seq"], record["messages"][-1]["seq"])
        self.api.engines.send.assert_not_called()

    def test_repeated_attach_does_not_duplicate_or_reimport_native_transcript(self):
        """Reopening an existing native session must preserve one shared identity."""
        self.api.claude_chat.transcript.side_effect = None
        self.api.claude_chat.transcript.return_value = self.native_fixture()
        first = self.attach()[1]["conversation"]
        second = self.attach()[1]["conversation"]
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(second["messages"]), 2)
        self.assertEqual(len(self.store.list_conversations()), 1)
        self.api.claude_chat.transcript.assert_called_once_with(NATIVE_ID, limit=400)

    def test_concurrent_attach_creates_only_one_shared_record(self):
        """Two browser tabs importing the same session must not fork its shared memory."""
        self.api.claude_chat.transcript.side_effect = None
        self.api.claude_chat.transcript.return_value = self.native_fixture()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            replies = list(pool.map(lambda _: self.attach(), range(4)))
        self.assertEqual({status for status, _ in replies}, {200})
        self.assertEqual(len({payload["conversation"]["id"] for _, payload in replies}), 1)
        self.assertEqual(self.api.claude_chat.transcript.call_count, 1)

    def test_invalid_native_session_is_rejected_before_transcript_read(self):
        """Untrusted native ids cannot become paths or trigger an implicit latest-session import."""
        for native_id in ("", "../secret", "not-a-session", "x" * 36):
            with self.subTest(native_id=native_id):
                self.assertEqual(self.attach(session_id=native_id)[0], 400)
        self.api.claude_chat.transcript.assert_not_called()
        self.assertEqual(self.store.list_conversations(), [])

    def test_unsupported_engine_cannot_import_a_claude_session(self):
        """Native ids belong to one provider, even when the conversation is shared."""
        for engine in ("google-pro", "codex", "aios", "unknown", ""):
            with self.subTest(engine=engine):
                self.assertEqual(self.attach(engine=engine)[0], 400)
        self.api.claude_chat.transcript.assert_not_called()

    def test_missing_native_session_reports_not_found_without_creating_record(self):
        """A failed import must not leave a new empty conversation that looks successful."""
        self.api.claude_chat.transcript.side_effect = None
        self.api.claude_chat.transcript.return_value = {"error": "not found"}
        self.assertEqual(self.attach()[0], 404)
        self.assertEqual(self.store.list_conversations(), [])

    def test_native_lookup_errors_are_a_client_error(self):
        """Unavailable native files and invalid lookups are reported, not silently imported."""
        for error in (FileNotFoundError("gone"), ValueError("invalid")):
            with self.subTest(error=type(error).__name__):
                self.api.claude_chat.transcript.side_effect = error
                self.assertEqual(self.attach()[0], 400)
        self.assertEqual(self.store.list_conversations(), [])

    def test_list_without_engine_returns_all_four_engine_conversations(self):
        """The common picker cannot hide conversations created by another engine."""
        ids = {engine: self.store.create(engine) for engine in self.api.engines.ENGINES}
        status, payload = self.api.post_conversations({"action": "list"})
        self.assertEqual(status, 200)
        self.assertEqual({row["id"] for row in payload["conversations"]}, set(ids.values()))
        status, payload = self.api.post_conversations({"action": "list", "engine": "google-pro"})
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in payload["conversations"]], [ids["google-pro"]])

    def test_invalid_create_engine_is_rejected(self):
        """The common picker does not turn arbitrary names into supported dispatch engines."""
        for engine in ("", "glm", "../outside"):
            with self.subTest(engine=engine):
                self.assertEqual(self.api.post_conversations({"action": "create", "engine": engine})[0], 400)

    def test_engine_send_forwards_shared_id_for_every_engine(self):
        """Claude uses the same conversation contract, with no browser-owned native id required."""
        conversation_id = self.store.create("claude")
        self.api.engines.send.side_effect = None
        for engine in self.api.engines.ENGINES:
            with self.subTest(engine=engine):
                self.api.engines.send.return_value = {"engine": engine, "job": "job", "conversation_id": conversation_id}
                status, payload = self.api.post_engine_send({"engine": engine, "message": "hello", "conversation_id": conversation_id})
                self.assertEqual(status, 200)
                self.assertEqual(payload["conversation_id"], conversation_id)
                self.assertEqual(self.api.engines.send.call_args.kwargs["conversation_id"], conversation_id)
                self.assertIsNone(self.api.engines.send.call_args.kwargs["session"])


if __name__ == "__main__":
    unittest.main()
