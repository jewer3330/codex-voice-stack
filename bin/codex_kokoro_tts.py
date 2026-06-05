#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from kokoro import KModel, KPipeline


REPO_ID = "hexgrad/Kokoro-82M-v1.1-zh"
SAMPLE_RATE = 24000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate QQ-compatible WAV speech with Kokoro.")
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--voice", default="zf_017")
    parser.add_argument("--speed", type=float, default=0.98)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit("text is empty")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = KModel(repo_id=REPO_ID).to(device).eval()
    en_pipeline = KPipeline(lang_code="a", repo_id=REPO_ID, model=False)

    def en_callable(value: str) -> str:
        try:
            return next(en_pipeline(value)).phonemes
        except StopIteration:
            return ""

    zh_pipeline = KPipeline(
        lang_code="z",
        repo_id=REPO_ID,
        model=model,
        en_callable=en_callable,
    )

    chunks = []
    for result in zh_pipeline(text, voice=args.voice, speed=args.speed):
        if result.audio is not None:
            chunks.append(result.audio.detach().cpu().numpy())

    if not chunks:
        raise SystemExit("no audio generated")

    audio = np.concatenate(chunks)
    sf.write(out_path, audio, SAMPLE_RATE)
    print(out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
