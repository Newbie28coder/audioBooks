# Audiobook Agent

A terminal tool that turns text, PDFs, photos or audio into a book you can read and listen to side by side. It detects the language, optionally translates it, builds a PDF, and speaks the book line by line with a voice. Your place is kept by a cute mascot bookmark.

Built for people who like following the text while a voice reads along.

## Features

- **Flexible input:** plain text, text-based PDFs, photos or screenshots (OCR), and audio files (speech-to-text with Whisper)
- **Automatic language detection** for audio and text
- **Translation** into 19 languages, including Hindi, Spanish, German, Tamil and more
- **Bilingual PDF:** original text in black, translation in blue beneath each paragraph
- **Line-by-line speech** using Microsoft Edge neural voices, with small pitch and speed changes for questions, exclamations and dialogue
- **Mascot bookmark:** a character walks along a progress track while you read
- **Resume anywhere:** type `Stop!` and pick up from the same line tomorrow
- **A library of many books,** each with its own bookmark, PDF and cached audio

## Requirements

- Python 3.10 or newer (tested setup: Python 3.13 with [uv](https://docs.astral.sh/uv/))
- Internet connection (voices and translation are online services)
- Fonts from [Google Noto](https://fonts.google.com/noto)
- Optional: [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) for photos

All tools used are free.

## Setup

1. Put `audiobook_agent_v2.py` in a project folder.
2. Install the packages:

   ```
   uv init
   uv add faster-whisper edge-tts pygame fpdf2 uharfbuzz langdetect pypdf deep-translator pillow pytesseract
   ```

3. Create a `fonts/` folder next to the script and add these files from the Noto downloads (look inside each `static` folder):

   - `NotoSans-Regular.ttf` (required, used as the default)
   - `NotoSansDevanagari-Regular.ttf` (for Hindi, Marathi, Sanskrit)
   - Other scripts as needed, such as `NotoSansTamil-Regular.ttf`

4. Optional, for photo input: install Tesseract and tick the **Hindi** language data (and any other languages you need). If it installs outside the default path, set the `TESSERACT_CMD` environment variable to the full path of `tesseract.exe`.

5. Run it:

   ```
   uv run audiobook_agent_v2.py
   ```

   When you see the command list and a `>` prompt, it is ready.

## Usage

| Command | What it does |
|---|---|
| `add <file>` | Add a book from `.txt`, `.pdf`, `.jpg/.png` or audio (`.mp3 .wav .m4a .ogg .flac`) |
| `paste` | Paste text as a new book (finish with an empty line) |
| `translate <language>` | Translate the current book, e.g. `translate es` or `translate Spanish` |
| `listen original` / `listen translated` | Choose which version is spoken |
| `Start Audiobook` | Speak from your bookmark (case is ignored) |
| `Stop!` | Stop and save the bookmark at that line |
| `bookmark` | Show your mascot and position |
| `mascot [number]` | Choose your bookmark character |
| `list` | Show all books with their progress |
| `open <n>` | Switch to book number n from `list` |
| `show [a-b]` | Print numbered lines (with translations) |
| `delete a-b` | Delete lines; the PDF and bookmark update automatically |
| `delbook` | Delete the whole book (asks to confirm) |
| `restart` | Reset the bookmark to the start |
| `help`, `quit` | Show commands, exit |

### A typical session

```
> add C:\books\story.pdf
Original language detected: Hindi (hi)
Translate to which language? (e.g. en, es, German; Enter to skip) es
> Start Audiobook
?? ?????????????????????? 12%  [5/40]
> Stop!
?? Spot saved at line 6. See you tomorrow!
```

Tomorrow: run the script, use `list` and `open 1` if needed, then `Start Audiobook`.

## How it works

```
input (audio / text / PDF / photo)
   -> language detection (Whisper or langdetect)
   -> split into lines
   -> optional translation (Google Translate via deep-translator)
   -> PDF (fpdf2 + Noto fonts)
   -> speech (Edge TTS), one line at a time, next line prepared in advance
   -> bookmark saved to book.json
```

### Project structure

```
audiobook/
??? audiobook_agent_v2.py
??? fonts/                  Noto font files
??? library/
    ??? <book name>_<code>/
        ??? book.json       text, translation, bookmark, mascot
        ??? book.pdf        reading copy
        ??? audio/          cached voice files
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `>>>` prompt appears and `uv run` gives `SyntaxError` | You are inside the Python shell. Type `exit()` and run it from the normal terminal prompt |
| PDF shows empty boxes instead of Hindi | The font is missing from `fonts/`, or the file name differs from the one in `FONT_FOR` |
| `Non-UTF-8 code ... no encoding declared` | Save the script as UTF-8 (VS Code status bar > **Save with Encoding** > UTF-8) |
| `Invalid voice` | Check voice names with `edge-tts --list-voices` and update the `VOICE` table |
| Translation fails | Check your internet. Large books can be throttled, so try a chapter at a time |
| Photo text is garbled | Use a flat, well-lit photo or a screenshot, and check with `show` |
| Hindi looks broken in the terminal | This is a terminal font issue only. The PDF and voice are unaffected |
| `uv run` prints nothing | Run `uv add ...` first so packages exist in the project |

## Limitations

- **Hindi and Sanskrit voices are weaker than Spanish or German.** Free neural voices handle everyday Hindi reasonably, but literary and Sanskrit-heavy text can sound off, and there is no Sanskrit voice at all.
- **Machine translation loses nuance,** especially for literary text. Review the output with `show`.
- **Whisper transcription is slow on a CPU,** and weaker for Hindi than for Spanish or German. Try short clips first.
- **OCR for Hindi** is the least accurate step. Scanned or curved pages often need clean-up.
- **Some PDFs extract as garbage** if they use old legacy Hindi fonts, and scanned PDFs need OCR first.
- **Edge TTS and Google Translate are unofficial routes** that could change or be rate-limited.
- **Expressions are basic:** pitch and speed shifts, not real emotion.
- Terminal emoji need a UTF-8 capable terminal, such as VS Code's.

## A note on content

Use this tool with books you own, public-domain works, or your own recordings and notes. Respect the copyright of any book you add.

## Ideas for later

- A read-along view that highlights the current line
- Spoken "Stop!" through the microphone
- Emotion tagging with an LLM for more expressive narration
- Offline translation with Argos Translate