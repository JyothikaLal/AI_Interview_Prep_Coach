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
