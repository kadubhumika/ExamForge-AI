# ExamForge AI 🎓

> AI-powered question paper generator for teachers. Upload a chapter PDF, set your question structure, get a print-ready exam with answer key in seconds.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green) ![Gemini](https://img.shields.io/badge/Gemini-1.5%20Flash-orange) ![License](https://img.shields.io/badge/license-MIT-purple)

## Features

- 🤖 **AI Generation** — Gemini generates structured question papers from any chapter PDF
- 📄 **PDF Output** — formatted question paper + answer key, ready to print
- 🔔 **Notifications** — real-time updates for assignment created, ready, deleted
- 🔐 **Auth** — email/password + Google OAuth with JWT sessions
- 📚 **My Library** — track all assignments with live status
- 🎨 **Dark Mode** — saved across all pages
- ⚡ **Background Jobs** — upload returns instantly, AI runs in background

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy, Alembic |
| AI | Google Gemini 1.5 Flash |
| Database | PostgreSQL (Neon) |
| Cache | Redis |
| PDF | ReportLab + pypdf |
| Auth | JWT + Google OAuth 2.0 |
| Frontend | HTML/CSS/JS + Tailwind CSS |
| Deploy | Render + Neon |

## Quick Start

```bash
# 1. Clone & install
git clone https://github.com/YOUR_USERNAME/examforge-ai.git
cd examforge-ai
pip install -r requirements.txt

# 2. Copy env and fill in values
cp .env.example .env

# 3. Start Postgres + Redis
docker-compose up -d

# 4. Run migrations
alembic upgrade head

# 5. Start backend
uvicorn main:app --reload --port 8085

# 6. Serve frontend
cd frontend && python -m http.server 5500
```

Open `http://127.0.0.1:5500/login.html`

## How it works
Upload PDF + set question structure

↓

Assignment created (PENDING)

↓

Background: extract text → Gemini → render PDF

↓

Frontend polls status every 2s

↓

DONE → view paper in browser + download PDF

## Deployment

| Service | Platform |
|---|---|
| Database | [Neon](https://neon.tech) free PostgreSQL |
| Backend | Render Web Service — `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Redis | Render Redis free instance |
| Frontend | Render Static Site — publish dir: `frontend` |

> ⚠️ Free Render services sleep after 15 min idle. First request takes ~30s to wake.

## API Docs

Run backend and visit `http://localhost:8085/docs`

---

Built with ❤️ for teachers who deserve better tools.
