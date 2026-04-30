import mimetypes
import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET

YOUTUBE_ID_PATTERN = re.compile(r"^[0-9A-Za-z_-]{11}$")
DEFAULT_VIDEO_QUALITIES = ["144p", "240p", "360p", "480p", "720p", "1080p"]
DEFAULT_AUDIO_QUALITIES = ["64 kbps", "128 kbps", "192 kbps", "320 kbps"]

# Supported browsers for cookie extraction
SUPPORTED_BROWSERS = ["chrome", "firefox", "brave", "edge", "safari", "chromium"]
BROWSER_COOKIE_MISSING_MARKERS = (
    "could not find chrome cookies database",
    "could not find firefox cookies database",
    "could not find edge cookies database",
    "could not find brave cookies database",
    "could not find chromium cookies database",
    "could not copy chrome cookie database",
    "could not copy firefox cookie database",
    "failed to decrypt",
)
AUTH_REQUIRED_MARKERS = (
    "sign in to confirm you're not a bot",
    "sign in to confirm youre not a bot",
    "confirm you're not a bot",
    "confirm youre not a bot",
    "use --cookies-from-browser or --cookies for the authentication",
    "--cookies-from-browser",
    "--cookies for the authentication",
    "login required",
    "this video is unavailable",
    "age-restricted",
    "members-only",
    "private video",
)
SIGNED_PAYLOAD_TTL_SECONDS = 600
YT_DLP_COOKIE_HELP_URL = "https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp"
YT_DLP_COOKIE_EXPORT_URL = "https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies"


# ✅ LOAD yt-dlp
def _load_yt_dlp():
    try:
        import yt_dlp
    except ImportError:
        return None
    return yt_dlp


# ✅ COOKIE PATH FIX (IMPORTANT)
def get_cookie_path():
    app_dir = Path(__file__).resolve().parent
    project_dir = app_dir.parent

    # Highest priority: runtime cookie content from env (useful on Render).
    cookie_content_b64 = os.environ.get("YT_DL_COOKIES_B64", "").strip()
    if cookie_content_b64:
        try:
            decoded = base64.b64decode(cookie_content_b64).decode("utf-8")
            temp_dir = Path(tempfile.mkdtemp())
            temp_cookie = temp_dir / "cookies.txt"
            temp_cookie.write_text(decoded, encoding="utf-8")
            if temp_cookie.stat().st_size > 0:
                print("🍪 Using cookies from YT_DL_COOKIES_B64")
                return str(temp_cookie)
        except Exception as e:
            print(f"⚠️ Failed to decode YT_DL_COOKIES_B64: {e}")

    cookie_content_raw = os.environ.get("YT_DL_COOKIES_RAW", "").strip()
    if cookie_content_raw:
        temp_dir = Path(tempfile.mkdtemp())
        temp_cookie = temp_dir / "cookies.txt"
        temp_cookie.write_text(cookie_content_raw, encoding="utf-8")
        if temp_cookie.stat().st_size > 0:
            print("🍪 Using cookies from YT_DL_COOKIES_RAW")
            return str(temp_cookie)

    env_cookie_path = os.environ.get("YT_DL_COOKIES_FILE", "").strip()
    if env_cookie_path:
        original = Path(env_cookie_path).expanduser()
    else:
        # Prefer project root path documented in README/AUTH guide.
        original = project_dir / "cookies.txt"

    if not original.exists():
        # Backward compatibility: older setups may have placed cookies in app dir.
        legacy_path = app_dir / "cookies.txt"
        if legacy_path.exists():
            original = legacy_path
        else:
            print("❌ cookies.txt NOT FOUND:", original)
            return None

    # Check if cookies.txt has content
    if original.stat().st_size == 0:
        print("⚠️ cookies.txt is empty, trying browser extraction...")
        return None

    temp_dir = Path(tempfile.mkdtemp())
    temp_cookie = temp_dir / "cookies.txt"

    shutil.copy(original, temp_cookie)
    return str(temp_cookie)


# ✅ BROWSER COOKIE EXTRACTION (Solves "Sign in to confirm you're not a bot")
def get_browser_cookies():
    """
    Extract cookies from browser to authenticate with YouTube.
    This solves the bot verification issue by using real browser session cookies.
    
    Note: This only works for local development where a browser is running.
    For production servers (Render, Vercel, etc.), use cookies.txt file instead.
    
    Environment variables to configure:
    - YT_DL_BROWSER: Browser name (chrome, firefox, brave, edge, safari, chromium)
    - YT_DL_BROWSER_PROFILE: Browser profile name (optional, defaults to default profile)
    """
    browser = os.environ.get("YT_DL_BROWSER", "").lower().strip()

    # In hosted environments (Render, Railway, etc.) browser DBs are usually absent.
    # Only attempt browser extraction there when explicitly configured.
    is_hosted = bool(
        os.environ.get("RENDER")
        or os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("K_SERVICE")
    )
    if is_hosted and not browser:
        print("⚠️ Hosted environment detected; skipping browser cookies. Use cookies.txt.")
        return None

    if not browser:
        # Local default
        browser = "chrome"
        print(f"🔍 Auto-detected browser: {browser}")
    
    if browser not in SUPPORTED_BROWSERS:
        print(f"⚠️ Unsupported browser: {browser}. Supported: {SUPPORTED_BROWSERS}")
        return None
    
    profile = os.environ.get("YT_DL_BROWSER_PROFILE", "").strip()
    
    # Check if we're in a headless/production environment
    # Browser cookies only work when a browser is actually running
    import sys
    if not hasattr(sys, 'real_prefix') and not os.path.exists(os.path.expanduser("~")):
        print("⚠️ No browser available in this environment. Use cookies.txt instead.")
        return None
    
    # yt-dlp Python API expects a tuple for cookiesfrombrowser.
    # Format: (browser, profile, keyring, container)
    cookies_from_browser = (browser, profile or None, None, None)
    
    print(f"🔑 Using browser cookies from: {browser}" + (f" profile: {profile}" if profile else ""))
    return cookies_from_browser


def _build_auth_opts():
    auth_opts = {}
    browser_cookies = get_browser_cookies()
    cookie_path = get_cookie_path()

    # Browser cookies first, then static cookies file.
    if browser_cookies:
        auth_opts["cookiesfrombrowser"] = browser_cookies
        print(f"🔑 Using browser cookies: {browser_cookies}")
    elif cookie_path:
        auth_opts["cookiefile"] = cookie_path
        print(f"🍪 Using cookies file: {cookie_path}")
    else:
        print("⚠️ No authentication method available - attempting without cookies")

    return auth_opts, browser_cookies, cookie_path


def _is_browser_cookie_runtime_error(error_msg: str) -> bool:
    text = _normalize_error_text(error_msg)
    if "_parse_browser_specification" in text:
        return True
    return any(marker in text for marker in BROWSER_COOKIE_MISSING_MARKERS)


def _requires_authentication(error_msg: str) -> bool:
    text = _normalize_error_text(error_msg)
    return any(marker in text for marker in AUTH_REQUIRED_MARKERS)


def _normalize_error_text(value: str) -> str:
    text = (value or "").lower()
    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()


def _auth_required_response(raw_error: str, browser_cookies=None, cookie_path=None):
    return JsonResponse({
        "error": (
            "YouTube authentication is required for this video. "
            "Set YT_DL_BROWSER (local) or provide YT_DL_COOKIES_B64/RAW/FILE, then retry."
        ),
        "details": raw_error,
        "requiresCookies": True,
        "authContext": {
            "browserConfigured": bool(browser_cookies),
            "cookieFileConfigured": bool(cookie_path),
        },
        "cookieHints": [
            "Local machine: set YT_DL_BROWSER=chrome (or firefox/brave/edge) and keep browser signed in to YouTube.",
            "Hosted backend: provide cookies via YT_DL_COOKIES_B64, YT_DL_COOKIES_RAW, or YT_DL_COOKIES_FILE.",
        ],
        "docs": [YT_DLP_COOKIE_HELP_URL, YT_DLP_COOKIE_EXPORT_URL],
    }, status=400)


def _extract_video_id(url: str) -> str:
    text = (url or "").strip()
    match = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11})(?:[?&]|$)", text)
    return match.group(1) if match else ""


def _parse_quality_value(quality: str, download_type: str):
    if download_type == "video":
        match = re.match(r"^(\d{3,4})p$", quality)
    else:
        match = re.match(r"^(\d{2,3})\s*kbps$", quality.lower())
    return int(match.group(1)) if match else None


def _selector_for(download_type: str, quality_value):
    return _selector_for_with_merge(download_type, quality_value, can_merge_streams=True)


def _selector_for_with_merge(download_type: str, quality_value, can_merge_streams: bool):
    if download_type == "audio":
        return (
            f"bestaudio[abr<={quality_value}]/bestaudio/best"
            if quality_value else "bestaudio/best"
        )

    if can_merge_streams:
        if quality_value is None:
            return "bestvideo+bestaudio/best"
        return (
            f"bestvideo[height<={quality_value}]+bestaudio/"
            f"best[height<={quality_value}]"
        )

    # Fallback for environments without ffmpeg: prefer pre-muxed video+audio.
    if quality_value is None:
        return "best[vcodec!=none][acodec!=none]/best"
    return (
        f"best[height<={quality_value}][vcodec!=none][acodec!=none]/"
        "best[vcodec!=none][acodec!=none]/best"
    )


def _payload_signature(payload: dict, secret: str) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(
        secret.encode("utf-8"),
        serialized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _local_helper_signing_secret() -> str:
    return (
        os.environ.get("YT_LOCAL_HELPER_SIGNING_KEY", "").strip()
        or settings.SECRET_KEY
    )


def _collect_qualities(info: dict, include_video_only: bool = True):
    formats = info.get("formats", [])

    video_vals = sorted({
        int(f["height"]) for f in formats
        if (
            f.get("vcodec") != "none"
            and f.get("height")
            and (include_video_only or f.get("acodec") != "none")
        )
    })

    audio_vals = sorted({
        int(round(float(f["abr"]))) for f in formats
        if f.get("acodec") != "none" and f.get("abr")
    })

    return (
        [f"{v}p" for v in video_vals] or DEFAULT_VIDEO_QUALITIES,
        [f"{a} kbps" for a in audio_vals] or DEFAULT_AUDIO_QUALITIES,
    )


def _ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg"))


def _resolve_downloaded_file(info: dict, ydl, temp_dir: Path):
    candidates = []

    def _add_candidate(path_value):
        if not path_value:
            return
        candidate = Path(path_value)
        if not candidate.is_absolute():
            candidate = temp_dir / candidate
        candidates.append(candidate)

    _add_candidate(info.get("filepath"))
    _add_candidate(info.get("_filename"))

    for item in info.get("requested_downloads") or []:
        if isinstance(item, dict):
            _add_candidate(item.get("filepath"))
            _add_candidate(item.get("_filename"))

    for item in info.get("requested_formats") or []:
        if isinstance(item, dict):
            _add_candidate(item.get("filepath"))
            _add_candidate(item.get("_filename"))

    try:
        _add_candidate(ydl.prepare_filename(info))
    except Exception:
        pass

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    fallback_files = sorted(
        [path for path in temp_dir.iterdir() if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return fallback_files[0] if fallback_files else None


def _stream_file_and_cleanup(file_path: Path, temp_dir: Path):
    try:
        with file_path.open("rb") as f:
            while chunk := f.read(8192):
                yield chunk
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ✅ HEALTH API
@require_GET
def health_view(_):
    return JsonResponse({"ok": True})


@require_GET
def local_job_view(request):
    url = request.GET.get("url", "").strip()
    dtype = request.GET.get("type", "video").strip().lower()
    quality = request.GET.get("quality", "").strip()

    video_id = _extract_video_id(url)
    if not YOUTUBE_ID_PATTERN.match(video_id):
        return JsonResponse({"error": "Invalid YouTube URL"}, status=400)

    if dtype not in {"video", "audio"}:
        return JsonResponse({"error": "Invalid download type"}, status=400)

    qval = _parse_quality_value(quality, dtype)
    selector = _selector_for(dtype, qval)

    now = int(time.time())
    payload = {
        "url": url,
        "type": dtype,
        "quality": quality,
        "format": selector,
        "videoId": video_id,
        "issuedAt": now,
        "expiresAt": now + SIGNED_PAYLOAD_TTL_SECONDS,
    }

    signature = _payload_signature(payload, _local_helper_signing_secret())

    return JsonResponse({
        "payload": payload,
        "signature": signature,
        "algorithm": "HMAC-SHA256",
        "ttlSeconds": SIGNED_PAYLOAD_TTL_SECONDS,
    })


# ✅ INFO API
@require_GET
def info_view(request):
    yt_dlp = _load_yt_dlp()
    if not yt_dlp:
        return JsonResponse({"error": "yt-dlp not installed"}, status=500)

    url = request.GET.get("url", "").strip()
    video_id = _extract_video_id(url)

    if not YOUTUBE_ID_PATTERN.match(video_id):
        return JsonResponse({"error": "Invalid YouTube URL"}, status=400)

    base_opts = {
        "quiet": False,  # Enable output for debugging
        "no_warnings": False,
        "skip_download": True,
        "noplaylist": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-us,en;q=0.5",
            "Sec-Fetch-Mode": "navigate",
        },
    }
    auth_opts, browser_cookies, cookie_path = _build_auth_opts()
    print(f"🔍 Debug: cookie_path={cookie_path}, browser_cookies={browser_cookies}")

    try:
        # First attempt without cookies. This works for many public videos.
        with yt_dlp.YoutubeDL(base_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        first_error = str(e)
        if not _requires_authentication(first_error):
            return JsonResponse({"error": first_error}, status=400)

        # Fallback: retry with auth only when needed.
        if not auth_opts:
            return _auth_required_response(first_error, browser_cookies, cookie_path)

        print("⚠️ Auth likely required, retrying with cookies...")
        auth_retry_opts = dict(base_opts)
        auth_retry_opts.update(auth_opts)
        try:
            with yt_dlp.YoutubeDL(auth_retry_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e2:
            second_error = str(e2)
            if _is_browser_cookie_runtime_error(second_error) and browser_cookies:
                print("⚠️ Browser cookie runtime error, retrying with cookie file/without browser cookies...")
                auth_retry_opts.pop("cookiesfrombrowser", None)
                if cookie_path:
                    auth_retry_opts["cookiefile"] = cookie_path
                try:
                    with yt_dlp.YoutubeDL(auth_retry_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                except Exception as e3:
                    final_error = str(e3)
                    if _requires_authentication(final_error):
                        return _auth_required_response(final_error, browser_cookies, cookie_path)
                    return JsonResponse({"error": final_error}, status=400)
            else:
                if _requires_authentication(second_error):
                    return _auth_required_response(second_error, browser_cookies, cookie_path)
                return JsonResponse({"error": second_error}, status=400)

    can_merge_streams = _ffmpeg_available()
    vq, aq = _collect_qualities(info, include_video_only=can_merge_streams)

    return JsonResponse({
        "videoId": video_id,
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "videoQualities": vq,
        "audioQualities": aq,
        "videoMergeAvailable": can_merge_streams,
    })


# ✅ DOWNLOAD API
@require_GET
def download_view(request):
    yt_dlp = _load_yt_dlp()
    if not yt_dlp:
        return JsonResponse({"error": "yt-dlp not installed"}, status=500)

    url = request.GET.get("url", "").strip()
    dtype = request.GET.get("type", "video").strip().lower()
    quality = request.GET.get("quality", "").strip()

    video_id = _extract_video_id(url)
    if not YOUTUBE_ID_PATTERN.match(video_id):
        return JsonResponse({"error": "Invalid URL"}, status=400)

    if dtype not in {"video", "audio"}:
        return JsonResponse({"error": "Invalid download type"}, status=400)

    qval = _parse_quality_value(quality, dtype)
    can_merge_streams = _ffmpeg_available()
    selector = _selector_for_with_merge(
        dtype,
        qval,
        can_merge_streams=can_merge_streams,
    )

    temp_dir = Path(tempfile.mkdtemp())
    output = str(temp_dir / "%(title)s.%(ext)s")

    # Authentication options are used only as fallback.
    auth_opts, browser_cookies, cookie_path = _build_auth_opts()

    base_opts = {
        "outtmpl": output,
        "format": selector,
        "quiet": False,  # Enable output for debugging
        "no_warnings": False,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-us,en;q=0.5",
            "Sec-Fetch-Mode": "navigate",
        },
    }

    print(f"🔍 Debug (download): cookie_path={cookie_path}, browser_cookies={browser_cookies}")

    try:
        # First attempt without cookies for public videos.
        with yt_dlp.YoutubeDL(base_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = _resolve_downloaded_file(info, ydl, temp_dir)
    except Exception as e:
        first_error = str(e)
        if not _requires_authentication(first_error):
            shutil.rmtree(temp_dir, ignore_errors=True)
            return JsonResponse({"error": first_error}, status=400)

        if not auth_opts:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return _auth_required_response(first_error, browser_cookies, cookie_path)

        print("⚠️ Auth likely required for download, retrying with cookies...")
        auth_retry_opts = dict(base_opts)
        auth_retry_opts.update(auth_opts)
        try:
            with yt_dlp.YoutubeDL(auth_retry_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = _resolve_downloaded_file(info, ydl, temp_dir)
        except Exception as e2:
            second_error = str(e2)
            if _is_browser_cookie_runtime_error(second_error) and browser_cookies:
                print("⚠️ Browser cookie runtime error, retrying with cookie file/without browser cookies...")
                auth_retry_opts.pop("cookiesfrombrowser", None)
                if cookie_path:
                    auth_retry_opts["cookiefile"] = cookie_path
                try:
                    with yt_dlp.YoutubeDL(auth_retry_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        file_path = _resolve_downloaded_file(info, ydl, temp_dir)
                except Exception as e3:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    final_error = str(e3)
                    if _requires_authentication(final_error):
                        return _auth_required_response(final_error, browser_cookies, cookie_path)
                    return JsonResponse({"error": final_error}, status=400)
            else:
                shutil.rmtree(temp_dir, ignore_errors=True)
                if _requires_authentication(second_error):
                    return _auth_required_response(second_error, browser_cookies, cookie_path)
                return JsonResponse({"error": second_error}, status=400)

    if not file_path:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JsonResponse(
            {"error": "Download completed but output file could not be located."},
            status=500,
        )

    response = StreamingHttpResponse(
        _stream_file_and_cleanup(file_path, temp_dir),
        content_type=mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    )

    response["Content-Disposition"] = f"attachment; filename={quote(file_path.name)}"
    return response
