#!/usr/bin/env python3
"""Watch a local folder and auto-upload new audio files into this repo."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


def sh(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def sanitize_name(name: str) -> str:
    clean = re.sub(r"\s+", "-", name.strip().lower())
    clean = re.sub(r"[^a-z0-9\-_.]", "", clean)
    clean = re.sub(r"-{2,}", "-", clean)
    return clean.strip("-_.") or "untitled"


def safe_dest_name(source: Path, beats_dir: Path) -> str:
    clean_stem = sanitize_name(source.stem)
    dest_name = f"{clean_stem}{source.suffix.lower()}"
    if not (beats_dir / dest_name).exists():
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


def load_state(state_file: Path) -> dict[str, str]:
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state_file: Path, state: dict[str, str]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def notify_discord(webhook_url: str | None, message: str) -> None:
    if not webhook_url:
        return
    body = json.dumps({"content": message}).encode("utf-8")
    request = Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "bernban-beats-uploader"},
        method="POST",
    )
    with urlopen(request, timeout=12) as response:
        response.read()


def public_track_url(site_base_url: str, filename: str) -> str:
    return site_base_url.rstrip("/") + "/" + quote(filename)


def upload_file(
    source: Path,
    repo_root: Path,
    upload_dir: Path,
    archive_dir: Path | None,
    discord_webhook_url: str | None,
    site_base_url: str,
) -> None:
    wait_for_stable_file(source)
    sh(["git", "pull", "--rebase", "origin", "main"], cwd=repo_root)

    dest_name = safe_dest_name(source, upload_dir)
    dest_path = upload_dir / dest_name
    shutil.copy2(source, dest_path)
    print(f"[copy] {source} -> {dest_path}")

    sh(
        [
            sys.executable,
            str(repo_root / "tools" / "generate_tracks_manifest.py"),
            "--beats-dir",
            "inprogress",
            "--output",
            "beats/inprogress-tracks.json",
            "--sort-by",
            "mtime",
            "--date-source",
            "mtime",
        ],
        cwd=repo_root,
    )
    sh(["git", "add", str(dest_path), "beats/inprogress-tracks.json"], cwd=repo_root)
    sh(["git", "commit", "-m", f"Add beat: {dest_name}"], cwd=repo_root)
    sh(["git", "push", "origin", "main"], cwd=repo_root)
    print(f"[push] uploaded {dest_name}")
    notify_discord(discord_webhook_url, f"New Bern Ban beat uploaded: {public_track_url(site_base_url, dest_name)}")

    if archive_dir:
        archive_dir.mkdir(parents=True, exist_ok=True)
        archived = archive_dir / source.name
        if archived.exists():
            suffix = datetime.now().strftime("%H%M%S")
            archived = archive_dir / f"{source.stem}-{suffix}{source.suffix}"
        shutil.move(str(source), str(archived))
        print(f"[archive] moved source to {archived}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--watch-dir",
        default=str(Path.home() / "Music" / "BeatsDrop"),
        help="Folder to watch for new .mp3 files",
    )
    parser.add_argument("--poll-seconds", type=float, default=5.0, help="Polling interval")
    parser.add_argument("--once", action="store_true", help="Upload pending files once, then exit")
    parser.add_argument(
        "--state-file",
        default=".uploader_state/state.json",
        help="State file path relative to repo root (or absolute path)",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Do not move processed source files into an archive folder",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    upload_dir = repo_root / "inprogress"
    if not upload_dir.exists():
        raise SystemExit(f"Missing upload directory at {upload_dir}")

    watch_dir = Path(args.watch_dir).expanduser().resolve()
    watch_dir.mkdir(parents=True, exist_ok=True)

    state_file = Path(args.state_file)
    if not state_file.is_absolute():
        state_file = repo_root / state_file
    state = load_state(state_file)

    archive_dir = None if args.no_archive else (watch_dir / "_uploaded")
    site_base_url = "https://bernban.com/inprogress"
    discord_webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    site_base_url = os.environ.get("BEATS_SITE_BASE_URL", site_base_url)

    print(f"[start] watching: {watch_dir}")
    print(f"[state] {state_file}")

    while True:
        audio_files = sorted(
            [
                p for p in watch_dir.iterdir()
                if p.is_file() and p.suffix.lower() in {".mp3", ".wav"}
            ]
        )
        for path in audio_files:
            key = str(path.resolve())
            signature = file_signature(path)
            if state.get(key) == signature:
                continue
            try:
                upload_file(path, repo_root, upload_dir, archive_dir, discord_webhook_url, site_base_url)
                state[key] = signature
                save_state(state_file, state)
            except subprocess.CalledProcessError as exc:
                print(f"[error] command failed ({exc.returncode}): {exc.cmd}")
                notify_discord(discord_webhook_url, f"Bern Ban beat upload failed: `{path.name}`")
            except Exception as exc:  # noqa: BLE001
                print(f"[error] failed to upload {path}: {exc}")
                notify_discord(discord_webhook_url, f"Bern Ban beat upload failed: `{path.name}`")
        if args.once:
            break
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
