#!/usr/bin/env bash
set -euo pipefail

ICLOUD_DROP="$HOME/Library/Mobile Documents/com~apple~CloudDocs/MP3 LISTEN"
DEFAULT_WATCH_DIR="$HOME/Music/BeatsDrop"
if [[ -d "$ICLOUD_DROP" ]]; then
  DEFAULT_WATCH_DIR="$ICLOUD_DROP"
fi

WATCH_DIR="${1:-$DEFAULT_WATCH_DIR}"
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
  <key>EnvironmentVariables</key>
  <dict>
    <key>BEATS_SITE_BASE_URL</key>
    <string>${BEATS_SITE_BASE_URL:-https://bernban.com/inprogress}</string>
    <key>DISCORD_WEBHOOK_URL</key>
    <string>${DISCORD_WEBHOOK_URL:-}</string>
  </dict>
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
echo "Set DISCORD_WEBHOOK_URL before installing if you want Discord alerts."
