# Deploy Frontend + Backend on Vercel

This repo has two deployable projects:

- Frontend (Vite React): `frontend/ui`
- Backend (Django API): `backend/downloading`

Create two separate Vercel projects (one for each folder).

## 1) Backend Project (Django)

Project root: `backend/downloading`

Vercel detects Django `manage.py` and deploys it with Python runtime.

Required Environment Variables:

- `DJANGO_DEBUG=false`
- `DJANGO_SECRET_KEY=<generate-random-secret>`
- `DJANGO_ALLOWED_HOSTS=.vercel.app,127.0.0.1,localhost`
- `CORS_ALLOWED_ORIGINS=https://<your-frontend>.vercel.app`
- `CORS_ALLOWED_ORIGIN_REGEXES=^https://.*\.vercel\.app$`
- `CSRF_TRUSTED_ORIGINS=https://*.vercel.app`

Health URL after deploy:

- `https://<your-backend>.vercel.app/api/yt/health`

## 2) Frontend Project (Vite)

Project root: `frontend/ui`

Environment Variable:

- `VITE_API_BASE_URL=https://<your-backend>.vercel.app`

`vercel.json` for SPA rewrites already exists in `frontend/ui/vercel.json`.

## 3) Test End-to-End

1. Open frontend URL on another device
2. Paste YouTube URL
3. Click Search
4. Thumbnail should load from backend API
5. Click Download

## Notes

- Backend uses `yt-dlp`, so long downloads may hit Vercel function duration limits on some plans.
- For heavy/long downloads, Render or VPS is usually more stable for backend jobs.
