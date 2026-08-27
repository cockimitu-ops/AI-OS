# Free Model Chain Behaviour

Purpose: Groq's `gpt-oss-120b` (or equivalent high-speed open models) frequently hits rate limits (per-minute limits) under Open Interpreter's intensive system prompt al
Last Updated: 2026-08-27
Status: Active
Related Documents: [[08_Research/README|08_Research]]

---

Groq's `gpt-oss-120b` (or equivalent high-speed open models) frequently hits rate limits (per-minute limits) under Open Interpreter's intensive system prompt alone, even without user code execution. Introducing a 20-second cooldown between requests successfully clears the rate limit state and restores normal operation.

---

*Written by TaskRunner on 2026-08-27. Generated content — review before treating as established fact.*
