#!/usr/bin/env bash
set -euo pipefail

DEFAULT_DROP_ROOT="$HOME/Library/Mobile Documents/com~apple~CloudDocs/MP3 LISTEN"
DROP_ROOT="${1:-$DEFAULT_DROP_ROOT}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="$(command -v python3)"
PLIST_PATH="$HOME/Library/LaunchAgents/com.bernban.share-uploader.plist"
LOG_DIR="$REPO_ROOT/.uploader_state"
mkdir -p "$LOG_DIR"
mkdir -p "$DROP_ROOT/tom" "$DROP_ROOT/adam"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.bernban.share-uploader</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_BIN</string>
    <string>$REPO_ROOT/tools/auto_upload_beats.py</string>
    <string>--drop-root</string>
    <string>$DROP_ROOT</string>
    <string>--people</string>
    <string>tom</string>
    <string>adam</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>WorkingDirectory</key>
  <string>$REPO_ROOT</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>SHARE_SITE_ROOT</key>
    <string>${SHARE_SITE_ROOT:-https://bernban.com}</string>
    <key>DISCORD_WEBHOOK_URL</key>
    <string>${DISCORD_WEBHOOK_URL:-}</string>
    <key>DISCORD_WEBHOOK_URL_TOM</key>
    <string>${DISCORD_WEBHOOK_URL_TOM:-}</string>
    <key>DISCORD_WEBHOOK_URL_ADAM</key>
    <string>${DISCORD_WEBHOOK_URL_ADAM:-}</string>
  </dict>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/launchd.err.log</string>
</dict>
</plist>
EOF

launchctl unload "$HOME/Library/LaunchAgents/com.bernban.beats-uploader.plist" >/dev/null 2>&1 || true
launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl load "$PLIST_PATH"

echo "Installed and started: $PLIST_PATH"
echo "Drop Tom uploads here: $DROP_ROOT/tom"
echo "Drop Adam uploads here: $DROP_ROOT/adam"
echo "Set DISCORD_WEBHOOK_URL, DISCORD_WEBHOOK_URL_TOM, or DISCORD_WEBHOOK_URL_ADAM before installing if you want Discord alerts."
