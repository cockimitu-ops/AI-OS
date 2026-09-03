extends SceneTree
## Direktes Berühren statt Zeigestrahl: die Fingerspitze muss die Fläche
## treffen, Rauschen darf den Druck nicht abreißen, und der Finger einer
## danebenliegenden Hand darf nicht durch das Paneel hindurch drücken.
const PanelScript = preload("res://WorkspacePanel.gd")

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var panel := PanelScript.new()
	panel.panel_id = "touch"
	root.add_child(panel)
	# Das Paneel liegt im Ursprung, Fläche in der xy-Ebene, Normale entlang z.
	var half := Vector2(1.12, 1.12 * 850.0 / 1100.0) * 0.5

	# Auslösetiefe: knapp davor zählt, weit davor nicht.
	assert(panel.touch_within(Vector3(0, 0, 0.01), 0.025), "Finger an der Fläche berührt sie")
	assert(not panel.touch_within(Vector3(0, 0, 0.2), 0.025), "Finger weit davor berührt nicht")

	# Hysterese: was beim Auslösen zu weit weg war, hält beim Loslassen noch.
	assert(not panel.touch_within(Vector3(0, 0, 0.06), 0.025), "Auslösen erst nah an der Fläche")
	assert(panel.touch_within(Vector3(0, 0, 0.06), 0.09), "Gehaltener Druck übersteht Zittern")

	# Seitlich daneben ist kein Druck, egal wie nah an der Ebene.
	assert(not panel.touch_within(Vector3(half.x + 0.1, 0, 0.0), 0.09), "Neben der Fläche zählt nicht")
	assert(not panel.touch_within(Vector3(0, half.y + 0.1, 0.0), 0.09), "Über der Fläche zählt nicht")

	# Die berührte Stelle ist die gedrückte Stelle.
	assert(panel.touch_pixel(Vector3.ZERO).is_equal_approx(Vector2(550, 425)), "Mitte trifft Mitte")
	var left_edge := panel.touch_pixel(Vector3(-half.x, 0, 0))
	assert(is_equal_approx(left_edge.x, 0.0), "Linke Kante ist Pixelspalte 0")

	# Ein Druck, der die Fläche nie erreicht hat, darf nicht klicken.
	var anchor := Node3D.new()
	root.add_child(anchor)
	assert(not panel.begin_point(anchor, Vector2(-50, -50)), "Außerhalb der Pixelfläche kein Druck")
	assert(panel.begin_point(anchor, Vector2(550, 600)), "Auf der Fläche beginnt ein Druck")
	# Zweite Hand darf einen laufenden Druck nicht übernehmen.
	var other := Node3D.new()
	root.add_child(other)
	assert(not panel.begin_point(other, Vector2(550, 600)), "Zweite Hand greift nicht dazwischen")
	panel.end_touch(anchor)

	print("test_touch_input ok")
	quit()
