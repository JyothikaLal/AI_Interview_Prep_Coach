import os
from groq import Groq
from dotenv import load_dotenv
from rag import load_retriever

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
_client = None
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

def _get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def evaluate_answer(question: str, answer: str) -> str:
    docs = retriever.invoke(question)
    context = "\n\n".join(d.page_content for d in docs)
    prompt = EVAL_PROMPT.format(question=question, answer=answer, context=context)
    response = _get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content
