#!/usr/bin/env bash
set -euo pipefail

WATCH_DIR="${1:-$HOME/Music/BeatsDrop}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="$(command -v python3)"
PLIST_PATH="$HOME/Library/LaunchAgents/com.bernban.beats-uploader.plist"
LOG_DIR="$REPO_ROOT/.uploader_state"
mkdir -p "$LOG_DIR"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.bernban.beats-uploader</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_BIN</string>
    <string>$REPO_ROOT/tools/auto_upload_beats.py</string>
    <string>--watch-dir</string>
    <string>$WATCH_DIR</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>WorkingDirectory</key>
  <string>$REPO_ROOT</string>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/launchd.err.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl load "$PLIST_PATH"

echo "Installed and started: $PLIST_PATH"
echo "Watching folder: $WATCH_DIR"
echo "Drop .mp3 files there and they will auto-upload."
