# audio-plus

Processed output for `org.MP3` is in [`output/`](output/). The numbered MP3 files are the goal-transcript sections in order:

- `1.mp3` through `10.mp3`
- `alignment_manifest.json` records the source boundaries, target windows, and stretch factors

Each clip was decoded and checked at 44.1 kHz stereo. Clips 1–9 decode to their target windows exactly; the final goal section has no closing timestamp, so `10.mp3` uses the duration of the final spoken phrase and is documented as a derived end time in the manifest.

`align_audio.py` contains the repeatable ffmpeg-based trim and dynamic time-stretch workflow. Set `FFMPEG_BIN` if ffmpeg is not on `PATH`.
