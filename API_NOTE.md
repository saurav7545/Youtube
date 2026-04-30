# API Note

Base URL (local): `http://127.0.0.1:8000`
API prefix: `/api/yt`

## Endpoints

### 1) Health
- Method: `GET`
- URL: `/api/yt/health`
- Purpose: quick server health check
- Success response:
```json
{"ok": true}
```

### 2) Video Info
- Method: `GET`
- URL: `/api/yt/info?url=<youtube-url>`
- Purpose: validate URL and fetch metadata/qualities before download
- Query params:
  - `url` (required)
- Success response (example):
```json
{
  "videoId": "dQw4w9WgXcQ",
  "title": "Example Title",
  "thumbnail": "https://...",
  "videoQualities": ["1080p", "720p", "480p"],
  "audioQualities": ["320 kbps", "192 kbps", "128 kbps"],
  "videoMergeAvailable": true
}
```

### 3) Download
- Method: `GET`
- URL: `/api/yt/download?url=<youtube-url>&type=video&quality=720p`
- Purpose: stream file download (audio or video)
- Query params:
  - `url` (required)
  - `type` (required): `video` or `audio`
  - `quality` (optional): `720p`, `360p`, `192 kbps`, etc.
- Success response: binary file stream with `Content-Disposition: attachment`

### 4) Local Job (optional advanced flow)
- Method: `GET`
- URL: `/api/yt/local-job?url=<youtube-url>&type=video&quality=720p`
- Purpose: generate signed payload for `local_helper.py`

## Error Shape

Most API errors return JSON like:
```json
{
  "error": "Human-readable message"
}
```

Authentication-required errors may include:
```json
{
  "error": "This video needs YouTube authentication...",
  "details": "raw yt-dlp message",
  "requiresCookies": true
}
```

## Quick cURL Examples

```bash
curl "http://127.0.0.1:8000/api/yt/health"
curl "http://127.0.0.1:8000/api/yt/info?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
curl -L "http://127.0.0.1:8000/api/yt/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&type=audio&quality=128%20kbps" -o sample.mp3
```
