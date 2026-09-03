extends Control
## Native chat surface for the movable 3D workspace. It deliberately speaks the
## same durable conversation/job protocol as the phone client, without HTML.

signal text_focus(field: Control)

var module_id := "chat"
var api_override: Node
var engine := "claude"
var conversation_id := ""
var engines: Array = []
var conversations: Array = []
var _models: Dictionary = {}
var _busy := false
var _pending: Dictionary = {}
var _engine_picker: OptionButton
var _model_picker: OptionButton
var _conversation_picker: OptionButton
var _session_bar: HBoxContainer
var _session_picker: OptionButton
var _history: VBoxContainer
var _scroll: ScrollContainer
var _compose: LineEdit
var _send: Button
var _fresh: Button
var _reload: Button
var _knowledge: Button
var _attach: Button
var _status: Label

const STATE_PATH := "user://aios_native_chat.cfg"
const POLL_START := 1.5
const POLL_MAX := 6.0
var state_path := STATE_PATH

func setup(id: String) -> void:
	module_id = id

func _ready() -> void:
	_build_ui()
	_load_state()
	await refresh()
	if not _pending.is_empty():
		_poll_pending()

func _client() -> Node:
	return api_override if api_override else get_node("/root/AIOSClient")

func _build_ui() -> void:
	var all := VBoxContainer.new()
	all.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(all)
	var bar := HBoxContainer.new()
	all.add_child(bar)
	_engine_picker = OptionButton.new()
	_engine_picker.custom_minimum_size.x = 250
	_engine_picker.fit_to_longest_item = false
	bar.add_child(_engine_picker)
	_engine_picker.item_selected.connect(_choose_engine)
	_model_picker = OptionButton.new()
	_model_picker.custom_minimum_size.x = 300
	_model_picker.fit_to_longest_item = false
	bar.add_child(_model_picker)
	_model_picker.item_selected.connect(func(_index):
		if _model_picker.item_count:
			_models[engine] = _model_picker.get_item_text(_model_picker.selected)
			_save_state())
	_fresh = Button.new()
	_fresh.text = "Neu"
	bar.add_child(_fresh)
	_fresh.pressed.connect(_create_conversation)
	_reload = Button.new()
	_reload.text = "↻"
	bar.add_child(_reload)
	_reload.pressed.connect(refresh)
	var conversation_bar := HBoxContainer.new()
	all.add_child(conversation_bar)
	var conversation_label := Label.new()
	conversation_label.text = "Unterhaltung"
	conversation_bar.add_child(conversation_label)
	_conversation_picker = OptionButton.new()
	_conversation_picker.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_conversation_picker.fit_to_longest_item = false
	conversation_bar.add_child(_conversation_picker)
	_conversation_picker.item_selected.connect(_choose_conversation)
	_knowledge = Button.new()
	_knowledge.text = "Wissen"
	conversation_bar.add_child(_knowledge)
	_knowledge.pressed.connect(_save_knowledge)
	_session_bar = HBoxContainer.new()
	all.add_child(_session_bar)
	var session_label := Label.new()
	session_label.text = "Claude-Sitzung"
	_session_bar.add_child(session_label)
	_session_picker = OptionButton.new()
	_session_picker.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_session_picker.fit_to_longest_item = false
	_session_bar.add_child(_session_picker)
	_attach = Button.new()
	_attach.text = "Import"
	_session_bar.add_child(_attach)
	_attach.pressed.connect(_attach_session)
	_status = Label.new()
	_status.text = "Verbinde Chat …"
	all.add_child(_status)
	_scroll = ScrollContainer.new()
	_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	all.add_child(_scroll)
	_history = VBoxContainer.new()
	_history.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_scroll.add_child(_history)
	var composer := HBoxContainer.new()
	all.add_child(composer)
	_compose = LineEdit.new()
	_compose.placeholder_text = "Nachricht an AIOS …"
	_compose.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	composer.add_child(_compose)
	_compose.focus_entered.connect(func(): text_focus.emit(_compose))
	_compose.text_submitted.connect(func(_text): _send_message())
	_send = Button.new()
	_send.text = "Senden"
	composer.add_child(_send)
	_send.pressed.connect(_send_message)

func refresh() -> void:
	if _busy:
		return
	_busy = true
	_update_busy()
	var catalogue = await _client().get_json("/api/engines")
	if catalogue is Dictionary:
		engines = catalogue.get("engines", [])
	_populate_engines()
	await _load_conversations()
	if conversation_id.is_empty():
		await _create_conversation(false)
	else:
		await _read_conversation()
	await _load_sessions()
	_busy = false
	_update_busy()

func _populate_engines() -> void:
	_engine_picker.clear()
	var selected := 0
	for i in engines.size():
		var spec: Dictionary = engines[i]
		var label := str(spec.get("label", spec.get("id", "?")))
		if not spec.get("available", false):
			label += " · nicht bereit"
		_engine_picker.add_item(label)
		_engine_picker.set_item_metadata(i, str(spec.get("id", "")))
		if spec.get("id", "") == engine:
			selected = i
	if _engine_picker.item_count:
		_engine_picker.select(selected)
		engine = str(_engine_picker.get_item_metadata(selected))
	_populate_models()

func _populate_models() -> void:
	_model_picker.clear()
	var spec := _engine_spec()
	for model in spec.get("models", []):
		_model_picker.add_item(str(model))
	var default_model := str(_models.get(engine, spec.get("default_model", "")))
	for i in _model_picker.item_count:
		if _model_picker.get_item_text(i) == default_model:
			_model_picker.select(i)

func _engine_spec() -> Dictionary:
	for candidate in engines:
		if candidate is Dictionary and candidate.get("id", "") == engine:
			return candidate
	return {}

func _choose_engine(index: int) -> void:
	if _busy:
		return
	engine = str(_engine_picker.get_item_metadata(index))
	_populate_models()
	_save_state()
	_load_sessions()

func _load_sessions() -> void:
	_session_bar.visible = engine == "claude"
	_session_picker.clear()
	if engine != "claude":
		return
	var response = await _client().get_json("/api/claude-sessions")
	if not response is Dictionary:
		return
	for session in response.get("sessions", []):
		if session is Dictionary:
			var label := str(session.get("title", session.get("id", "Sitzung")))
			label += " · %d Nachrichten" % int(session.get("messages", 0))
			_session_picker.add_item(label)
			_session_picker.set_item_metadata(_session_picker.item_count - 1, str(session.get("id", "")))

func _attach_session() -> void:
	if _busy or _session_picker.item_count == 0:
		return
	_busy = true
	_update_busy()
	var session_id := str(_session_picker.get_item_metadata(_session_picker.selected))
	var response = await _client().post_json("/api/conversations", {
		"action": "attach", "engine": "claude", "session_id": session_id})
	if response is Dictionary and response.get("conversation", {}) is Dictionary:
		var record: Dictionary = response.conversation
		conversation_id = str(record.get("id", ""))
		_render_record(record)
		_save_state()
		await _load_conversations()
	else:
		_status.text = "Claude-Sitzung konnte nicht übernommen werden."
	_busy = false
	_update_busy()

func _save_knowledge() -> void:
	if _busy or conversation_id.is_empty():
		return
	_busy = true
	_update_busy()
	var response = await _client().post_json("/api/knowledge-save", {"conversation_id": conversation_id})
	_status.text = "Im Wissensspeicher gesichert." if response is Dictionary and response.get("ok", false) else "Wissen konnte nicht gesichert werden."
	_busy = false
	_update_busy()

func _load_conversations() -> void:
	var listing = await _client().post_json("/api/conversations", {"action": "list", "limit": 50})
	conversations = listing.get("conversations", []) if listing is Dictionary else []
	if conversation_id.is_empty() and not conversations.is_empty():
		conversation_id = str(conversations[0].get("id", ""))
	_conversation_picker.clear()
	var selected := 0
	for i in conversations.size():
		var record: Dictionary = conversations[i]
		var title := str(record.get("title", "Unterhaltung"))
		var count := int(record.get("message_count", 0))
		_conversation_picker.add_item("%s · %d" % [title, count])
		_conversation_picker.set_item_metadata(i, str(record.get("id", "")))
		if record.get("id", "") == conversation_id:
			selected = i
	if _conversation_picker.item_count:
		_conversation_picker.select(selected)

func _choose_conversation(index: int) -> void:
	if _busy:
		return
	conversation_id = str(_conversation_picker.get_item_metadata(index))
	_save_state()
	_open_selected_conversation()

func _open_selected_conversation() -> void:
	if _busy:
		return
	_busy = true
	_update_busy()
	await _read_conversation()
	_busy = false
	_update_busy()

func _create_conversation(lock := true) -> void:
	if lock and _busy:
		return
	if lock:
		_busy = true
		_update_busy()
	var response = await _client().post_json("/api/conversations", {"action": "create", "engine": engine})
	if response is Dictionary and response.get("conversation", {}) is Dictionary:
		var record: Dictionary = response.conversation
		conversation_id = str(record.get("id", ""))
		_render_record(record)
		_save_state()
		await _load_conversations()
	else:
		_status.text = "Unterhaltung konnte nicht angelegt werden."
	if lock:
		_busy = false
		_update_busy()

func _read_conversation() -> void:
	var response = await _client().post_json("/api/conversations", {
		"action": "read", "conversation_id": conversation_id})
	if response is Dictionary and response.get("conversation", {}) is Dictionary:
		_render_record(response.conversation)
	else:
		_status.text = "Verlauf ist gerade nicht erreichbar."

func _render_record(record: Dictionary) -> void:
	_clear_history()
	var messages: Array = record.get("messages", [])
	if messages.is_empty():
		_add_bubble("Neue Unterhaltung — schreib einfach los.", "system")
	for item in messages:
		if item is Dictionary:
			_add_bubble(str(item.get("text", "")), str(item.get("role", "assistant")), str(item.get("engine", "")))
	_status.text = "%s · %d Nachrichten · gemeinsames Gedächtnis" % [str(record.get("title", "Unterhaltung")), messages.size()]
	_scroll_to_bottom()

func _clear_history() -> void:
	for child in _history.get_children():
		child.queue_free()

func _add_bubble(text: String, role: String, answered_by := "") -> Label:
	var label := Label.new()
	var prefix := "Du" if role == "user" else (answered_by if not answered_by.is_empty() else "AIOS")
	if role == "system":
		prefix = ""
	label.text = (prefix + "\n" if not prefix.is_empty() else "") + text
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.custom_minimum_size.y = 56
	label.add_theme_color_override("font_color", Color("a9bdd0") if role == "system" else Color("edf3f7"))
	_history.add_child(label)
	return label

func _send_message() -> void:
	if _busy:
		return
	var message := _compose.text.strip_edges()
	if message.is_empty():
		return
	var spec := _engine_spec()
	if not spec.is_empty() and not spec.get("available", false):
		_status.text = str(spec.get("reason", "Diese Engine ist nicht bereit."))
		return
	_compose.clear()
	_add_bubble(message, "user")
	var pending_label := _add_bubble("denkt nach …", "assistant", engine)
	_busy = true
	_update_busy()
	if conversation_id.is_empty():
		await _create_conversation(false)
	var model := ""
	if _model_picker.item_count:
		model = _model_picker.get_item_text(_model_picker.selected)
	var payload := build_send_payload(engine, model, message, conversation_id)
	var queued = await _client().post_json("/api/engine-send", payload)
	if not queued is Dictionary or str(queued.get("job", "")).is_empty():
		pending_label.text = "Fehler: Kein Antwort-Ticket erhalten."
		_busy = false
		_update_busy()
		return
	_pending = {
		"id": str(queued.job), "engine": str(queued.get("engine", engine)),
		"conversation_id": str(queued.get("conversation_id", conversation_id))}
	engine = _pending.engine
	conversation_id = _pending.conversation_id
	_save_state()
	_poll_pending(pending_label)

func _poll_pending(label: Label = null) -> void:
	if _pending.is_empty():
		return
	if label == null:
		label = _add_bubble("Hole die ausstehende Antwort …", "assistant", str(_pending.get("engine", engine)))
		_busy = true
		_update_busy()
	var delay := POLL_START
	while not _pending.is_empty():
		await get_tree().create_timer(delay).timeout
		var response = await _client().post_json("/api/engine-result", {
			"engine": _pending.engine, "job": _pending.id,
			"conversation_id": _pending.conversation_id})
		if not response is Dictionary:
			label.text = "Verbindung unterbrochen — Antwort bleibt auf dem Server erhalten …"
			delay = next_poll_delay(delay)
			continue
		match classify_result(response):
			"handoff":
				label.text = "↪ " + str(response.get("handed_off", {}).get("note", "An andere Engine übergeben"))
				_pending.id = str(response.get("job", _pending.id))
				_pending.engine = str(response.get("engine", _pending.engine))
				_pending.conversation_id = str(response.get("conversation_id", _pending.conversation_id))
				engine = _pending.engine
				conversation_id = _pending.conversation_id
				_save_state()
			"ready":
				_pending.clear()
				_save_state()
				if response.get("ok", false):
					await _read_conversation()
				else:
					label.text = "Fehler: " + str(response.get("error", "Antwort fehlgeschlagen"))
				_busy = false
				_update_busy()
				return
			"lost":
				label.text = "Job verloren: " + str(response.get("error", "unbekannter Fehler"))
				_pending.clear()
				_save_state()
				_busy = false
				_update_busy()
				return
			_:
				label.text = "denkt nach … %ss" % response.get("elapsed", 0)
		delay = next_poll_delay(delay)

func _update_busy() -> void:
	if _send:
		_send.disabled = _busy
	if _engine_picker:
		_engine_picker.disabled = _busy
	if _model_picker:
		_model_picker.disabled = _busy
	if _conversation_picker:
		_conversation_picker.disabled = _busy
	if _fresh:
		_fresh.disabled = _busy
	if _reload:
		_reload.disabled = _busy
	if _knowledge:
		_knowledge.disabled = _busy or conversation_id.is_empty()
	if _attach:
		_attach.disabled = _busy or _session_picker.item_count == 0

func _scroll_to_bottom() -> void:
	await get_tree().process_frame
	_scroll.scroll_vertical = int(_scroll.get_v_scroll_bar().max_value)

func _load_state() -> void:
	var config := ConfigFile.new()
	if config.load(state_path) != OK:
		return
	engine = str(config.get_value("chat", "engine", engine))
	var models = config.get_value("chat", "models", {})
	_models = models if models is Dictionary else {}
	conversation_id = str(config.get_value("chat", "conversation_id", ""))
	var pending = config.get_value("chat", "pending", {})
	_pending = pending if pending is Dictionary else {}

func _save_state() -> void:
	var config := ConfigFile.new()
	config.set_value("chat", "engine", engine)
	config.set_value("chat", "models", _models)
	config.set_value("chat", "conversation_id", conversation_id)
	config.set_value("chat", "pending", _pending)
	config.save(state_path)

static func build_send_payload(chosen_engine: String, model: String, message: String, conversation: String) -> Dictionary:
	var payload := {"engine": chosen_engine, "message": message, "thread": "vr", "conversation_id": conversation}
	if not model.is_empty():
		payload.model = model
	return payload

static func classify_result(result: Dictionary) -> String:
	if result.get("handed_off", false):
		return "handoff"
	if result.get("ready", false):
		return "ready"
	if result.get("lost", false):
		return "lost"
	return "waiting"

static func next_poll_delay(current: float) -> float:
	return minf(current * 1.3, POLL_MAX)
