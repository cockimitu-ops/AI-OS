extends Node
## Nonblocking MJPEG receiver. Retains only the newest frame, never a playback backlog.
signal frame_received(bytes: PackedByteArray)
signal stream_error(message: String)
var device_id := ""
var last_frame_ms := 0
var _http := HTTPClient.new()
var _buffer := PackedByteArray()
var _requested := false
var _retry_at := 0
var _started_at := 0
var _enabled := false

func start() -> void:
	_enabled = true
	_retry_at = 0
	_started_at = Time.get_ticks_msec()

func stop() -> void:
	_enabled = false
	_http.close()
	_buffer.clear()
	_requested = false

func _exit_tree() -> void:
	stop()

func _fail(message: String) -> void:
	_http.close()
	_requested = false
	_buffer.clear()
	_retry_at = Time.get_ticks_msec() + 4000
	stream_error.emit(message)

func _process(_delta: float) -> void:
	if not _enabled:
		return
	var now := Time.get_ticks_msec()
	if now < _retry_at:
		return
	if _http.get_status() == HTTPClient.STATUS_DISCONNECTED:
		var base: String = get_node("/root/AIOSClient").BASE_URL
		var authority := base.get_slice("://", 1).get_slice("/", 0)
		var host := authority.get_slice(":", 0)
		var port := int(authority.get_slice(":", 1)) if authority.contains(":") else 80
		_started_at = now
		var error := _http.connect_to_host(host, port)
		if error != OK:
			_fail("Bildverbindung nicht erreichbar")
			return
	_http.poll()
	var status := _http.get_status()
	if status in [HTTPClient.STATUS_CANT_RESOLVE, HTTPClient.STATUS_CANT_CONNECT, HTTPClient.STATUS_CONNECTION_ERROR, HTTPClient.STATUS_TLS_HANDSHAKE_ERROR]:
		_fail("Livebild unterbrochen · verbindet erneut")
		return
	if status == HTTPClient.STATUS_CONNECTED:
		if _requested:
			_fail("Livebild beendet · verbindet erneut")
			return
		var headers: PackedStringArray = get_node("/root/AIOSClient")._headers()
		var error := _http.request(HTTPClient.METHOD_GET, "/device-stream?device=" + device_id.uri_encode(), headers)
		if error != OK:
			_fail("Livebild konnte nicht starten")
			return
		_requested = true
	if status == HTTPClient.STATUS_BODY:
		if _http.get_response_code() != 200:
			_fail("Livebild HTTP " + str(_http.get_response_code()))
			return
		for _i in range(24):
			var chunk := _http.read_response_body_chunk()
			if chunk.is_empty():
				break
			_buffer.append_array(chunk)
			_http.poll()
		if _buffer.size() > 4 * 1024 * 1024:
			_fail("Ungültiger Bildstrom")
			return
		var decoded := newest_frame(_buffer)
		_buffer = decoded.remaining
		if not decoded.frame.is_empty():
			last_frame_ms = now
			frame_received.emit(decoded.frame)
	if now - maxi(last_frame_ms, _started_at) > 15000:
		_fail("Noch kein Livebild · verbindet erneut")

static func _marker(data: PackedByteArray, second: int, from: int) -> int:
	var at := data.find(255, from)
	while at >= 0 and at + 1 < data.size():
		if data[at + 1] == second:
			return at
		at = data.find(255, at + 1)
	return -1

static func newest_frame(data: PackedByteArray) -> Dictionary:
	var frame := PackedByteArray()
	var offset := 0
	while true:
		var start := _marker(data, 216, offset)
		if start < 0:
			# Keep a trailing FF when a JPEG marker straddles network chunks.
			return {"frame": frame, "remaining": data.slice(maxi(offset, data.size() - 1))}
		var end := _marker(data, 217, start + 2)
		if end < 0:
			return {"frame": frame, "remaining": data.slice(start)}
		frame = data.slice(start, end + 2)
		offset = end + 2
	return {"frame": frame, "remaining": PackedByteArray()}
