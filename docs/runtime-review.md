# Runtime review — 2026-09-07

## Resolution — 2026-09-08

Both P2 findings below are resolved. Production requests run in a cancellable subprocess with a total timeout and bounded output; the slow loopback response regression passes. Display state transitions synchronously transfer a frame under an SPI lock before returning; failed listening transfer prevents capture. Error-screen/idle failures no longer replace the original interaction error. All 27 tests and the offline simulation pass. The findings below are retained as review history, not open defects.

Scope: `ai_cube/*.py`, `tests/*.py`, `pyproject.toml`, `.env.example`, `THIRD_PARTY.md`, against `docs/design.md`. This is a review of newly created files, not an existing commit diff. No runtime code was changed by this review.

## Actionable findings

### P2 — Enforce an elapsed deadline for API responses

Location: `ai_cube/provider.py:57-58`.

`self.open(..., timeout=self.timeout)` followed by one `response.read(limit + 1)` does not enforce a total request deadline. urllib documents the timeout as applying to blocking operations. A server or proxy that delivers occasional bytes inside each socket timeout can keep the cube in `thinking` far beyond `CUBE_API_TIMEOUT`; the large TTS size limit makes this particularly pronounced. The UI loop is blocked during the request and cannot accept a fresh interaction until it finishes.

Use a monotonic request deadline and bounded reads with each blocking wait constrained by the remaining time, or an isolated request worker with bounded cancellation and cleanup. Keep automatic retries disabled. Add a local slow-response test that sends bytes often enough to avoid the socket inactivity timeout but exceeds the total request budget. A plain fake response that returns immediately does not exercise this failure mode.

Reference: [Python urllib.request timeout documentation](https://docs.python.org/3/library/urllib.request.html#urllib.request.urlopen).

### P2 — Confirm the listening frame before opening the microphone

Location: `ai_cube/display.py:93-95`, used by `ai_cube/core.py` in `run_turn` immediately before `audio.record()`.

`show('listening')` checks the previous animation error and merely assigns `self.state`; the actual frame is sent by the background thread at its next update. Recording therefore begins while the LCD can still show idle. If that next SPI update fails, the microphone continues recording for the turn while the LCD remains idle, because the error is only checked after `record()` returns. The screen is the only recording indicator in the design.

Make state transitions acknowledge a successfully written frame before returning, with serialization of SPI operations. Abort before `arecord` is started if the listening frame cannot be written. Add a mocked display/SPI failure test verifying that a failed first listening frame prevents microphone capture. Consider checking display health during capture if a later animation failure must also stop recording.

## Confirmed by source inspection

- No microphone process is created at startup or idle; `arecord` is opened only in `record()` after a trigger.
- Release-to-arm behavior prevents a held touch at boot or the end of a turn from immediately triggering another turn; busy inputs are discarded by resetting the latch.
- Endpointer budgets are 12 seconds of PCM, 5 seconds without detected speech, and 1 second of trailing silence. A separate wall-clock watchdog bounds stalled capture to the configured duration plus 3 seconds, followed by process shutdown time.
- Capture and playback use `finally` cleanup; speaker WAV data is removed by a temporary-directory context on ordinary success, errors, or interruption. Abrupt power loss is outside this guarantee.
- HTTP bodies have explicit byte limits, redirects are disabled, response text is bounded, and audio format/duration/frame count are validated. Credentials and response contents are not written to application logs.
- The chat payload uses WAV base64 `input_audio`; TTS requests WAV from `/audio/speech`. These agree with the [official audio input example](https://docs.orcarouter.ai/advanced/audio-input) and [TTS documentation](https://docs.orcarouter.ai/other-apis/tts) inspected during this review.
- GPIO assignments in the runtime match the design contract, including backlight GPIO24 to avoid the I2S BCLK on GPIO18. Rendering uses small 240×240 buffers and NumPy conversion rather than a Python per-pixel loop.

## Verification limits

The parent agent reported 23 unit tests passing and `python -m ai_cube --simulate` passing. Those results are supplied evidence, not independently rerun in this review: `python` was not available on this review shell's PATH. Existing tests cover pure logic and payload construction, but not ALSA subprocess cleanup, LCD update synchronization, slow HTTP bodies, or physical hardware.

There is no real Pi, connected display/sensor/audio hardware, or API key available here. ST7789 orientation/offsets and actual SPI behavior, GPIO permissions, ALSA card names, MAX98357A channel behavior, sensor calibration, acoustic endpoint thresholds, and Zero 2 W CPU/thermal measurements remain hardware acceptance work. No real API success or physical integration success is claimed.
