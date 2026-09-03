extends SceneTree
## A ray over letterbox bars must not click a phone; lost tracking must not tap.
const PanelScript = preload("res://WorkspacePanel.gd")
var clicks := 0

func _init() -> void:
	var midpoint := PanelScript.pixel_from_local(Vector3.ZERO, Vector2(1.12, 0.865))
	assert(midpoint.is_equal_approx(Vector2(550, 425)))
	var rect := Rect2(0, 0, 1000, 700)
	var size := Vector2(1080, 2400)
	assert(PanelScript.image_point(Vector2(5, 350), rect, size).x == -1, "Letterbox is not part of the phone")
	assert(PanelScript.image_point(Vector2(500, 350), rect, size).is_equal_approx(Vector2(540, 1200)), "Center maps through aspect-preserving scaling")
	assert(PanelScript.image_point(Vector2.ZERO, rect, Vector2.ZERO).x == -1, "An unavailable screen must not accept input")
	call_deferred("_run")

func _run() -> void:
	var panel := PanelScript.new()
	panel.panel_id = "test"
	root.add_child(panel)
	var anchor := Node3D.new()
	root.add_child(anchor)
	var scroll := ScrollContainer.new()
	panel.body.add_child(scroll)
	scroll.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var rows := VBoxContainer.new()
	rows.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(rows)
	for i in range(30):
		var button := Button.new()
		button.text = "Row %d" % i
		button.custom_minimum_size.y = 80
		button.pressed.connect(func(): clicks += 1)
		rows.add_child(button)
	await process_frame
	await process_frame
	panel.hide()
	await process_frame
	assert(panel._shape.disabled, "A hidden module must stop intercepting hand rays")
	panel.show()
	await process_frame
	assert(not panel._shape.disabled, "A reopened module must accept hand rays again")
	var ray := RayCast3D.new()
	root.add_child(ray)
	ray.position = Vector3(0, 0, 1)
	ray.target_position = Vector3(0, 0, -2)
	assert(panel.begin_pointer(anchor, ray))
	assert(panel._scroll == scroll, "A pinch on list content must select its scroll container")
	ray.position.y += 0.15
	panel.move_pointer(anchor, ray)
	assert(scroll.scroll_vertical > 0, "Dragging upward must reveal lower rows")
	panel.end_pointer(anchor, ray)
	assert(clicks == 0, "Finishing a scroll must never activate a button underneath")
	panel._owner = anchor
	panel._dragged = false
	panel.end_pointer(anchor, null, true)
	assert(panel._owner == null, "Tracking loss cancels without requiring a ray or triggering a click")
	var field := LineEdit.new()
	panel.body.add_child(field)
	field.grab_focus()
	panel.type_text("Grüße")
	assert(field.text == "Grüße", "Virtual keyboard must preserve German characters in the focused field")
	panel.type_key(KEY_BACKSPACE, "backspace")
	assert(field.text == "Grüß", "Backspace must edit the focused native field")
	panel.queue_free()
	anchor.queue_free()
	ray.queue_free()
	await process_frame
	print("PASS: panel mapping, letterbox exclusion, swipe scrolling without accidental clicks, lost-tracking cancellation")
	quit()
