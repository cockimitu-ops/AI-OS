extends SceneTree

const Chat = preload("res://WorkspaceChat.gd")
var failures := 0

class FakeClient:
	extends Node
	var calls: Array = []
	func get_json(path: String) -> Variant:
		calls.append(["GET", path, {}])
		if path == "/api/claude-sessions":
			return {"sessions": [{"id": "01234567-89ab-cdef-0123-456789abcdef", "title": "Native Arbeit", "messages": 12}]}
		return {"engines": [{"id": "claude", "label": "Claude", "available": true,
			"models": ["sonnet", "opus"], "default_model": "sonnet"}]}
	func post_json(path: String, body: Dictionary) -> Variant:
		calls.append(["POST", path, body.duplicate(true)])
		if body.get("action") == "list":
			return {"conversations": [{"id": "conv-test", "title": "Gespeicherter Chat", "message_count": 2}]}
		if body.get("action") == "read":
			return {"conversation": {"id": "conv-test", "title": "Gespeicherter Chat", "messages": [
				{"role": "user", "text": "Hallo"}, {"role": "assistant", "text": "Bereit", "engine": "claude"}]}}
		return null

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var payload := Chat.build_send_payload("google", "gemini-2.5-pro", "weiter", "conv-7")
	_check(payload == {"engine": "google", "model": "gemini-2.5-pro", "message": "weiter", "thread": "vr", "conversation_id": "conv-7"}, "send payload preserves shared conversation and explicit model")
	var default_payload := Chat.build_send_payload("claude", "", "hallo", "conv-8")
	_check(not default_payload.has("model"), "empty model lets server choose its default")
	_check(Chat.classify_result({"handed_off": {"note": "limit"}, "ready": true}) == "handoff", "handoff is applied before stale ready flag")
	_check(Chat.classify_result({"ready": true, "ok": true}) == "ready", "completed jobs stop polling")
	_check(Chat.classify_result({"lost": true}) == "lost", "lost jobs stop polling with an error")
	_check(Chat.classify_result({"elapsed": 9}) == "waiting", "unfinished jobs keep polling")
	var delay := 1.5
	for _i in 20:
		delay = Chat.next_poll_delay(delay)
	_check(is_equal_approx(delay, 6.0), "poll backoff is capped at six seconds")
	_check(Chat.next_poll_delay(1.5) > 1.5, "poll backoff grows after each request")
	var state_path := "user://aios_native_chat_test.cfg"
	DirAccess.remove_absolute(ProjectSettings.globalize_path(state_path))
	var host := Node.new()
	get_root().add_child(host)
	var fake := FakeClient.new()
	host.add_child(fake)
	var chat := Chat.new()
	chat.api_override = fake
	chat.state_path = state_path
	host.add_child(chat)
	_check(fake.calls.size() == 4, "opening chat fetches catalogue, conversation list, transcript, and importable Claude sessions")
	_check(fake.calls[1][2] == {"action": "list", "limit": 50}, "conversation picker requests the bounded shared list")
	_check(fake.calls[2][2] == {"action": "read", "conversation_id": "conv-test"}, "selected shared conversation is read by id")
	_check(chat._conversation_picker.item_count == 1 and chat._conversation_picker.get_item_metadata(0) == "conv-test", "saved conversations are selectable in native UI")
	_check(chat._history.get_child_count() == 2, "native transcript renders every stored message")
	_check(chat._session_picker.item_count == 1 and chat._session_picker.get_item_metadata(0) == "01234567-89ab-cdef-0123-456789abcdef", "existing native Claude sessions can be selected for import")
	host.queue_free()
	DirAccess.remove_absolute(ProjectSettings.globalize_path(state_path))
	if failures:
		printerr("WORKSPACE CHAT TESTS FAILED: %d" % failures)
		quit(1)
	else:
		print("WORKSPACE CHAT TESTS PASSED")
		quit(0)

func _check(value: bool, message: String) -> void:
	if not value:
		failures += 1
		printerr("FAIL: " + message)
