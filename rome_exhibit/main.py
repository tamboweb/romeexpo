"""
Ancient Rome Interactive Exhibit - main application

Runs a Flask web server for the touchscreen UI, and a background
thread that continuously watches the PN532 NFC reader. When a real
tag is scanned, it looks up which artifact it belongs to, tells the
LED strip to change, and makes that info available to the browser
through a small API. The browser polls that API a few times a second
and updates the screen - no button-pressing involved.
"""

import json
import os
import threading
import time

from flask import Flask, jsonify, render_template

from nfc.reader import NFCReader
from lighting.effects import LightingController

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_PATH = os.path.join(BASE_DIR, "config", "artifacts.json")
TAG_MAP_PATH = os.path.join(BASE_DIR, "config", "tag_map.json")

# How long (seconds) a tag must be gone before the screen returns to idle.
# A little slack here stops brief mis-reads from flickering back to idle.
IDLE_TIMEOUT = 1.5

app = Flask(__name__)

nfc_reader = NFCReader()
lighting = LightingController()

# Shared state between the background scanning thread and the web API.
# "seq" increases every time something changes, so the browser can tell
# a fresh event apart from "nothing new happened".
_state_lock = threading.Lock()
_current_state = {"artifact_id": None, "seq": 0, "raw_uid": None}


def load_artifacts():
    try:
        with open(ARTIFACTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as err:
        print(f"[artifacts] could not load {ARTIFACTS_PATH}: {err}")
        return []


def load_tag_map():
    try:
        with open(TAG_MAP_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as err:
        print(f"[tags] could not load {TAG_MAP_PATH}: {err}")
        return {}
    return {uid: artifact_id for uid, artifact_id in raw.items()
            if not uid.startswith("_")}


def artifacts_by_id():
    return {a["id"]: a for a in load_artifacts()}


def _update_state(artifact_id, raw_uid=None):
    with _state_lock:
        _current_state["artifact_id"] = artifact_id
        _current_state["raw_uid"] = raw_uid
        _current_state["seq"] += 1


def _scanning_loop():
    """Runs forever in the background, polling the NFC reader."""
    if not nfc_reader.is_connected:
        print("[scan-loop] NFC reader not connected - the exhibit screen "
              "will just stay on the idle screen. Check wiring and "
              "config/tag_map.json.")

    tag_map = load_tag_map()
    tags_by_id = artifacts_by_id()

    last_uid = None
    last_seen_time = 0
    lighting.idle()

    while True:
        uid = nfc_reader.scan_once(timeout=0.2)
        now = time.time()

        if uid:
            last_seen_time = now
            if uid != last_uid:
                last_uid = uid
                artifact_id = tag_map.get(uid)
                if artifact_id and artifact_id in tags_by_id:
                    artifact = tags_by_id[artifact_id]
                    print(f"[scan-loop] recognised tag {uid} -> {artifact_id}")
                    lighting.set_effect(artifact["lighting"]["mode"],
                                         artifact["lighting"]["color"])
                    _update_state(artifact_id, raw_uid=uid)
                else:
                    print(f"[scan-loop] unrecognised tag: {uid}")
                    _update_state("__unknown__", raw_uid=uid)
        else:
            if last_uid is not None and (now - last_seen_time) > IDLE_TIMEOUT:
                last_uid = None
                lighting.idle()
                _update_state(None)

        time.sleep(0.05)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/artifacts")
def api_artifacts():
    return jsonify(load_artifacts())


@app.route("/api/current-scan")
def api_current_scan():
    """The browser polls this a few times a second to see what's on
    the pedestal right now."""
    with _state_lock:
        return jsonify(dict(_current_state))


if __name__ == "__main__":
    scanner_thread = threading.Thread(target=_scanning_loop, daemon=True)
    scanner_thread.start()

    app.run(host="0.0.0.0", port=5000, debug=False)
