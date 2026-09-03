extends Node3D
## Native workspace modules share hand input, never an embedded web page.
const PANEL = preload("res://WorkspacePanel.gd")
const CONTENT = preload("res://WorkspaceContent.gd")
const CHAT = preload("res://WorkspaceChat.gd")
const FILES = preload("res://WorkspaceFiles.gd")
const MODULES := {"today": "Heute", "chat": "Chat", "command": "Zentrale", "proposals": "Vorschläge", "money": "Money Board", "costs": "Kosten", "snipes": "Snipes", "dmarc": "DMARC-Leads", "flip": "Flip-Log", "files": "Dateien & Wissen", "nodes": "Rechner & Aufgaben"}
var _panels: Dictionary = {}
var _gestures: Dictionary = {}
var _saved: Dictionary = {}
var _devices: Array = []
var _launcher: Node3D
var _keyboard: Node3D
var _keyboard_target: Node3D
var _compose: LineEdit
var _caps := false
var _key_buttons: Array[Button] = []
var _device_buttons: VBoxContainer
var _active_panel: Node3D
var _dock_follow := true
var _loading_devices := false
@onready var _camera: XRCamera3D = $XROrigin3D/XRCamera3D
@onready var _root: Node3D = $Panels

func _ready() -> void:
	var xr := XRServer.find_interface("OpenXR")
	if xr and xr.is_initialized():
		get_viewport().use_xr = true
	else:
		push_warning("OpenXR unavailable; desktop preview only.")
	for hand in [$XROrigin3D/LeftHand, $XROrigin3D/RightHand]:
		hand.tracking_lost.connect(_on_tracking_lost)
	_build_launcher()
	var layout = await AIOSClient.get_json("/api/vr-layout")
	if layout is Dictionary:
		_saved = layout.get("panels", {})
	open_module("today")
	await refresh_devices()
	for device in _devices:
		if device.get("id", "") != "pico":
			open_device(device)

## Alles in Reichweite: gedrückt wird mit der Fingerspitze direkt auf der
## Fläche, nicht über einen Zeigestrahl. Auslösen früh, loslassen erst deutlich
## weiter weg - dieses Hysterese-Fenster ist der Grund, warum ein zitternder
## Finger den Druck nicht mehr abreißen lässt.
const REACH := 0.68
const TOUCH_DEPTH := 0.025
const RELEASE_DEPTH := 0.09
const HOVER_DEPTH := 0.16
## Standardgröße der Paneele. Über die Kopfzeile (− / +) jederzeit verstellbar,
## die gewählte Größe wird pro Paneel mitgespeichert.
const PANEL_SCALE := 0.62

func _process(_delta: float) -> void:
	for hand in [$XROrigin3D/LeftHand, $XROrigin3D/RightHand]:
		_update_touch(hand)
	if _launcher and _dock_follow and not _launcher.get("_grabbed_by"):
		var yaw := _camera.global_rotation.y
		_launcher.global_position = _camera.global_position + Basis(Vector3.UP, yaw) * Vector3(0, -0.46, -0.66)
		_launcher.global_rotation = Vector3(deg_to_rad(-16), yaw, 0)

func _update_touch(hand: Node3D) -> void:
	var anchor: Node3D = hand.anchor
	if not hand.is_tracked:
		_end_touch(anchor, true)
		return
	var tip: Vector3 = hand.fingertip.global_position
	if _gestures.has(anchor):
		var panel = _gestures[anchor]
		if not is_instance_valid(panel) or not panel.visible:
			_gestures.erase(anchor)
		elif panel.touch_within(tip, RELEASE_DEPTH):
			panel.move_point(anchor, panel.touch_pixel(tip))
		else:
			_end_touch(anchor, false)
		return
	var target = _panel_at(tip, TOUCH_DEPTH)
	if target:
		if target.begin_point(anchor, target.touch_pixel(tip)):
			_gestures[anchor] = target
			if target == _launcher and target.get("_grabbed_by"):
				_dock_follow = false
		return
	var hovered = _panel_at(tip, HOVER_DEPTH)
	if hovered:
		hovered.hover_point(hovered.touch_pixel(tip))

## Das Paneel, dessen Fläche die Fingerspitze am nächsten ist - bei
## überlappenden Paneelen darf nicht das hintere den Druck abfangen.
func _panel_at(tip: Vector3, depth: float):
	var best = null
	var best_depth := depth
	for panel in _panels.values():
		if not panel.visible or not panel.touch_within(tip, depth):
			continue
		var distance: float = absf(panel.touch_local(tip).z)
		if distance <= best_depth:
			best_depth = distance
			best = panel
	return best

func _new_panel(id: String, label: String, module := "", device := "", kind := "phone") -> Node3D:
	var panel := PANEL.new()
	panel.panel_id = id
	panel.title = label
	panel.module_id = module
	panel.device_id = device
	panel.device_kind = kind
	if module != "":
		panel.content_script = FILES if module == "files" else (CHAT if module == "chat" else CONTENT)
	panel.reset_requested.connect(reset_panel)
	panel.close_requested.connect(close_panel)
	panel.keyboard_requested.connect(show_keyboard)
	panel.focus_requested.connect(func(selected):
		if selected != _keyboard and selected != _launcher:
			_active_panel = selected
	)
	_root.add_child(panel)
	_panels[id] = panel
	if id != "workspace_launcher" and id != "workspace_keyboard":
		_place(panel)
	return panel

func open_module(id: String) -> void:
	var key := "workspace_" + id
	if _panels.has(key):
		_panels[key].show()
		return
	_new_panel(key, MODULES.get(id, id), id)

func open_device(device: Dictionary) -> void:
	var id: String = device.get("id", "")
	if id.is_empty() or id == "pico":
		return
	if _panels.has(id):
		_panels[id].show()
		return
	var panel := _new_panel(id, device.get("label", id), "", id, device.get("kind", "phone"))
	if device.get("width") != null and device.get("height") != null:
		panel._image_size = Vector2(float(device.width), float(device.height))

func _place(panel: Node3D, use_saved := true) -> void:
	var saved: Dictionary = _saved.get(panel.panel_id, {})
	if use_saved and saved.has("position") and saved.has("rotation"):
		var p: Array = saved.position
		var r: Array = saved.rotation
		if p.size() == 3 and r.size() == 3:
			panel.position = Vector3(p[0], p[1], p[2])
			panel.rotation_degrees = Vector3(r[0], r[1], r[2])
			panel.scale = Vector3.ONE * clampf(float(saved.get("scale", 1)), 0.22, 2.6)
			return
	# Neu geöffnete Paneele erscheinen dort, wo gerade hingeschaut wird. Vorher
	# bekam jedes einen festen Gitterplatz bis ±60°, was auf Armlänge seitlich
	# neben dem Kopf landet: das Paneel ging auf, war aber schlicht nicht im
	# Blickfeld - genau das sah aus, als hätte sich der Chat nie geöffnet.
	# Ist die Mitte schon belegt, weicht das neue Paneel seitlich aus, statt
	# sich in ein bereits stehendes hineinzustellen.
	var yaw := _camera.global_rotation.y
	var offsets := [0.0, -26.0, 26.0, -52.0, 52.0]
	var angle := 0.0
	for candidate in offsets:
		angle = deg_to_rad(candidate)
		var spot := _camera.global_position + Basis(Vector3.UP, yaw) * Vector3(sin(angle) * REACH, -0.06, -cos(angle) * REACH)
		if not _occupied(spot, panel):
			break
	panel.global_position = _camera.global_position + Basis(Vector3.UP, yaw) * Vector3(sin(angle) * REACH, -0.06, -cos(angle) * REACH)
	panel.global_rotation = Vector3(0, yaw - angle, 0)
	panel.scale = Vector3.ONE * PANEL_SCALE

## Steht dort schon ein sichtbares Paneel? Der Schwellwert entspricht grob
## einer halben Paneelbreite auf Standardgröße.
func _occupied(spot: Vector3, exclude: Node3D) -> bool:
	for panel in _panels.values():
		if panel == exclude or not panel.visible or panel == _launcher or panel == _keyboard:
			continue
		if panel.global_position.distance_to(spot) < 0.34:
			return true
	return false

func reset_panel(panel: Node3D) -> void:
	if panel == _launcher:
		_dock_follow = true
		return
	if panel == _keyboard:
		_position_keyboard()
		return
	var yaw := _camera.global_rotation.y
	panel.global_position = _camera.global_position + Basis(Vector3.UP, yaw) * Vector3(0, -0.06, -REACH)
	panel.global_rotation = Vector3(0, yaw, 0)
	panel.scale = Vector3.ONE * PANEL_SCALE
	panel.save_layout()

func reset_all() -> void:
	for panel in _panels.values():
		if panel == _launcher or panel == _keyboard:
			continue
		_place(panel, false)
		panel.save_layout()
	_dock_follow = true
	if _keyboard:
		_position_keyboard()

func close_panel(panel: Node3D) -> void:
	if panel == _launcher:
		return
	for anchor in _gestures.keys():
		if _gestures[anchor] == panel:
			_gestures.erase(anchor)
	panel.hide()
	if panel == _keyboard:
		_launcher.show()
	elif panel == _keyboard_target and _keyboard:
		_keyboard.hide()
		_launcher.show()

func _on_tracking_lost(anchor: Node3D) -> void:
	_end_touch(anchor, true)

func _end_touch(anchor: Node3D, cancelled: bool) -> void:
	if not _gestures.has(anchor):
		return
	var panel = _gestures[anchor]
	_gestures.erase(anchor)
	if is_instance_valid(panel):
		panel.end_touch(anchor, cancelled)

func _build_launcher() -> void:
	_launcher = _new_panel("workspace_launcher", "Werkzeuge · oben greifen")
	_launcher.scale = Vector3.ONE * 0.60
	var column := VBoxContainer.new()
	_launcher.body.add_child(column)
	column.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var hint := Label.new()
	hint.text = "Module öffnen · mit dem Zeigefinger antippen · Kopfzeile ziehen zum Verschieben"
	column.add_child(hint)
	var grid := GridContainer.new()
	grid.columns = 3
	column.add_child(grid)
	for id in MODULES:
		var button: Button = _launcher._button(grid, MODULES[id], open_module.bind(id))
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var row := HBoxContainer.new()
	column.add_child(row)
	_launcher._button(row, "Alle Positionen zurücksetzen", reset_all)
	_launcher._button(row, "Tastatur", func():
		if _active_panel:
			show_keyboard(_active_panel)
	)
	_launcher._button(row, "Geräte neu suchen", refresh_devices)
	_device_buttons = VBoxContainer.new()
	column.add_child(_device_buttons)

func refresh_devices() -> void:
	if _loading_devices:
		return
	_loading_devices = true
	var response = await AIOSClient.get_json("/api/devices")
	_loading_devices = false
	for child in _device_buttons.get_children():
		child.queue_free()
	if not response is Dictionary:
		var status := Label.new()
		status.text = "Server nicht erreichbar · Geräte neu suchen"
		_device_buttons.add_child(status)
		return
	_devices = response.get("devices", [])
	var row := HBoxContainer.new()
	_device_buttons.add_child(row)
	for device in _devices:
		if device.get("id") == "pico":
			continue
		var label: String = device.get("label", device.get("id", "Gerät"))
		if not device.get("reachable", false):
			label += " · offline"
		_launcher._button(row, label, open_device.bind(device))

func show_keyboard(target: Node3D) -> void:
	if target == _keyboard or target == _launcher:
		target = _active_panel
	if not is_instance_valid(target):
		return
	_keyboard_target = target
	if not _keyboard:
		_keyboard = _new_panel("workspace_keyboard", "Tastatur")
		_build_keyboard()
	_keyboard.show()
	_launcher.hide()
	_compose.placeholder_text = "Text für " + target.title + " · dann Text senden"
	_compose.visible = target.device_id != ""
	_position_keyboard()

func _position_keyboard() -> void:
	var yaw := _camera.global_rotation.y
	_keyboard.global_position = _camera.global_position + Basis(Vector3.UP, yaw) * Vector3(0, -0.40, -0.56)
	_keyboard.global_rotation = Vector3(deg_to_rad(-22), yaw, 0)
	_keyboard.scale = Vector3.ONE * 0.78

func _build_keyboard() -> void:
	var column := VBoxContainer.new()
	_keyboard.body.add_child(column)
	column.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_compose = LineEdit.new()
	_compose.custom_minimum_size.y = 96
	_compose.add_theme_font_size_override("font_size", 40)
	column.add_child(_compose)
	# Tastenhöhe und Schrift bewusst groß: getroffen wird mit der Fingerspitze,
	# und die Handverfolgung zittert um einige Millimeter. Eine Taste, die
	# kleiner als dieses Zittern ist, trifft man nicht zuverlässig - genau das
	# machte das Tippen vorher unbrauchbar. Die Sonderzeichenreihe ist raus,
	# damit die verbleibenden Tasten breiter werden.
	for letters in ["1234567890", "qwertzuiopü", "asdfghjklöä", "yxcvbnm,.-"]:
		var row := HBoxContainer.new()
		column.add_child(row)
		for letter in letters:
			var button: Button = _keyboard._button(row, letter, _letter.bind(letter))
			button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			button.custom_minimum_size.y = 118
			button.add_theme_font_size_override("font_size", 44)
			_key_buttons.append(button)
	var row := HBoxContainer.new()
	column.add_child(row)
	for entry in [
		["Shift", func():
			_caps = not _caps
			for button in _key_buttons:
				button.text = button.text.to_upper() if _caps else button.text.to_lower()
		],
		["Leertaste", _letter.bind(" ")],
		["⌫", func(): _key(KEY_BACKSPACE, "backspace")],
		["Enter", func(): _key(KEY_ENTER, "enter")],
		["Text senden", func():
			if is_instance_valid(_keyboard_target) and not _compose.text.is_empty():
				_keyboard_target.type_text(_compose.text)
				_compose.text = ""
		],
	]:
		var button: Button = _keyboard._button(row, entry[0], entry[1])
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.custom_minimum_size.y = 118
		button.add_theme_font_size_override("font_size", 36)
	var hint := Label.new()
	hint.text = "Modul: zuerst Textfeld antippen · Geräte: Text sammeln und senden"
	column.add_child(hint)

func _letter(letter: String) -> void:
	if not is_instance_valid(_keyboard_target):
		return
	var value := letter.to_upper() if _caps else letter
	if _keyboard_target.device_id != "":
		_compose.text += value
	else:
		_keyboard_target.type_text(value)

func _key(code: int, remote: String) -> void:
	if not is_instance_valid(_keyboard_target):
		return
	if _keyboard_target.device_id != "" and code == KEY_BACKSPACE and not _compose.text.is_empty():
		_compose.text = _compose.text.left(-1)
		return
	_keyboard_target.type_key(code, remote)
