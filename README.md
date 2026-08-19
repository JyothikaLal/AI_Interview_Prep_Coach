# AI Interview Prep Coach

AI Interview Prep Coach is a small Flask-based interview practice app with speech-to-text, retrieval-based coaching tips, and Groq-powered answer feedback.

## What it does

- Records spoken answers from the browser
- Transcribes audio with Faster-Whisper
- Retrieves guidance from the local knowledge base
- Scores answers and suggests improvements
- Adapts the next question based on weak areas

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a local `.env` file with your Groq key. Do not commit the key.

```bash
GROQ_API_KEY=your_key_here
```

Build the index and run the app:

```bash
python3 src/rag.py
cd src
python3 app.py
```

Open `http://localhost:5000` in your browser.

## Project Files

- `src/app.py` - Flask API and session flow
- `src/asr.py` - Speech-to-text
- `src/rag.py` - Knowledge base indexing and retrieval
- `src/evaluate.py` - Groq-backed evaluation
- `src/questions.py` - Question bank
- `src/session.py` - Interview session logic
- `index.html` - Web UI

## GitHub Notes

- `.env` is ignored by `.gitignore`
- Generated audio, FAISS data, and model cache files are also ignored
- Only source code and this README should be committed
