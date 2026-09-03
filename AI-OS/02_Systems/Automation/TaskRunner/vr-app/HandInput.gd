extends Node3D
## Pico's action poses can be invalid even when raw optical joints are available.

signal grab_pressed(anchor: Node3D, ray: RayCast3D)
signal grab_released(anchor: Node3D)
signal tracking_lost(anchor: Node3D)

## Direktes Berühren statt Laserzeiger. Der Zeigestrahl ging vom Pinch-Punkt
## aus und nahm die Fingerspitze auch für die Richtung - beim Zukneifen wandert
## also zwangsläufig beides, der Strahl rutscht genau im Moment des Klickens weg.
## Dazu verdecken sich Daumen und Zeigefinger beim Pinchen gegenseitig vor den
## Kameras, weshalb der Pinch nur etwa jedes zehnte Mal ankam. Beides entfällt,
## wenn die Fingerspitze die Paneelfläche einfach durchstößt: keine Richtung,
## die verrutschen kann, und ein ausgestreckter Zeigefinger ist die für die
## Kameras am besten sichtbare Handhaltung überhaupt.
var fingertip := Node3D.new()
var is_tracked := false

@export_enum("left", "right") var hand := "left"
const PINCH_CLOSE := 0.025
const PINCH_OPEN := 0.045
const BONES := [[1, 2, 3, 4, 5], [1, 6, 7, 8, 9, 10], [1, 11, 12, 13, 14, 15], [1, 16, 17, 18, 19, 20], [1, 21, 22, 23, 24, 25]]
var anchor := Node3D.new()
var ray := RayCast3D.new()
var _joints := MultiMeshInstance3D.new()
var _lines := MeshInstance3D.new()
var _line_mesh := ImmediateMesh.new()
var _material := StandardMaterial3D.new()
var _camera: XRCamera3D
var _pinching := false
var _armed := false
var _tracked := false
var _xr: OpenXRInterface
var _aim_dir := Vector3.ZERO

func _ready() -> void:
	_camera = get_parent().get_node("XRCamera3D")
	_xr = XRServer.find_interface("OpenXR") as OpenXRInterface
	add_child(anchor)
	add_child(fingertip)
	add_child(ray)
	ray.target_position = Vector3(0, 0, -5)
	ray.enabled = true
	_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_material.albedo_color = Color(0.35, 0.85, 1.0) if hand == "left" else Color(1.0, 0.75, 0.35)
	var sphere := SphereMesh.new()
	sphere.radius = 0.006
	sphere.height = 0.012
	sphere.radial_segments = 8
	sphere.rings = 4
	var multimesh := MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.mesh = sphere
	multimesh.instance_count = 26
	_joints.multimesh = multimesh
	_joints.material_override = _material
	add_child(_joints)
	_lines.mesh = _line_mesh
	_lines.material_override = _material
	add_child(_lines)
	_joints.hide()
	_lines.hide()

static func next_pinch(was_pinching: bool, distance: float) -> bool:
	if not is_finite(distance) or distance < 0.0:
		return false
	return distance < PINCH_OPEN if was_pinching else distance <= PINCH_CLOSE

func _physics_process(_delta: float) -> void:
	var tracker := XRServer.get_tracker("/user/hand_tracker/" + hand) as XRHandTracker
	if tracker == null or not tracker.has_tracking_data or (_xr and _xr.get_session_state() != OpenXRInterface.SESSION_STATE_FOCUSED):
		_lose_tracking()
		return
	var positions := PackedVector3Array()
	var valid: Array[bool] = []
	for joint in range(26):
		var flags := tracker.get_hand_joint_flags(joint)
		var point := tracker.get_hand_joint_transform(joint).origin
		var ok := (flags & XRHandTracker.HAND_JOINT_FLAG_POSITION_VALID) != 0 and point.is_finite() and point.length() < 20.0
		positions.append(point if ok else Vector3.ZERO)
		valid.append(ok)
		var scale_basis := Basis.IDENTITY if ok else Basis.from_scale(Vector3.ZERO)
		_joints.multimesh.set_instance_transform(joint, Transform3D(scale_basis, positions[joint]))
	if not valid[0] or not valid[5] or not valid[10]:
		_lose_tracking()
		return
	var palm := tracker.get_hand_joint_transform(XRHandTracker.HAND_JOINT_PALM)
	if not palm.basis.is_finite() or absf(palm.basis.determinant()) < 0.01:
		_lose_tracking()
		return
	if not _tracked:
		print("AIOS_HAND ", hand, " tracking acquired")
	_tracked = true
	_joints.show()
	_lines.show()
	var pinch_point := (positions[5] + positions[10]) * 0.5
	anchor.transform = Transform3D(palm.basis.orthonormalized(), pinch_point)
	# Zeigefingerspitze: das, womit tatsächlich gedrückt wird.
	fingertip.position = positions[10]
	is_tracked = true
	# Der Strahl bleibt nur noch als kurzer Stummel für das Greifen am
	# Paneelkopf bestehen, nicht mehr als Zeiger quer durch den Raum.
	var direction := (positions[10] - positions[0]).normalized()
	_aim_dir = direction if _aim_dir == Vector3.ZERO else _aim_dir.slerp(direction, 0.35)
	ray.position = pinch_point
	ray.target_position = _aim_dir * 0.35
	ray.force_raycast_update()
	_line_mesh.clear_surfaces()
	_line_mesh.surface_begin(Mesh.PRIMITIVE_LINES)
	for chain in BONES:
		for i in range(chain.size() - 1):
			if valid[chain[i]] and valid[chain[i + 1]]:
				_line_mesh.surface_add_vertex(positions[chain[i]])
				_line_mesh.surface_add_vertex(positions[chain[i + 1]])
	_line_mesh.surface_end()
	var distance := positions[5].distance_to(positions[10])
	if distance >= PINCH_OPEN:
		_armed = true
	var pinching := _armed and next_pinch(_pinching, distance)
	if pinching != _pinching:
		_pinching = pinching
		print("AIOS_HAND ", hand, " pinch=", pinching, " distance=", distance)
		if pinching:
			grab_pressed.emit(anchor, ray)
		else:
			grab_released.emit(anchor)

func _lose_tracking() -> void:
	if _tracked:
		tracking_lost.emit(anchor)
		print("AIOS_HAND ", hand, " tracking lost")
	_tracked = false
	is_tracked = false
	_armed = false
	_aim_dir = Vector3.ZERO
	_joints.hide()
	_lines.hide()
	if _pinching:
		_pinching = false
		grab_released.emit(anchor)
