# Bern Ban Share Pages

This repo powers `bernban.com` and has private-ish, noindex audio share pages:

- `bernban.com/tom/`
- `bernban.com/adam/`

The old `bernban.com/beats/` page redirects to `bernban.com/tom/`.

## Drop Folders

Do not drop files directly into:

```text
/Users/nathanbernier/Library/Mobile Documents/com~apple~CloudDocs/MP3 LISTEN
```

Use the person folders inside it:

```text
/Users/nathanbernier/Library/Mobile Documents/com~apple~CloudDocs/MP3 LISTEN/tom
/Users/nathanbernier/Library/Mobile Documents/com~apple~CloudDocs/MP3 LISTEN/adam
```

Only files inside those two folders auto-upload.

## Auto Upload Setup

Install the background uploader:

```bash
./tools/install_launch_agent.sh
```

The installer creates the `tom` and `adam` drop folders if they do not already
exist. The uploader accepts `.mp3` and `.wav` files.

When you drop a file into `MP3 LISTEN/tom`, it:

- Copies the file into `tom/audio/`
- Adds it to `tom/tracks.json`
- Commits and pushes to GitHub
- Moves the original into `MP3 LISTEN/tom/_uploaded`

Adam works the same way with `MP3 LISTEN/adam`, `adam/audio/`, and
`adam/tracks.json`.

## Discord Alerts

For one shared alert channel:

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
./tools/install_launch_agent.sh
```

For separate channels:

```bash
export DISCORD_WEBHOOK_URL_TOM="https://discord.com/api/webhooks/..."
export DISCORD_WEBHOOK_URL_ADAM="https://discord.com/api/webhooks/..."
./tools/install_launch_agent.sh
```

## One-Time Upload

To process anything currently waiting in the person folders once:

```bash
python3 tools/auto_upload_beats.py --once
```

## Logs

- `.uploader_state/launchd.out.log`
- `.uploader_state/launchd.err.log`

## Stop/Start Service

```bash
launchctl unload ~/Library/LaunchAgents/com.bernban.share-uploader.plist
launchctl load ~/Library/LaunchAgents/com.bernban.share-uploader.plist
```

## Site Notes

- Tom page: `tom/index.html`
- Tom manifest: `tom/tracks.json`
- Tom new audio: `tom/audio/`
- Adam page: `adam/index.html`
- Adam manifest: `adam/tracks.json`
- Adam new audio: `adam/audio/`

The old `beats/` and `inprogress/` audio files are kept so existing links keep
working.

## Netlify Setup

Create a Netlify site from GitHub repo `24hourbreakfast/beats`:

- Branch: `main`
- Build command: leave empty
- Publish directory: `.`

`netlify.toml` is included and sets deploy defaults.

## AB Visual Batch Generation

Generate a full AB art pack in one command:

```bash
export OPENAI_API_KEY="your_key_here"
./tools/generate_ab_visuals.sh
```

Prompt config:

- `ab/visual-prompts.json`

Output:

- PNGs in `assets/ab/`
- Manifest in `assets/ab/manifest.json`
