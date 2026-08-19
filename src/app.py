from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from asr import transcribe
from session import InterviewSession
import os

app = Flask(__name__)
ROOT_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = ROOT_DIR / "data" / "audio"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Session management
sessions = {}


@app.route("/", methods=["GET"])
def home():
    """Serve the frontend application."""
    return send_from_directory(ROOT_DIR, "index.html")

@app.route("/transcribe", methods=["POST"])
def transcribe_endpoint():
    """Endpoint to transcribe audio"""
    audio_file = request.files["audio"]
    path = os.path.join(UPLOAD_DIR, audio_file.filename)
    audio_file.save(path)
    return jsonify({"transcript": transcribe(path)})

@app.route("/session/start", methods=["POST"])
def start_session():
    """Start a new interview session"""
    session_id = "demo"
    sessions[session_id] = InterviewSession(max_questions=4)
    next_q = sessions[session_id]._pick_next_question()
    return jsonify({"session_id": session_id, "next_question": next_q["text"]})

@app.route("/session/answer", methods=["POST"])
def answer():
    """Submit an answer to a question"""
    try:
        session_id = request.form["session_id"]
        if session_id not in sessions:
            return jsonify({"error": "Session not found. Please start a new session."}), 400

        audio_file = request.files["audio"]
        path = os.path.join(UPLOAD_DIR, audio_file.filename)
        audio_file.save(path)

        session = sessions[session_id]
        result = session.run_turn(path)

        if session.is_complete():
            return jsonify({"done": True, "last_result": result, "report": session.generate_report()})

        next_q = session._pick_next_question()
        return jsonify({"done": False, "last_result": result, "next_question": next_q["text"] if next_q else None})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=False, use_reloader=False, port=5000)
