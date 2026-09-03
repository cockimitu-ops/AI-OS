extends Node
## Render actual native controls for visual checks without needing the headset.
const PanelScript = preload("res://WorkspacePanel.gd")
var _panel: Node3D

func _ready() -> void:
	var arguments := OS.get_cmdline_user_args()
	var module := arguments[0] if not arguments.is_empty() else ""
	_panel = PanelScript.new()
	_panel.panel_id = "preview"
	_panel.title = "AIOS · " + module
	if module != "":
		_panel.content_script = load("res://WorkspaceFiles.gd" if module == "files" else ("res://WorkspaceChat.gd" if module == "chat" else "res://WorkspaceContent.gd"))
		_panel.module_id = module
	add_child(_panel)
	_panel.viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	if module == "":
		var label := Label.new()
		label.text = "Native 3D-Module\nPinchen zum Klicken · ziehen zum Wischen"
		_panel.body.add_child(label)
	await get_tree().create_timer(12.0 if module != "" else 1.0).timeout
	await RenderingServer.frame_post_draw
	var path := "/home/nost/vr-debug-20260903/native-" + (module if module != "" else "shell") + ".png"
	var error: int = _panel.viewport.get_texture().get_image().save_png(path)
	print("PREVIEW ", path, " result=", error)
	get_tree().quit(error)
