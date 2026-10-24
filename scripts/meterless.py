"""
meterless.py: Connect Archus to the Meterless Runtime provider.

  python scripts/meterless.py status            # online / unauthorized / offline (+ token field when unauthorized)
  python scripts/meterless.py detect            # Auto Detect on 127.0.0.1, localhost, [::1] x 8088, 8090, 8787, 11434
  python scripts/meterless.py connect [URL]     # a base URL in any form, or a connect link (asked hidden when omitted)
  python scripts/meterless.py token             # paste the token (hidden input; or pipe it with --stdin)
  python scripts/meterless.py models            # routing modes served by the runtime
  python scripts/meterless.py mode [ID]         # show or save the routing mode (e.g. meterless/deep)
  python scripts/meterless.py chat "Say hello"  # plain text request on meterless/auto (or --model)

The token and connect-link key are stored in data/provider_settings.json (gitignored) and never printed.
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.adapters.meterless_runtime import (  # noqa: E402
    MeterlessModeError,
    MeterlessRuntimeProvider,
    MeterlessTokenError,
    TOKEN_KEY,
)


def show(result: dict) -> None:
    print(json.dumps(result, indent=2))


NO_PROMPT = False


def ask_token(provider: MeterlessRuntimeProvider, from_stdin: bool = False) -> bool:
    """The token field: hidden input, validated, stored under meterless_runtime_token."""
    if from_stdin:
        value = sys.stdin.readline()
    elif NO_PROMPT:
        print(f"Unauthorized: paste the token with `python scripts/meterless.py token` ({TOKEN_KEY}).")
        return False
    elif sys.stdin.isatty():
        value = getpass.getpass(f"Paste the Meterless Runtime token ({TOKEN_KEY}): ")
    else:
        return False
    try:
        provider.set_token(value)
    except MeterlessTokenError as e:
        print(f"Token not saved: {e}")
        return False
    print("Token saved.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-prompt", action="store_true", help="never ask for input (scripts, CI)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("detect")
    p_connect = sub.add_parser("connect")
    p_connect.add_argument("url", nargs="?", help="base URL or connect link (omit to type it hidden)")
    p_token = sub.add_parser("token")
    p_token.add_argument("--stdin", action="store_true", help="read the token from stdin instead of a prompt")
    sub.add_parser("models")
    p_mode = sub.add_parser("mode")
    p_mode.add_argument("mode", nargs="?", help="routing mode to save, e.g. meterless/deep (omit to show)")
    p_chat = sub.add_parser("chat")
    p_chat.add_argument("text")
    p_chat.add_argument("--model", default=None, help="routing mode for this message (default: the saved mode)")
    args = parser.parse_args()
    global NO_PROMPT
    NO_PROMPT = args.no_prompt

    provider = MeterlessRuntimeProvider()

    if args.command == "status":
        result = provider.status()
        show(result)
        if result["status"] == "unauthorized" and ask_token(provider):
            show(provider.status())
        return 0 if provider.status()["status"] == "online" else 1

    if args.command == "detect":
        hit = provider.auto_detect()
        if hit is None:
            print("Auto Detect: no Meterless Runtime found on 127.0.0.1, localhost or [::1] (ports 8088, 8090, 8787, 11434).")
            return 1
        print(f"Auto Detect: found {hit['base_url']} ({hit['status']}), saved.")
        show(hit)
        if hit["status"] == "unauthorized":
            ask_token(provider)
        return 0

    if args.command == "connect":
        if not args.url and NO_PROMPT:
            print("connect needs a URL or connect link when --no-prompt is set.")
            return 1
        pasted = args.url or getpass.getpass("Paste the base URL or connect link: ")
        result = provider.connect(pasted)  # a connect link's key is stored, never echoed
        show(result)
        if result["status"] == "unauthorized" and ask_token(provider):
            show(provider.status())
        return 0 if provider.status()["status"] in ("online", "unauthorized") else 1

    if args.command == "token":
        if not ask_token(provider, from_stdin=args.stdin):
            return 1
        show(provider.status())
        return 0

    if args.command == "models":
        show({"base_url": provider.base_url, "models": provider.list_models()})
        return 0

    if args.command == "mode":
        if not args.mode:
            show({"model": provider.model})
            return 0
        try:
            result = provider.set_model(args.mode)
        except MeterlessModeError as e:
            print(e)
            return 1
        show(result)
        if result["offered_by_runtime"] is False:
            print("Saved, but the runtime doesn't list this mode right now; it may route it anyway.")
        return 0

    if args.command == "chat":
        model = args.model or provider.model
        try:
            reply = provider.chat_completion([{"role": "user", "content": args.text}], model=model)
        except (MeterlessTokenError, MeterlessModeError) as e:
            print(e)
            return 1
        print(f"[{model}] {type(reply).__name__}: {reply}")
        return 0 if isinstance(reply, str) else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
