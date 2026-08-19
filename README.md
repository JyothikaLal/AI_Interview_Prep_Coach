# AI Interview Prep Coach

AI Interview Prep Coach is a browser-based interview practice app that records spoken answers, turns them into text, retrieves coaching notes from a local knowledge base, and asks Groq to grade the response with targeted feedback.

## Overview

The project combines four ideas:

- Speech-to-text, so you can answer out loud instead of typing
- Retrieval, so feedback is grounded in your own interview notes instead of being generic
- LLM evaluation, so the answer gets a useful score and improvement advice
- Session state, so the app can remember which questions were asked and adapt the next one

## How It Works

1. The browser records audio with the MediaRecorder API in `index.html`.
2. The frontend sends the audio file to the Flask backend in `src/app.py`.
3. `src/asr.py` uses Faster-Whisper to transcribe the speech into text.
4. `src/rag.py` loads markdown files from `data/kb/`, builds a simple local vector index, and returns the most relevant notes for the current question.
5. `src/evaluate.py` sends the question, transcript, and retrieved context to Groq.
6. `src/session.py` stores the interview history, tracks weak areas, and picks the next question.

## Main Concepts and Why They Are Used

### Flask backend

`src/app.py` is the server layer. It exposes a small set of routes for the UI:

- `/` serves the frontend
- `/transcribe` converts audio to text
- `/session/start` creates a new interview session
- `/session/answer` submits an answer and returns feedback
- `/health` is a lightweight status check

Flask is used here because the application is simple, local, and easy to wire to a single-page frontend.

### Speech-to-text with Faster-Whisper

`src/asr.py` loads `faster_whisper.WhisperModel` and runs transcription on CPU with `int8` quantization.

Why this exists:

- It lets the app accept spoken answers instead of text input
- CPU `int8` keeps the model lighter for local use
- The model is cached under `data/models/` so it does not need to redownload every time

Concepts used here:

- Automatic Speech Recognition (ASR): converting spoken audio into text
- Model caching: storing downloaded model files locally for reuse
- CPU inference: running the model without requiring a GPU
- Quantization: using `int8` to reduce memory and speed up inference on local machines

### Retrieval-augmented generation

`src/rag.py` reads markdown files from `data/kb/`, tokenizes the text, builds a vocabulary, and stores vectors in `data/faiss_index/index.json`.

This is the retrieval part of the app.

Why it matters:

- It grounds the evaluation in interview coaching material
- It makes the feedback more specific than a plain LLM prompt
- It keeps the project self-contained with local markdown knowledge files

Note: the index folder is named `faiss_index`, but the implementation is a lightweight local cosine-similarity index stored as JSON.

Concepts used here:

- RAG (Retrieval-Augmented Generation): retrieving relevant context before asking the LLM to respond
- Knowledge base ingestion: loading markdown files from `data/kb/`
- Tokenization: splitting text into lowercased alphanumeric tokens
- Vocabulary building: assigning each token a stable index in the vector space
- Bag-of-words vectorization: counting token frequency per document and query
- Cosine similarity: ranking documents by how close they are to the question text
- Top-k retrieval: returning the most relevant few documents instead of everything

Why this approach was chosen:

- It is simple and transparent
- It works offline with local markdown files
- It is easy to inspect and debug
- It keeps the feedback tied to project-specific coaching notes

### Groq evaluation

`src/evaluate.py` loads the `GROQ_API_KEY` from `.env`, retrieves context for the current question, and sends a prompt to Groq using the `llama-3.3-70b-versatile` model.

Why this exists:

- It produces human-readable interview feedback
- It gives a score out of 10
- It highlights strengths, missing pieces, and one concrete improvement suggestion

Concepts used here:

- LLM prompting: instructing the model with a structured task and expected output
- Prompt grounding: providing retrieved context so the model uses the knowledge base
- Chat completions API: sending a user message to a hosted model endpoint
- Temperature control: keeping output more focused and less random with `temperature=0.3`
- Model selection: choosing a larger model for better interview-quality feedback

What the LLM is expected to do:

- Read the interview question
- Read the candidate transcript
- Read the retrieved coaching context
- Return a score, strengths, weaknesses, and one concrete improvement suggestion

### Session state and adaptive questioning

`src/session.py` keeps track of:

- Which questions were already asked
- The transcript and feedback for each turn
- Weak categories identified from low scores

It then uses that history to choose the next question.

Why this exists:

- It makes the interview feel like a real coaching session
- It avoids repeating the same question
- It prioritizes weak areas so the practice adapts to the user

Concepts used here:

- Session state: storing user progress across requests
- Adaptive questioning: changing the next question based on earlier performance
- Weak-area tracking: remembering categories that scored below the threshold
- Score extraction: reading the numeric score back from the LLM response with a regex
- Report generation: building a readable markdown session summary from accumulated turns

### Frontend and browser recording

The browser UI in `index.html` uses the MediaRecorder API to capture audio and send it to the backend.

Concepts used here:

- Browser media capture: recording microphone input directly in the page
- Multipart form upload: sending audio files to Flask endpoints
- Client-server separation: keeping recording in the frontend and evaluation in the backend
- Lightweight UI flow: start session, record answer, submit, and receive feedback

### Knowledge base files

The retrieval layer reads markdown files from `data/kb/`, currently including interview coaching tips.

Why markdown is used:

- It is easy to edit
- It is easy to version control
- It works well as human-readable source material for retrieval

### Generated data and local artifacts

The project creates a few local-only outputs during use:

- `data/audio/` stores uploaded recordings
- `data/models/` stores Whisper model downloads
- `data/faiss_index/` stores the saved retrieval index

These are intentionally ignored so the GitHub repo stays clean and lightweight.

## Project Structure

- `src/app.py` - Flask routes and session orchestration
- `src/asr.py` - Audio transcription with Faster-Whisper
- `src/rag.py` - Local retrieval index over the knowledge base
- `src/evaluate.py` - Groq prompt construction and scoring
- `src/questions.py` - Small built-in question bank
- `src/session.py` - Interview flow, weak-area tracking, and report generation
- `index.html` - Browser UI and recording logic
- `data/kb/` - Markdown knowledge base used by retrieval
- `data/audio/` - Uploaded audio files during a session
- `data/models/` - Cached Whisper model files
- `data/faiss_index/` - Saved local retrieval index

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a local `.env` file in the project root with your Groq key:

```bash
GROQ_API_KEY=your_key_here
```

Build the local retrieval index, then start the app:

```bash
python3 src/rag.py
cd src
python3 app.py
```

Open `http://localhost:5000` in your browser.

## Interview Flow

1. Start a session from the UI.
2. Listen to the question and record your answer.
3. Submit the audio.
4. The backend transcribes the answer.
5. The retrieval layer finds relevant coaching material.
6. Groq scores the response and generates feedback.
7. The session logic decides the next question.
8. After the configured number of questions, the app returns a session report.

## API Endpoints

### `POST /transcribe`

Uploads audio and returns a transcript.

### `POST /session/start`

Starts a new session and returns the first question.

### `POST /session/answer`

Submits an answer, returns feedback, and either the next question or a final report.

### `GET /health`

Returns a simple `{"status": "ok"}` response for health checks.

## Configuration Notes

- `.env` is ignored by `.gitignore`, so your API key stays local
- `WHISPER_MODEL` can be set to change the Whisper model name, with `tiny.en` as the default
- `max_questions=4` in `src/app.py` controls session length
- Scores below 6 are treated as weak areas in `src/session.py`

## GitHub Notes

- Commit the source code, question bank, knowledge base, and this README
- Do not commit `.env`
- Do not commit generated audio, model cache files, or the retrieval index if you want a clean repository
