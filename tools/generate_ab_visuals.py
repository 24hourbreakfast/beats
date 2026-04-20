#!/usr/bin/env python3
"""Batch-generate AB visuals from prompt config using an image API."""

from __future__ import annotations

import argparse
import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Config must be a JSON object")
    prompts = data.get("prompts")
    if not isinstance(prompts, list) or not prompts:
        raise ValueError("Config must include a non-empty 'prompts' array")
    return data


def post_json(url: str, api_key: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=timeout) as res:
            raw = res.read().decode("utf-8")
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code} from image API: {details}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Network error calling image API: {exc}") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON response from image API: {raw[:240]}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Unexpected non-object response from image API")
    return parsed


def resolve_prompt_entry(entry: dict[str, Any], defaults: dict[str, Any], index: int) -> dict[str, str]:
    name = str(entry.get("name", "")).strip()
    prompt = str(entry.get("prompt", "")).strip()
    if not name:
        name = f"ab-visual-{index:02d}"
    if not prompt:
        raise ValueError(f"Prompt entry #{index} is missing 'prompt'")
    size = str(entry.get("size", defaults.get("size", "1536x1024"))).strip()
    quality = str(entry.get("quality", defaults.get("quality", "medium"))).strip()
    return {"name": name, "prompt": prompt, "size": size, "quality": quality}


def write_manifest(path: Path, items: list[dict[str, str]], model: str) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "model": model,
        "items": items,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="ab/visual-prompts.json",
        help="Prompt configuration JSON file",
    )
    parser.add_argument(
        "--output-dir",
        default="assets/ab",
        help="Directory for generated images",
    )
    parser.add_argument(
        "--manifest",
        default="assets/ab/manifest.json",
        help="Metadata output file",
    )
    parser.add_argument(
        "--api-base",
        default="https://api.openai.com/v1",
        help="Image API base URL",
    )
    parser.add_argument(
        "--model",
        default="gpt-image-1",
        help="Image model ID",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="HTTP timeout per generation request",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and print plan only",
    )
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not args.dry_run and not api_key:
        raise SystemExit("Missing OPENAI_API_KEY")

    config_path = Path(args.config).resolve()
    output_dir = Path(args.output_dir).resolve()
    manifest_path = Path(args.manifest).resolve()

    config = load_config(config_path)
    defaults = config.get("defaults", {})
    if not isinstance(defaults, dict):
        defaults = {}
    prompts = config["prompts"]

    output_dir.mkdir(parents=True, exist_ok=True)

    items: list[dict[str, str]] = []
    endpoint = args.api_base.rstrip("/") + "/images/generations"
    for idx, raw in enumerate(prompts, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Prompt entry #{idx} must be an object")
        entry = resolve_prompt_entry(raw, defaults, idx)
        filename = f"{entry['name']}.png"
        output_file = output_dir / filename

        if output_file.exists() and not args.overwrite:
            print(f"[skip] exists: {output_file}")
            items.append(
                {
                    "name": entry["name"],
                    "file": str(output_file.relative_to(output_dir.parent)),
                    "size": entry["size"],
                    "quality": entry["quality"],
                    "prompt": entry["prompt"],
                }
            )
            continue

        if args.dry_run:
            print(f"[plan] {filename} :: {entry['size']} :: {entry['quality']}")
            items.append(
                {
                    "name": entry["name"],
                    "file": str(output_file.relative_to(output_dir.parent)),
                    "size": entry["size"],
                    "quality": entry["quality"],
                    "prompt": entry["prompt"],
                }
            )
            continue

        payload = {
            "model": args.model,
            "prompt": entry["prompt"],
            "size": entry["size"],
            "quality": entry["quality"],
            "n": 1,
            "response_format": "b64_json",
        }
        data = post_json(endpoint, api_key, payload, args.timeout)
        images = data.get("data")
        if not isinstance(images, list) or not images:
            raise RuntimeError(f"Missing image data for prompt '{entry['name']}'")
        first = images[0]
        if not isinstance(first, dict):
            raise RuntimeError(f"Malformed image payload for prompt '{entry['name']}'")
        b64 = first.get("b64_json")
        if not isinstance(b64, str) or not b64:
            raise RuntimeError(f"No b64_json returned for prompt '{entry['name']}'")
        image_bytes = base64.b64decode(b64)
        output_file.write_bytes(image_bytes)
        print(f"[ok] wrote {output_file}")

        items.append(
            {
                "name": entry["name"],
                "file": str(output_file.relative_to(output_dir.parent)),
                "size": entry["size"],
                "quality": entry["quality"],
                "prompt": entry["prompt"],
            }
        )

    if args.dry_run:
        print("[dry-run] no files were written")
        return 0

    write_manifest(manifest_path, items, args.model)
    print(f"[manifest] wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
