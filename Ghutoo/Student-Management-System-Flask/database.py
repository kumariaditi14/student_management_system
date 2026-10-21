"""Initialize the local SQLite database used by the application."""

import sqlite3
from pathlib import Path

DATABASE = Path(__file__).resolve().parent / "students.db"


def create_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            usn TEXT UNIQUE NOT NULL,
            gender TEXT NOT NULL,
            dob TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            pincode TEXT NOT NULL,
            department TEXT NOT NULL,
            semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
            section TEXT NOT NULL,
            batch TEXT NOT NULL,
            father_name TEXT NOT NULL,
            mother_name TEXT NOT NULL,
            parent_phone TEXT NOT NULL,
            github TEXT,
            linkedin TEXT
        )""")


if __name__ == "__main__":
    create_database()
