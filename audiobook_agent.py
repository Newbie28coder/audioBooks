import asyncio
import hashlib
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import edge_tts
import pygame
from fpdf import FPDF
from fpdf.errors import FPDFException
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from pypdf import PdfReader
from pypdf.errors import PdfReadError

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

LIB = Path("library")
FONTS = Path("fonts")
LIB.mkdir(exist_ok = True)

# language code -> Edge TTS voice (verify names with: edge-tts --list-voices)
VOICE = {
    "hi": "hi-IN-SwaraNeural", "en": "en-IN-NeerjaNeural", "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural", "bn": "bn-IN-TanishaaNeural", "mr": "mr-IN-AarohiNeural",
    "gu": "gu-IN-DhwaniNeural", "kn": "kn-IN-SapnaNeural", "ml": "ml-IN-SobhanaNeural",
    "ur": "ur-IN-GulNeural", "fr": "fr-FR-DeniseNeural", "es": "es-ES-ElviraNeural",
    "de": "de-DE-KatjaNeural", 
}

# language code -> font file inside ./fonts (download from Google Noto)
FONT_FOR = {
    "hi": "NotoSansDevanagari-Regular.ttf", "mr": "NotoSansDevanagari-Regular.ttf",
    "ta": "NotoSansTamil-Regular.ttf", "te": "NotoSansTelugu-Regular.ttf",
    "bn": "NotoSansBengali-Regular.ttf", "gu": "NotoSansGujarati-Regular.ttf",
    "kn": "NotoSansKannada-Regular.ttf", "ml": "NotoSansMalayalam-Regular.ttf",
    "ur": "NotoNastaliqUrdu-Regular.ttf",
}
DEFAULT_FONT = "NotoSans-Regular.ttf"

_whisper = None 

# 1. Input + Language 
def detect_lang(text):
    sample = text[3000]
    deva = sum("\u0900" <= c <= "\u097f" for c in sample)
    if deva > len(sample) * 0.3:
        return "hi"
    return detect(sample)

def transcribe(path: str):
    global _whisper
    from faster_whisper import WhisperModel
    if _whisper is None:
        _whisper = WhisperModel("small", compute_type="int8")
# use "medium" for better Hindi
    segments, info = _whisper.transcribe(path, vad_filter = True)
    text = " ".join(s.text.strip() for s in segments)
    return text, info.language

def read_input(path: str):
    p = Path(path.strip('"'))
    ext = p.suffix.lower()
    if ext in {".mp3", ".wav", ".m4a", ".ogg", ".flac"}:
        return transcribe(str(p))
    if ext == ".pdf":
        text = "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
    else:
        text = p.read_text(encoding = "utf-8")
    return text, detect(text[:3000])

# 2. Split into speakable lines 
def split_lines(text: str):
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[|.!?])\s+", text)
    out = []
    for s in parts:
        while len(s) > 300: # break very long sentences at a comma/space
            cut = max(s.rfind(",", 0, 300), s.rfind(" ", 0, 300))
            out.append(s[:cut + 1].strip())
            s = s[cut + 1:]
        if s.strip():
            out.append(s.strip())
    return out 

# 3. PDF in the same language 
def build_pdf(title: str, lang: str, lines, out_path: Path):
    pdf = FPDF()
    pdf.add_page()
    font = FONTS / FONT_FOR.get(lang, DEFAULT_FONT)
    if not font.exists():
        font = FONTS / DEFAULT_FONT
    pdf.add_font("body", fname = str(font))
    pdf.set_text_shaping(True) # needed for Hindi/Tamil etc.
    pdf.set_font("body", size = 14)
    pdf.multi_cell(0, 10, title, new_x = "LMARGIN", new_y = "NEXT")
    pdf.ln(4)
    for i in range(0, len(lines), 5): # 5 lines per paragraph 
        pdf.multi_cell(0, 8, " ".join(lines[i:i + 5]), new_x ="LMARGIN", new_y = "NEXT")
        pdf.ln(3)
    pdf.output(str(out_path))

def create_book(title: str, text: str, lang: str):
    lines = split_lines(text)
    bid = re.sub(r"\W+", "_", title)[:30] + "_" + hashlib.md5(text[:500].encode()).hexdigest()[:6]
    d = LIB / bid 
    (d / "audio").mkdir(parents = True, exist_ok = True)
    book = {"id":bid, "title":title, "lang":lang, "lines":lines, "bookmark":0}
    (d / "book.json").write_text(json.dumps(book, ensure_ascii = False), encoding = "utf-8")
    build_pdf(title, lang, lines, d / "book.pdf")
    print(f"Saved '{title}' ({lang}, {len(lines)} lines). PDF: {d / 'book.pdf'}")
    return book 

def load_books():
    return [json.loads(p.read_text(encoding = "utf-8")) for p in sorted(LIB.glob("*/book.json"))]

def save_book(book):
    (LIB / book["id"] / "book.json").write_text(json.dumps(book, ensure_ascii = False), encoding = "utf-8")

# 4. Speaking with simple "expression"
def style_for(line: str):
    rate, pitch = "+0%", "+0Hz"
    if line.endswith("?"):
        pitch = "+4Hz"
    elif line.endswith("!"):
        rate, pitch = "+8%", "+3Hz"
    if line[:1] in "\"'\u201c\u2018":  # dialogue sounds a bit livelier
        rate, pitch = "+5%", "+3Hz"
    return rate, pitch

def full_voice(short):
    lang, region, name = re.match(r"^([a-z]{2,})-([A-Z]{2,})-(.+)$", short).groups()
    return f"Microsoft Server Speech Text to Speech Voice ({lang}-{region}, {name})"

def make_audio(book, i):
    f = LIB / book["id"] / "audio" / f"{i}.mp3"
    if not f.exists():
        rate, pitch = style_for(book["lines"][i])
        comm = edge_tts.Communicate(book["lines"][i],
                                    full_voice(VOICE.get(book["lang"], "en-IN-NeerjaNeural")),
                                    rate = rate, pitch = pitch)
        asyncio.run(comm.save(str(f)))
    return f 

class Player:
    def __init__(self):
        pygame.mixer.init()
        self.stop_flag = threading.Event()
        self.thread = None
        self.pool = ThreadPoolExecutor(max_workers = 1)

    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self, book):
        if self.running():
            print("Already playing. Type Stop! first.")
            return 
        self.stop_flag.clear()
        self.thread = threading.Thread(target = self._run, args = (book,), daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_flag.set()
        pygame.mixer.music.stop()
        if self.thread:
            self.thread.join(timeout = 3)

    def _run(self, book):
        i = book["bookmark"]
        n = len(book["lines"])
        print(f"\nPlaying '{book['title']}' from line {i + 1} / {n}. Type Stop! to pause.")
        nxt = self.pool.submit(make_audio, book, i)
        while i < n and not self.stop_flag.is_set():
            f = nxt.result()
            if i + 1 < n:
                nxt = self.pool.submit(make_audio, book, i + 1)  # prepare next line
            book["bookmark"] = i
            print(f"[{i + 1}/{n}] {book['lines'][i]}")
            pygame.mixer.music.load(str(f))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and not self.stop_flag.is_set():
                pygame.time.wait(100)
            if self.stop_flag.is_set():
                break
            i += 1
        if i >= n:
            book["bookmark"] = 0
            print("The end. Bookmark reset.")
        save_book(book)
        if self.stop_flag.is_set():
            print(f"Bookmark saved at line {book['bookmark'] + 1}. See you tomorrow.")

def main():
    player = Player()
    books = load_books()
    current = books[0] if books else None 
    print("Commands: add <file> | paste | list | open <n> | Start Audiobook | Stop! | bookmark | restart | quit")
    while True:
        cmd = input("\n> ").strip()
        low = cmd.lower()
        if low == "stop!":
            player.stop()
        elif low == "start audiobook":
            if current:
                player.start(current)
            else:
                print("No book selected. Use: add <file> or paste")
        elif low.startswith("add "):
            try:
                text, lang = read_input(cmd[4:])
                title = Path(cmd[4:].strip('"')).stem
                current = create_book(title, text, lang)
            except (OSError, ValueError, RuntimeError, LangDetectException, PdfReadError, FPDFException) as e:
                print(f"Could not add: {e}")
        elif low == "paste":
            buf = []
            while (ln := input("  ")).strip():
                buf.append(ln)
            text = "\n".join(buf)
            if text:
                current = create_book("pasted_" + hashlib.md5(text.encode()).hexdigest()[:4], text, detect(text))
        elif low == "list":
            books = load_books()
            for k, b in enumerate(books, 1):
                print(f"{k}. {b['title']} [{b['lang']}] line {b['bookmark'] + 1}/{len(b['lines'])}")
        elif low.startswith("open "):
            books = load_books()
            try:
                current = books[int(low.split()[1]) - 1]
                print(f"Opened '{current['title']}' at line {current['bookmark'] + 1}")
            except (ValueError, IndexError):
                print("Invalid number. Use 'list' first.")
        elif low == "bookmark" and current:
            print(f"'{current['title']}': line {current['bookmark'] + 1}/{len(current['lines'])}")
        elif low == "restart" and current:
            current["bookmark"] = 0
            save_book(current)
            print("Bookmark reset.")
        elif low in {"quit", "exit"}:
            player.stop()
            break
        else:
            print("Unknown Command.")

if __name__ == "__main__":
    main()

        
