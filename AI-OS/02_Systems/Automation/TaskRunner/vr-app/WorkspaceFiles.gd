extends Control
## Files and knowledge use native scrollable controls, including local imports.
signal text_focus(field: Control)
var module_id := "files"
var api_override: Node
var _column: VBoxContainer
var _results: VBoxContainer
var _status: Label
var _query: LineEdit
var _filename: LineEdit
var _selected_path := ""
var _busy := false
var _voice_confirm := false
var _picker: FileDialog

func _client() -> Node:
	return api_override if api_override else get_node("/root/AIOSClient")

func _ready() -> void:
	_column = VBoxContainer.new()
	add_child(_column)
	_column.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var tools := HBoxContainer.new()
	_column.add_child(tools)
	_button(tools, "Server-Dateien", refresh)
	_button(tools, "Heruntergeladen", _local_files)
	_button(tools, "Datei auswählen", _select_file)
	_button(tools, "Stimmprofil importieren", _voice_import)
	var search := HBoxContainer.new()
	_column.add_child(search)
	_query = _field(search, "Wissen im Vault suchen …")
	_button(search, "Suchen", _search)
	_query.text_submitted.connect(func(_text): _search())
	var upload := HBoxContainer.new()
	_column.add_child(upload)
	_filename = _field(upload, "Dateiname für den Upload")
	_button(upload, "Hochladen", _upload)
	_status = _label(_column, "Lädt Dateien …")
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_column.add_child(scroll)
	_results = VBoxContainer.new()
	_results.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(_results)
	refresh()

func _button(parent: Node, label: String, callback: Callable) -> Button:
	var button := Button.new()
	button.text = label
	button.focus_mode = Control.FOCUS_NONE
	parent.add_child(button)
	button.pressed.connect(callback)
	return button

func _label(parent: Node, text: String) -> Label:
	var label := Label.new()
	label.text = text
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	parent.add_child(label)
	return label

func _field(parent: Node, placeholder: String) -> LineEdit:
	var field := LineEdit.new()
	field.placeholder_text = placeholder
	field.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	parent.add_child(field)
	field.focus_entered.connect(func(): text_focus.emit(field))
	return field

func _clear() -> void:
	for child in _results.get_children():
		_results.remove_child(child)
		child.queue_free()

func refresh() -> void:
	if _busy:
		return
	_busy = true
	_status.text = "Lädt Dateien …"
	var downloads = await _client().get_json("/api/downloads")
	var uploads = await _client().get_json("/api/uploads")
	_clear()
	_label(_results, "Erstellte Dateien")
	if downloads is Dictionary:
		for file in downloads.get("files", []):
			var row := HBoxContainer.new()
			_results.add_child(row)
			_label(row, str(file.get("name", "Datei")) + " · " + String.humanize_size(int(file.get("size", 0))))
			_button(row, "Laden & öffnen", _download.bind(file))
	_label(_results, "Hochgeladen")
	if uploads is Dictionary:
		for file in uploads.get("files", []):
			_label(_results, str(file.get("name", "Datei")) + " · " + String.humanize_size(int(file.get("size", 0))))
	_status.text = "Dateien bereit" if downloads is Dictionary else "Keine Verbindung · Server-Dateien erneut drücken"
	_busy = false

func _search() -> void:
	if _busy or _query.text.strip_edges().length() < 2:
		return
	_busy = true
	var response = await _client().post_json("/api/vault-search", {"query": _query.text.strip_edges(), "limit": 20})
	_clear()
	if response is Dictionary and response.has("hits"):
		_status.text = "%d Treffer" % int(response.get("total", 0))
		for hit in response.hits:
			_button(_results, str(hit.get("page", "Seite")), _open_page.bind(str(hit.get("page", ""))))
			_label(_results, str(hit.get("snippet", "")))
	else:
		_status.text = "Suche fehlgeschlagen · erneut versuchen"
	_busy = false

func _open_page(page: String) -> void:
	if _busy:
		return
	_busy = true
	var response = await _client().post_json("/api/vault-page", {"page": page})
	if response is Dictionary and response.has("content"):
		_clear()
		_button(_results, "Zurück zur Suche", _search)
		_label(_results, page)
		_label(_results, str(response.content))
		_status.text = "Auszug · Seite ist länger" if response.get("truncated", false) else "Wissensseite"
	else:
		_status.text = "Seite nicht erreichbar"
	_busy = false

static func safe_local_name(name: String) -> String:
	return name.replace("\\", "/").get_file().validate_filename()

func _download(file: Dictionary) -> void:
	if _busy:
		return
	_busy = true
	_status.text = "Lädt " + str(file.get("name", "Datei"))
	var url: String = file.get("url", "")
	# Encode each segment: spaces and non-ASCII names remain valid HTTP paths.
	var parts := url.split("/")
	for i in range(parts.size()):
		parts[i] = parts[i].uri_encode()
	var bytes: PackedByteArray = await _client().get_bytes("/".join(parts))
	if bytes.is_empty():
		_status.text = "Download fehlgeschlagen"
	else:
		DirAccess.make_dir_recursive_absolute("user://downloads")
		var name := safe_local_name(str(file.get("name", "download")))
		var path := "user://downloads/" + name
		if FileAccess.file_exists(path):
			path = "user://downloads/%d_%s" % [int(Time.get_unix_time_from_system()), name]
		var output := FileAccess.open(path, FileAccess.WRITE)
		if output:
			output.store_buffer(bytes)
			output.close()
			_open_local(path)
		else:
			_status.text = "Datei konnte nicht gespeichert werden"
	_busy = false

func _local_files() -> void:
	_clear()
	var dir := DirAccess.open("user://downloads")
	if not dir:
		_status.text = "Noch keine Dateien heruntergeladen"
		return
	for name in dir.get_files():
		_button(_results, name, _open_local.bind("user://downloads/" + name))
	_status.text = "Auf dieser Brille gespeichert"

func _open_local(path: String) -> void:
	var extension := path.get_extension().to_lower()
	_clear()
	_button(_results, "Zurück zu Downloads", _local_files)
	_status.text = "Gespeichert: " + path.get_file()
	if extension in ["txt", "md", "json", "csv", "log"]:
		var text := FileAccess.get_file_as_string(path)
		_label(_results, text.left(100000))
		if text.length() > 100000:
			_label(_results, "Vorschau gekürzt. Die vollständige Datei bleibt gespeichert.")
	elif extension in ["png", "jpg", "jpeg", "webp"]:
		var image := Image.load_from_file(path)
		if image:
			var picture := TextureRect.new()
			picture.texture = ImageTexture.create_from_image(image)
			picture.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
			picture.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			picture.custom_minimum_size.y = 450
			_results.add_child(picture)
	else:
		_label(_results, "Datei heruntergeladen. Zum Öffnen wird eine passende Geräte-App benötigt.")
		_button(_results, "Mit Geräte-App öffnen", func():
			var error := OS.shell_open(ProjectSettings.globalize_path(path))
			if error != OK:
				_status.text = "Keine passende App verfügbar · Datei bleibt gespeichert"
		)

func _select_file() -> void:
	if not _picker:
		_picker = FileDialog.new()
		_picker.access = FileDialog.ACCESS_FILESYSTEM
		_picker.file_mode = FileDialog.FILE_MODE_OPEN_FILE
		_picker.use_native_dialog = OS.get_name() == "Android"
		_picker.size = Vector2i(950, 650)
		add_child(_picker)
		_picker.file_selected.connect(func(path: String):
			_selected_path = path
			var proposed := path.get_file().uri_decode()
			_filename.text = proposed if proposed.contains(".") else "upload.txt"
			_status.text = "Ausgewählt · Dateiname prüfen und Hochladen drücken"
		)
	_picker.popup_centered(Vector2i(950, 650))

func _upload() -> void:
	if _busy or _selected_path.is_empty() or _filename.text.strip_edges().is_empty():
		_status.text = "Zuerst eine Datei auswählen und benennen"
		return
	var file := FileAccess.open(_selected_path, FileAccess.READ)
	if not file:
		_status.text = "Datei nicht lesbar · bitte erneut auswählen"
		return
	var limit := 250 * 1024 * 1024 if _filename.text.to_lower().ends_with(".apk") else 25 * 1024 * 1024
	if file.get_length() > limit:
		_status.text = "Datei zu groß · maximal " + String.humanize_size(limit)
		file.close()
		return
	_busy = true
	var bytes := file.get_buffer(file.get_length())
	file.close()
	var response = await _client().post_bytes("/api/upload?name=" + _filename.text.strip_edges().uri_encode(), bytes)
	_busy = false
	_status.text = "Hochgeladen: " + str(response.name) if response is Dictionary and response.has("name") else str(response.get("error", "Upload fehlgeschlagen") if response is Dictionary else "Upload fehlgeschlagen")

func _voice_import() -> void:
	if not _voice_confirm:
		_voice_confirm = true
		_status.text = "Stimmprofil aus Chat-Exporten neu erstellen? Erneut drücken bestätigt."
		return
	_voice_confirm = false
	_status.text = "Import läuft …"
	var response = await _client().post_json("/api/voice-import", {})
	_status.text = str(response.get("output", response.get("error", "Import abgeschlossen"))) if response is Dictionary else "Import nicht erreichbar"
