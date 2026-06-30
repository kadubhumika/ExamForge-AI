# ExamForge AI 🎓

> AI-powered question paper generator and grading assistant for teachers. Upload a chapter PDF → get a question paper with answer key. Upload student answer sheets → get AI-graded results instantly.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green) ![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-orange)

## Features

- 🤖 **AI Question Generation** — upload a chapter PDF, get a complete question paper + answer key
- 📝 **AI Answer Sheet Grading** — upload scanned/handwritten student PDFs, AI grades each question
- 📊 **Analytics Dashboard** — school-wide teacher performance, leaderboard, trends
- 🔐 **Auth** — email/password + Google OAuth
- 📚 **My Library** — track assignments and results
- 🎨 **Dark Mode** + 🔔 **Notifications**

## Tech Stack

FastAPI · SQLAlchemy · Alembic · Google Gemini 2.5 Flash · PostgreSQL (Neon) · Redis · ReportLab · pdf2image + Poppler · JWT + Google OAuth · HTML/JS + Tailwind + Chart.js · Render (Docker)

## Quick Start

```bash
git clone https://github.com/kadubhumika/ExamForge-AI.git
cd ExamForge-AI
pip install -r requirements.txt

cp .env.example .env
docker-compose up -d
alembic upgrade head

uvicorn main:app --reload --port 8085
# new terminal
cd frontend && python -m http.server 5500
```

Open `http://127.0.0.1:5500/login.html`

> Requires Poppler installed for student PDF grading (`apt-get install poppler-utils` / `brew install poppler` / [Windows build](https://github.com/oschwartz10612/poppler-windows/releases))

## How it works
## How it works
Generate:  Upload PDF → Gemini → Question Paper + Answer Key → Download
Evaluate:  Upload student answer sheets → Gemini Vision grades vs key → Results PDF
Analytics: School-wide teacher performance + class average trends

## Deployment

| Service | Platform |
|---|---|
| Database | [Neon](https://neon.tech) |
| Backend | Render (Docker) |
| Redis | Render Redis |
| Frontend | Render Static Site |

> Free Render tier sleeps after 15 min idle — first request takes ~30s.

## Live Demo

🔗 https://examforge-ai-1.onrender.com
💻 https://github.com/kadubhumika/ExamForge-AI

---

Built with ❤️ for teachers who deserve better tools.
