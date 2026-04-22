import mimetypes
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


def _load_yt_dlp():
    try:
        import yt_dlp
    except ImportError:
        return None
    return yt_dlp


def _extract_video_id(url: str) -> str:
    text = (url or "").strip()
    if not text:
        return ""

    match = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11})(?:[?&]|$)", text)
    if match:
        return match.group(1)
    return ""


def _parse_quality_value(quality: str, download_type: str):
    if download_type == "video":
        match = re.match(r"^(\d{3,4})p$", quality)
    else:
        match = re.match(r"^(\d{2,3})\s*kbps$", quality.lower())

    if not match:
        return None
    return int(match.group(1))


def _selector_for(download_type: str, quality_value: int | None) -> str:
    if download_type == "audio":
        if quality_value is None:
            return "bestaudio/best"
        return f"bestaudio[abr<={quality_value}]/bestaudio/best"

    if quality_value is None:
        return "bestvideo+bestaudio/best"

    return (
        f"bestvideo[height<={quality_value}][ext=mp4]+bestaudio[ext=m4a]/"
        f"best[height<={quality_value}][ext=mp4]/best[height<={quality_value}]"
    )


def _collect_qualities(info: dict):
    formats = info.get("formats", [])

    video_vals = sorted(
        {
            int(fmt.get("height"))
            for fmt in formats
            if fmt.get("vcodec") not in (None, "none") and fmt.get("height")
        }
    )
    audio_vals = sorted(
        {
            int(round(float(fmt.get("abr"))))
            for fmt in formats
            if fmt.get("acodec") not in (None, "none") and fmt.get("abr")
        }
    )

    video_qualities = [f"{value}p" for value in video_vals] or DEFAULT_VIDEO_QUALITIES
    audio_qualities = (
        [f"{value} kbps" for value in audio_vals] or DEFAULT_AUDIO_QUALITIES
    )
    return video_qualities, audio_qualities


def _stream_file_and_cleanup(file_path: Path, temp_dir: Path):
    try:
        with file_path.open("rb") as file_obj:
            while True:
                chunk = file_obj.read(8192)
                if not chunk:
                    break
                yield chunk
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@require_GET
def health_view(_request):
    return JsonResponse({"ok": True, "service": "yt"})


@require_GET
def info_view(request):
    yt_dlp = _load_yt_dlp()
    if yt_dlp is None:
        return JsonResponse(
            {"error": "yt-dlp is not installed on backend."},
            status=500,
        )

    url = request.GET.get("url", "").strip()
    video_id = _extract_video_id(url)
    if not YOUTUBE_ID_PATTERN.match(video_id):
        return JsonResponse(
            {"error": "Invalid YouTube URL. Please provide a valid link."},
            status=400,
        )

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
         "cookiesfrombrowser": ("chrome",),

        "http_headers": {
            "User-Agent": "Mozilla/5.0"
        },
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        return JsonResponse(
            {"error": f"Unable to fetch video details: {exc}"},
            status=400,
        )

    video_qualities, audio_qualities = _collect_qualities(info)
    thumbnail = info.get("thumbnail") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

    return JsonResponse(
        {
            "videoId": video_id,
            "title": info.get("title") or "YouTube Video",
            "thumbnail": thumbnail,
            "videoQualities": video_qualities,
            "audioQualities": audio_qualities,
        }
    )


@require_GET
def download_view(request):
    yt_dlp = _load_yt_dlp()
    if yt_dlp is None:
        return JsonResponse(
            {"error": "yt-dlp is not installed on backend."},
            status=500,
        )

    url = request.GET.get("url", "").strip()
    download_type = request.GET.get("type", "video").strip().lower()
    quality = request.GET.get("quality", "").strip()

    if download_type not in {"video", "audio"}:
        return JsonResponse(
            {"error": "Invalid download type. Use 'video' or 'audio'."},
            status=400,
        )

    video_id = _extract_video_id(url)
    if not YOUTUBE_ID_PATTERN.match(video_id):
        return JsonResponse(
            {"error": "Invalid YouTube URL. Please provide a valid link."},
            status=400,
        )

    quality_value = _parse_quality_value(quality, download_type)
    format_selector = _selector_for(download_type, quality_value)

    temp_dir = Path(tempfile.mkdtemp(prefix="yt_dl_"))
    output_template = str(temp_dir / "%(title).120s-%(id)s.%(ext)s")

    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "outtmpl": output_template,
        "format": format_selector,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_path = None

            requested = info.get("requested_downloads") or []
            if requested and requested[0].get("filepath"):
                downloaded_path = Path(requested[0]["filepath"])
            else:
                downloaded_path = Path(ydl.prepare_filename(info))

            if not downloaded_path.exists():
                files = sorted(temp_dir.glob("*"))
                if not files:
                    raise FileNotFoundError("Downloaded file not found.")
                downloaded_path = files[0]
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JsonResponse({"error": f"Download failed: {exc}"}, status=400)

    content_type = mimetypes.guess_type(downloaded_path.name)[0] or "application/octet-stream"
    response = StreamingHttpResponse(
        _stream_file_and_cleanup(downloaded_path, temp_dir),
        content_type=content_type,
    )
    response["Content-Disposition"] = (
        f"attachment; filename*=UTF-8''{quote(downloaded_path.name)}"
    )
    return response
