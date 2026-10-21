# College Complaint Portal

A role-based complaint management system built with Streamlit and SQLite.

This project is designed for a college environment where:

- Students can register, log in, and raise complaints.
- Grievance managers can handle complaints assigned to their category.
- Admins can monitor the full system, review updates, and officially close complaints.

The goal is to keep complaint handling simple, trackable, and more transparent for everyone involved.

## What This Project Does

The portal supports the full complaint flow from submission to closure.

- Student registration and login
- Complaint submission with category-based manager assignment
- Auto-detected complaint priority
- Special handling for critical complaints
- Complaint timeline and progress tracking
- Separate dashboards for students, grievance managers, and admins
- Admin review of manager updates and close requests
- Optional REST API using FastAPI

## Tech Stack

- Python 3.10+
- Streamlit (UI)
- SQLite via Python's built-in `sqlite3` module (raw SQL, single file `complaint_portal.db`)
- FastAPI + Uvicorn (optional REST API, not used by the Streamlit UI)
- `bcrypt` (password hashing)
- `pandas` (tables in the dashboards)
- `python-dotenv` (loads settings and seed passwords from `.env`)
- `pytest` (tests)

## Current Project Structure

```text
Complaint_Complaint_Portal/
|-- main.py
|-- README.md
|-- requirements.txt
|-- app/
|   |-- __init__.py
|   |-- components/
|   |   |-- __init__.py
|   |   `-- ui.py
|   `-- pages/
|       |-- __init__.py
|       |-- admin.py
|       |-- auth.py
|       |-- manager.py
|       `-- student.py
|-- api/
|   |-- __init__.py
|   `-- routes.py
|-- config/
|   |-- __init__.py
|   `-- settings.py
|-- database/
|   |-- __init__.py
|   |-- connection.py
|   `-- models.py
|-- scripts/
|   `-- reset_seed_passwords.py
|-- tests/
`-- .env              (your local copy, never committed)
```

## How The App Is Organized

### `main.py`

This is the Streamlit entry point. It:

- sets the page configuration
- initializes the database
- injects UI styling
- routes users to the correct dashboard based on role

### `database/connection.py`

This file opens the SQLite connection (`complaint_portal.db` in the working directory) and returns rows as dictionaries.
The rest of the app uses `get_connection()` from here.

### `database/models.py`

Despite the name, this file currently does more than just models. It contains:

- table creation logic
- user registration and login logic
- complaint CRUD operations
- timeline/history operations
- admin and manager actions
- dashboard stats queries

### `config/settings.py`

This file stores:

- predefined admin and manager accounts (their seed passwords are read from `.env`)
- category-to-manager mapping
- complaint statuses
- priority keyword rules
- password rules and the student ID generator

### `app/pages/`

These files handle the Streamlit dashboards:

- `auth.py` for login and student registration
- `student.py` for complaint submission, ticket viewing, and status tracking
- `manager.py` for complaint handling and updates
- `admin.py` for monitoring, approvals, and final closure

### `api/routes.py`

This is the optional FastAPI layer for exposing the same system through REST endpoints.

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/saxenamayank-20/College_Complaint_Portal.git
cd College_Complaint_Portal
```

### 2. Create and activate a virtual environment

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure `.env`

Create a file named `.env` in the project folder with these variables:

```
ADMIN_SEED_PASSWORD=
GM001_PASSWORD=
GM002_PASSWORD=
GM003_PASSWORD=
GM004_PASSWORD=
```

Set strong, unique values for `ADMIN_SEED_PASSWORD` and `GM001_PASSWORD` … `GM004_PASSWORD`.
These are used to create the admin and grievance manager accounts on first run. An account whose
password is empty is skipped. No passwords are stored in the code.

If the database already exists and you change these values, apply them with:

```bash
python scripts/reset_seed_passwords.py
```

### 5. Run the App

The SQLite database file (`complaint_portal.db`) will be created automatically on first run.

```bash
streamlit run main.py
```

No additional database configuration is needed.

### 6. Run the tests

```bash
pytest
```

## Running The Project

### Run the Streamlit app

```bash
streamlit run main.py
```

Default local URL:

`http://localhost:8501`

### Run the FastAPI backend

If you want the API too:

```bash
uvicorn api.routes:app --reload --port 8000
```

API docs:

`http://localhost:8000/docs`

## User Roles In The System

### Student

- Create an account
- Log in
- Submit complaints
- View previous complaints
- Track complaint progress and timeline

### Grievance Manager

- View assigned complaints
- Update status
- Add remarks
- Post updates to admin
- Request final closure after resolution

### Admin

- View all active complaints by category
- Monitor complaint statistics
- Review manager updates
- Approve or force final complaint closure

## Important Notes

- `database/models.py` is currently acting as both schema setup and database service layer.
- `database/connection.py` should not be removed unless the database layer is refactored.
- The API is optional. The Streamlit app works as the main interface.
- On first run, `init_db()` creates the required tables automatically.

## Possible Future Cleanup

Next I'm moving it to a FastAPI backend with JWT auth, PostgreSQL and a React frontend, then adding AI features.

## License

This project is currently suitable for educational and personal use unless you add a separate license.
