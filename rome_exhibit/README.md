# Ancient Rome Exhibit — Setup Guide

This turns the browser prototype into a real app that runs on the Raspberry Pi:
a small Python web server (Flask) that the touchscreen's browser connects to.

## Quick install (on the Pi, after cloning this repo)

```bash
git clone <your-repo-url>
cd rome_exhibit
sudo ./install.sh
```

This handles Python packages and the auto-start service for you. It'll print
out the few things you still need to do by hand (wiring, tag UIDs, kiosk
browser) — those are also covered step-by-step below if you want more detail.

## What's in this folder

```
rome_exhibit/
    main.py                 <- starts the server, runs the NFC scanning loop
    install.sh               <- one-shot setup script for the Pi
    requirements.txt        <- Python packages it needs
    config/
        artifacts.json       <- the artifact database (edit this to add artifacts)
        tag_map.json          <- maps physical NFC tag UIDs to artifacts
    nfc/
        reader.py             <- talks to the PN532 NFC reader
    lighting/
        effects.py            <- talks to the WS2812B LED strip
    tools/
        scan_uid.py            <- run this to find a tag's UID
    templates/
        index.html            <- page structure
    static/
        css/style.css         <- all visual styling
        js/app.js              <- screen logic, polls for real scans
        images/                <- artifact photos go here
    systemd/
        rome-exhibit.service   <- makes the server start automatically on boot
```

## Step 1 — Copy the project onto the Pi

On your laptop, unzip the project, then copy the whole `rome_exhibit` folder onto
the Pi. The easiest way (from a terminal on your laptop, with the Pi on the
same network):

```bash
scp -r rome_exhibit root@<your-pi-ip-address>:/root/
```

Replace `<your-pi-ip-address>` with the Pi's IP (find it on the Pi itself by
running `hostname -I`). If `scp` asks for a password, use your Pi login
password.

If you'd rather not use the terminal, a USB stick or a Git repo both work
fine too — the important part is that the folder ends up at `/root/rome_exhibit`
on the Pi.

## Step 2 — Enable SPI (needed for the NFC reader)

The PN532 talks to the Pi over SPI, which is off by default.

```bash
dietpi-config
```

Go to **Advanced Options**, find **SPI**, and turn it **on**. Reboot when it
asks you to.

## Step 3 — Wire up the hardware

**PN532 NFC reader** (set the board's switches/jumpers to SPI mode if it has
them - check the sticker/manual on your specific board):

| PN532 pin | Connects to Pi pin |
|---|---|
| VCC | 3.3V |
| GND | GND |
| SCK | GPIO11 (SCLK) |
| MISO | GPIO9 |
| MOSI | GPIO10 |
| SS (CS) | GPIO5 |

**WS2812B LED strip** (through the logic-level shifter, powered by the
external 5V supply — don't power the strip from the Pi itself):

| LED strip wire | Connects to |
|---|---|
| 5V | External 5V power supply (+) |
| GND | External supply (–) **and** Pi GND (grounds must be shared) |
| DIN (data) | Through the level shifter, into GPIO18 |

## Step 4 — Install Python dependencies on the Pi

Open a terminal **on the Pi** (or SSH into it: `ssh root@<your-pi-ip-address>`):

```bash
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip build-essential
cd /root/rome_exhibit
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

`venv` creates an isolated Python environment just for this project. The
`apt-get install` line pulls in the compiler tools the LED library needs to
build itself during install.

## Step 5 — Find each tag's UID

Every physical NTAG213 sticker has its own unique ID number. You need to find
each one and tell the app which artifact it belongs to.

```bash
sudo venv/bin/python3 tools/scan_uid.py
```

Hold each tag against the reader one at a time and write down the UID it
prints (e.g. `04A1B2C3D4`) alongside which artifact it's stuck to. Press
`Ctrl+C` when you've done them all.

Open `config/tag_map.json` and fill in the real UIDs:

```json
{
  "04A1B2C3D4": "artifact_coin",
  "04E5F6A7B8": "artifact_helmet"
}
```

(Delete the `"_comment"` line and the placeholder UIDs that came with the
project — replace them with your real ones.)

## Step 6 — Test it manually

Still in that terminal, with the venv active. Because the LED strip needs
root access, run it with `sudo` (using the venv's own Python so it can still
find Flask and the other packages):

```bash
sudo venv/bin/python3 main.py
```

You should see it print that the PN532 connected, and that it's running on
`http://0.0.0.0:5000`. On the Pi's own screen, open a browser and go to:

```
http://localhost:5000
```

Hold an artifact's tag against the reader — the screen and LEDs should react
for real, no button-pressing needed. Press `Ctrl+C` in the terminal to stop
when you're done testing.

If the PN532 doesn't connect, double check the wiring and that SPI is
enabled (Step 2). If the LEDs don't light up, double check the level shifter
wiring and that you ran the app with `sudo`.

## Step 7 — Make the server start automatically on boot

This is what `systemd/rome-exhibit.service` is for — it tells the Pi's operating
system to start `main.py` itself, every time the Pi powers on, without you
needing to open a terminal. It's already set up to run as root (which the
LEDs need).

```bash
sudo cp /root/rome_exhibit/systemd/rome-exhibit.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rome-exhibit.service
sudo systemctl start rome-exhibit.service
```

Check it's running:

```bash
sudo systemctl status rome-exhibit.service
```

You should see `active (running)`. From now on, the server starts by itself
whenever the Pi boots — you can test this with `sudo reboot`.

If you copied the project somewhere other than `/root/rome_exhibit`, open
`rome-exhibit.service` in a text editor first and update the paths to match,
before copying it in.

## Step 8 — Fullscreen on boot

Once the server auto-starts (Step 7), the last piece is making a browser open
automatically, fullscreen, pointed at `http://localhost:5000`, with no desktop
visible to visitors — install Chromium through `dietpi-software` (ID 113) and
set `SOFTWARE_CHROMIUM_AUTOSTART_URL=http://localhost:5000` in
`/boot/dietpi.txt`, then reboot.

## Adding or editing an artifact

Everything about an artifact — its name, its text, its photo, its lighting
colour — lives in one place: `config/artifacts.json`. You never need to touch
any code to add a new one.

**1. Add the photo.** Drop a `.jpg` or `.png` file into `static/images/`.
   Give it a simple name with no spaces, e.g. `sandal.jpg`.

**2. Add an entry to `config/artifacts.json`.** Copy one of the existing
   `{ ... }` blocks and change the values:

```json
{
  "id": "artifact_sandal",
  "name": "Roman Sandal",
  "meta": "Caliga · Leather",
  "period": "1ST CENTURY AD",
  "emoji": "👞",
  "image": "sandal.jpg",
  "description": "One short paragraph about what it is and what it was used for.",
  "facts": [
    "A short, interesting fact.",
    "Another one.",
    "A third one."
  ],
  "lighting": { "mode": "amber", "color": "#B4915A" }
}
```

What each field means:
- `id` — a unique short name for this artifact, no spaces. Used internally.
- `name` — the big heading shown on screen.
- `meta` — the small italic line under the name (type of object · material).
- `period` — the small label shown near the photo.
- `emoji` — a fallback shown only if the photo is missing or fails to load.
- `image` — the exact filename you put in `static/images/`.
- `description` — one short paragraph, plain English.
- `facts` — a list of short one-sentence facts, shown as bullet points.
- `lighting.color` — a hex colour code for the glow behind the photo, and
  the actual colour the LED strip lights up in when this artifact is
  scanned. Pick one that matches the artifact — warm gold for metal,
  reddish for iron/blood-red dyes, pale stone colour for marble, etc.
- `lighting.mode` — `"ember"` makes the LEDs pulse; anything else is a
  steady glow.

**3. Give it a physical NFC tag.** Stick an NTAG213 sticker to the real
object, run `tools/scan_uid.py` to read its UID, and add a line for it in
`config/tag_map.json` pointing at this artifact's `id`.

**4. Save everything and restart the service:**
`sudo systemctl restart rome-exhibit.service` (or just re-run `main.py` if
you're testing manually). No other code changes needed.
