# OpenHarvey

Open-source AI-powered legal document analysis and contract review platform built with [FastHTML](https://fastht.ml) and [LangChain](https://langchain.com).

## Features

- **AI Assistant** - Chat with AI about your legal documents using any supported LLM
- **Multi-LLM Support** - OpenAI (GPT-4o, GPT-4.1, o4-mini), Anthropic (Claude Sonnet 4.6, Haiku 4.5), Google (Gemini 2.5 Flash/Pro) via LangChain
- **Projects** - Organize documents into projects
- **Document Upload** - Upload and manage PDF, DOCX, DOC, and TXT files
- **Tabular Reviews** - Spreadsheet-style document analysis
- **Workflows** - Reusable prompt templates for common legal tasks
- **Accounts** - User authentication with per-user model preferences

## Tech Stack

- **Frontend & Backend**: [FastHTML](https://fastht.ml) + [MonsterUI](https://monsterui.answer.ai) (Python, server-rendered with HTMX)
- **LLM Integration**: [LangChain](https://langchain.com) (multi-provider)
- **Database**: PostgreSQL via SQLAlchemy
- **Auth**: Session-based with bcrypt password hashing

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file (or edit the existing one) with your database and API keys:

```
DB_URL=postgresql://user:pass@host:5432/dbname
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...
DEFAULT_MODEL=gpt-4o-mini
```

Set at least one LLM provider API key depending on which models you want to use.

Create the `openharvey` database and apply the schema:

```bash
createdb -h <host> -U <user> openharvey
psql $DB_URL -f sql/create_schema.sql
```

Tables are also auto-created on first run via SQLAlchemy if they don't exist.

Run the app:

```bash
python main.py
```

Open `http://localhost:5001`.

## Project Structure

```
main.py              - FastHTML app with all routes
components.py        - Reusable UI components
db.py                - SQLAlchemy models and database setup
llm.py               - LangChain multi-LLM integration
sql/create_schema.sql - PostgreSQL schema
requirements.txt     - Python dependencies
```

## License

AGPL-3.0-only. See `LICENSE`.
