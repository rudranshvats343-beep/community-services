# SmartSchool – Digital Library Management System

This folder contains the original React + Vite interface plus a first-stage Python/SQLite REST API.

## Frontend (existing interface)

Requirements: Node.js LTS.

```bash
npm install
npm run dev
```

Open the local URL shown by Vite (usually `http://localhost:5173`).

The existing React screens currently keep their working demo records in browser `localStorage`. The frontend has **not yet been migrated to call the API**, so its current screen data is not shared with the backend database.

## Backend API

Requirements: Python 3.9+ (standard library only; no pip packages required).

Windows: double-click `start-backend.bat`.

macOS/Linux:

```bash
./start-backend.sh
```

Or run `python server.py` from this folder. The API starts at `http://127.0.0.1:8000` and creates `data/smartschool.db` automatically.

Health check: `GET http://127.0.0.1:8000/api/health`

### Demo administrator

- Username: `admin`
- Password: `Admin@123`

Change this demo password and restrict network access before using real student data. This local demo backend keeps bearer tokens in process memory; tokens are cleared when the server restarts. It is not production-ready authentication/session infrastructure.

### Implemented API routes

- `POST /api/login`, `GET /api/me`
- `GET /api/dashboard`, `GET/POST /api/books`, `PUT/DELETE /api/books/{id}`
- `GET/POST /api/students`, `DELETE /api/students/{id}` (deactivation)
- `GET/POST /api/librarians`
- `GET /api/categories`
- `GET /api/transactions`, `POST /api/transactions/issue`, `POST /api/transactions/return`
- `GET/POST /api/reservations`, `PUT /api/reservations/{id}`
- `GET /api/fines`, `POST /api/fine-payments`
- `GET /api/notifications`, `PUT /api/notifications/{id}`
- `GET/PUT /api/settings`, `GET /api/activity`

The API uses SQLite foreign keys, unique constraints, indexes, password hashing (PBKDF2-HMAC-SHA256), role checks on protected routes, transactional issue/return updates, overdue fine calculation and audit records.

## Current implementation status

- Existing React interface: retained.
- Existing localStorage book/student/issue workflows: retained as a classroom prototype.
- SQLite backend schema and REST endpoints: added and smoke-tested.
- Frontend-to-backend integration, full role-specific screens, librarian/student account provisioning workflow, PDF/Excel exports, QR scanning, email delivery, production-grade sessions/CSRF/rate limiting and deployment hardening: **not yet completed**.

Do not enter real student personal data until the remaining security and integration work is completed and approved by the school.
