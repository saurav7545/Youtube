# Youtube

A web application for downloading YouTube videos and audio files.

## Features

- Download YouTube videos in various qualities (144p to 1080p)
- Download YouTube audio in various bitrates (64 kbps to 320 kbps)
- Clean and modern UI
- CORS-enabled backend

## Authentication Setup (Important!)

To avoid YouTube's "Sign in to confirm you're not a bot" error, you need to configure authentication.

### For Local Development (Using Browser Cookies)

1. Navigate to the backend directory:
   ```bash
   cd backend/downloading
   ```

2. The `.env` file already has `YT_DL_BROWSER=chrome` configured.

3. **Important**: Make sure you're logged into YouTube in your Chrome browser AND Chrome is running when you start the backend.

4. Start the backend server:
   ```bash
   python manage.py runserver
   ```

5. Check the console output - you should see messages like:
   - `🔑 Using browser cookies from: chrome`
   - `🔍 Debug: cookie_path=None, browser_cookies=chrome`

If you don't see these messages or still get errors, try the manual cookies method below.

### For Production Deployment (Render, Vercel, etc.)

**Important:** Browser cookies only work for local development. For production servers, you must use a cookies.txt file:

1. Export cookies from your browser using a browser extension (see [AUTHENTICATION_GUIDE.md](backend/downloading/AUTHENTICATION_GUIDE.md))
2. Upload the `cookies.txt` file to your production server in the `backend/downloading/` directory
3. Restart your production server

For detailed authentication instructions, see [AUTHENTICATION_GUIDE.md](backend/downloading/AUTHENTICATION_GUIDE.md).

## Project Structure

```
Youtube/
├── backend/
│   └── downloading/
│       ├── yt/              # Django app for YouTube downloader
│       ├── downloading/     # Django project settings
│       ├── manage.py        # Django management script
│       ├── requirements.txt # Python dependencies
│       ├── cookies.txt      # (Optional) Manual cookies file
│       └── .env             # Environment configuration
└── frontend/
    └── ui/                  # React frontend (Vite)
```

## Installation

### Backend

```bash
cd backend/downloading
pip install -r requirements.txt
cp .env.example .env
# Edit .env and configure YT_DL_BROWSER
python manage.py runserver
```

### Frontend

```bash
cd frontend/ui
npm install
cp .env.example .env.local
# Edit .env.local if needed
npm run dev
```

## Environment Variables

### Backend (.env)

- `DJANGO_DEBUG` - Debug mode
- `DJANGO_ALLOWED_HOSTS` - Allowed hosts
- `CORS_ALLOWED_ORIGINS` - CORS origins
- `YT_DL_BROWSER` - Browser for cookie extraction (chrome, firefox, brave, edge, safari, chromium)
- `YT_DL_BROWSER_PROFILE` - (Optional) Browser profile name

### Frontend (.env.local)

- Configure API endpoint URL if needed

## Troubleshooting

### "Sign in to confirm you're not a bot" error:
1. Set `YT_DL_BROWSER=chrome` in your backend `.env` file
2. Make sure you're logged into YouTube in your browser
3. Restart the backend server

### "_parse_browser_specification() takes from 1 to 4 positional arguments" error:
This error occurs due to a yt-dlp version compatibility issue. To fix:

1. Stop the backend server
2. Reinstall the correct yt-dlp version:
   ```bash
   cd backend/downloading
   pip install -r requirements.txt --force-reinstall
   ```
3. Restart the backend server

The project uses yt-dlp version 2024.12.23 which is stable and doesn't have this issue.

See [AUTHENTICATION_GUIDE.md](backend/downloading/AUTHENTICATION_GUIDE.md) for more details.

## License

MIT
