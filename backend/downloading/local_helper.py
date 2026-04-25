import argparse
import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def compute_signature(payload: dict, key: str) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(
        key.encode("utf-8"),
        serialized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def load_job(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Unable to read payload file: {exc}") from exc


def validate_job(job: dict):
    payload = job.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Invalid payload format: missing payload object")

    required = ["url", "type", "format", "expiresAt"]
    for key in required:
        if key not in payload:
            raise ValueError(f"Invalid payload format: missing {key}")

    if int(payload.get("expiresAt", 0)) < int(time.time()):
        raise ValueError("Payload expired. Generate a new local-job payload.")

    return payload


def maybe_verify_signature(job: dict, signing_key: str | None):
    if not signing_key:
        print("Warning: signature verification skipped (no --signing-key provided).")
        return

    payload = job.get("payload", {})
    expected = compute_signature(payload, signing_key)
    provided = str(job.get("signature", "")).strip()
    if not provided or not hmac.compare_digest(expected, provided):
        raise ValueError("Signature mismatch. Refusing to run download.")


def run_download(payload: dict, browser: str | None):
    command = ["yt-dlp", "-f", payload["format"]]
    if browser:
        command.extend(["--cookies-from-browser", browser])
    command.append(payload["url"])

    print("Running:", " ".join(command))
    subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser(
        description="Run YouTube download locally using a signed backend payload."
    )
    parser.add_argument("--payload-file", required=True, help="Path to payload json file")
    parser.add_argument(
        "--signing-key",
        default=os.environ.get("YT_LOCAL_HELPER_SIGNING_KEY", ""),
        help="Optional HMAC key to verify backend signature",
    )
    parser.add_argument(
        "--cookies-from-browser",
        default="",
        help="Optional browser name for local cookies (chrome/firefox/edge/etc)",
    )
    args = parser.parse_args()

    job = load_job(Path(args.payload_file))
    payload = validate_job(job)
    maybe_verify_signature(job, args.signing_key.strip() or None)

    try:
        run_download(payload, args.cookies_from_browser.strip() or None)
    except subprocess.CalledProcessError as exc:
        print(f"Download failed with exit code {exc.returncode}")
        sys.exit(exc.returncode)


if __name__ == "__main__":
    main()
