# Ghutoo Student Directory

A lightweight student management web app built with Python 3.14, Flask, SQLite, and ReportLab. It supports student records, search and filters, a dashboard, and CSV/PDF exports.

## Requirements

- Python 3.14 (the project is configured for Python 3.14)
- `pip`

## Setup

Create and activate a virtual environment, then install the app dependencies:

```bash
python3.14 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the application from this directory:

```bash
python app.py
```

Open <http://127.0.0.1:5000>. The app uses `students.db` in this directory. The existing database is retained; to initialize a fresh database, run `python database.py`.

## Features

- Add, browse, search, filter, edit, and remove student records
- Import many records from CSV; rows matching an existing USN update that student
- Dashboard summaries by gender, department, and study year
- Export the directory to CSV or PDF and download individual student profiles
- Responsive interface for desktop and mobile screens
# student_management_system
