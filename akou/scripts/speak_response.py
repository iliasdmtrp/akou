"""
speak_response.py — Stop hook του akou: διαβάζει φωναχτά την τελευταία απάντηση του Claude.

Το Claude Code το καλεί ως Stop hook με JSON στο stdin (περιέχει `transcript_path`).
Βρίσκει το τελευταίο μήνυμα του assistant, το μετατρέπει σε ομιλία (edge-tts,
ελληνικές νευρωνικές φωνές) και το παίζει.

Μιλά ΜΟΝΟ όταν config.json -> "speak_responses": true.

Ρυθμίσεις (config.json):
    speak_responses : true/false
    tts_voice       : π.χ. "el-GR-AthinaNeural" ή "el-GR-NestorasNeural"
    tts_max_chars   : μέγιστοι χαρακτήρες προς εκφώνηση (default 1200)
"""
import asyncio
import ctypes
import json
import os
import re
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # load_config


def _last_assistant_text(transcript_path):
    if not transcript_path or not os.path.exists(transcript_path):
        return ""
    last = ""
    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            msg = obj.get("message", obj)
            role = msg.get("role") or obj.get("type")
            if role != "assistant":
                continue
            content = msg.get("content", "")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = " ".join(
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            else:
                text = ""
            if text.strip():
                last = text.strip()
    return last


def _for_speech(text, max_chars):
    text = re.sub(r"```.*?```", " (μπλοκ κώδικα) ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"[*_#>|]+", " ", text)
    text = re.sub(r"https?://\S+", " (σύνδεσμος) ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "… (η απάντηση συνεχίζεται στην οθόνη)"
    return text


async def _tts(text, voice, out):
    import edge_tts
    await edge_tts.Communicate(text, voice).save(out)


def _play_mp3(path):
    """Παίζει mp3 μέσω Windows MCI (winmm) — χωρίς εξαρτήσεις/ffmpeg."""
    mci = ctypes.windll.winmm.mciSendStringW
    alias = "akoutts"
    mci(f'open "{path}" type mpegvideo alias {alias}', None, 0, None)
    try:
        buf = ctypes.create_unicode_buffer(64)
        mci(f"status {alias} length", buf, 64, None)
        length = int(buf.value or 0)
        mci(f"play {alias}", None, 0, None)
        waited = 0
        while waited <= length + 300:
            time.sleep(0.15)
            waited += 150
            mci(f"status {alias} mode", buf, 64, None)
            if buf.value != "playing":
                break
    finally:
        mci(f"close {alias}", None, 0, None)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    cfg = core.load_config()
    if not cfg.get("speak_responses", True):
        return
    voice = cfg.get("tts_voice", "el-GR-AthinaNeural")
    max_chars = int(cfg.get("tts_max_chars", 1200))

    text = _for_speech(_last_assistant_text(payload.get("transcript_path", "")), max_chars)
    if not text:
        return
    out = os.path.join(tempfile.gettempdir(), "akou_response.mp3")
    try:
        asyncio.run(_tts(text, voice, out))
        _play_mp3(out)
    except Exception as e:
        print(f"akou speak_response error: {e}", file=sys.stderr)
    finally:
        try:
            os.remove(out)
        except OSError:
            pass


if __name__ == "__main__":
    main()
