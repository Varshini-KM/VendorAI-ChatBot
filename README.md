# 🛒 VendorAI

An AI-powered, multilingual (English / Hindi / Tamil) business assistant chatbot
for street vendors and small informal businesses. Talk to it like a person —
it records sales and expenses, tracks inventory, calculates profit, and gives
restocking advice, all from plain natural-language chat.

> Built as a portfolio project tackling a real problem: informal vendors in India
> rarely keep digital financial records, which locks them out of formal credit.
> The transaction history this bot builds is a first step toward alternative
> credit-scoring for the unbanked (see "Vision" below).

---

## ✨ Features

- 💬 Chat interface (text now, voice-input slot ready for Whisper)
- 🧾 Natural-language sales logging — handles multi-item messages
  (*"sold 12 coconuts for 900 and 5 mangoes for 250"*)
- 💸 Natural-language expense logging (multi-entry too)
- 📦 Inventory that auto-updates from sales and stock-purchase expenses
- 📈 Profit calculation, daily/weekly/monthly reports
- 🔔 Smart restock suggestions (low-stock **and** sales-velocity based)
- 📊 Visual dashboard (Plotly charts)
- 📤 CSV / PDF report export
- 🌐 Multilingual: English, Hindi, Tamil
- 🧠 Works with **zero API keys** via a built-in rule-based fallback extractor —
  add an OpenAI or Grok key any time for full multilingual LLM accuracy

---

## 🏗️ Architecture

```
User message
   │
   ▼
[extract_intent node]  <-- LLM (or fallback) converts messy text -> strict JSON
   │  (Pydantic validates the JSON — LLM output is NEVER trusted blindly)
   ▼
[conditional routing on intent]
   │
   ├── add_sale ───────────┐
   ├── add_expense ────────┤
   ├── check_profit ───────┤──▶ handler node (pure Python) reads/writes DB
   ├── check_report ───────┤
   ├── check_inventory ────┤
   ├── restock_suggestion ─┤
   └── unknown ────────────┘
   │
   ▼
Response text + structured data → back to the user
```

**Key design decision:** the LLM only ever does *intent + entity extraction*
(and, separately, turning already-computed numbers into friendly phrasing for
analytical questions). It never writes SQL, never touches the database, and
its output is always validated against a strict Pydantic schema before
anything happens. This is what makes the system reliable enough to trust with
real financial data — a point worth highlighting in your project report/viva.

Built with **LangGraph** for the flow, with **LangSmith** tracing available
(optional) to debug extraction accuracy across English/Hindi/Tamil.

---

## 📁 Project Structure

```
vendorai/
├── backend/
│   ├── main.py            FastAPI app + all endpoints
│   ├── config.py          env var / settings loader
│   ├── database.py        SQLAlchemy models (vendors, sales, expenses, inventory, chat_history)
│   ├── schemas.py         Pydantic contracts (LLM output + API request/response)
│   ├── prompts.py         the two system prompts (extraction, Q&A)
│   ├── llm_service.py     OpenAI/Grok client + rule-based fallback extractor
│   ├── handlers.py        DB read/write logic per intent (only place that touches DB)
│   ├── analytics.py       pandas-based profit/report/restock calculations
│   ├── export_utils.py    CSV / PDF report generation
│   └── graph.py           LangGraph flow definition
├── frontend/
│   ├── app.py             Streamlit landing page
│   ├── utils/api_client.py
│   └── pages/
│       ├── 1_Chat.py
│       ├── 2_Dashboard.py
│       ├── 3_Reports.py
│       └── 4_Inventory.py
├── data/                  SQLite DB lives here (auto-created)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Setup (VS Code)

1. **Open the folder** `vendorai/` in VS Code.

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```
   You can leave every key blank and the app will still run (fallback mode).
   To use a real LLM, open `.env` and paste in `OPENAI_API_KEY` (or `GROK_API_KEY`).

5. **Run the backend** (from the project root, terminal 1):
   ```bash
   uvicorn backend.main:app --reload
   ```
   Visit http://127.0.0.1:8000/docs to see the interactive API docs.
   
**Run with Docker (quick demo / deploy)**

If you prefer a reproducible demo or to deploy the app quickly, there's a Docker setup included. From the project root (where `docker-compose.yml` lives):

```bash
# build images and run both services
docker compose up --build

# then open the frontend at http://localhost:8501
# and the API docs at http://localhost:8000/docs
```

There is also a small seed script to populate example data:

```bash
docker compose run --rm backend python vendorai/seed_db.py
```

6. **Run the frontend** (from the project root, terminal 2):
   ```bash
   streamlit run frontend/app.py
   ```
   This opens the chatbot UI in your browser (usually http://localhost:8501).

7. **Try it out** — on the Chat page type:
   - `I sold 12 coconuts for 900 rupees`
   - `bought onions for 250 and tomatoes for 400`
   - `how much profit did I make today?`
   - `what should I restock?`
   
---


---

## 🗺️ Roadmap (as discussed)

- **Week 1 (MVP)** — chat-based sales/expense logging, profit calc, basic reports ✅ (this codebase)
- **Week 2** — real voice input via Whisper, richer charts, restock intelligence ✅ (hooks in place, wire up your Whisper key)
- **Stretch goals** — multi-vendor auth/login, WhatsApp bot integration, alternative
  credit-scoring model fed by transaction history, comparison writeup of
  OpenAI vs Grok extraction accuracy (LangSmith traces make this easy to evaluate)

---

## 🌍 Vision

OkCredit, Khatabook, and Aye Finance have shown that digitizing informal
vendors' records unlocks real value — from simpler bookkeeping to actual
credit access. VendorAI's bet is that **removing the literacy/typing barrier
entirely** (chat or speak naturally, in your own language) is what gets
first-time digital adoption from vendors who've never used an app like this
before. The `chat_history` + `sales`/`expenses` tables this project builds are
exactly the structured transaction trail a future alternative credit-scoring
layer would need.

---

## 🔧 Extending it further

- **Voice input**: `frontend/pages/1_Chat.py` already has an `st.audio_input`
  widget wired up — pipe its bytes through Whisper (or any STT API) in
  `backend/llm_service.py` and feed the transcript into the same `/chat` flow.
- **Comparing OpenAI vs Grok**: flip `LLM_PROVIDER` in `.env` between `openai`
  and `grok`, run the same set of test messages through `/chat`, and compare
  `confidence` scores and LangSmith traces.
- **PostgreSQL**: swap `DATABASE_URL` in `backend/config.py` — since everything
  goes through SQLAlchemy, no other code changes are needed.
