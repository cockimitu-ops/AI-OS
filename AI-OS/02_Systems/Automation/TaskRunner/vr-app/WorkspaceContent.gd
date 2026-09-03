class_name WorkspaceContent
extends Control

## Native workspace modules for the VR room. Each instance owns one module and
## renders into a SubViewport; no browser surface or HTML is involved.

signal text_focus(field: Control)

@export var module_id := "today"

const TITLES := {
	"today": "Heute", "command": "Zentrale", "proposals": "Vorschläge",
	"money": "Geld", "costs": "Kosten", "dmarc": "DMARC-Leads",
	"snipes": "Snipes", "flips": "Flip-Log", "files": "Dateien",
}
const BG := Color("10161d")
const CARD := Color("19232d")
const GOLD := Color("e8b45a")
const TEXT := Color("edf3f7")
const MUTED := Color("9caab5")
const GOOD := Color("68d391")
const BAD := Color("fc8181")

var _status: Label
var _scroll: ScrollContainer
var _body: VBoxContainer
var _busy := false
var _confirm_action := ""
var _confirm_value: Variant
var _snipe_filters := {"tier": null, "watch": null, "max_price": null, "max_distance": null}
var _jobs: Dictionary = {}
var _consensus_polling := false
var _node_polling := false

static func consensus_state(result: Dictionary) -> String:
	if not str(result.get("error", "")).is_empty(): return "error"
	if str(result.get("status", "")) in ["pending", "running"]: return "waiting"
	if str(result.get("status", "")) == "completed" or not (result.get("replies", {}) as Dictionary).is_empty(): return "complete"
	return "error"

static func consensus_cards(result: Dictionary) -> Array:
	if not str(result.get("error", "")).is_empty():
		return [{"title": "Konsens fehlgeschlagen", "lines": [str(result.error)], "error": true}]
	var cards: Array = []
	var replies: Dictionary = result.get("replies", {})
	if replies.is_empty(): return [{"title": "Konsens", "lines": ["Keine Antworten · Status: %s" % result.get("status", "?")], "error": true}]
	var comparison: Dictionary = result.get("comparison", {})
	var verdict := "Beide sind sich einig." if comparison.get("identical", false) else str(comparison.get("disagreement_explanation", "Die Antworten unterscheiden sich."))
	cards.append({"title": "Konsens-Ergebnis", "lines": [verdict], "error": false})
	for engine in replies:
		var answer: Dictionary = replies[engine]
		cards.append({"title": str(engine), "lines": [str(answer.get("reply", "")) if answer.get("ok", false) else str(answer.get("error", "Keine Antwort"))], "error": not answer.get("ok", false)})
	return cards

static func node_state(result: Dictionary) -> String:
	if result.get("lost", false): return "lost"
	if result.get("ready", false): return "complete"
	return "waiting"

func _save_jobs() -> void:
	var file := FileAccess.open("user://workspace_jobs_%s.json" % module_id, FileAccess.WRITE)
	if file: file.store_string(JSON.stringify(_jobs))

func _load_jobs() -> void:
	var path := "user://workspace_jobs_%s.json" % module_id
	if not FileAccess.file_exists(path): return
	var value = JSON.parse_string(FileAccess.get_file_as_string(path))
	if value is Dictionary: _jobs = value

static func supported_modules() -> PackedStringArray:
	return PackedStringArray(["today", "command", "proposals", "money", "costs", "dmarc", "snipes", "flip", "files", "nodes"])

func confirm_gate(key: String) -> bool:
	if _confirm_action != key:
		_confirm_action = key
		return false
	_confirm_action = ""
	return true

func setup(id: String) -> void:
	module_id = id
	if is_node_ready(): refresh()

func _ready() -> void:
	_load_jobs()
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var bg := ColorRect.new()
	bg.color = BG
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var root := VBoxContainer.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 18)
	root.add_theme_constant_override("separation", 12)
	add_child(root)
	var bar := HBoxContainer.new()
	root.add_child(bar)
	_status = Label.new()
	_status.text = "Bereit"
	_status.add_theme_color_override("font_color", MUTED)
	_status.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bar.add_child(_status)
	bar.add_child(_button("Aktualisieren", refresh))
	_scroll = ScrollContainer.new()
	_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	root.add_child(_scroll)
	_new_body()
	call_deferred("refresh")

func refresh() -> void:
	if _busy or not is_node_ready(): return
	_busy = true
	_status.text = "Lädt …"
	_new_body()
	match module_id:
		"today": await _load_today()
		"command": await _load_command()
		"proposals": await _load_proposals()
		"money": await _load_money()
		"costs": await _load_costs()
		"dmarc": await _load_dmarc()
		"snipes": await _load_snipes()
		"flip", "flips": await _load_flips()
		"files", "downloads": await _load_files()
		"nodes": await _load_nodes()
		_: _empty("Dieses Modul ist noch nicht bekannt: %s" % module_id)
	_busy = false
	if _status.text == "Lädt …": _status.text = "Aktuell"

func _client() -> Node:
	return get_node_or_null("/root/AIOSClient")

func _api_get(path: String) -> Variant:
	var client := _client()
	return null if client == null else await client.get_json(path)

func _post(path: String, body: Dictionary = {}) -> Variant:
	var client := _client()
	return null if client == null else await client.post_json(path, body)

func _new_body() -> void:
	if _body:
		_scroll.remove_child(_body)
		_body.queue_free()
	_body = VBoxContainer.new()
	_body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_body.add_theme_constant_override("separation", 12)
	_scroll.add_child(_body)

func _label(text: String, size := 24, color := TEXT) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return label

func _button(text: String, callback: Callable, danger := false) -> Button:
	var button := Button.new()
	button.text = text
	button.custom_minimum_size = Vector2(0, 54)
	button.add_theme_font_size_override("font_size", 22)
	button.add_theme_color_override("font_color", BAD if danger else TEXT)
	button.pressed.connect(callback)
	return button

func _card(title: String, lines: Array, accent := GOLD) -> VBoxContainer:
	var panel := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = CARD
	style.corner_radius_top_left = 14; style.corner_radius_top_right = 14
	style.corner_radius_bottom_left = 14; style.corner_radius_bottom_right = 14
	style.border_width_left = 4; style.border_color = accent
	style.content_margin_left = 18; style.content_margin_right = 18
	style.content_margin_top = 14; style.content_margin_bottom = 14
	panel.add_theme_stylebox_override("panel", style)
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	box.add_child(_label(title, 28, accent))
	for line in lines:
		box.add_child(_label(str(line), 22, MUTED))
	panel.add_child(box)
	_body.add_child(panel)
	return box

func _row_buttons(parent: Container, specs: Array) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	parent.add_child(row)
	for spec in specs:
		var b := _button(str(spec[0]), spec[1], bool(spec[2]) if spec.size() > 2 else false)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(b)

func _empty(message: String) -> void:
	_body.add_child(_label(message, 25, MUTED))

func _failed(message := "Server nicht erreichbar") -> void:
	_status.text = "Fehler"
	var box := _card("Konnte nicht laden", [message], BAD)
	box.add_child(_button("Erneut versuchen", refresh))

func _field(placeholder: String, multiline := false) -> Control:
	var field: Control
	if multiline:
		var edit := TextEdit.new(); edit.placeholder_text = placeholder
		edit.custom_minimum_size = Vector2(0, 150); field = edit
	else:
		var line := LineEdit.new(); line.placeholder_text = placeholder
		line.custom_minimum_size = Vector2(0, 58); field = line
	field.add_theme_font_size_override("font_size", 22)
	field.focus_entered.connect(func(): text_focus.emit(field))
	return field

func _load_today() -> void:
	var d = await _api_get("/api/today")
	if not d is Dictionary: _failed(); return
	var actions: Array = d.get("next_actions", [])
	if actions.is_empty() and d.get("next_action") is Dictionary: actions = [d.next_action]
	if actions.is_empty(): _empty("Alles erledigt.")
	for i in range(actions.size()):
		var a: Dictionary = actions[i]
		var meta := "%s min" % a.get("minutes", 0)
		if float(a.get("euros", 0)) > 0: meta += " · ~%s EUR" % a.euros
		_card("ZUERST" if a.get("gates", false) else ("Als Nächstes" if i == 0 else "Danach"),
			[a.get("action", ""), meta, a.get("note", "")], GOLD if i == 0 else MUTED)
	var s: Dictionary = d.get("signals", {})
	_card("Pipeline", ["%s Leads mit Postadresse · %s Briefe raus · %s Vorschläge offen" %
		[s.get("leads_mailable", 0), s.get("letters_sent", 0), d.get("proposals_pending", 0)]], GOOD)

func _load_command() -> void:
	var d = await _api_get("/api/workers")
	if not d is Dictionary: _failed(); return
	var workers: Array = d.get("engines", [])
	var wb := _card("Wer arbeitet", ["Niemand arbeitet gerade."] if workers.is_empty() else [], GOOD)
	for w in workers: wb.add_child(_label("%s · %s\n%s" % [w.get("engine", "?"), w.get("model", ""), w.get("message", "")], 21, MUTED))
	var q: Dictionary = d.get("queue", {})
	_card("Warteschlange", ["%s Posteingang · %s laufen · %s warten" % [q.get("inbox", 0), q.get("running", 0), q.get("queued", 0)]])
	var s: Dictionary = d.get("safety", {})
	var safety := _card("Schalter", ["Router: %s · heute $%.2f von $%.2f" % [s.get("router_mode", "?"), float(s.get("daily_spent_usd", 0)), float(s.get("daily_spend_cap", 0))]])
	_row_buttons(safety, [["Weiterlaufen" if s.get("global_freeze", false) else "Alles anhalten", Callable(self, "_ask_safety").bind("freeze", not s.get("global_freeze", false)), true], ["Sparsam", Callable(self, "_set_safety").bind({"router_mode":"cost"})], ["Schnell", Callable(self, "_set_safety").bind({"router_mode":"speed"})], ["Gründlich", Callable(self, "_set_safety").bind({"router_mode":"thorough"})]])
	_row_buttons(safety, [["Paid: AN" if s.get("paid_opt_in", false) else "Paid: AUS", Callable(self, "_ask_safety").bind("paid", not s.get("paid_opt_in", false)), true]])
	var cap := _field("Neues Tageslimit in USD") as LineEdit
	safety.add_child(cap)
	cap.text_submitted.connect(func(value): _set_daily_cap(value))
	var services: Array = d.get("services", [])
	var failed := services.filter(func(x): return x.get("active") == "failed")
	_card("Dienste", ["%s aktiv · %s fehlgeschlagen · %s schlafen" % [services.size() - failed.size(), failed.size(), max(0, services.size() - failed.size())]], BAD if failed.size() else GOOD)

func _ask_safety(kind: String, value: Variant) -> void:
	if not confirm_gate(kind):
		_confirm_value = value
		_status.text = "Zur Bestätigung denselben Knopf erneut drücken"
		return
	await _set_safety({"global_freeze": value} if kind == "freeze" else {"paid_opt_in": value})

func _set_daily_cap(value: String) -> void:
	var clean := value.replace(",", ".")
	if not clean.is_valid_float() or float(clean) < 0:
		_status.text = "Limit muss eine Zahl ab 0 sein"; return
	await _set_safety({"daily_spend_cap": float(clean)})

func _set_safety(patch: Dictionary) -> void:
	_status.text = "Speichert …"
	var result = await _post("/api/safety-controls", patch)
	if result == null: _status.text = "Speichern fehlgeschlagen"; return
	_busy = false; refresh()

func _load_proposals() -> void:
	var d = await _api_get("/api/proposals")
	if not d is Dictionary: _failed(); return
	var review: Array = d.get("review", [])
	var tools := _card("Vorschlagsrunde", ["Neue Vorschläge: %s" % d.get("pending", 0)])
	_row_buttons(tools, [["Runde öffnen", Callable(self, "_simple_action").bind("/api/proposal-open", {})], ["Ideen sammeln", Callable(self, "_ask_simple").bind("ideas", "/api/suggestions-generate", {}), true]])
	var batch := _field("IDs für Batch-Freigabe, z.B. 1,3,4") as LineEdit
	tools.add_child(batch)
	tools.add_child(_button("Batch freigeben", Callable(self, "_approve_batch").bind(batch), true))
	var consensus := _field("Frage an Google Pro + Codex", true) as TextEdit
	tools.add_child(consensus)
	tools.add_child(_button("Konsens prüfen", Callable(self, "_start_consensus").bind(consensus)))
	if not str(_jobs.get("consensus_pending", "")).is_empty():
		tools.add_child(_button("Laufende Konsensprüfung wieder aufnehmen", _resume_consensus))
	if _jobs.get("consensus_result") is Dictionary: _render_consensus(_jobs.consensus_result)
	var restore := _card("Wiederherstellungspunkte", ["Anlegen oder vorhandene Punkte anzeigen"])
	var checkpoint_name := _field("Name des neuen Punkts") as LineEdit
	restore.add_child(checkpoint_name)
	_row_buttons(restore, [["Anlegen", Callable(self, "_create_checkpoint").bind(checkpoint_name)], ["Vorhandene zeigen", Callable(self, "_show_checkpoints")]])
	if review.is_empty(): _empty("Nichts zu entscheiden. %s neue Vorschläge warten." % d.get("pending", 0))
	for p in review:
		var box := _card("Ich baue das" if p.get("kind") == "ai" else "Braucht dich", [p.get("text", ""), p.get("explanation", ""), "von %s" % p.get("agent", "?")])
		_row_buttons(box, [["Annehmen", Callable(self, "_ask_proposal").bind(int(p.get("n", 0)), true)], ["Ablehnen", Callable(self, "_ask_proposal").bind(int(p.get("n", 0)), false), true]])
	var todos: Array = d.get("todos", [])
	for t in todos:
		var box := _card("Offen · %s" % t.get("agent", ""), [t.get("text", ""), t.get("added", "")], MUTED)
		box.add_child(_button("Als erledigt markieren", Callable(self, "_todo_done").bind(int(t.get("n", 0)))))

func _ask_proposal(index: int, approve: bool) -> void:
	var key := "proposal_%s_%s" % [index, approve]
	if not confirm_gate(key):
		_status.text = "Noch einmal drücken, um die Entscheidung zu bestätigen"
		return
	_status.text = "Entscheidet …"
	var r = await _post("/api/proposal-decide", {"index": index, "approve": approve})
	if r == null: _status.text = "Entscheidung fehlgeschlagen"; return
	_busy = false; refresh()

func _todo_done(index: int) -> void:
	var r = await _post("/api/todo-done", {"index": index})
	if r == null: _status.text = "Speichern fehlgeschlagen"; return
	_busy = false; refresh()

func _ask_simple(key: String, path: String, body: Dictionary) -> void:
	if not confirm_gate(key):
		_status.text = "Noch einmal drücken zum Bestätigen"; return
	await _simple_action(path, body)

func _simple_action(path: String, body: Dictionary) -> void:
	_status.text = "Wird ausgeführt …"
	var r = await _post(path, body)
	if r == null: _status.text = "Aktion fehlgeschlagen"; return
	_busy = false; refresh()

func _approve_batch(field: LineEdit) -> void:
	var ids: Array[int] = []
	for piece in field.text.split(","):
		if piece.strip_edges().is_valid_int(): ids.append(int(piece))
	if ids.is_empty(): _status.text = "Bitte mindestens eine gültige ID eingeben"; return
	await _ask_simple("batch_" + field.text, "/api/proposals-batch", {"ids": ids, "decision": "approved"})

func _start_consensus(field: TextEdit) -> void:
	if _consensus_polling or not str(_jobs.get("consensus_pending", "")).is_empty():
		_status.text = "Es gibt eine laufende Prüfung — Wieder aufnehmen drücken"; return
	var prompt := field.text.strip_edges()
	if prompt.is_empty(): _status.text = "Bitte eine Frage eingeben"; return
	var started = await _post("/api/consensus-start", {"prompt": prompt})
	if not started is Dictionary or str(started.get("id", "")).is_empty(): _status.text = "Konsens konnte nicht starten"; return
	_jobs["consensus_pending"] = str(started.id)
	_jobs.erase("consensus_result")
	_save_jobs()
	field.text = ""
	await _resume_consensus()

func _resume_consensus() -> void:
	if _consensus_polling: return
	var id := str(_jobs.get("consensus_pending", ""))
	if id.is_empty(): return
	_consensus_polling = true
	_status.text = "Google Pro und Codex prüfen …"
	for attempt in range(90):
		await get_tree().create_timer(2.0).timeout
		var result = await _post("/api/consensus-result", {"id": id})
		if not result is Dictionary:
			_status.text = "Verbindung unterbrochen — Prüfung bleibt gespeichert"
			continue
		if consensus_state(result) == "waiting":
			_status.text = "Prüfung läuft … %s s" % ((attempt + 1) * 2)
			continue
		_jobs.erase("consensus_pending")
		_jobs["consensus_result"] = result
		_save_jobs()
		_render_consensus(result)
		_consensus_polling = false
		_status.text = "Konsens fertig" if consensus_state(result) == "complete" else "Konsens fehlgeschlagen"
		return
	_consensus_polling = false
	_status.text = "Läuft weiter — Aktualisieren, dann Wieder aufnehmen"
	_body.add_child(_button("Konsensprüfung wieder aufnehmen", _resume_consensus))

func _render_consensus(result: Dictionary) -> void:
	for card in consensus_cards(result):
		_card(card.title, card.lines, BAD if card.error else GOOD)

func _create_checkpoint(field: LineEdit) -> void:
	var label := field.text.strip_edges()
	if label.is_empty(): _status.text = "Bitte einen Namen eingeben"; return
	var r = await _post("/api/checkpoint-create", {"label": label})
	_status.text = "Punkt erstellt: %s" % r.get("id", "?") if r is Dictionary else "Anlegen fehlgeschlagen"
	field.text = ""

func _show_checkpoints() -> void:
	var r = await _api_get("/api/checkpoints")
	if not r is Dictionary: _status.text = "Punkte nicht abrufbar"; return
	for point in r.get("checkpoints", []):
		var box := _card("Punkt %s" % point.get("id", "?"), [point.get("label", ""), "%s Dateien" % point.get("files_count", 0)], MUTED)
		box.add_child(_button("Destruktiv wiederherstellen", Callable(self, "_restore_checkpoint").bind(str(point.get("id", ""))), true))

func _restore_checkpoint(id: String) -> void:
	await _ask_simple("restore_" + id, "/api/checkpoint-restore", {"id": id})

func _load_money() -> void:
	var d = await _api_get("/api/money-board")
	if not d is Dictionary: _failed(); return
	var s: Dictionary = d.get("signals", {})
	_card("Stand", ["%s Briefe · %s qualifiziert · %s mit Postadresse" % [s.get("letters_sent", 0), s.get("leads_qualified", 0), s.get("leads_mailable", 0)]], GOOD)
	var actions: Array = d.get("actions", [])
	if actions.is_empty(): _empty("Nichts offen — alles erledigt.")
	for a in actions: _card("ZUERST" if a.get("gates", false) else ("~%s EUR" % a.get("euros", 0) if a.get("euros", 0) else "Basis"), [a.get("action", ""), "%s min · %s" % [a.get("minutes", 0), a.get("note", "")]])

func _load_costs() -> void:
	var d = await _api_get("/api/costs")
	if not d is Dictionary: _failed(); return
	var o: Dictionary = d.get("openrouter", {})
	_card("OpenRouter-Guthaben", ["$%.2f verfügbar" % float(o.get("balance_usd", 0)), "$%.2f diesen Monat von $%.2f · $%.2f übrig" % [float(o.get("month_spent_usd", 0)), float(o.get("budget_usd", 0)), float(o.get("budget_left_usd", 0))], "Bezahltes Modell: %s" % o.get("paid_model", "aus")], BAD if float(o.get("balance_usd", 0)) < 2 else GOOD)
	var usage: Dictionary = o.get("usage", {})
	_card("Nutzung", ["Heute $%.3f · 7 Tage $%.3f · Monat $%.3f" % [float(usage.get("today", 0)), float(usage.get("week", 0)), float(usage.get("month", 0))]])
	var c: Dictionary = d.get("claude", {})
	_card("Claude-Schätzung", ["$%.2f diesen Monat · $%.2f insgesamt" % [float(c.get("month_usd", 0)), float(c.get("total_usd", 0))], c.get("note", "")], MUTED)
	for call in (o.get("calls", []) as Array).slice(0, 12): _card(str(call.get("model", "Aufruf")).get_file(), ["%s · $%.4f" % [call.get("ts", ""), float(call.get("usd", 0))]], MUTED)

func _load_dmarc() -> void:
	var d = await _api_get("/api/dmarc-leads")
	if not d is Dictionary: _failed(); return
	var leads: Array = d.get("leads", [])
	_card("Pipeline", ["%s qualifiziert · %s gezeigt" % [d.get("total_qualified", 0), leads.size()]], GOOD)
	if leads.is_empty(): _empty("Noch keine Leads.")
	for lead in leads:
		var address: Dictionary = lead.get("address", {}) if lead.get("address") is Dictionary else {}
		_card(str(lead.get("name", lead.get("domain", "Lead"))), ["%s · Score %s" % [lead.get("domain", ""), lead.get("score", "?")], "DMARC %s · %s · %s" % [lead.get("dmarc", "fehlt"), lead.get("provider", ""), address.get("city", "")]], MUTED)

func _load_snipes() -> void:
	var d = await _post("/api/snipes", _snipe_filters)
	if not d is Dictionary: _failed(); return
	var filters := _card("Filter", ["Antippen schaltet Filter ein oder aus"])
	var specs: Array = []
	for tier in ["S", "A", "B", "C"]: specs.append([tier, Callable(self, "_toggle_filter").bind("tier", tier)])
	specs.append(["≤15 km", Callable(self, "_toggle_filter").bind("max_distance", 15)])
	specs.append(["Reset", Callable(self, "_clear_filters")])
	_row_buttons(filters, specs)
	var snipes: Array = d.get("snipes", [])
	if snipes.is_empty(): _empty("Keine Funde für diese Filter.")
	for s in snipes:
		var reasons: Array = s.get("reasons", [])
		_card("%s · %s" % [s.get("tier", "?"), s.get("title", "Fund")], ["%s EUR · %s km · %s" % [s.get("price", "?"), s.get("distance", "?"), s.get("watch", "")], " · ".join(reasons)], GOLD if s.get("tier") in ["S", "A"] else MUTED)

func _toggle_filter(key: String, value: Variant) -> void:
	_snipe_filters[key] = null if _snipe_filters[key] == value else value
	_busy = false; refresh()

func _clear_filters() -> void:
	for key in _snipe_filters: _snipe_filters[key] = null
	_busy = false; refresh()

func _load_flips() -> void:
	var d = await _api_get("/api/flip-log")
	if not d is Dictionary: _failed(); return
	var rows: Array = d.get("rows", [])
	if rows.is_empty(): _empty("Noch keine Flips geloggt.")
	for row in rows:
		_card(str(row.get("Item", "Flip")), ["offen" if row.get("open", false) else "%s EUR netto" % row.get("Net €", "?"), "%s · %s · Kauf %s EUR" % [row.get("Date", ""), row.get("Category", ""), row.get("Buy €", "?")]], MUTED if row.get("open", false) else GOOD)

func _load_files() -> void:
	var downloads = await _api_get("/api/downloads")
	var uploads = await _api_get("/api/uploads")
	if not downloads is Dictionary and not uploads is Dictionary: _failed(); return
	var down: Array = downloads.get("files", downloads.get("downloads", [])) if downloads is Dictionary else []
	var up: Array = uploads.get("files", uploads.get("uploads", [])) if uploads is Dictionary else []
	_card("Downloads", ["%s Dateien vom AI-OS" % down.size()], GOOD)
	for f in down: _card(str(f.get("name", "Datei")), [_file_meta(f)], MUTED)
	_card("Uploads / Vault-Eingang", ["%s private Dateien" % up.size()], GOLD)
	for f in up: _card(str(f.get("name", "Datei")), [_file_meta(f)], MUTED)
	if down.is_empty() and up.is_empty(): _empty("Noch keine Dateien.")
	var actions := _card("Wissenswerkzeuge", ["Erstellt das Stimmprofil aus den vorhandenen Text-Uploads."])
	actions.add_child(_button("Stimmprofil neu bauen", Callable(self, "_ask_simple").bind("voice", "/api/voice-import", {}), true))

func _file_meta(file: Dictionary) -> String:
	var size := float(file.get("size", file.get("bytes", 0)))
	var size_text := "%.1f MB" % (size / 1048576.0) if size >= 1048576 else "%.0f KB" % (size / 1024.0)
	return "%s · %s" % [size_text, file.get("updated", file.get("mtime", ""))]

func _load_nodes() -> void:
	var d = await _api_get("/api/nodes")
	if not d is Dictionary: _failed(); return
	var nodes: Array = d.get("nodes", [])
	if _jobs.get("node_pending") is Dictionary:
		_body.add_child(_button("Laufenden Rechnerbefehl wieder aufnehmen", _resume_node))
	if _jobs.get("node_result") is Dictionary:
		var result: Dictionary = _jobs.node_result
		_card("Letzte Rechnerausgabe", [result.get("output", "(keine Ausgabe)")], GOOD if result.get("ok", false) else BAD)
	if nodes.is_empty(): _empty("Keine Rechner registriert."); return
	for node in nodes:
		var online := bool(node.get("online", false))
		var box := _card(str(node.get("id", "Rechner")), ["online · %s Kerne" % node.get("cores", "?") if online else "offline"], GOOD if online else MUTED)
		if online:
			var command := _field("Befehl für diesen Rechner") as LineEdit
			box.add_child(command)
			box.add_child(_button("Befehl einreihen", Callable(self, "_run_node").bind(str(node.get("id", "")), command), true))

func _run_node(node_id: String, input: LineEdit) -> void:
	if _node_polling or _jobs.get("node_pending") is Dictionary:
		_status.text = "Ein Rechnerbefehl läuft noch — Wieder aufnehmen drücken"; return
	var command := input.text.strip_edges()
	if command.is_empty(): _status.text = "Bitte einen Befehl eingeben"; return
	var key := "node_%s_%s" % [node_id, command]
	if not confirm_gate(key):
		_status.text = "Befehl nochmals drücken zum Bestätigen"; return
	_status.text = "%s: eingereiht …" % node_id
	var queued = await _post("/api/node-run", {"node": node_id, "command": command})
	if not queued is Dictionary: _status.text = "Einreihen fehlgeschlagen"; return
	input.text = ""
	var job := str(queued.get("job_id", ""))
	if job.is_empty(): _status.text = "Server lieferte keine Job-ID"; return
	_jobs["node_pending"] = {"job_id": job, "node": node_id}
	_jobs.erase("node_result")
	_save_jobs()
	await _resume_node()

func _resume_node() -> void:
	if _node_polling or not _jobs.get("node_pending") is Dictionary: return
	_node_polling = true
	var pending: Dictionary = _jobs.node_pending
	var job := str(pending.get("job_id", ""))
	var node_id := str(pending.get("node", "Rechner"))
	for attempt in range(30):
		await get_tree().create_timer(minf(4.0, 0.8 + attempt * 0.2)).timeout
		var result = await _post("/api/node-result", {"job_id": job})
		if result is Dictionary and node_state(result) == "complete":
			_jobs.erase("node_pending"); _jobs["node_result"] = result; _save_jobs()
			_card("Ausgabe · %s" % node_id, [result.get("output", "(keine Ausgabe)")], GOOD if result.get("ok", false) else BAD)
			_node_polling = false; _status.text = "Fertig"; return
		if result is Dictionary and node_state(result) == "lost":
			_jobs.erase("node_pending"); _save_jobs(); _node_polling = false
			_status.text = str(result.get("error", "Job verloren")); return
	_node_polling = false
	_status.text = "Läuft weiter — Aktualisieren, dann Wieder aufnehmen"
	_body.add_child(_button("Rechnerbefehl wieder aufnehmen", _resume_node))
