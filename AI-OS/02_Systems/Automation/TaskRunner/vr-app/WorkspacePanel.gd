extends Node3D
## One native viewport per movable module. Gestures never move a panel by accident.

signal reset_requested(panel: Node3D)
signal close_requested(panel: Node3D)
signal keyboard_requested(panel: Node3D)
signal focus_requested(panel: Node3D)

const PIXELS := Vector2i(1100, 850)
const HEADER := 76.0
## Loosened from 14: hand-tracking is noisier than the controller aim this was
## tuned for, and residual jitter over a held pinch was enough on its own to
## misclassify most clicks as drags even with a calmer aim ray (see HandInput.gd).
const DRAG_THRESHOLD := 26.0
const STREAM = preload("res://NativeScreenStream.gd")
var panel_id := ""
var title := ""
var module_id := ""
var device_id := ""
var device_kind := "phone"
var content_script: Script
var viewport: SubViewport
var body: Control
var content: Control
var screen: TextureRect
var _status: Label
var _grip: Label
var _mesh: MeshInstance3D
var _shape: CollisionShape3D
var _grabbed_by: Node3D
var _grab_offset := Transform3D.IDENTITY
var _owner: Node3D
var _start := Vector2.ZERO
var _last := Vector2.ZERO
var _started_ms := 0
var _dragged := false
var _scroll: ScrollContainer
var _scroll_start := Vector2.ZERO
var _refreshing := false
var _elapsed := 0.0
var _image_size := Vector2.ZERO
var _device_start := Vector2(-1, -1)
var _action_busy := false
var _actions: Array[Dictionary] = []
var _physical_size := Vector2(1.12, 1.12 * 850.0 / 1100.0)
var _stream: Node
var _click_button := "left"
var _clicks := 1

func _ready() -> void:
	viewport = SubViewport.new()
	viewport.size = PIXELS
	viewport.transparent_bg = true
	viewport.disable_3d = true
	viewport.render_target_update_mode = SubViewport.UPDATE_WHEN_VISIBLE
	viewport.gui_disable_input = false
	viewport.gui_embed_subwindows = true
	add_child(viewport)
	var root := PanelContainer.new()
	root.size = PIXELS
	root.theme = _theme()
	viewport.add_child(root)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 0)
	root.add_child(column)
	var chrome := HBoxContainer.new()
	chrome.custom_minimum_size.y = HEADER
	column.add_child(chrome)
	var grip := Label.new()
	_grip = grip
	grip.text = "  ⠿  " + title
	grip.custom_minimum_size.x = 420
	grip.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	grip.add_theme_font_size_override("font_size", 38)
	chrome.add_child(grip)
	_button(chrome, "−", func(): resize_panel(-0.12))
	_button(chrome, "+", func(): resize_panel(0.12))
	_button(chrome, "⌨", func(): keyboard_requested.emit(self))
	_button(chrome, "Reset", func(): reset_requested.emit(self))
	_button(chrome, "×", func(): close_requested.emit(self))
	body = Control.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(body)
	if device_id != "":
		_build_device()
	elif content_script:
		content = content_script.new()
		content.set("module_id", module_id)
		body.add_child(content)
		content.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		if content.has_signal("text_focus"):
			content.connect("text_focus", func(_field): keyboard_requested.emit(self))
	_mesh = MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size = _physical_size
	_mesh.mesh = quad
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.albedo_texture = viewport.get_texture()
	material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR
	_mesh.material_override = material
	add_child(_mesh)
	
	var frame_mesh := MeshInstance3D.new()
	var frame_quad := QuadMesh.new()
	frame_quad.size = _physical_size + Vector2(0.012, 0.012)
	frame_mesh.mesh = frame_quad
	var frame_mat := StandardMaterial3D.new()
	frame_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	frame_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	frame_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	frame_mat.albedo_color = Color(0.0, 0.6, 1.0, 0.15)
	frame_mesh.material_override = frame_mat
	frame_mesh.position.z = -0.002
	add_child(frame_mesh)
	var collider := StaticBody3D.new()
	add_child(collider)
	_shape = CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(_physical_size.x, _physical_size.y, 0.012)
	_shape.shape = box
	collider.add_child(_shape)
	visibility_changed.connect(_visibility_changed)
	if device_id != "":
		_refresh_device()
		_stream = STREAM.new()
		_stream.device_id = device_id
		add_child(_stream)
		_stream.frame_received.connect(_receive_live_frame)
		_stream.stream_error.connect(func(message): _status.text = message)
		_stream.start()

func _visibility_changed() -> void:
	if _shape:
		_shape.set_deferred("disabled", not visible)
	if viewport:
		viewport.render_target_update_mode = SubViewport.UPDATE_WHEN_VISIBLE if visible else SubViewport.UPDATE_DISABLED
	if content:
		content.process_mode = Node.PROCESS_MODE_INHERIT if visible else Node.PROCESS_MODE_DISABLED
	if not visible and _owner:
		end_pointer(_owner, null, true)
	if _stream:
		if visible:
			_stream.start()
		else:
			_stream.stop()

## Schriftgrößen gelten im 1100x850-Viewport, der anschließend auf eine gut
## halbmetergroße Fläche geschrumpft wird - was am Monitor bequem lesbar wäre,
## ist im Headset zu klein. Deshalb durchgehend größer als sonst üblich.
static func _theme() -> Theme:
	var theme := Theme.new()
	theme.default_font_size = 34
	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color(0.0, 0.1, 0.2, 0.15)
	panel_style.border_color = Color(0.0, 0.8, 1.0, 0.6)
	panel_style.set_border_width_all(2)
	panel_style.set_corner_radius_all(6)
	panel_style.shadow_color = Color(0.0, 0.6, 1.0, 0.4)
	panel_style.shadow_size = 12
	panel_style.content_margin_left = 16
	panel_style.content_margin_right = 16
	panel_style.content_margin_bottom = 12
	theme.set_stylebox("panel", "PanelContainer", panel_style)
	for state in ["normal", "hover", "pressed", "focus"]:
		var style := StyleBoxFlat.new()
		var is_active = (state == "hover" or state == "pressed")
		style.bg_color = Color(1.0, 0.6, 0.0, 0.2) if is_active else Color(0.0, 0.6, 1.0, 0.1)
		style.border_color = Color(1.0, 0.7, 0.0, 0.8) if is_active else Color(0.0, 0.7, 1.0, 0.4)
		style.set_border_width_all(2 if is_active else 1)
		style.set_corner_radius_all(4)
		if is_active:
			style.shadow_color = Color(1.0, 0.6, 0.0, 0.3)
			style.shadow_size = 8
		style.content_margin_left = 18
		style.content_margin_right = 18
		style.content_margin_top = 18
		style.content_margin_bottom = 18
		theme.set_stylebox(state, "Button", style)
	theme.set_color("font_color", "Label", Color(0.6, 0.9, 1.0, 1.0))
	theme.set_font_size("font_size", "Button", 32)
	theme.set_font_size("font_size", "Label", 32)
	theme.set_font_size("font_size", "LineEdit", 34)
	theme.set_font_size("font_size", "OptionButton", 30)
	theme.set_constant("separation", "VBoxContainer", 14)
	theme.set_constant("separation", "HBoxContainer", 12)
	theme.set_constant("scrollbar_width", "VScrollBar", 34)
	return theme

## Mindestgröße, weil hier mit der Fingerspitze getroffen wird und nicht mit
## einem Mauszeiger: ein Knopf, der kleiner als die Zitterbreite der
## Handverfolgung ist, lässt sich nicht zuverlässig treffen.
func _button(parent: Node, text: String, callback: Callable) -> Button:
	var button := Button.new()
	button.text = text
	button.focus_mode = Control.FOCUS_NONE
	button.custom_minimum_size = Vector2(78, 78)
	parent.add_child(button)
	button.pressed.connect(callback)
	return button

func _build_device() -> void:
	var column := VBoxContainer.new()
	body.add_child(column)
	column.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_status = Label.new()
	_status.text = "Verbinde Bildschirm …"
	column.add_child(_status)
	screen = TextureRect.new()
	screen.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	screen.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	screen.size_flags_vertical = Control.SIZE_EXPAND_FILL
	screen.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(screen)
	var toolbar := HBoxContainer.new()
	column.add_child(toolbar)
	if device_kind == "desktop":
		_button(toolbar, "Esc", func(): device_action({"action": "key", "key": "esc"}))
		_button(toolbar, "Tab", func(): device_action({"action": "key", "key": "tab"}))
		_button(toolbar, "Rechtsklick", func():
			_click_button = "right"
			_status.text = "Nächste Berührung: Rechtsklick"
		)
		_button(toolbar, "Doppelklick", func():
			_clicks = 2
			_status.text = "Nächste Berührung: Doppelklick"
		)
	else:
		_button(toolbar, "Zurück", func(): device_action({"action": "key", "key": "back"}))
		_button(toolbar, "Home", func(): device_action({"action": "key", "key": "home"}))
		_button(toolbar, "Apps", func(): device_action({"action": "key", "key": "recents"}))
	_button(toolbar, "↑ Scroll", func(): _scroll_device(-1))
	_button(toolbar, "↓ Scroll", func(): _scroll_device(1))
	_button(toolbar, "Tastatur", func(): keyboard_requested.emit(self))
	_button(toolbar, "Neu laden", func(): _refresh_device())

func _process(delta: float) -> void:
	if _grabbed_by:
		global_transform = _grabbed_by.global_transform * _grab_offset
	if device_id != "" and visible:
		_elapsed += delta
		var live: bool = _stream != null and Time.get_ticks_msec() - int(_stream.last_frame_ms) < 3000 and _stream.last_frame_ms > 0
		if not live and _elapsed >= 3.0:
			_elapsed = 0.0
			_refresh_device()

func _receive_live_frame(bytes: PackedByteArray) -> void:
	var image := Image.new()
	if image.load_jpg_from_buffer(bytes) != OK:
		return
	if screen.texture is ImageTexture and screen.texture.get_width() == image.get_width() and screen.texture.get_height() == image.get_height():
		(screen.texture as ImageTexture).update(image)
	else:
		screen.texture = ImageTexture.create_from_image(image)
	_status.text = "Live · antippen: tippen · über die Fläche ziehen: wischen · Kopfzeile: verschieben"

func _refresh_device() -> void:
	if _refreshing or not is_inside_tree():
		return
	_refreshing = true
	var response = await get_node("/root/AIOSClient").post_json("/api/device-action", {"device": device_id, "action": "screenshot"})
	if not is_inside_tree():
		return
	if response == null or not response.get("ok", false) or not response.has("url"):
		_status.text = "Offline · " + str(response.get("error", "keine Verbindung") if response is Dictionary else "keine Verbindung")
		_refreshing = false
		return
	var bytes: PackedByteArray = await get_node("/root/AIOSClient").get_bytes(str(response["url"]))
	if not is_inside_tree():
		return
	var image := Image.new()
	var error := image.load_png_from_buffer(bytes)
	if error != OK:
		error = image.load_jpg_from_buffer(bytes)
	if error == OK:
		_image_size = Vector2(response.get("width", image.get_width()), response.get("height", image.get_height()))
		screen.texture = ImageTexture.create_from_image(image)
		_status.text = "Antippen: tippen · über die Fläche ziehen: wischen · Kopfzeile ziehen: verschieben"
	else:
		_status.text = "Bild nicht verfügbar · Neu laden"
	_refreshing = false

func device_action(payload: Dictionary) -> void:
	if _actions.size() >= 8:
		_status.text = "Verbindung beschäftigt · kurz warten"
		return
	_actions.append({"payload": payload.duplicate(), "time": Time.get_ticks_msec()})
	if _action_busy:
		return
	_action_busy = true
	while not _actions.is_empty():
		var queued: Dictionary = _actions.pop_front()
		if Time.get_ticks_msec() - int(queued.time) > 2000:
			_status.text = "Eingabe abgelaufen · bitte erneut ausführen"
			continue
		var action: Dictionary = queued.payload
		action["device"] = device_id
		var response = await get_node("/root/AIOSClient").post_json("/api/device-action", action)
		if response is Dictionary and response.get("ok", false):
			_status.text = "Eingabe gesendet"
		else:
			_status.text = str(response.get("error", "Eingabe fehlgeschlagen") if response is Dictionary else "Verbindung unterbrochen")
			_actions.clear()
		_elapsed = 5.0
	_action_busy = false

func _scroll_device(direction: int) -> void:
	if device_kind == "desktop":
		device_action({"action": "scroll", "dy": direction * 480, "x": int(_image_size.x / 2), "y": int(_image_size.y / 2)})
	else:
		var start := 0.72 if direction > 0 else 0.28
		device_action({"action": "swipe", "x1": int(_image_size.x * 0.5), "x2": int(_image_size.x * 0.5), "y1": int(_image_size.y * start), "y2": int(_image_size.y * (1.0 - start)), "ms": 350})

static func pixel_from_local(point: Vector3, extent: Vector2) -> Vector2:
	return Vector2((point.x / extent.x + 0.5) * PIXELS.x, (0.5 - point.y / extent.y) * PIXELS.y)

func ray_pixel(ray: RayCast3D) -> Vector2:
	var origin := to_local(ray.global_position)
	var target := to_local(ray.to_global(ray.target_position))
	var direction := target - origin
	if absf(direction.z) < 0.00001:
		return Vector2(-10000, -10000)
	var distance := -origin.z / direction.z
	if distance < 0.0:
		return Vector2(-10000, -10000)
	return pixel_from_local(origin + direction * distance, _physical_size)

static func image_point(point: Vector2, rect: Rect2, image_size: Vector2) -> Vector2:
	if image_size.x <= 0 or image_size.y <= 0 or rect.size.x <= 0 or rect.size.y <= 0:
		return Vector2(-1, -1)
	var ratio := minf(rect.size.x / image_size.x, rect.size.y / image_size.y)
	var origin := rect.position + (rect.size - image_size * ratio) * 0.5
	var result := (point - origin) / ratio
	if result.x < 0 or result.y < 0 or result.x >= image_size.x or result.y >= image_size.y:
		return Vector2(-1, -1)
	return result.floor()

## Fingerspitze -> Pixel. Anders als beim Strahl gibt es hier keine Richtung,
## die verrutschen könnte: die Stelle, die der Finger berührt, ist die Stelle,
## die gedrückt wird.
func touch_local(global_point: Vector3) -> Vector3:
	return to_local(global_point)

func touch_pixel(global_point: Vector3) -> Vector2:
	return pixel_from_local(to_local(global_point), _physical_size)

## Innerhalb der Fläche und nah genug an ihrer Ebene, um als Berührung zu
## zählen. Die Tiefe ist bewusst großzügig: Handtracking-Rauschen von wenigen
## Millimetern darf einen Druck nicht abreißen lassen.
func touch_within(global_point: Vector3, depth := 0.06) -> bool:
	var local := to_local(global_point)
	var half := _physical_size * 0.5
	return absf(local.x) <= half.x and absf(local.y) <= half.y and absf(local.z) <= depth

func hover(ray: RayCast3D) -> void:
	hover_point(ray_pixel(ray))

func hover_point(point: Vector2) -> void:
	var event := InputEventMouseMotion.new()
	event.position = point
	event.global_position = point
	viewport.push_input(event, true)

func begin_pointer(anchor: Node3D, ray: RayCast3D) -> bool:
	return begin_point(anchor, ray_pixel(ray))

func begin_point(anchor: Node3D, point: Vector2) -> bool:
	if _owner or _grabbed_by:
		return false
	if not Rect2(Vector2.ZERO, Vector2(PIXELS)).has_point(point):
		return false
	_owner = anchor
	_start = point
	_last = point
	_started_ms = Time.get_ticks_msec()
	_dragged = false
	_device_start = Vector2(-1, -1)
	focus_requested.emit(self)
	if _grip.get_global_rect().has_point(point):
		_grabbed_by = anchor
		_grab_offset = anchor.global_transform.affine_inverse() * global_transform
	else:
		_scroll = _find_scroll(body, point)
		if _scroll:
			_scroll_start = Vector2(_scroll.scroll_horizontal, _scroll.scroll_vertical)
		if screen:
			_device_start = image_point(point, screen.get_global_rect(), _image_size)
	return true

func move_pointer(anchor: Node3D, ray: RayCast3D) -> void:
	move_point(anchor, ray_pixel(ray))

func move_point(anchor: Node3D, point: Vector2) -> void:
	if anchor != _owner or _grabbed_by:
		return
	if point.distance_to(_start) > DRAG_THRESHOLD:
		_dragged = true
	if _dragged and _scroll:
		_scroll.scroll_vertical = int(_scroll_start.y + _start.y - point.y)
		_scroll.scroll_horizontal = int(_scroll_start.x + _start.x - point.x)
	_last = point

func end_pointer(anchor: Node3D, ray: RayCast3D, cancelled := false) -> void:
	end_point(anchor, _last if ray == null else ray_pixel(ray), cancelled)

## Der Finger ist beim Loslassen meist schon von der Fläche weg, seine aktuelle
## Position also kein brauchbarer Klickpunkt mehr - deshalb die zuletzt
## berührte Stelle.
func end_touch(anchor: Node3D, cancelled := false) -> void:
	end_point(anchor, _last, cancelled)

func end_point(anchor: Node3D, point: Vector2, cancelled := false) -> void:
	if anchor != _owner:
		return
	_owner = null
	if _grabbed_by:
		_grabbed_by = null
		if not cancelled:
			save_layout()
		return
	if cancelled:
		_scroll = null
		return
	if screen and _device_start.x >= 0:
		var ending := image_point(point, screen.get_global_rect(), _image_size)
		if ending.x >= 0:
			if _dragged:
				device_action({"action": "swipe", "x1": int(_device_start.x), "y1": int(_device_start.y), "x2": int(ending.x), "y2": int(ending.y), "ms": clampi(Time.get_ticks_msec() - _started_ms, 100, 1200)})
			else:
				device_action({"action": "tap", "x": int(ending.x), "y": int(ending.y), "button": _click_button, "clicks": _clicks})
				_click_button = "left"
				_clicks = 1
	elif not _dragged and Rect2(Vector2.ZERO, Vector2(PIXELS)).has_point(point):
		for pressed in [true, false]:
			var event := InputEventMouseButton.new()
			event.position = point
			event.global_position = point
			event.button_index = MOUSE_BUTTON_LEFT
			event.pressed = pressed
			viewport.push_input(event, true)
	_scroll = null

func _find_scroll(node: Node, point: Vector2) -> ScrollContainer:
	var children := node.get_children()
	children.reverse()
	for child in children:
		if child is Control and (not child.is_visible_in_tree() or not child.get_global_rect().has_point(point)):
			continue
		var nested := _find_scroll(child, point)
		if nested:
			return nested
	if node is ScrollContainer and node.get_global_rect().has_point(point):
		return node
	return null

## Größer/kleiner über die Kopfzeile. Untere Grenze tiefer und obere höher als
## früher, weil die Standardgröße beim Wechsel auf Armlänge deutlich kleiner
## geworden ist - der alte Bereich hätte kaum noch Spielraum nach unten gelassen.
func resize_panel(amount: float) -> void:
	var next := clampf(scale.x + amount, 0.22, 2.6)
	scale = Vector3.ONE * next
	save_layout()

func save_layout() -> void:
	get_node("/root/AIOSClient").post_json("/api/vr-layout", {"device": panel_id, "position": [position.x, position.y, position.z], "rotation": [rotation_degrees.x, rotation_degrees.y, rotation_degrees.z], "scale": scale.x})

func type_text(text: String) -> void:
	if device_id != "":
		device_action({"action": "text", "text": text})
		return
	for character in text:
		var event := InputEventKey.new()
		event.unicode = character.unicode_at(0)
		event.pressed = true
		viewport.push_input(event, true)

func type_key(keycode: int, remote_key: String) -> void:
	if device_id != "":
		device_action({"action": "key", "key": remote_key})
		return
	for pressed in [true, false]:
		var event := InputEventKey.new()
		event.keycode = keycode
		event.pressed = pressed
		viewport.push_input(event, true)
