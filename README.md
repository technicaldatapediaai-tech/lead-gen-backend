# Lead Genius Backend API

This is the backend service for the Lead Genius platform, built with **FastAPI**.

## 🛠 Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (via SQLModel & SQLAlchemy)
- **Migrations**: Alembic
- **AI Integration**: OpenRouter (OpenAI compatible), Google Gemini (optional)
- **Authentication**: JWT (OAuth2 with Password Flow)
- **Task Queue**: Background Tasks (built-in FastAPI)

## 🚀 Setup & Installation

### 1. Prerequisites

- Python 3.10+
- PostgreSQL installed and running locally or remote.

### 2. Installation

1.  Clone the repository and navigate to `backend/`.
2.  Create a virtual environment:
    ```bash
    python -m venv venv
    ```
3.  Activate the virtual environment:
    - **Windows**: `venv\Scripts\activate`
    - **Mac/Linux**: `source venv/bin/activate`
4.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### 3. Configuration (`.env`)

Create a `.env` file in the `backend/` root directory. Refer to `config.py` for all available settings.

**Essential Variables:**

```ini
# Server
DEV_MODE=True
SECRET_KEY=your_super_secret_key_here

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/lead_genius

# AI Services
OPENAI_API_KEY=your_openrouter_api_key
OPENAI_BASE_URL=https://openrouter.ai/api/v1  # Or standard OpenAI URL

# Integrations
APOLLO_API_KEY=your_apollo_key
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
```

### 4. Database Setup

To initialize the database tables:

```bash
python database.py
# Or check for 'create_db.py' if available
```

*(Note: Alembic migrations can be run with `alembic upgrade head` if configured)*

### 5. Running the Server

Start the interactive development server:

```bash
uvicorn main:app --reload
```

- **API Base URL**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📂 Project Structure

- `main.py`: Application entry point.
- `config.py`: Configuration loader using Pydantic.
- `api/`: API route definitions (routers).
- `models/`: Database models (SQLModel).
- `schemas/`: Pydantic schemas for request/response validation.
- `services/`: Business logic layer.
- `repositories/`: Database abstraction layer.
- `core/`: Core utilities (security, logging).

## ✅ Testing

Run unit tests using pytest (if installed):

```bash
pytest
```

## 🔍 Common Issues

- **ModuleNotFoundError**: Ensure you are running commands from the parent directory or have installed the package efficiently. Ensure `venv` is active.
- **Database Connection**: Check `DATABASE_URL` in `.env`. Ensure the database `lead_genius` exists.
