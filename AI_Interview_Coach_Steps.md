# AI Interview Prep Coach — Step-by-Step Build (Granular)

## Step 1: Set up project folders
```bash
mkdir ai-interview-coach && cd ai-interview-coach
mkdir data data/audio data/kb src
```

## Step 2: Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

## Step 3: Install dependencies
```bash
pip install faster-whisper flask langchain langchain-community \
    langgraph sentence-transformers faiss-cpu chromadb \
    groq python-dotenv pypdf
```

## Step 4: Get a Groq API key
Sign up free at console.groq.com, create a key, then:
```bash
echo "GROQ_API_KEY=your_key_here" > .env
```
(Alternative: install Ollama and run `ollama pull llama3.1:8b` if you'd rather not depend on an external API.)

## Step 5: Confirm Whisper downloads and loads correctly
```bash
python3 -c "from faster_whisper import WhisperModel; m = WhisperModel('small'); print('Whisper OK')"
```

## Step 6: Record test audio
Record 4–5 short (30–60 sec) answers to common interview questions on your phone/laptop mic. Save as `.wav`/`.mp3` in `data/audio/`. Use your real project talking points (e.g. SmartVision Gate) as content — this becomes your test set for the whole build.

## Step 7: Write the ASR function
Create `src/asr.py`:
```python
from faster_whisper import WhisperModel

model = WhisperModel("small", device="cpu", compute_type="int8")

def transcribe(audio_path: str) -> str:
    segments, info = model.transcribe(audio_path, beam_size=5)
    return " ".join(seg.text.strip() for seg in segments)

if __name__ == "__main__":
    print(transcribe("data/audio/test.wav"))
```
Run it, confirm the transcript is accurate.

## Step 8: Build a minimal Flask app around ASR
Create `src/app.py`:
```python
from flask import Flask, request, jsonify
from asr import transcribe
import os

app = Flask(__name__)
UPLOAD_DIR = "data/audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/transcribe", methods=["POST"])
def transcribe_endpoint():
    audio_file = request.files["audio"]
    path = os.path.join(UPLOAD_DIR, audio_file.filename)
    audio_file.save(path)
    return jsonify({"transcript": transcribe(path)})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
```

## Step 9: Test the ASR endpoint
```bash
curl -X POST -F "audio=@data/audio/test.wav" http://localhost:5000/transcribe
```
✅ Checkpoint: audio in, clean transcript out. Commit to git.

---

## Step 10: Write your interview knowledge base
Create `data/kb/interview_tips.md` with: the STAR method, common ML/CV interview question categories, good vs. bad answer examples, and a rubric for what a strong project-deep-dive answer should mention (data pipeline, model choice justification, metrics, tradeoffs). 2000–5000 words is plenty.

## Step 11: Chunk and index the knowledge base
Create `src/rag.py`:
```python
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

KB_DIR = "data/kb"
INDEX_DIR = "data/faiss_index"

def build_index():
    loader = DirectoryLoader(KB_DIR, glob="**/*.md", loader_cls=TextLoader)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    FAISS.from_documents(chunks, embeddings).save_local(INDEX_DIR)
    print(f"Indexed {len(chunks)} chunks.")

def load_retriever(k=3):
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
    return vectorstore.as_retriever(search_kwargs={"k": k})

if __name__ == "__main__":
    build_index()
```

## Step 12: Build the FAISS index
```bash
python3 src/rag.py
```

## Step 13: Write the LLM evaluation function (grounded in retrieval)
Create `src/evaluate.py`:
```python
import os
from groq import Groq
from dotenv import load_dotenv
from rag import load_retriever

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
retriever = load_retriever()

EVAL_PROMPT = """You are an expert technical interview coach.

Interview question: {question}
Candidate's answer (transcribed from speech): {answer}

Relevant coaching material:
{context}

Evaluate the answer using the coaching material above. Give:
1. A score out of 10
2. What was strong
3. What was missing or weak
4. One specific suggestion to improve"""

def evaluate_answer(question: str, answer: str) -> str:
    docs = retriever.invoke(question)
    context = "\n\n".join(d.page_content for d in docs)
    prompt = EVAL_PROMPT.format(question=question, answer=answer, context=context)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content
```

## Step 14: Test retrieval + evaluation together
```bash
python3 -c "
from src.evaluate import evaluate_answer
print(evaluate_answer('Tell me about a challenging project.', 'I built a gesture-controlled music player using MediaPipe and OpenCV.'))
"
```
✅ Checkpoint: feedback is specific and references your knowledge base content, not generic LLM opinion. Commit to git.

---

## Step 15: Define your question bank
Create `src/questions.py`:
```python
QUESTION_BANK = [
    {"id": "q1", "category": "behavioral", "text": "Tell me about a challenging project you worked on."},
    {"id": "q2", "category": "technical", "text": "Walk me through how you'd design a real-time object detection pipeline."},
    {"id": "q3", "category": "project", "text": "Explain a tradeoff you made in one of your ML projects."},
    {"id": "q4", "category": "behavioral", "text": "Describe a time you had to learn something quickly under a deadline."},
]
```

## Step 16: Write the session/agent logic
Create `src/session.py` — this is the piece that makes decisions (which question to ask next) based on accumulated performance, which is what makes it "agentic":
```python
import re
from evaluate import evaluate_answer
from asr import transcribe
from questions import QUESTION_BANK

class InterviewSession:
    def __init__(self, max_questions=4):
        self.max_questions = max_questions
        self.asked_ids = []
        self.records = []
        self.weak_categories = []

    def _pick_next_question(self):
        remaining = [q for q in QUESTION_BANK if q["id"] not in self.asked_ids]
        if not remaining:
            return None
        if self.weak_categories:
            prioritized = [q for q in remaining if q["category"] in self.weak_categories]
            return prioritized[0] if prioritized else remaining[0]
        return remaining[0]

    def _extract_score(self, feedback_text):
        match = re.search(r"(\d+)\s*/\s*10", feedback_text)
        return int(match.group(1)) if match else None

    def run_turn(self, audio_path):
        question = self._pick_next_question()
        if question is None:
            return None

        transcript = transcribe(audio_path)
        feedback = evaluate_answer(question["text"], transcript)
        score = self._extract_score(feedback)

        self.asked_ids.append(question["id"])
        self.records.append({
            "question": question["text"], "category": question["category"],
            "transcript": transcript, "feedback": feedback, "score": score,
        })

        if score is not None and score < 6 and question["category"] not in self.weak_categories:
            self.weak_categories.append(question["category"])

        return {"question": question["text"], "transcript": transcript, "feedback": feedback, "score": score}

    def is_complete(self):
        return len(self.asked_ids) >= self.max_questions or self._pick_next_question() is None

    def generate_report(self):
        scored = [r["score"] for r in self.records if r["score"]]
        avg_score = sum(scored) / max(1, len(scored))
        weak = ", ".join(self.weak_categories) if self.weak_categories else "None identified"
        report = f"# Interview Session Report\n\nQuestions answered: {len(self.records)}\nAverage score: {avg_score:.1f}/10\nWeak areas: {weak}\n\n"
        for i, r in enumerate(self.records, 1):
            report += f"## Q{i}: {r['question']}\n**Your answer:** {r['transcript']}\n\n**Feedback:** {r['feedback']}\n\n---\n\n"
        return report
```

## Step 17: Add session endpoints to Flask
Append to `src/app.py`:
```python
from session import InterviewSession

sessions = {}

@app.route("/session/start", methods=["POST"])
def start_session():
    session_id = "demo"
    sessions[session_id] = InterviewSession(max_questions=4)
    next_q = sessions[session_id]._pick_next_question()
    return jsonify({"session_id": session_id, "next_question": next_q["text"]})

@app.route("/session/answer", methods=["POST"])
def answer():
    session_id = request.form["session_id"]
    audio_file = request.files["audio"]
    path = os.path.join(UPLOAD_DIR, audio_file.filename)
    audio_file.save(path)

    session = sessions[session_id]
    result = session.run_turn(path)

    if session.is_complete():
        return jsonify({"done": True, "last_result": result, "report": session.generate_report()})
    next_q = session._pick_next_question()
    return jsonify({"done": False, "last_result": result, "next_question": next_q["text"]})
```

## Step 18: Run a full end-to-end session test
```bash
curl -X POST http://localhost:5000/session/start
curl -X POST -F "session_id=demo" -F "audio=@data/audio/answer1.wav" http://localhost:5000/session/answer
# repeat with answer2.wav, answer3.wav, answer4.wav
```
Confirm: giving a deliberately weak technical answer causes the next technical question to be prioritized, and the final response includes a full report.

✅ **Checkpoint: full pipeline works end to end.** Commit to git.

## Step 19: Build a minimal frontend (optional but nice for demos)
A single `index.html` with the browser's `MediaRecorder` API to record audio, POST to `/session/answer`, and display feedback + next question. Keep this small — 1–2 hours max.

## Step 20: Write the README
Include the architecture diagram, setup steps, and a sample report screenshot. Push to GitHub.

---

## Docker — should you use it?

**Short answer: yes, but scope it to "runs cleanly for a demo/interview," not production-grade deployment.** It's genuinely worth doing here for two reasons specific to your project:

1. **Whisper + FAISS + sentence-transformers have finicky dependencies** (ffmpeg, torch, C++ build tools for some packages). Docker means "it works on my machine" becomes "it works, period" — useful if you demo this on a different laptop or during an interview screen-share.
2. **It's a resume/interview talking point** — "containerized the app" is a legitimate, expected skill for ML engineer roles, and it's low effort to add given you already have a working app.

### Where Docker fits in the plan
Add this as **Step 21**, after everything works locally:

**Step 21: Containerize the app**

Create `Dockerfile` in the project root:
```dockerfile
FROM python:3.11-slim

# ffmpeg is required by faster-whisper for audio decoding
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY data/kb/ ./data/kb/

WORKDIR /app/src
EXPOSE 5000
CMD ["python3", "app.py"]
```

Create `requirements.txt` (freeze what you installed in Step 3):
```bash
pip freeze > requirements.txt
```

Build and run:
```bash
docker build -t interview-coach .
docker run -p 5000:5000 --env-file .env interview-coach
```

**One important gotcha:** the FAISS index (`data/faiss_index/`) needs to either be built inside the container (run `python3 rag.py` as part of the image build, or as an entrypoint step) or mounted in as a volume. Simplest fix — add this line to the Dockerfile before `CMD`:
```dockerfile
RUN python3 src/rag.py
```
This bakes the index into the image so it doesn't need to be rebuilt on every container start.

**Should you use `docker-compose`?** Only if you want to run this as multiple services (e.g., Flask app + Ollama as a separate container instead of using the Groq API). For a single Flask container calling an external Groq API, plain `docker run` is enough — don't over-engineer this part given your timeline.

**What NOT to bother with in 4 days:** Kubernetes, multi-stage optimized builds, GPU passthrough for Whisper. These are legitimate next steps to *mention* as "future scaling" in your README, but implementing them now would eat time better spent making the core pipeline solid.
