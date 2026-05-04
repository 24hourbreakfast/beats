#!/usr/bin/env python3
"""Watch person-specific drop folders and publish MP3s to matching pages."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


SUPPORTED_SUFFIXES = {".mp3"}
DEFAULT_PEOPLE = ("tom", "adam")


def sh(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def sanitize_name(name: str) -> str:
    clean = re.sub(r"\s+", "-", name.strip().lower())
    clean = re.sub(r"[^a-z0-9\-_.]", "", clean)
    clean = re.sub(r"-{2,}", "-", clean)
    return clean.strip("-_.") or "untitled"


def nice_title(filename: str) -> str:
    path = Path(filename)
    stem = path.stem if path.suffix.lower() in SUPPORTED_SUFFIXES else filename
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    stem = re.sub(r"\s{2,}", " ", stem)
    return stem or "Untitled"


def safe_dest_name(source: Path, upload_dir: Path) -> str:
    clean_stem = sanitize_name(source.stem)
    dest_name = f"{clean_stem}{source.suffix.lower()}"
    if not (upload_dir / dest_name).exists():
        return dest_name
    suffix = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{clean_stem}-{suffix}{source.suffix.lower()}"


def file_signature(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_size}:{int(stat.st_mtime)}"


def wait_for_stable_file(path: Path, checks: int = 3, pause: float = 1.5) -> None:
    stable_count = 0
    previous = None
    for _ in range(40):
        if not path.exists():
            raise FileNotFoundError(path)
        current = path.stat().st_size
        if current == previous:
            stable_count += 1
            if stable_count >= checks:
                return
        else:
            stable_count = 0
        previous = current
        time.sleep(pause)
    raise TimeoutError(f"File never stabilized: {path}")


def load_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_state(state_file: Path) -> dict[str, str]:
    state = load_json(state_file, {})
    return state if isinstance(state, dict) else {}


def save_state(state_file: Path, state: dict[str, str]) -> None:
    write_json(state_file, state)


def notify_discord(webhook_url: str | None, message: str) -> None:
    if not webhook_url:
        return
    body = json.dumps({"content": message}).encode("utf-8")
    request = Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "bernban-share-uploader"},
        method="POST",
    )
    with urlopen(request, timeout=12) as response:
        response.read()


def discord_webhook_for(person: str) -> str | None:
    specific = os.environ.get(f"DISCORD_WEBHOOK_URL_{person.upper()}")
    return specific or os.environ.get("DISCORD_WEBHOOK_URL")


def public_track_url(site_root: str, person: str, filename: str) -> str:
    return site_root.rstrip("/") + f"/{person}/audio/" + quote(filename)


def manifest_entry(dest_name: str) -> dict[str, str]:
    now = datetime.now()
    return {
        "file": dest_name,
        "title": nice_title(dest_name),
        "date_label": now.strftime("%b %-d, %Y"),
        "timestamp": now.isoformat(timespec="seconds"),
    }


def update_manifest(manifest_path: Path, dest_name: str) -> None:
    manifest = load_json(manifest_path, {"tracks": []})
    if not isinstance(manifest, dict):
        manifest = {"tracks": []}
    tracks = manifest.get("tracks", [])
    if not isinstance(tracks, list):
        tracks = []
    tracks = [track for track in tracks if not (isinstance(track, dict) and track.get("file") == dest_name)]
    tracks.insert(0, manifest_entry(dest_name))
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    manifest["tracks"] = tracks
    write_json(manifest_path, manifest)


def upload_file(
    source: Path,
    repo_root: Path,
    person: str,
    archive_dir: Path | None,
    site_root: str,
) -> None:
    wait_for_stable_file(source)
    sh(["git", "pull", "--rebase", "origin", "main"], cwd=repo_root)

    upload_dir = repo_root / person / "audio"
    manifest_path = repo_root / person / "tracks.json"
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest_name = safe_dest_name(source, upload_dir)
    dest_path = upload_dir / dest_name
    shutil.copy2(source, dest_path)
    update_manifest(manifest_path, dest_name)
    print(f"[copy] {source} -> {dest_path}")

    sh(["git", "add", str(dest_path), str(manifest_path)], cwd=repo_root)
    sh(["git", "commit", "-m", f"Add {person} upload: {dest_name}"], cwd=repo_root)
    sh(["git", "push", "origin", "main"], cwd=repo_root)

    url = public_track_url(site_root, person, dest_name)
    print(f"[push] uploaded {url}")
    notify_discord(discord_webhook_for(person), f"New Bern Ban upload for {person.title()}: {url}")

    if archive_dir:
        archive_dir.mkdir(parents=True, exist_ok=True)
        archived = archive_dir / source.name
        if archived.exists():
            suffix = datetime.now().strftime("%H%M%S")
            archived = archive_dir / f"{source.stem}-{suffix}{source.suffix}"
        shutil.move(str(source), str(archived))
        print(f"[archive] moved source to {archived}")


def iter_audio_files(watch_dir: Path) -> list[Path]:
    if not watch_dir.exists():
        watch_dir.mkdir(parents=True, exist_ok=True)
    return sorted(
        [
            path for path in watch_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        ]
    )


def process_person(
    person: str,
    drop_root: Path,
    repo_root: Path,
    state: dict[str, str],
    site_root: str,
    no_archive: bool,
) -> None:
    watch_dir = drop_root / person
    archive_dir = None if no_archive else (watch_dir / "_uploaded")
    for path in iter_audio_files(watch_dir):
        key = str(path.resolve())
        signature = file_signature(path)
        if state.get(key) == signature:
            continue
        try:
            upload_file(path, repo_root, person, archive_dir, site_root)
            state[key] = signature
        except subprocess.CalledProcessError as exc:
            print(f"[error] command failed ({exc.returncode}): {exc.cmd}")
            notify_discord(discord_webhook_for(person), f"Bern Ban upload failed for {person.title()}: `{path.name}`")
        except Exception as exc:  # noqa: BLE001
            print(f"[error] failed to upload {path}: {exc}")
            notify_discord(discord_webhook_for(person), f"Bern Ban upload failed for {person.title()}: `{path.name}`")


def main() -> int:
    default_drop_root = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "MP3 LISTEN"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--drop-root",
        default=str(default_drop_root),
        help="Parent folder containing person folders, such as tom/ and adam/",
    )
    parser.add_argument(
        "--watch-dir",
        dest="drop_root",
        help="Deprecated alias for --drop-root",
    )
    parser.add_argument(
        "--people",
        nargs="+",
        default=list(DEFAULT_PEOPLE),
        help="Person folder names to watch",
    )
    parser.add_argument("--poll-seconds", type=float, default=5.0, help="Polling interval")
    parser.add_argument("--once", action="store_true", help="Upload pending files once, then exit")
    parser.add_argument(
        "--state-file",
        default=".uploader_state/state.json",
        help="State file path relative to repo root (or absolute path)",
    )
    parser.add_argument(
        "--site-root",
        default=os.environ.get("SHARE_SITE_ROOT", "https://bernban.com"),
        help="Public site root used in Discord links",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Do not move processed source files into an archive folder",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    drop_root = Path(args.drop_root).expanduser().resolve()
    drop_root.mkdir(parents=True, exist_ok=True)

    state_file = Path(args.state_file)
    if not state_file.is_absolute():
        state_file = repo_root / state_file
    state = load_state(state_file)

    people = [sanitize_name(person) for person in args.people]
    print(f"[start] watching root: {drop_root}")
    print(f"[people] {', '.join(people)}")
    print(f"[state] {state_file}")

    while True:
        for person in people:
            process_person(person, drop_root, repo_root, state, args.site_root, args.no_archive)
            save_state(state_file, state)
        if args.once:
            break
        time.sleep(args.poll_seconds)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
