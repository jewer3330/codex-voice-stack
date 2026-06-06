#!/usr/bin/env python3
"""Thin Codex CLI wrapper around RealtimeSTT.

The wrapper keeps the local assistant workflow small:

- `listen-once` captures one utterance and exits.
- `listen-loop` keeps a wake phrase loop alive until stopped by the caller.
- `setup` installs the Python runtime into a service-owned venv.

Runtime files live under CODEX_SERVER_ROOT/codex-voice-listener by default.
"""

from __future__ import annotations

import argparse
import inspect
import json
import logging
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_WAKE_PHRASES = ("小莫", "小莫小莫", "小茉", "茉茉")
DEFAULT_MODEL = "base"
DEFAULT_LANGUAGE = "zh"
DEFAULT_TIMEOUT_SECONDS = 12.0
DEFAULT_PET_REPLY = "小莫在。"


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def default_server_root() -> Path:
    return Path(os.environ.get("CODEX_SERVER_ROOT", default_codex_home() / "servers")).expanduser()


def default_listener_home() -> Path:
    return Path(
        os.environ.get(
            "CODEX_VOICE_LISTENER_HOME",
            default_server_root() / "codex-voice-listener",
        )
    ).expanduser()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_runtime_dirs(home: Path) -> dict[str, Path]:
    dirs = {
        "home": home,
        "data": home / "data",
        "logs": home / "logs",
        "models": home / "models",
        "tmp": home / "tmp",
        "venv": home / ".venv",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def write_state(home: Path, **payload: Any) -> None:
    state = {
        "updatedAt": now_iso(),
        **payload,
    }
    state_path = home / "data" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def split_csv(value: str | None, fallback: tuple[str, ...]) -> list[str]:
    if not value:
        return list(fallback)
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize_text(text: str) -> str:
    table = str.maketrans(
        {
            "，": "",
            "。": "",
            "！": "",
            "？": "",
            ",": "",
            ".": "",
            "!": "",
            "?": "",
            " ": "",
            "\t": "",
            "\n": "",
            "語": "语",
            "聽": "听",
            "聲": "声",
            "嗎": "吗",
            "這": "这",
            "個": "个",
            "麼": "么",
            "開": "开",
            "關": "关",
        }
    )
    return text.translate(table).lower()


def phrase_in_text(text: str, phrases: list[str]) -> str | None:
    normalized = normalize_text(text)
    for phrase in phrases:
        if normalize_text(phrase) in normalized:
            return phrase
    return None


def strip_wake_phrase(text: str, phrase: str | None, phrases: list[str]) -> str:
    cleaned = text.strip()
    candidates = [phrase] if phrase else []
    candidates.extend(item for item in phrases if item not in candidates)
    for candidate in candidates:
        if not candidate:
            continue
        cleaned = cleaned.replace(candidate, "", 1)
    return cleaned.strip(" ，。,.!?！？")


def find_python_for_setup(explicit: str | None) -> str:
    candidates = []
    if explicit:
        candidates.append(explicit)
    candidates.extend(
        [
            os.environ.get("CODEX_VOICE_LISTENER_PYTHON", ""),
            "python3.12",
            "python3.11",
            "python3",
            "python",
        ]
    )
    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        resolved = shutil.which(candidate) if os.sep not in candidate else candidate
        if not resolved:
            continue
        result = subprocess.run(
            [
                resolved,
                "-c",
                "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return resolved
    raise SystemExit(
        "codex-voice-listener-setup: Python 3.11+ is required. "
        "Install python3.11/python3.12 first, or set CODEX_VOICE_LISTENER_PYTHON."
    )


def venv_python(home: Path) -> Path:
    if platform.system().lower().startswith("win"):
        return home / ".venv" / "Scripts" / "python.exe"
    return home / ".venv" / "bin" / "python"


def run_checked(args: list[str], *, env: dict[str, str] | None = None) -> None:
    printable = " ".join(args)
    print(f"+ {printable}", flush=True)
    subprocess.run(args, env=env, check=True)


def macos_portaudio_env() -> dict[str, str]:
    env = os.environ.copy()
    if platform.system() != "Darwin":
        return env
    prefixes: list[str] = []
    try:
        result = subprocess.run(
            ["brew", "--prefix", "portaudio"],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            prefixes.append(result.stdout.strip())
    except FileNotFoundError:
        pass
    prefixes.extend(["/opt/homebrew/opt/portaudio", "/usr/local/opt/portaudio"])
    for prefix in prefixes:
        root = Path(prefix)
        header = root / "include" / "portaudio.h"
        if not header.exists():
            continue
        include = str(root / "include")
        lib = str(root / "lib")
        pkgconfig = str(root / "lib" / "pkgconfig")
        env["CPPFLAGS"] = f"-I{include} {env.get('CPPFLAGS', '')}".strip()
        env["CFLAGS"] = f"-I{include} {env.get('CFLAGS', '')}".strip()
        env["LDFLAGS"] = f"-L{lib} {env.get('LDFLAGS', '')}".strip()
        env["PKG_CONFIG_PATH"] = f"{pkgconfig}:{env.get('PKG_CONFIG_PATH', '')}".rstrip(":")
        break
    return env


def install_realtimestt(py: Path, packages: list[str]) -> None:
    env = macos_portaudio_env()
    try:
        run_checked([str(py), "-m", "pip", "install", *packages], env=env)
    except subprocess.CalledProcessError as exc:
        if platform.system() == "Darwin":
            raise SystemExit(
                "RealtimeSTT install failed. On macOS this is commonly caused by missing PortAudio.\n"
                "Install it with: brew install portaudio\n"
                "Then rerun: codex-voice-listener-setup"
            ) from exc
        raise


def cmd_setup(args: argparse.Namespace) -> int:
    home = default_listener_home()
    paths = ensure_runtime_dirs(home)
    python_bin = find_python_for_setup(args.python)
    py = venv_python(home)

    if not py.exists() or args.recreate:
        if paths["venv"].exists() and args.recreate:
            shutil.rmtree(paths["venv"])
        run_checked([python_bin, "-m", "venv", str(paths["venv"])])

    packages = [
        "RealtimeSTT[faster-whisper]",
    ]
    if args.extra:
        packages.extend(args.extra)

    run_checked([str(py), "-m", "pip", "install", "--upgrade", "pip", "wheel", "setuptools"])
    install_realtimestt(py, packages)

    write_state(
        home,
        status="setup-ok",
        python=str(py),
        packages=packages,
        home=str(home),
    )
    print(f"codex voice listener runtime ready: {home}")
    return 0


def import_recorder() -> Any:
    try:
        from RealtimeSTT import AudioToTextRecorder
    except ImportError as exc:
        raise SystemExit(
            "RealtimeSTT is not installed for this Python. Run codex-voice-listener-setup first."
        ) from exc
    return AudioToTextRecorder


def recorder_log_level(value: str) -> int:
    if value.isdigit():
        return int(value)
    return int(getattr(logging, value.upper(), logging.WARNING))


def recorder_config(args: argparse.Namespace, home: Path) -> dict[str, Any]:
    config: dict[str, Any] = {
        "model": args.model,
        "language": args.language,
        "download_root": str(home / "models"),
        "compute_type": args.compute_type,
        "spinner": args.spinner,
        "use_microphone": True,
        "post_speech_silence_duration": args.post_speech_silence_duration,
        "min_length_of_recording": args.min_length_of_recording,
        "webrtc_sensitivity": args.webrtc_sensitivity,
        "silero_sensitivity": args.silero_sensitivity,
        "silero_use_onnx": args.silero_use_onnx,
        "level": recorder_log_level(args.log_level),
        "no_log_file": True,
    }
    if args.realtime:
        config.update(
            {
                "enable_realtime_transcription": True,
                "realtime_model_type": args.realtime_model,
            }
        )
    if args.backend:
        config["transcription_engine"] = args.backend
    if args.initial_prompt:
        config["initial_prompt"] = args.initial_prompt
    return config


def filter_recorder_config(AudioToTextRecorder: Any, config: dict[str, Any]) -> dict[str, Any]:
    try:
        signature = inspect.signature(AudioToTextRecorder)
    except (TypeError, ValueError):
        return config
    parameters = signature.parameters
    if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()):
        return config
    allowed = set(parameters)
    return {key: value for key, value in config.items() if key in allowed}


def listen_once(args: argparse.Namespace, *, home: Path, recorder: Any | None = None) -> str:
    AudioToTextRecorder = import_recorder()
    config = filter_recorder_config(AudioToTextRecorder, recorder_config(args, home))
    write_state(home, status="listening-once", model=args.model, language=args.language)
    append_jsonl(
        home / "data" / "events.jsonl",
        {"time": now_iso(), "event": "listen-once-start", "model": args.model, "language": args.language},
    )

    started = time.monotonic()
    text = ""
    try:
        if recorder is not None:
            if args.prompt:
                print(args.prompt, flush=True)
            text = recorder.text()
        else:
            with AudioToTextRecorder(**config) as local_recorder:
                if args.prompt:
                    print(args.prompt, flush=True)
                text = local_recorder.text()
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        write_state(home, status="error", error=str(exc))
        append_jsonl(
            home / "data" / "events.jsonl",
            {"time": now_iso(), "event": "error", "where": "listen-once", "error": str(exc)},
        )
        raise

    elapsed = round(time.monotonic() - started, 3)
    text = (text or "").strip()
    write_state(home, status="idle", lastText=text, elapsedSeconds=elapsed)
    append_jsonl(
        home / "data" / "events.jsonl",
        {"time": now_iso(), "event": "transcript", "mode": "once", "text": text, "elapsedSeconds": elapsed},
    )
    return text


def speak(text: str, args: argparse.Namespace) -> None:
    if args.no_say or not text.strip():
        return
    command = args.say_command or os.environ.get("CODEX_VOICE_LISTENER_SAY_COMMAND")
    if not command:
        command = str(default_codex_home() / "bin" / "codex-pet-say")
    executable = shutil.which(command) if os.sep not in command else command
    if not executable or not Path(executable).exists():
        print(f"say command not found: {command}", file=sys.stderr)
        return
    subprocess.run([executable, text], check=False)


def notify_qq(text: str, args: argparse.Namespace) -> None:
    if args.no_qq or not text.strip():
        return
    command = args.qq_command or os.environ.get("CODEX_VOICE_LISTENER_QQ_COMMAND")
    if not command:
        command = str(default_codex_home() / "bin" / "codex-qq-notify")
    executable = shutil.which(command) if os.sep not in command else command
    if not executable or not Path(executable).exists():
        print(f"qq notify command not found: {command}", file=sys.stderr)
        return
    subprocess.run([executable, text], check=False)


def run_codex(prompt: str, args: argparse.Namespace, home: Path) -> str:
    command = args.codex_command or os.environ.get("CODEX_VOICE_LISTENER_CODEX_COMMAND", "codex")
    codex_bin = shutil.which(command) if os.sep not in command else command
    if not codex_bin:
        raise SystemExit(f"codex command not found: {command}")

    cwd = Path(args.codex_cwd or os.environ.get("CODEX_VOICE_LISTENER_CODEX_CWD", Path.home())).expanduser()
    cwd.mkdir(parents=True, exist_ok=True)
    output_path = home / "data" / "last-codex-reply.txt"
    full_prompt = args.codex_prompt_template.format(text=prompt)
    cmd = [
        codex_bin,
        "exec",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        str(cwd),
        "-o",
        str(output_path),
    ]
    if args.codex_model:
        cmd.extend(["-m", args.codex_model])
    cmd.append(full_prompt)

    append_jsonl(home / "data" / "events.jsonl", {"time": now_iso(), "event": "codex-start", "text": prompt})
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    append_jsonl(
        home / "data" / "events.jsonl",
        {
            "time": now_iso(),
            "event": "codex-exit",
            "returncode": result.returncode,
            "stdoutTail": result.stdout[-1000:],
            "stderrTail": result.stderr[-1000:],
        },
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"codex exited {result.returncode}")
    if output_path.exists():
        reply = output_path.read_text(encoding="utf-8").strip()
    else:
        reply = result.stdout.strip()
    return reply


def handle_transcript(text: str, args: argparse.Namespace, home: Path, *, wake_phrase: str | None = None) -> None:
    text = text.strip()
    if not text:
        return
    user_text = strip_wake_phrase(text, wake_phrase, split_csv(args.wake_phrases, DEFAULT_WAKE_PHRASES))
    if not user_text:
        user_text = text

    append_jsonl(
        home / "data" / "events.jsonl",
        {"time": now_iso(), "event": "command", "text": user_text, "rawText": text, "wakePhrase": wake_phrase},
    )

    if args.dispatch == "none":
        print(user_text, flush=True)
        return
    if args.dispatch == "say":
        speak(args.reply or DEFAULT_PET_REPLY, args)
        return
    if args.dispatch == "qq":
        notify_qq(user_text, args)
        return
    if args.dispatch == "codex":
        reply = run_codex(user_text, args, home)
        print(reply, flush=True)
        write_state(home, status="idle", lastText=user_text, lastReply=reply)
        if args.reply:
            speak(args.reply.format(text=user_text, reply=reply), args)
        else:
            speak(reply, args)
        if args.qq:
            notify_qq(reply, args)
        return
    raise SystemExit(f"unknown dispatch mode: {args.dispatch}")


def cmd_listen_once(args: argparse.Namespace) -> int:
    home = default_listener_home()
    ensure_runtime_dirs(home)
    text = listen_once(args, home=home)
    if args.json:
        print(json.dumps({"text": text, "time": now_iso()}, ensure_ascii=False), flush=True)
    else:
        print(text, flush=True)
    if args.dispatch != "none":
        handle_transcript(text, args, home)
    return 0


def cmd_listen_loop(args: argparse.Namespace) -> int:
    home = default_listener_home()
    ensure_runtime_dirs(home)
    phrases = split_csv(args.wake_phrases, DEFAULT_WAKE_PHRASES)
    stop = False
    AudioToTextRecorder = import_recorder()
    config = filter_recorder_config(AudioToTextRecorder, recorder_config(args, home))

    def _stop(_signum: int, _frame: Any) -> None:
        nonlocal stop
        stop = True
        write_state(home, status="stopping")

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    write_state(home, status="listening-loop", wakePhrases=phrases, model=args.model, language=args.language)
    append_jsonl(
        home / "data" / "events.jsonl",
        {"time": now_iso(), "event": "listen-loop-start", "wakePhrases": phrases},
    )
    print(f"codex voice listener started; wake phrases: {', '.join(phrases)}", flush=True)

    with AudioToTextRecorder(**config) as recorder:
        while not stop:
            try:
                text = listen_once(args, home=home, recorder=recorder)
            except KeyboardInterrupt:
                break
            except Exception as exc:
                append_jsonl(home / "data" / "events.jsonl", {"time": now_iso(), "event": "loop-error", "error": str(exc)})
                print(f"listen error: {exc}", file=sys.stderr, flush=True)
                time.sleep(args.error_sleep)
                continue

            matched = phrase_in_text(text, phrases)
            if not matched:
                append_jsonl(
                    home / "data" / "events.jsonl",
                    {"time": now_iso(), "event": "ignored", "text": text},
                )
                continue

            append_jsonl(
                home / "data" / "events.jsonl",
                {"time": now_iso(), "event": "wake", "text": text, "wakePhrase": matched},
            )
            write_state(home, status="awake", lastText=text, wakePhrase=matched)
            handle_transcript(text, args, home, wake_phrase=matched)

    write_state(home, status="stopped")
    append_jsonl(home / "data" / "events.jsonl", {"time": now_iso(), "event": "listen-loop-stop"})
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    home = default_listener_home()
    paths = ensure_runtime_dirs(home)
    py = venv_python(home)
    checks: list[dict[str, Any]] = [
        {"name": "home", "ok": home.exists(), "value": str(home)},
        {"name": "venv-python", "ok": py.exists(), "value": str(py)},
        {"name": "codex", "ok": shutil.which("codex") is not None, "value": shutil.which("codex")},
        {"name": "pet-say", "ok": (default_codex_home() / "bin" / "codex-pet-say").exists(), "value": str(default_codex_home() / "bin" / "codex-pet-say")},
    ]
    try:
        import_recorder()
        checks.append({"name": "RealtimeSTT-import", "ok": True, "value": "ok"})
    except SystemExit as exc:
        checks.append({"name": "RealtimeSTT-import", "ok": False, "value": str(exc)})

    payload = {
        "home": str(home),
        "paths": {key: str(value) for key, value in paths.items()},
        "checks": checks,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    hard_checks = {"home", "codex", "pet-say"}
    return 0 if all(item["ok"] for item in checks if item["name"] in hard_checks) else 1


def add_recorder_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default=os.environ.get("CODEX_VOICE_LISTENER_MODEL", DEFAULT_MODEL))
    parser.add_argument("--language", default=os.environ.get("CODEX_VOICE_LISTENER_LANGUAGE", DEFAULT_LANGUAGE))
    parser.add_argument("--backend", default=os.environ.get("CODEX_VOICE_LISTENER_BACKEND", ""))
    parser.add_argument("--compute-type", default=os.environ.get("CODEX_VOICE_LISTENER_COMPUTE_TYPE", "int8"))
    parser.add_argument("--initial-prompt", default=os.environ.get("CODEX_VOICE_LISTENER_INITIAL_PROMPT", "普通话语音，常见词包括小莫、小莫小莫、Codex、QQ、画图、语音、天气。"))
    parser.add_argument("--prompt", default=os.environ.get("CODEX_VOICE_LISTENER_PROMPT", "请说话..."))
    parser.add_argument("--post-speech-silence-duration", type=float, default=float(os.environ.get("CODEX_VOICE_LISTENER_POST_SILENCE", "0.8")))
    parser.add_argument("--min-length-of-recording", type=float, default=float(os.environ.get("CODEX_VOICE_LISTENER_MIN_RECORDING", "0.5")))
    parser.add_argument("--webrtc-sensitivity", type=int, default=int(os.environ.get("CODEX_VOICE_LISTENER_WEBRTC_SENSITIVITY", "3")))
    parser.add_argument("--silero-sensitivity", type=float, default=float(os.environ.get("CODEX_VOICE_LISTENER_SILERO_SENSITIVITY", "0.4")))
    parser.add_argument("--silero-use-onnx", action="store_true", default=os.environ.get("CODEX_VOICE_LISTENER_SILERO_ONNX", "0") == "1")
    parser.add_argument("--spinner", action=argparse.BooleanOptionalAction, default=os.environ.get("CODEX_VOICE_LISTENER_SPINNER", "0") == "1")
    parser.add_argument("--realtime", action="store_true", default=os.environ.get("CODEX_VOICE_LISTENER_REALTIME", "0") == "1")
    parser.add_argument("--realtime-model", default=os.environ.get("CODEX_VOICE_LISTENER_REALTIME_MODEL", "tiny"))
    parser.add_argument("--log-level", default=os.environ.get("CODEX_VOICE_LISTENER_LOG_LEVEL", "WARNING"))


def add_dispatch_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dispatch", choices=["none", "say", "qq", "codex"], default=os.environ.get("CODEX_VOICE_LISTENER_DISPATCH", "none"))
    parser.add_argument("--reply", default=os.environ.get("CODEX_VOICE_LISTENER_REPLY", ""))
    parser.add_argument("--say-command", default=os.environ.get("CODEX_VOICE_LISTENER_SAY_COMMAND", ""))
    parser.add_argument("--qq", action="store_true", default=os.environ.get("CODEX_VOICE_LISTENER_QQ", "0") == "1")
    parser.add_argument("--no-say", action="store_true", default=os.environ.get("CODEX_VOICE_LISTENER_NO_SAY", "0") == "1")
    parser.add_argument("--no-qq", action="store_true", default=os.environ.get("CODEX_VOICE_LISTENER_NO_QQ", "0") == "1")
    parser.add_argument("--qq-command", default=os.environ.get("CODEX_VOICE_LISTENER_QQ_COMMAND", ""))
    parser.add_argument("--codex-command", default=os.environ.get("CODEX_VOICE_LISTENER_CODEX_COMMAND", ""))
    parser.add_argument("--codex-cwd", default=os.environ.get("CODEX_VOICE_LISTENER_CODEX_CWD", ""))
    parser.add_argument("--codex-model", default=os.environ.get("CODEX_VOICE_LISTENER_CODEX_MODEL", ""))
    parser.add_argument(
        "--codex-prompt-template",
        default=os.environ.get(
            "CODEX_VOICE_LISTENER_CODEX_PROMPT_TEMPLATE",
            "用户通过本机语音说：{text}\n请直接完成或简短回答。需要本机说话时，用可用的语音工具。",
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex_realtimestt_listener.py")
    sub = parser.add_subparsers(dest="command", required=True)

    setup = sub.add_parser("setup", help="Create the RealtimeSTT runtime venv.")
    setup.add_argument("--python", default="")
    setup.add_argument("--recreate", action="store_true")
    setup.add_argument("--extra", action="append", default=[])
    setup.set_defaults(func=cmd_setup)

    doctor = sub.add_parser("doctor", help="Show local runtime diagnostics.")
    doctor.set_defaults(func=cmd_doctor)

    once = sub.add_parser("listen-once", help="Listen for one utterance and exit.")
    add_recorder_options(once)
    add_dispatch_options(once)
    once.add_argument("--json", action="store_true")
    once.set_defaults(func=cmd_listen_once)

    loop = sub.add_parser("listen-loop", help="Listen continuously and dispatch after a wake phrase.")
    add_recorder_options(loop)
    add_dispatch_options(loop)
    loop.add_argument("--wake-phrases", default=os.environ.get("CODEX_VOICE_LISTENER_WAKE_PHRASES", ",".join(DEFAULT_WAKE_PHRASES)))
    loop.add_argument("--error-sleep", type=float, default=float(os.environ.get("CODEX_VOICE_LISTENER_ERROR_SLEEP", "2")))
    loop.set_defaults(func=cmd_listen_loop)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
