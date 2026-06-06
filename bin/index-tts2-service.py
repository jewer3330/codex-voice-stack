#!/usr/bin/env python3
"""Small local HTTP service for a warmed IndexTTS2 model."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
import uuid
import wave
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse


DEFAULT_CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path(__file__).resolve().parents[1]))
DEFAULT_SERVER_ROOT = Path(os.environ.get("CODEX_SERVER_ROOT", Path.home() / ".codex" / "servers"))
DEFAULT_VOICE_TTS_HOME = Path(os.environ.get("VOICE_TTS_HOME", DEFAULT_SERVER_ROOT / "voice-tts"))
DEFAULT_INDEX_REPO = str(Path(os.environ.get("INDEX_TTS_REPO", DEFAULT_CODEX_HOME / "bin/index-tts")))
DEFAULT_MODEL_DIR = str(Path(os.environ.get("INDEX_TTS2_MODEL_DIR", DEFAULT_VOICE_TTS_HOME / "models/IndexTeam/IndexTTS-2")))
DEFAULT_OUTPUT_DIR = str(Path(os.environ.get("INDEX_TTS2_OUTPUT_DIR", DEFAULT_VOICE_TTS_HOME / "outputs/index-tts2")))
DEFAULT_PROMPT = str(Path(os.environ.get("INDEX_TTS2_DEFAULT_PROMPT", DEFAULT_VOICE_TTS_HOME / "samples/daguanjia_kokoro_zf021_v2.wav")))
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 49231


def main() -> int:
    args = parse_args()
    validate_paths(args)
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    print(
        json.dumps(
            {
                "event": "loading",
                "engine": "indextts2",
                "model_dir": args.model_dir,
                "index_repo": args.index_repo,
                "host": args.host,
                "port": args.port,
                "started_at": utc_now(),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    os.chdir(args.index_repo)
    sys.path.insert(0, args.index_repo)
    sys.path.insert(0, str(Path(args.index_repo) / "indextts"))

    from indextts.infer_v2 import IndexTTS2

    tts = IndexTTS2(
        cfg_path=str(Path(args.model_dir) / "config.yaml"),
        model_dir=args.model_dir,
        use_fp16=args.fp16,
        device=args.device,
        use_cuda_kernel=args.cuda_kernel,
        use_deepspeed=args.deepspeed,
        use_accel=args.accel,
        use_torch_compile=args.torch_compile,
    )

    state = ServiceState(args=args, tts=tts)
    handler = build_handler(state)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    server.daemon_threads = True

    print(
        json.dumps(
            {
                "event": "ready",
                "engine": "indextts2",
                "device": getattr(tts, "device", None),
                "pid": os.getpid(),
                "health": f"http://{args.host}:{args.port}/health",
                "ready_at": utc_now(),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


class ServiceState:
    def __init__(self, args: argparse.Namespace, tts: object) -> None:
        self.args = args
        self.tts = tts
        self.lock = Lock()
        self.started_at = utc_now()
        self.request_count = 0


def build_handler(state: ServiceState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "IndexTTS2Service/0.1"

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self.send_json(
                    {
                        "ok": True,
                        "engine": "indextts2",
                        "device": getattr(state.tts, "device", None),
                        "pid": os.getpid(),
                        "started_at": state.started_at,
                        "request_count": state.request_count,
                        "model_dir": state.args.model_dir,
                        "default_prompt": state.args.default_prompt,
                    }
                )
                return
            self.send_json({"ok": False, "error": "not found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/synthesize":
                self.send_json({"ok": False, "error": "not found"}, status=404)
                return

            try:
                payload = self.read_json()
                response = synthesize(state, payload)
                self.send_json(response)
            except ClientError as error:
                self.send_json({"ok": False, "error": str(error)}, status=error.status)
            except Exception as error:  # pragma: no cover - logged for service diagnostics
                traceback.print_exc()
                self.send_json({"ok": False, "error": str(error)}, status=500)

        def read_json(self) -> dict:
            length = int(self.headers.get("content-length", "0"))
            if length <= 0:
                raise ClientError("empty request body", status=400)
            if length > 1_000_000:
                raise ClientError("request body too large", status=413)
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as error:
                raise ClientError(f"invalid json: {error}", status=400) from error
            if not isinstance(payload, dict):
                raise ClientError("json body must be an object", status=400)
            return payload

        def send_json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            if state.args.verbose:
                print(f"{self.address_string()} - {fmt % args}", flush=True)

    return Handler


def synthesize(state: ServiceState, payload: dict) -> dict:
    text = str(payload.get("text", "")).strip()
    if not text:
        raise ClientError("text is required", status=400)
    if len(text) > state.args.max_chars:
        raise ClientError(f"text is too long; max {state.args.max_chars} chars", status=400)

    prompt_path = str(payload.get("prompt_path") or state.args.default_prompt)
    if not Path(prompt_path).is_file():
        raise ClientError(f"prompt audio not found: {prompt_path}", status=400)

    output_path = resolve_output_path(state.args.output_dir, payload.get("output_path"))
    emo_audio_prompt = payload.get("emo_audio_prompt")
    if emo_audio_prompt is not None and not Path(str(emo_audio_prompt)).is_file():
        raise ClientError(f"emotion audio not found: {emo_audio_prompt}", status=400)

    emo_alpha = coerce_float(payload.get("emo_alpha", 1.0), "emo_alpha")
    max_segment_tokens = coerce_int(
        payload.get("max_text_tokens_per_segment", state.args.max_text_tokens_per_segment),
        "max_text_tokens_per_segment",
    )
    use_emo_text = bool(payload.get("use_emo_text", False))
    use_random = bool(payload.get("use_random", False))
    emo_text = payload.get("emo_text")
    emo_vector = coerce_emo_vector(payload.get("emo_vector"))
    generation_kwargs = coerce_generation_kwargs(payload)

    request_id = uuid.uuid4().hex[:12]
    started_at = utc_now()
    started = time.perf_counter()
    print(
        json.dumps(
            {
                "event": "request",
                "request_id": request_id,
                "chars": len(text),
                "prompt_path": prompt_path,
                "output_path": str(output_path),
                "started_at": started_at,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    with state.lock:
        state.request_count += 1
        result = state.tts.infer(
            spk_audio_prompt=prompt_path,
            text=text,
            output_path=str(output_path),
            emo_audio_prompt=str(emo_audio_prompt) if emo_audio_prompt else None,
            emo_alpha=emo_alpha,
            emo_vector=emo_vector,
            use_emo_text=use_emo_text,
            emo_text=str(emo_text) if emo_text else None,
            use_random=use_random,
            verbose=state.args.verbose,
            max_text_tokens_per_segment=max_segment_tokens,
            **generation_kwargs,
        )

    elapsed = time.perf_counter() - started
    duration = wav_duration(output_path)
    print(
        json.dumps(
            {
                "event": "complete",
                "request_id": request_id,
                "elapsed_sec": round(elapsed, 3),
                "duration_sec": round(duration, 3) if duration is not None else None,
                "result": result,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    return {
        "ok": True,
        "engine": "indextts2",
        "request_id": request_id,
        "output_path": str(output_path),
        "duration_sec": duration,
        "elapsed_sec": elapsed,
        "started_at": started_at,
        "finished_at": utc_now(),
    }


class ClientError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def resolve_output_path(output_dir: str, raw: object) -> Path:
    base = Path(output_dir).resolve()
    if raw:
        candidate = Path(str(raw))
        if not candidate.is_absolute():
            candidate = base / candidate
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        candidate = base / f"tts-{stamp}-{uuid.uuid4().hex[:8]}.wav"

    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(base)
    except ValueError as error:
        raise ClientError(f"output_path must stay under {base}", status=400) from error
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def coerce_float(value: object, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ClientError(f"{name} must be a number", status=400) from error


def coerce_int(value: object, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ClientError(f"{name} must be an integer", status=400) from error


def coerce_emo_vector(value: object) -> list[float] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 8:
        raise ClientError("emo_vector must be an array of 8 numbers", status=400)
    return [coerce_float(item, "emo_vector") for item in value]


def coerce_generation_kwargs(payload: dict) -> dict:
    specs = {
        "do_sample": bool,
        "top_p": float,
        "top_k": int,
        "temperature": float,
        "length_penalty": float,
        "num_beams": int,
        "repetition_penalty": float,
        "max_mel_tokens": int,
    }
    kwargs = {}
    for key, caster in specs.items():
        if key not in payload:
            continue
        try:
            kwargs[key] = caster(payload[key])
        except (TypeError, ValueError) as error:
            raise ClientError(f"{key} has invalid value", status=400) from error
    return kwargs


def wav_duration(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
        return frames / rate if rate else None
    except (FileNotFoundError, wave.Error):
        return None


def validate_paths(args: argparse.Namespace) -> None:
    index_repo = Path(args.index_repo)
    model_dir = Path(args.model_dir)
    if not index_repo.is_dir():
        raise SystemExit(f"IndexTTS repo not found: {index_repo}")
    for filename in ("bpe.model", "gpt.pth", "config.yaml", "s2mel.pth", "wav2vec2bert_stats.pt"):
        required = model_dir / filename
        if not required.is_file():
            raise SystemExit(f"required model file missing: {required}")
    if not Path(args.default_prompt).is_file():
        raise SystemExit(f"default prompt audio missing: {args.default_prompt}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a warmed IndexTTS2 model over localhost HTTP.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--index-repo", default=DEFAULT_INDEX_REPO)
    parser.add_argument("--model-dir", default=DEFAULT_MODEL_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--default-prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--device", default=None, help="Override torch device, e.g. cpu, mps, cuda:0.")
    parser.add_argument("--fp16", action="store_true")
    parser.add_argument("--deepspeed", action="store_true")
    parser.add_argument("--cuda-kernel", action="store_true")
    parser.add_argument("--accel", action="store_true")
    parser.add_argument("--torch-compile", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--max-chars", type=int, default=800)
    parser.add_argument("--max-text-tokens-per-segment", type=int, default=80)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
