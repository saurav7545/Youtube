# 🚀 Deployment Guide (Frontend + Backend on Vercel)

This repository contains two separate deployable applications:

- 🎨 **Frontend (React + Vite)** → `frontend/ui`
- ⚙️ **Backend (Django API)** → `backend/downloading`

👉 You need to create **two separate Vercel projects** (one for frontend, one for backend).

---

## 🔧 1) Backend Deployment (Django)

- **Project Root:** `backend/downloading`
- Vercel automatically detects `manage.py` and uses Python runtime

---

### 🔑 Required Environment Variables

```env
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=your-secret-key
DJANGO_ALLOWED_HOSTS=.vercel.app,127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=https://<your-frontend>.vercel.app
CORS_ALLOWED_ORIGIN_REGEXES=^https://.*\.vercel\.app$
CSRF_TRUSTED_ORIGINS=https://*.vercel.app