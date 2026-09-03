extends Node3D
## Startet OpenXR, holt die echten Geräte vom Server, setzt für jedes ein
## Panel an seine gespeicherte Stelle - oder, beim allerersten Start, fächer-
## förmig vor Felix auf, damit nie eins hinter einem anderen versteckt liegt.

const PANEL_SCENE := preload("res://Panel.tscn")

@onready var _panels_root: Node3D = $Panels

func _ready() -> void:
	_start_openxr()
	for hand in [$XROrigin3D/LeftHand, $XROrigin3D/RightHand]:
		hand.grab_pressed.connect(_on_grab)
		hand.grab_released.connect(_on_release)
	await _populate_room()

func _start_openxr() -> void:
	var xr := XRServer.find_interface("OpenXR")
	if xr == null or not xr.is_initialized():
		push_warning("Room: OpenXR-Schnittstelle nicht verfügbar - läuft als flaches Fenster.")
		return
	get_viewport().use_xr = true

func _populate_room() -> void:
	var devices = await AIOSClient.get_json("/api/devices")
	var layout = await AIOSClient.get_json("/api/vr-layout")
	if devices == null or not devices.has("devices"):
		push_warning("Room: /api/devices nicht erreichbar.")
		return
	var saved: Dictionary = {}
	if layout != null and layout.has("panels"):
		saved = layout["panels"]

	# Pico ist die Brille selbst, die gerade zuschaut - kein Ziel, das sie im
	# eigenen Raum spiegeln müsste. Vorab gefiltert, damit die Fächer-Mitte
	# unten auf der tatsächlichen Panel-Zahl beruht, nicht der Geräte-Zahl
	# inklusive der ausgeschlossenen Brille.
	var targets: Array = []
	for dev in devices["devices"]:
		var id: String = dev.get("id", "")
		if id != "" and id != "pico":
			targets.append(id)

	var placed := 0
	for id in targets:
		var panel := PANEL_SCENE.instantiate()
		panel.device_id = id
		_panels_root.add_child(panel)
		if saved.has(id):
			var p = saved[id]
			panel.position = Vector3(p["position"][0], p["position"][1], p["position"][2])
			panel.rotation_degrees = Vector3(p["rotation"][0], p["rotation"][1], p["rotation"][2])
		else:
			# Fächer vor dem Startpunkt: 0.9m Abstand, 35° auseinander,
			# mittig auf Augenhöhe - jedes neue Gerät bekommt automatisch
			# einen freien Platz statt Felix' letztes Panel zu überlappen.
			var angle := deg_to_rad(35.0 * (placed - (targets.size() - 1) / 2.0))
			var camera := $XROrigin3D/XRCamera3D as XRCamera3D
			var yaw := camera.global_rotation.y
			panel.global_position = camera.global_position + Basis(Vector3.UP, yaw) * Vector3(sin(angle) * 1.4, -0.1, -cos(angle) * 1.4)
			panel.rotation_degrees = Vector3(0, rad_to_deg(yaw - angle), 0)
		placed += 1

func _on_grab(anchor: Node3D, ray: RayCast3D) -> void:
	if not ray.is_colliding():
		return
	var hit := ray.get_collider() as Node
	if hit == null:
		return
	var panel := hit.get_parent()
	if panel and panel.has_method("grab") and panel.get("_grabbed_by") == null:
		panel.grab(anchor)
		print("AIOS_ROOM grabbed ", panel.device_id)

func _on_release(anchor: Node3D) -> void:
	for panel in _panels_root.get_children():
		if panel.has_method("release") and panel.get("_grabbed_by") == anchor:
			panel.release()
			print("AIOS_ROOM released ", panel.device_id, " at ", panel.position)
