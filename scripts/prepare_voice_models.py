"""Download both local inference models. Run from the repository root."""
import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend" if (ROOT / "backend" / "app").is_dir() else ROOT
sys.path.insert(0, str(BACKEND))
from app.config import get_settings
from app.services.speaker_command import SPEAKER_MODEL_NAME


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models-dir", type=Path, default=BACKEND / "data" / "models")
    args = parser.parse_args()
    target = args.models_dir.resolve()
    target.mkdir(parents=True, exist_ok=True)
    speaker = target / SPEAKER_MODEL_NAME
    if not speaker.is_file():
        print("Downloading speaker model (~27 MB)...", flush=True)
        temporary = target / (SPEAKER_MODEL_NAME + ".part")
        urllib.request.urlretrieve(get_settings().speaker_model_url, temporary)
        temporary.replace(speaker)
    print(f"Speaker: {speaker}")


if __name__ == "__main__":
    main()
