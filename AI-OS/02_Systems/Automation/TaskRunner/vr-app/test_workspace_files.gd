extends SceneTree
const Files = preload("res://WorkspaceFiles.gd")
class FakeAPI extends Node:
	var requests: Array = []
	func get_json(_path: String) -> Dictionary:
		return {"files": []}
	func post_json(path: String, body: Dictionary) -> Dictionary:
		requests.append({"path": path, "body": body})
		if path == "/api/vault-search":
			return {"hits": [{"page": "Notes/test.md", "snippet": "Matching note"}], "total": 1}
		return {"page": "Notes/test.md", "content": "Readable note", "truncated": false}
	func post_bytes(path: String, bytes: PackedByteArray) -> Dictionary:
		requests.append({"path": path, "bytes": bytes})
		return {"name": "test.txt", "size": bytes.size()}

func _init() -> void:
	call_deferred("run")

func run() -> void:
	var fake := FakeAPI.new()
	root.add_child(fake)
	var files := Files.new()
	files.api_override = fake
	files.size = Vector2(1068, 750)
	root.add_child(files)
	await process_frame
	files._query.text = "AIOS"
	await files._search()
	assert(fake.requests[-1].body == {"query": "AIOS", "limit": 20}, "Search must use the real vault contract")
	await files._open_page("Notes/test.md")
	assert(files._results.get_child(2).text == "Readable note", "Vault content must be rendered, not just metadata")
	assert(Files.safe_local_name("../../outside.txt") == "outside.txt", "A downloaded filename must stay in the local downloads directory")
	var output := FileAccess.open("user://native-file-test.txt", FileAccess.WRITE)
	output.store_string("Grüße from VR")
	output.close()
	files._selected_path = "user://native-file-test.txt"
	files._filename.text = "test.txt"
	await files._upload()
	assert(fake.requests[-1].path == "/api/upload?name=test.txt")
	assert(fake.requests[-1].bytes.get_string_from_utf8() == "Grüße from VR", "Upload must preserve the selected file bytes")
	DirAccess.remove_absolute("user://native-file-test.txt")
	files.queue_free()
	fake.queue_free()
	await process_frame
	print("PASS: native vault search/read, safe downloads, binary upload contract")
	quit()
