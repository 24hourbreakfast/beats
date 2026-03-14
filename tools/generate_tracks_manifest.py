#!/usr/bin/env python3
"""Generate track manifests for static hosting (Netlify/GitHub Pages)."""

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


def sort_key_timestamp(path: Path) -> tuple[int, str]:
    stamp = parse_stamp(path.name)
    if stamp:
        return (int(stamp.timestamp()), path.name.lower())
    # Non-timestamped legacy files are sorted after timestamped files.
    return (0, path.name.lower())


def sort_key_mtime(path: Path) -> tuple[float, str]:
    return (path.stat().st_mtime, path.name.lower())


def build_manifest(tracks_dir: Path, sort_by: str, date_source: str) -> dict[str, object]:
    mp3s = [p for p in tracks_dir.glob("*.mp3") if p.is_file()]
    if sort_by == "mtime":
        mp3s.sort(key=sort_key_mtime, reverse=True)
    else:
        mp3s.sort(key=sort_key_timestamp, reverse=True)
    tracks = []
    for path in mp3s:
        stamp = parse_stamp(path.name)
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        if date_source == "mtime":
            date_label = modified.strftime("%b %-d, %Y")
            timestamp = modified.isoformat()
        else:
            date_label = stamp.strftime("%b %-d, %Y") if stamp else "Unknown date"
            timestamp = stamp.isoformat() if stamp else None
        tracks.append(
            {
                "file": path.name,
                "title": nice_title(path.name),
                "date_label": date_label,
                "timestamp": timestamp,
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
    parser.add_argument(
        "--sort-by",
        choices=("timestamp", "mtime"),
        default="timestamp",
        help="How to sort tracks",
    )
    parser.add_argument(
        "--date-source",
        choices=("timestamp", "mtime"),
        default="timestamp",
        help="How to generate date labels",
    )
    args = parser.parse_args()

    tracks_dir = Path(args.beats_dir).resolve()
    output = Path(args.output).resolve()
    manifest = build_manifest(tracks_dir, args.sort_by, args.date_source)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[manifest] wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
