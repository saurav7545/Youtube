import mimetypes
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET

YOUTUBE_ID_PATTERN = re.compile(r"^[0-9A-Za-z_-]{11}$")
DEFAULT_VIDEO_QUALITIES = ["144p", "240p", "360p", "480p", "720p", "1080p"]
DEFAULT_AUDIO_QUALITIES = ["64 kbps", "128 kbps", "192 kbps", "320 kbps"]

# Supported browsers for cookie extraction
SUPPORTED_BROWSERS = ["chrome", "firefox", "brave", "edge", "safari", "chromium"]


# ✅ LOAD yt-dlp
def _load_yt_dlp():
    try:
        import yt_dlp
    except ImportError:
        return None
    return yt_dlp


# ✅ COOKIE PATH FIX (IMPORTANT)
def get_cookie_path():
    base_dir = Path(__file__).resolve().parent
    original = base_dir / "cookies.txt"

    if not original.exists():
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
    
    Environment variables to configure:
    - YT_DL_BROWSER: Browser name (chrome, firefox, brave, edge, safari, chromium)
    - YT_DL_BROWSER_PROFILE: Browser profile name (optional, defaults to default profile)
    """
    browser = os.environ.get("YT_DL_BROWSER", "").lower().strip()
    
    if not browser:
        # Try to auto-detect browser based on platform
        import sys
        if sys.platform == "darwin":  # macOS
            browser = "chrome"
        elif sys.platform == "win32":  # Windows
            browser = "chrome"
        else:  # Linux
            browser = "chrome"
    
    if browser not in SUPPORTED_BROWSERS:
        print(f"⚠️ Unsupported browser: {browser}. Supported: {SUPPORTED_BROWSERS}")
        return None
    
    profile = os.environ.get("YT_DL_BROWSER_PROFILE", "")
    
    # Build cookies_from_browser parameter as a tuple
    # yt-dlp expects: (browser_name, profile_path, keyring, container)
    # We only provide browser_name and optionally profile
    cookies_from_browser = (browser, profile) if profile else browser
    
    print(f"🔑 Using browser cookies from: {browser}" + (f" profile: {profile}" if profile else ""))
    return cookies_from_browser


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
    if download_type == "audio":
        return (
            f"bestaudio[abr<={quality_value}]/bestaudio/best"
            if quality_value else "bestaudio/best"
        )

    if quality_value is None:
        return "bestvideo+bestaudio/best"

    return (
        f"bestvideo[height<={quality_value}]+bestaudio/"
        f"best[height<={quality_value}]"
    )


def _collect_qualities(info: dict):
    formats = info.get("formats", [])

    video_vals = sorted({
        int(f["height"]) for f in formats
        if f.get("vcodec") != "none" and f.get("height")
    })

    audio_vals = sorted({
        int(round(float(f["abr"]))) for f in formats
        if f.get("acodec") != "none" and f.get("abr")
    })

    return (
        [f"{v}p" for v in video_vals] or DEFAULT_VIDEO_QUALITIES,
        [f"{a} kbps" for a in audio_vals] or DEFAULT_AUDIO_QUALITIES,
    )


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

    # Try multiple authentication methods in order of preference:
    # 1. Browser cookies (most reliable for YouTube)
    # 2. cookies.txt file
    cookie_path = get_cookie_path()
    browser_cookies = get_browser_cookies()

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "http_headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
    }

    # Prefer browser cookies for YouTube (solves bot verification)
    if browser_cookies:
        opts["cookiesfrombrowser"] = browser_cookies
    elif cookie_path:
        opts["cookiefile"] = cookie_path

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    vq, aq = _collect_qualities(info)

    return JsonResponse({
        "videoId": video_id,
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "videoQualities": vq,
        "audioQualities": aq,
    })


# ✅ DOWNLOAD API
@require_GET
def download_view(request):
    yt_dlp = _load_yt_dlp()
    if not yt_dlp:
        return JsonResponse({"error": "yt-dlp not installed"}, status=500)

    url = request.GET.get("url", "").strip()
    dtype = request.GET.get("type", "video")
    quality = request.GET.get("quality", "")

    video_id = _extract_video_id(url)
    if not YOUTUBE_ID_PATTERN.match(video_id):
        return JsonResponse({"error": "Invalid URL"}, status=400)

    qval = _parse_quality_value(quality, dtype)
    selector = _selector_for(dtype, qval)

    temp_dir = Path(tempfile.mkdtemp())
    output = str(temp_dir / "%(title)s.%(ext)s")

    # Try multiple authentication methods in order of preference:
    # 1. Browser cookies (most reliable for YouTube)
    # 2. cookies.txt file
    cookie_path = get_cookie_path()
    browser_cookies = get_browser_cookies()

    opts = {
        "outtmpl": output,
        "format": selector,
        "quiet": True,
        "no_warnings": True,
    }

    # Prefer browser cookies for YouTube (solves bot verification)
    if browser_cookies:
        opts["cookiesfrombrowser"] = browser_cookies
    elif cookie_path:
        opts["cookiefile"] = cookie_path

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = Path(ydl.prepare_filename(info))
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JsonResponse({"error": str(e)}, status=400)

    response = StreamingHttpResponse(
        _stream_file_and_cleanup(file_path, temp_dir),
        content_type=mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    )

    response["Content-Disposition"] = f"attachment; filename={quote(file_path.name)}"
    return response