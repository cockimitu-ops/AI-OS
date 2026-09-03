extends Node3D
## Ein Gerät als greifbare Fläche im Raum. Zeigt dessen Bildschirm, folgt der
## Hand solange sie zupackt, meldet die neue Stelle dem Server beim Loslassen.

@export var device_id: String = ""

@onready var _mesh: MeshInstance3D = $Screen
@onready var _label: Label3D = $Label

var _grabbed_by: Node3D = null
var _grab_offset: Transform3D = Transform3D.IDENTITY
var _refresh_timer: float = 0.0
const REFRESH_INTERVAL := 2.0  # Sekunden zwischen zwei Screenshots.

func _ready() -> void:
	# Panel.tscn definiert das QuadMesh einmal als sub_resource - ohne
	# duplicate() teilen sich ALLE Panel-Instanzen dasselbe Mesh-Objekt, und
	# _refresh_screen() passt unten die Größe ans Seitenverhältnis des
	# jeweiligen Geräts an. Mit drei Geräten unterschiedlichen Formats (Pico
	# quer, Handys hochkant) hieße das: jedes Bild-Update verzerrt heimlich
	# auch die Panels der anderen Geräte.
	_mesh.mesh = _mesh.mesh.duplicate()
	_label.text = device_id
	_refresh_screen()

func _process(delta: float) -> void:
	if _grabbed_by:
		# Das Panel hängt an der Hand, mit dem Versatz vom Moment des
		# Zugreifens - sonst springt es beim Anfassen auf die Handmitte,
		# statt an der Stelle zu bleiben, an der man es berührt hat.
		global_transform = _grabbed_by.global_transform * _grab_offset
		return
	_refresh_timer += delta
	if _refresh_timer >= REFRESH_INTERVAL:
		_refresh_timer = 0.0
		_refresh_screen()

func grab(controller: Node3D) -> void:
	_grabbed_by = controller
	_grab_offset = controller.global_transform.affine_inverse() * global_transform

func release() -> void:
	if not _grabbed_by:
		return
	_grabbed_by = null
	var pos := global_position
	var rot := rotation_degrees
	# Erst loslassen, dann melden - ein langsamer Server darf die Hand nicht
	# eine Zehntelsekunde festhalten.
	AIOSClient.post_json("/api/vr-layout", {
		"device": device_id,
		"position": [pos.x, pos.y, pos.z],
		"rotation": [rot.x, rot.y, rot.z],
	})

func _refresh_screen() -> void:
	var res = await AIOSClient.post_json("/api/device-action", {
		"device": device_id, "action": "screenshot",
	})
	if res == null or not res.has("url"):
		return
	var bytes := await AIOSClient.get_bytes(res["url"])
	if bytes.is_empty():
		return
	var img := Image.new()
	var err := img.load_png_from_buffer(bytes)
	if err != OK:
		return
	var tex := ImageTexture.create_from_image(img)
	var mat := _mesh.get_surface_override_material(0)
	if mat == null:
		mat = StandardMaterial3D.new()
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		_mesh.set_surface_override_material(0, mat)
	mat.albedo_texture = tex
	# Quer-/Hochformat des echten Geräts übernehmen, statt es auf ein
	# quadratisches Panel zu quetschen.
	var aspect := float(img.get_width()) / float(img.get_height())
	var h: float = _mesh.mesh.size.y
	_mesh.mesh.size = Vector2(h * aspect, h)
