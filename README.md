<div align="center">

# 🛰️ CodeOrbit

**An AI-powered code companion that reviews your code, teaches you concepts, and converts between languages.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-codeorbit--ldex.onrender.com-4f46e5?style=for-the-badge)](https://codeorbit-ldex.onrender.com/)

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/Django%20REST%20Framework-API-a30000)
![Channels](https://img.shields.io/badge/Django%20Channels-WebSockets-44b78b)
![Postgres](https://img.shields.io/badge/PostgreSQL-Neon-336791?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Valkey-DC382D?logo=redis&logoColor=white)
![Groq](https://img.shields.io/badge/LLM-Groq-f55036)

[Live Demo](https://codeorbit-ldex.onrender.com/) · [Report a Bug](https://github.com/Stutikhanna112004/CodeOrbit/issues) · [Request a Feature](https://github.com/Stutikhanna112004/CodeOrbit/issues)

</div>

---

## ✨ What is CodeOrbit?

CodeOrbit is a full-stack web app that puts an AI senior engineer in your browser. Paste code, ask a question, or pick a target language, and get structured, actionable answers in seconds.

It has three modes, all in one editor-style interface:

| Mode | What it does |
| --- | --- |
| 🔍 **Review** | Analyses your code and returns a quality score (0–100), a summary, findings by category (bugs, security, performance, readability, best practices), line-level comments with fixes, positives, and a fully rewritten improved version. |
| 🎓 **Learn** | Ask *"explain recursion"* or *"how do closures work"* and get a clear explanation, a real-world analogy, a runnable code example, common beginner mistakes, a practice exercise, and what to learn next. |
| 🔄 **Convert** | Translate code from one language to idiomatic code in another, with key differences, caveats, and an equivalent-concepts table. |

**Supported languages:** Python · JavaScript · TypeScript · Java · C++ · Go · Rust

---

## 🧰 Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | Django 5.2, Django REST Framework |
| Auth | JWT (`djangorestframework-simplejwt`) with access and refresh tokens |
| Real-time | Django Channels + Daphne (ASGI), WebSockets for streaming reviews |
| AI | [Groq](https://groq.com/) API (`openai/gpt-oss-120b` by default) |
| Database | PostgreSQL (Neon in production, SQLite optional locally) |
| Cache / channel layer | Redis-compatible Key Value store (Render) |
| Static files | WhiteNoise |
| Hosting | Render (web service + Key Value), Neon (Postgres) |

---

## 🏗️ Architecture

```mermaid
flowchart LR
    U[Browser<br/>Review · Learn · Convert] -->|HTTPS + JWT| API[Django REST API]
    U <-->|WebSocket| WS[Django Channels<br/>Daphne ASGI]
    API --> AI[reviews/ai_service.py]
    WS --> AI
    AI -->|chat completions| G[(Groq API)]
    API --> DB[(PostgreSQL<br/>Neon)]
    WS --> R[(Redis<br/>channel layer)]
```

**How a request flows:**

1. The user signs in and receives a JWT access token (plus a refresh token).
2. The frontend sends code or a question to the REST API, or opens a WebSocket for a streamed review.
3. `reviews/ai_service.py` builds a task-specific prompt, calls Groq, strips any markdown fences, and parses the JSON response.
4. The structured result is returned to the UI and rendered. Review history and stats are stored in PostgreSQL.

---

## 📁 Project Structure

```
CodeOrbit/
├── core/                  # Django project: settings, urls, asgi
├── reviews/               # Main app
│   ├── ai_service.py      # Groq client, prompts, JSON parsing, streaming
│   └── ...                # models, views, serializers, consumers
├── templates/             # Single-page UI (Review / Learn / Convert)
├── build.sh               # Render build script
├── render.yaml            # Render service definition
├── requirements.txt
├── test.http              # Ready-made API requests
├── test_websocket.html    # Quick WebSocket test page
└── manage.py
```

---

## 🔌 API Overview

All AI endpoints require a valid JWT: `Authorization: Bearer <access_token>`.

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/auth/login/` | Obtain access and refresh tokens |
| `POST` | `/api/auth/refresh/` | Refresh an access token |
| `POST` | `/api/teach/` | Explain a programming concept |
| `POST` | `/api/convert/` | Convert code between languages |
| `GET` | `/api/reviews/stats/` | Review statistics for the signed-in user |

Reviews can also be streamed over WebSocket (see `test_websocket.html` for a working example). Try the REST endpoints quickly with the requests in `test.http`.

> Endpoint names above reflect the deployed app. Check `reviews/urls.py` for the full, current list.

---

## 🚀 Getting Started (Local)

### Prerequisites

- Python 3.11+
- A free [Groq API key](https://console.groq.com/)
- Optional: Redis (for WebSockets) and PostgreSQL. SQLite works for basic local development.

### 1. Clone and install

```bash
git clone https://github.com/Stutikhanna112004/CodeOrbit.git
cd CodeOrbit

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root (it is git-ignored, never commit it):

```env
SECRET_KEY=change-me
DEBUG=True
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b

# Optional locally. Leave unset to use SQLite.
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
REDIS_URL=redis://localhost:6379
```

### 3. Migrate and run

```bash
python manage.py migrate
python manage.py createsuperuser     # optional, for the admin panel
daphne -b 127.0.0.1 -p 8000 core.asgi:application
```

Open **http://127.0.0.1:8000/** and you're in. (`python manage.py runserver` also works for HTTP-only testing.)

---

## ⚙️ Environment Variables

| Variable | Required | Description |
| --- | :---: | --- |
| `SECRET_KEY` | ✅ | Django secret key |
| `DEBUG` | | `True` for local, `False` in production |
| `GROQ_API_KEY` | ✅ | Your Groq API key |
| `GROQ_MODEL` | | Model ID. Defaults to `openai/gpt-oss-120b` |
| `DATABASE_URL` | ✅ in prod | PostgreSQL connection string (SSL required for Neon) |
| `REDIS_URL` | ✅ in prod | Redis/Key Value URL for the Channels layer |

> Variable names should match what `core/settings.py` reads. Update this table if you rename any.

---

## ☁️ Deployment

CodeOrbit is deployed on **Render** with a **Neon** Postgres database and a **Render Key Value** instance.

**Start command**

```bash
python manage.py migrate && daphne -b 0.0.0.0 -p $PORT core.asgi:application
```

**Checklist**

1. Create a Postgres database on [Neon](https://neon.tech/) and copy the connection string into `DATABASE_URL`. Use the same region as your Render services to keep latency low.
2. Create a Key Value (Redis) instance on Render, in the **same region** as the web service, and use its **internal** URL for `REDIS_URL`.
3. Add `GROQ_API_KEY`, `SECRET_KEY`, and the other variables in the service's **Environment** tab.
4. Deploy. Migrations run automatically on every start.

---

## 🛠️ Troubleshooting

<details>
<summary><b>Groq returns <code>404 model_not_found</code></b></summary>

Groq retires models over time. If the model in `GROQ_MODEL` is decommissioned, requests fail with a 404. Set `GROQ_MODEL` to a currently supported model (check [Groq's model list](https://console.groq.com/docs/models)), for example `openai/gpt-oss-120b` or `qwen/qwen3.6-27b`, and redeploy. No code change needed.
</details>

<details>
<summary><b><code>could not translate host name ... Name or service not known</code></b></summary>

The database hostname isn't reachable. Render's free Postgres expires after a limited period and internal hostnames only resolve inside the same region. Point `DATABASE_URL` at a live database (for example Neon).
</details>

<details>
<summary><b><code>password authentication failed</code></b></summary>

The password in `DATABASE_URL` doesn't match. Reset the role password in your database provider, copy the full connection string with the copy button, and paste it without quotes or extra spaces.
</details>

<details>
<summary><b>First request is slow</b></summary>

Free-tier services sleep when idle. Render's web service and Neon's compute may take several seconds to wake up. Open the site a minute before a demo.
</details>

<details>
<summary><b><code>Invalid JSON from AI</code></b></summary>

The model returned text that isn't valid JSON, often because a long answer was cut off. Raise `max_tokens` in `ai_service.py` or try a different `GROQ_MODEL`.
</details>

---

## 🗺️ Roadmap

- [ ] Save and revisit past reviews with a history view
- [ ] Side-by-side diff between original and improved code
- [ ] Shareable review links
- [ ] More languages (C#, PHP, Kotlin, Swift)
- [ ] Export reviews as PDF or Markdown
- [ ] Rate limiting and usage quotas per user
- [ ] Automated tests and CI with GitHub Actions

---

## 🔒 Security Notes

- Never commit `.env` files or API keys. Keep them in your host's environment settings.
- If a key or database password is ever exposed, rotate it immediately.
- All AI endpoints are protected with JWT authentication.

---

## 🤝 Contributing

Contributions, issues, and feature ideas are welcome.

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 👩‍💻 Author

**Stuti**

- GitHub: [@Stutikhanna112004](https://github.com/Stutikhanna112004)

If CodeOrbit helped you, consider giving the repo a ⭐

---

## 📄 License

Add a license file (for example MIT) and reference it here.
