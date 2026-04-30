# YouTube Authentication Guide (yt-dlp)

If you see:

`Sign in to confirm you’re not a bot`

then YouTube is blocking anonymous access for that video. You must provide authenticated cookies.

## Option A: Local Development (recommended)

Use browser session cookies directly.

1. Sign in to YouTube in your browser.
2. Set env in `backend/downloading/.env`:

```env
YT_DL_BROWSER=chrome
# optional:
# YT_DL_BROWSER_PROFILE=Default
```

Supported browsers: `chrome`, `firefox`, `brave`, `edge`, `safari`, `chromium`

## Option B: Hosted Server (Render/Vercel backend)

Browser cookie DB is usually unavailable on hosted servers, so use `cookies.txt`.

1. Export fresh YouTube cookies as `cookies.txt`.
2. Provide one of these env vars:

```env
YT_DL_COOKIES_B64=<base64 of cookies.txt>
# or
YT_DL_COOKIES_RAW=<raw cookies.txt content>
# or
YT_DL_COOKIES_FILE=/absolute/path/to/cookies.txt
```

PowerShell helper to create base64:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("cookies.txt"))
```

## Verify

Call:

`GET /api/yt/info?url=<youtube-url>`

If auth is still required, backend returns:
- `requiresCookies: true`
- `details` with raw yt-dlp error
- `cookieHints` and `docs` links

## Official yt-dlp docs

- https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp
- https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies
