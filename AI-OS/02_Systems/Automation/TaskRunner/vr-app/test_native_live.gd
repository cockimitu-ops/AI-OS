extends Node
const Stream = preload("res://NativeScreenStream.gd")
var frames := 0
var stream: Node
var started := 0
func _ready() -> void:
	stream = Stream.new()
	var args := OS.get_cmdline_user_args()
	stream.device_id = args[0] if not args.is_empty() else "laptop"
	add_child(stream)
	stream.frame_received.connect(func(bytes: PackedByteArray):
		var image := Image.new()
		assert(image.load_jpg_from_buffer(bytes) == OK)
		frames += 1
		if frames == 8:
			print("PASS: actual ", stream.device_id, " MJPEG, frames=", frames, " elapsed_ms=", Time.get_ticks_msec() - started, " size=", image.get_size())
			stream.stop()
			get_tree().quit()
	)
	stream.stream_error.connect(func(message): print(message))
	started = Time.get_ticks_msec()
	stream.start()
	await get_tree().create_timer(25).timeout
	if frames < 8:
		print("FAIL: insufficient actual live frames: ", frames)
		get_tree().quit(1)
