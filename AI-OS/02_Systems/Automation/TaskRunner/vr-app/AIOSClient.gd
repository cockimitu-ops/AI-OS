extends Node
## Dünner HTTP-Client zum AI-OS-Server. Autoload, ein einziger Ort für
## Adresse und Token statt beides in jedem Panel-Skript zu wiederholen.
##
## Tailscale ist die eigentliche Zugriffsgrenze (siehe webapp/server.py) -
## der Token hier ist dieselbe zweite Sicherung, die auch der Browser-Client
## mitschickt, kein Ersatz dafür.

const BASE_URL := "http://100.64.2.100:8787"

## Der Token steht in `AIOSSecret.gd`, die per .gitignore draußen bleibt -
## dieses Repository ist öffentlich, und ein dort im Klartext veröffentlichter
## Bearer-Token wäre verbrannt, auch wenn Tailscale die eigentliche
## Zugriffsgrenze ist. Vorlage zum Anlegen: `AIOSSecret.example.gd`.
static func _token() -> String:
	if ResourceLoader.exists("res://AIOSSecret.gd"):
		return load("res://AIOSSecret.gd").TOKEN
	push_warning("AIOSClient: AIOSSecret.gd fehlt - Anfragen werden abgelehnt.")
	return ""

func _headers() -> PackedStringArray:
	return PackedStringArray([
		"Authorization: Bearer %s" % _token(),
		"Content-Type: application/json",
	])

## Ein GET/POST als Coroutine - Aufrufer schreibt `var d = await client.get_json(...)`.
## -> Dictionary/Array aus der Antwort, oder null bei Fehler (Netz weg, kein
## JSON, Server nicht erreichbar). Ein Panel, das gerade offline ist, muss
## deswegen abstürzen können, nicht die App.
func get_json(path: String) -> Variant:
	return await _request(path, HTTPClient.METHOD_GET, "")

func post_json(path: String, body: Dictionary) -> Variant:
	return await _request(path, HTTPClient.METHOD_POST, JSON.stringify(body))

func post_bytes(path: String, body: PackedByteArray) -> Variant:
	var req := HTTPRequest.new()
	req.timeout = 120.0
	add_child(req)
	var headers := PackedStringArray()
	for header in _headers():
		if not header.begins_with("Content-Type:"):
			headers.append(header)
	headers.append("Content-Type: application/octet-stream")
	var error := req.request_raw(BASE_URL + path, headers, HTTPClient.METHOD_POST, body)
	if error != OK:
		req.queue_free()
		return {"error": "Upload konnte nicht starten"}
	var result: Array = await req.request_completed
	req.queue_free()
	var parsed = JSON.parse_string((result[3] as PackedByteArray).get_string_from_utf8())
	return parsed if parsed is Dictionary else {"error": "Upload fehlgeschlagen"}

func _request(path: String, method: int, body: String) -> Variant:
	var req := HTTPRequest.new()
	req.timeout = 130.0 if path == "/api/voice-import" else 30.0
	add_child(req)
	var err := req.request(BASE_URL + path, _headers(), method, body)
	if err != OK:
		req.queue_free()
		push_warning("AIOSClient: request() Fehler %s für %s" % [err, path])
		return null
	var result: Array = await req.request_completed
	req.queue_free()
	var response_code: int = result[1]
	var raw: PackedByteArray = result[3]
	if response_code < 200 or response_code >= 300:
		push_warning("AIOSClient: HTTP %s für %s" % [response_code, path])
		return null
	var parsed = JSON.parse_string(raw.get_string_from_utf8())
	return parsed

## Rohe Bildbytes laden (Screenshot-PNG). Getrennt von get_json(), weil ein
## PNG kein JSON ist - derselbe Fehler, den die Konsensprüfung im Web-Client
## gemacht hat, hier gar nicht erst einbauen.
func get_bytes(path: String) -> PackedByteArray:
	var req := HTTPRequest.new()
	req.timeout = 15.0
	add_child(req)
	var err := req.request(BASE_URL + path, _headers(), HTTPClient.METHOD_GET)
	if err != OK:
		req.queue_free()
		return PackedByteArray()
	var result: Array = await req.request_completed
	req.queue_free()
	var response_code: int = result[1]
	if response_code < 200 or response_code >= 300:
		return PackedByteArray()
	return result[3]
