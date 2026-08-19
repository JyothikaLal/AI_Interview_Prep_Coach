import os
from pathlib import Path

from faster_whisper import WhisperModel

_model = None
ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_CACHE_DIR = ROOT_DIR / "data" / "models"
MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Use a smaller default model to keep first-run downloads faster on CPU machines.
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "tiny.en")


def _get_model():
    global _model
    if _model is None:
        _model = WhisperModel(
            WHISPER_MODEL_NAME,
            device="cpu",
            compute_type="int8",
            download_root=str(MODEL_CACHE_DIR),
        )
    return _model


def transcribe(audio_path: str) -> str:
    segments, _ = _get_model().transcribe(audio_path, beam_size=5)
    return " ".join(seg.text.strip() for seg in segments)


if __name__ == "__main__":
    print(transcribe("data/audio/test.wav"))
