
# GhostComm Find

GhostComm Find is a secure, AI-powered lost-and-found platform designed to help members of the JKUAT community report, find, and recover lost belongings.

## Features

- Report lost and found items.
- Browse item reports.
- Support AI-assisted matching of lost and found items.
- Provide a web interface connected to a FastAPI backend.

## Technology Stack

- **Frontend:** React and Vite
- **Backend:** Python and FastAPI
- **API documentation:** FastAPI Swagger UI

## Getting Started

### Backend

Open PowerShell and run:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

The API documentation will be available at:

http://127.0.0.1:8000/docs

### Frontend

Open a second PowerShell terminal and run:

```powershell
npm install
npm run dev
```

Open the local URL printed by Vite in your terminal.

## Security

Do not commit `.env` files, credentials, API keys, or other secrets to GitHub.
