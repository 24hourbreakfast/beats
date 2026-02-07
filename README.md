# Bern Ban Beats

This repo powers `burnban.com/beats` and now includes:

- Vaporwave-styled beat page with a cleaner player
- Newest tracks first
- Automatic local watch-folder uploads to GitHub

## Site

Page lives at:

- `beats/index.html`

Tracks are served from:

- `beats/*.mp3`

## Auto Upload Setup (macOS)

1. Run one install command:

```bash
./tools/install_launch_agent.sh "/Users/nathanbernier/Music/BeatsDrop"
```

2. Drop new `.mp3` files into that watch folder.
3. The uploader will:
   - Copy file into `beats/` with a timestamp prefix
   - Commit + push to `main`
   - Move source file into `<watch-folder>/_uploaded`

### Logs

- `.uploader_state/launchd.out.log`
- `.uploader_state/launchd.err.log`

### Stop/Start Service

```bash
launchctl unload ~/Library/LaunchAgents/com.bernban.beats-uploader.plist
launchctl load ~/Library/LaunchAgents/com.bernban.beats-uploader.plist
```
