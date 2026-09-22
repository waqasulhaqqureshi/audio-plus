#!/usr/bin/env python3
"""Create the requested, time-normalised phrase clips from org.MP3.

The supplied org transcript has one-second anchors.  The boundaries below are
refined to the first/last audible sample around each utterance (the long
pauses make the section boundaries unambiguous).  Each non-placeholder clip
is trimmed first and then passed through atempo so its decoded duration is the
corresponding goal-transcript window.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"

# The first goal section is not present in the supplied recording: org.MP3 is
# silent until the answer starts at about 00:05.30.  A silent 3-second clip is
# emitted so the requested numbered sequence remains intact.
SECTIONS = [
    {
        "number": 1,
        "goal_start": 0.0,
        "goal_end": 3.0,
        "source_start": 0.0,
        "source_end": 3.0,
        "text": "Let's talk about travel. Tell me about the last place that you went to.",
        "missing_source_audio": True,
    },
    {
        "number": 2,
        "goal_start": 3.0,
        "goal_end": 44.0,
        "source_start": 5.30,
        "source_end": 42.38,
        "text": "The last place that I traveled to was Thailand, Bangkok to be specific. ... in a country like Thailand.",
    },
    {
        "number": 3,
        "goal_start": 44.0,
        "goal_end": 73.0,
        "source_start": 42.38,
        "source_end": 70.92,
        "text": "So, would you prefer a city break or a beach holiday? ... something that I'd like to get away to.",
    },
    {
        "number": 4,
        "goal_start": 73.0,
        "goal_end": 87.0,
        "source_start": 70.92,
        "source_end": 83.40,
        "text": "Is there anywhere you haven't been yet that you would love to go to? ... I'd really like to go to the Philippines.",
    },
    {
        "number": 5,
        "goal_start": 87.0,
        "goal_end": 103.0,
        "source_start": 83.40,
        "source_end": 98.32,
        "text": "Yeah, very many places that I haven't been to. ... go visit other places.",
    },
    {
        "number": 6,
        "goal_start": 103.0,
        "goal_end": 108.0,
        "source_start": 98.32,
        "source_end": 104.16,
        "text": "Now, let's talk about the future. In 10 years time, what job would you like to have?",
    },
    {
        "number": 7,
        "goal_start": 108.0,
        "goal_end": 132.0,
        "source_start": 104.16,
        "source_end": 124.98,
        "text": "I would like to have my own business. ... I have a passion for interior design on a separate note.",
    },
    {
        "number": 8,
        "goal_start": 132.0,
        "goal_end": 141.0,
        "source_start": 124.98,
        "source_end": 131.96,
        "text": "But yes, a businesswoman is definitely something that I hope I'm able to be in the next 10 years.",
    },
    {
        "number": 9,
        "goal_start": 141.0,
        "goal_end": 145.0,
        "source_start": 131.96,
        "source_end": 135.96,
        "text": "And will English be useful in your future career?",
    },
    {
        "number": 10,
        "goal_start": 145.0,
        # The goal transcript has no final [mm:ss] marker.  Its end is
        # therefore derived from the end of the final spoken phrase below.
        "goal_end": 161.84,
        "source_start": 135.96,
        "source_end": 152.80,
        "text": "Yes. Where I come from, English is a very commonly spoken language. ... it would be necessary for me specifically.",
        "goal_end_derived": True,
    },
]


def find_input() -> Path:
    for name in ("org.mp3", "org.MP3", "ORG.MP3"):
        candidate = ROOT / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not find org.mp3/org.MP3 in the repository root")


def find_ffmpeg() -> str:
    configured = os.environ.get("FFMPEG_BIN")
    if configured:
        return configured
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - only reached on an unprepared machine
        raise RuntimeError("ffmpeg is required; install it or set FFMPEG_BIN") from exc


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> None:
    source = find_input()
    ffmpeg = find_ffmpeg()
    OUTPUT.mkdir(exist_ok=True)
    for old in OUTPUT.glob("*.mp3"):
        old.unlink()

    manifest_sections = []
    for section in SECTIONS:
        number = section["number"]
        target_duration = section["goal_end"] - section["goal_start"]
        source_duration = section["source_end"] - section["source_start"]
        output_file = OUTPUT / f"{number}.mp3"

        if section.get("missing_source_audio"):
            command = [
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t", f"{target_duration:.6f}",
                "-ar", "44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "192k",
                "-map_metadata", "-1", str(output_file),
            ]
            speed_factor = None
        else:
            # atempo > 1 speeds up; atempo < 1 slows down.
            speed_factor = source_duration / target_duration
            if not 0.5 <= speed_factor <= 2.0:
                raise ValueError(f"atempo factor out of range for section {number}: {speed_factor}")
            filter_graph = (
                f"atrim=start={section['source_start']:.6f}:end={section['source_end']:.6f},"
                f"asetpts=PTS-STARTPTS,atempo={speed_factor:.12f},"
                f"apad,atrim=duration={target_duration:.6f},asetpts=PTS-STARTPTS"
            )
            command = [
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(source), "-map", "0:a:0", "-vn", "-af", filter_graph,
                "-ar", "44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "192k",
                "-map_metadata", "-1", str(output_file),
            ]
        run(command)

        row = dict(section)
        row.update(
            {
                "output": str(output_file.relative_to(ROOT)),
                "target_duration_seconds": round(target_duration, 6),
                "source_duration_seconds": round(source_duration, 6),
                "atempo_factor": None if speed_factor is None else round(speed_factor, 12),
                "processing": "silent placeholder (goal phrase absent from org.MP3)"
                if section.get("missing_source_audio")
                else "trim, dynamic time-stretch, and MP3 encode",
            }
        )
        manifest_sections.append(row)

    manifest = {
        "source": source.name,
        "method": "provided org transcript anchors refined against audible pauses; per-section atempo normalization",
        "sample_rate_hz": 44100,
        "channels": 2,
        "output_format": "MP3, 192 kbps",
        "notes": [
            "The first goal prompt is absent from the supplied recording, which is silent until approximately 00:05.30; output/1.mp3 is a 3-second silent placeholder.",
            "The final goal section has no closing timestamp, so its target end is derived from the end of the final spoken phrase (145.00 + 16.84 = 161.84 seconds).",
        ],
        "sections": manifest_sections,
    }
    (OUTPUT / "alignment_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Created {len(SECTIONS)} clips in {OUTPUT}")


if __name__ == "__main__":
    main()
