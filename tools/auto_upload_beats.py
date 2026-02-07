#!/usr/bin/env python3
"""Watch a local folder and auto-upload new MP3s into this repo."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path


def sh(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def sanitize_name(name: str) -> str:
    clean = re.sub(r"\s+", "-", name.strip().lower())
    clean = re.sub(r"[^a-z0-9\-_.]", "", clean)
    clean = re.sub(r"-{2,}", "-", clean)
    return clean.strip("-_.") or "untitled"


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


def upload_file(
    source: Path,
    repo_root: Path,
    beats_dir: Path,
    archive_dir: Path | None,
) -> None:
    wait_for_stable_file(source)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = sanitize_name(source.stem)
    dest_name = f"{stamp}__{safe_name}.mp3"
    dest_path = beats_dir / dest_name
    shutil.copy2(source, dest_path)
    print(f"[copy] {source} -> {dest_path}")

    sh(["git", "add", str(dest_path)], cwd=repo_root)
    sh(["git", "commit", "-m", f"Add beat: {dest_name}"], cwd=repo_root)
    sh(["git", "pull", "--rebase", "origin", "main"], cwd=repo_root)
    sh(["git", "push", "origin", "main"], cwd=repo_root)
    print(f"[push] uploaded {dest_name}")

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
    beats_dir = repo_root / "beats"
    if not beats_dir.exists():
        raise SystemExit(f"Missing beats directory at {beats_dir}")

    watch_dir = Path(args.watch_dir).expanduser().resolve()
    watch_dir.mkdir(parents=True, exist_ok=True)

    state_file = Path(args.state_file)
    if not state_file.is_absolute():
        state_file = repo_root / state_file
    state = load_state(state_file)

    archive_dir = None if args.no_archive else (watch_dir / "_uploaded")
    print(f"[start] watching: {watch_dir}")
    print(f"[state] {state_file}")

    while True:
        mp3_files = sorted([p for p in watch_dir.glob("*.mp3") if p.is_file()])
        for path in mp3_files:
            key = str(path.resolve())
            signature = file_signature(path)
            if state.get(key) == signature:
                continue
            try:
                upload_file(path, repo_root, beats_dir, archive_dir)
                state[key] = signature
                save_state(state_file, state)
            except subprocess.CalledProcessError as exc:
                print(f"[error] command failed ({exc.returncode}): {exc.cmd}")
            except Exception as exc:  # noqa: BLE001
                print(f"[error] failed to upload {path}: {exc}")
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
