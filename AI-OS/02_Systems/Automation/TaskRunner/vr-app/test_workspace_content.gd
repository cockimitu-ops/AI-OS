extends SceneTree

func _init() -> void:
	var script = load("res://WorkspaceContent.gd")
	var content = script.new()
	var expected := ["today", "command", "proposals", "money", "costs", "dmarc", "snipes", "flip", "files", "nodes"]
	assert(Array(content.supported_modules()) == expected, "Every launcher module needs a native implementation")
	assert(not content.confirm_gate("restore_a"), "Destructive restore must not run on first press")
	assert(content.confirm_gate("restore_a"), "Repeating the exact action confirms it")
	assert(not content.confirm_gate("node_pc_cmd"), "A different dangerous action needs its own confirmation")
	assert(not content.confirm_gate("restore_a"), "Switching action invalidates the previous confirmation")
	# Matches safety_controls consensus_result: status/replies/comparison, not ready/reply.
	assert(content.consensus_state({"status":"pending"}) == "waiting")
	assert(content.consensus_state({"status":"running"}) == "waiting")
	var check := {"status":"completed", "replies":{"google-pro":{"ok":true,"reply":"Google evidence"}, "codex":{"ok":true,"reply":"Codex evidence"}}, "comparison":{"identical":false,"disagreement_explanation":"Different tradeoffs"}}
	assert(content.consensus_state(check) == "complete", "Completed real API result must finish polling")
	var cards: Array = content.consensus_cards(check)
	assert(cards.size() == 3, "Verdict plus both named engines remain visible")
	assert(cards[0].lines[0] == "Different tradeoffs")
	assert(cards[1].title == "google-pro" and cards[1].lines[0] == "Google evidence")
	assert(cards[2].title == "codex" and cards[2].lines[0] == "Codex evidence")
	var failed := {"status":"completed", "replies":{"codex":{"ok":false,"error":"Quota exhausted"}}, "comparison":{}}
	assert(content.consensus_cards(failed)[1].error, "Engine failures must not look like successful answers")
	assert(content.consensus_state({"error":"Unknown ID"}) == "error")
	assert(content.node_state({"ready":false,"state":"wartet"}) == "waiting")
	assert(content.node_state({"ready":true,"ok":false,"output":"exit 1"}) == "complete", "Failed completed commands still finish polling")
	assert(content.node_state({"ready":false,"lost":true,"error":"Job nicht mehr auffindbar"}) == "lost")
	var source: String = script.source_code.to_lower()
	assert("webview" not in source and "web_view" not in source, "Workspace content must stay native")
	content.free()
	print("WORKSPACE_CONTENT_TESTS_OK")
	quit(0)

