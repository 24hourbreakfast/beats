#!/usr/bin/env python3
"""Generate beats/tracks.json for static hosting (Netlify/GitHub Pages)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

STAMP_RE = re.compile(r"^(?P<stamp>\d{8}-\d{6})__(?P<rest>.+)$")


def parse_stamp(filename: str) -> datetime | None:
    match = STAMP_RE.match(filename)
    if not match:
        return None
    try:
        return datetime.strptime(match.group("stamp"), "%Y%m%d-%H%M%S")
    except ValueError:
        return None


def nice_title(filename: str) -> str:
    stem = filename[:-4] if filename.lower().endswith(".mp3") else filename
    match = STAMP_RE.match(stem)
    if match:
        stem = match.group("rest")
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    stem = re.sub(r"\s{2,}", " ", stem)
    return stem or "Untitled"


def sort_key(path: Path) -> tuple[int, str]:
    stamp = parse_stamp(path.name)
    if stamp:
        return (int(stamp.timestamp()), path.name.lower())
    # Non-timestamped legacy files are sorted after timestamped files.
    return (0, path.name.lower())


def build_manifest(beats_dir: Path) -> dict[str, object]:
    mp3s = [p for p in beats_dir.glob("*.mp3") if p.is_file()]
    mp3s.sort(key=sort_key, reverse=True)
    tracks = []
    for path in mp3s:
        stamp = parse_stamp(path.name)
        tracks.append(
            {
                "file": path.name,
                "title": nice_title(path.name),
                "date_label": stamp.strftime("%b %-d, %Y") if stamp else "Unknown date",
                "timestamp": stamp.isoformat() if stamp else None,
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "tracks": tracks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--beats-dir",
        default="beats",
        help="Directory containing .mp3 files",
    )
    parser.add_argument(
        "--output",
        default="beats/tracks.json",
        help="Output manifest file path",
    )
    args = parser.parse_args()

    beats_dir = Path(args.beats_dir).resolve()
    output = Path(args.output).resolve()
    manifest = build_manifest(beats_dir)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[manifest] wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
