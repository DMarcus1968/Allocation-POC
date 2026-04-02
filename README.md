# Meeting Notes — Conference Call Listener

A desktop app that listens to your video conference calls (Zoom, Teams, Google Meet, etc.) and automatically creates meeting notes with decisions and action items.

**No plugins or integrations needed** — it captures the audio playing through your speakers.

---

## Setup Guide for macOS (Step by Step)

### Step 1: Install Python

1. Open **Safari** (the compass icon in your Dock)
2. Go to **python.org/downloads**
3. Click the big yellow **"Download Python 3.x"** button
4. When the download finishes, open the `.pkg` file from your Downloads folder
5. Click **Continue** through the installer, then **Install**
6. Enter your Mac password when asked

**How to check it worked:**
- Open **Terminal** (press `Cmd + Space`, type "Terminal", press Enter)
- Type `python3 --version` and press Enter
- You should see something like `Python 3.12.x`

---

### Step 2: Install BlackHole (for capturing call audio)

Your Mac doesn't let apps record system audio by default. BlackHole is a free tool that fixes this.

1. Open Safari and go to **existential.audio/blackhole**
2. Enter your email address
3. Click **"Download BlackHole 2ch (Free)"**
4. Open the downloaded file and follow the installer

**After installing BlackHole, set up audio routing:**

1. Open **Audio MIDI Setup** (press `Cmd + Space`, type "Audio MIDI Setup", press Enter)
2. Click the **"+"** button at the bottom-left corner
3. Select **"Create Multi-Output Device"**
4. In the list on the right, check **both**:
   - Your regular speakers/headphones (e.g., "MacBook Pro Speakers")
   - "BlackHole 2ch"
5. Make sure your speakers/headphones has the **"Drift Correction"** checkbox checked
6. Right-click the new Multi-Output Device and choose **"Use This Device for Sound Output"**

**What this does:** Your call audio now plays through both your speakers (so you can hear it) AND BlackHole (so the app can capture it).

---

### Step 3: Get a Claude API Key

The app uses Claude to turn your transcript into organized notes.

1. Open Safari and go to **console.anthropic.com**
2. Create an account (or sign in)
3. Go to **API Keys** in the left sidebar
4. Click **"Create Key"**
5. Copy the key — you'll paste it into the app later
6. Add some credits to your account under **Billing** (the cost is very low — a typical 1-hour meeting costs about $0.01–0.05)

---

### Step 4: Download and Launch the App

1. Open **Terminal** (press `Cmd + Space`, type "Terminal", press Enter)
2. Copy and paste these commands one at a time, pressing Enter after each:

```bash
cd ~/Desktop
git clone https://github.com/DMarcus1968/Allocation-POC.git MeetingNotes
cd MeetingNotes
./start.sh
```

The first launch will take a few minutes to install packages. After that, it starts instantly.

---

### Step 5: Using the App

1. **Paste your API key** in the "Anthropic API Key" field at the top
2. **Select "BlackHole 2ch"** from the audio device dropdown
3. **Start your video call** (Zoom, Teams, Meet, etc.)
4. **Click "Start Recording"** — the timer starts counting
5. When your call ends, **click "Stop Recording"**
6. Wait while it:
   - Saves a backup of the audio
   - Transcribes the speech (1-3 minutes per hour of audio)
   - Generates your meeting notes
7. **Your notes appear** in the app with:
   - **Summary** — what was discussed
   - **Key Decisions** — what was decided
   - **Action Items** — who does what, by when
   - **Open Questions** — unresolved topics
8. Click **"Save Notes..."** to save to a file

All files are also auto-saved to the `output/` folder.

---

## Future Launches

After the first setup, just:

1. Open **Terminal**
2. Type:
```bash
cd ~/Desktop/MeetingNotes && ./start.sh
```

**Tip:** You can create a shortcut by saving this as an Automator app (ask if you'd like help with that).

---

## Troubleshooting

**"No loopback device detected"**
- Make sure BlackHole is installed (Step 2)
- Click "Refresh" in the device dropdown

**"Can't hear my call anymore"**
- Go to System Settings > Sound > Output
- Make sure "Multi-Output Device" is selected (not just BlackHole alone)

**"No speech detected"**
- Check that the correct audio device is selected
- Make sure your call audio is actually playing through BlackHole
- Try recording a YouTube video first as a test

**"Claude API error"**
- Check that your API key is correct
- Make sure you have credits in your Anthropic account

**App won't start**
- Open Terminal and run: `python3 -m pip install --user sounddevice numpy openai-whisper anthropic`
- Try again with `./start.sh`
