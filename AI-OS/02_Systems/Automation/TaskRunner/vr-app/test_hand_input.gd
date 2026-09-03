extends SceneTree
## Regressions for pinch jitter, invalid samples, and Pico's rejected palm bindings.
const HandInput = preload("res://HandInput.gd")

func _init() -> void:
	assert(not HandInput.next_pinch(false, 0.03), "An open hand must not grab in the hysteresis band")
	assert(HandInput.next_pinch(false, 0.02), "Touching fingertips starts a grab")
	assert(HandInput.next_pinch(true, 0.035), "Small tracking jitter must not drop a grabbed panel")
	assert(not HandInput.next_pinch(true, 0.05), "Separating fingertips releases the panel")
	assert(not HandInput.next_pinch(true, NAN), "Invalid joint data must release the panel")
	assert(not HandInput.next_pinch(false, INF), "Invalid joint data must not start a grab")
	var map := load("res://openxr_action_map.tres") as OpenXRActionMap
	assert(map != null)
	var has_simple := false
	for profile in map.interaction_profiles:
		if profile.interaction_profile_path == "/interaction_profiles/khr/simple_controller":
			has_simple = true
			assert(profile.bindings.size() == 8)
		for binding in profile.bindings:
			assert(not str(binding.binding_path).contains("grip_surface/pose"), "Pico rejects the entire binding set when grip_surface/pose is present")
	assert(has_simple, "Keep the legacy hand-emulation fallback")
	print("PASS: pinch hysteresis, invalid tracking, Pico action-map compatibility")
	quit()
