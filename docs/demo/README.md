# Recorded POC

The video records one screenshot-driven reset action on the synthetic macOS clinic app. A local Ollama vision model proposed the click. An operator approved it in the console. Native input reset the form, and the new screenshot showed the empty state.

The starting appointment was prepared manually. The video does not demonstrate autonomous booking, a live EHR connection, patient identity validation, or general model reliability. All fixture data is fictional. There is no audio.

## For whoever builds this

`openclerk-poc.mp4` is a 42-second, 1280 × 820 H.264 video. It combines caption cards, a captured operator-review screenshot, and a window-only ScreenCaptureKit recording of the actual click and visible result. The native segment runs at normal speed; unrelated desktop surfaces were excluded. The local model was `qwen3-vl:2b`.

The sequence is: explanation, real review screenshot, recorded native result, local setup card. The demonstration was recorded on 2026-10-06. A separate fresh-process native test run encountered bridge timeouts; see the saved validation reports. A successful console demonstration does not erase those failures.

Decisions still needed: the maintainer needs to establish why newly started bridges can time out on this host, and obtain an interactive Windows host for native validation.
