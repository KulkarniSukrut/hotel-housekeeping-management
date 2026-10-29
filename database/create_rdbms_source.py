
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "rdbms_source.db"


def create_source_database():
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    connection.executescript("""
    DROP TABLE IF EXISTS checklist_items;
    DROP TABLE IF EXISTS tasks;
    DROP TABLE IF EXISTS rooms;
    DROP TABLE IF EXISTS staff;

    CREATE TABLE rooms (
        id INTEGER PRIMARY KEY,
        room_number INTEGER UNIQUE NOT NULL,
        room_type TEXT NOT NULL,
        housekeeping_status TEXT NOT NULL
    );

    CREATE TABLE staff (
        id INTEGER PRIMARY KEY,
        employee_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        role TEXT NOT NULL
    );

    CREATE TABLE tasks (
        id INTEGER PRIMARY KEY,
        task_code TEXT UNIQUE NOT NULL,
        room_id INTEGER NOT NULL,
        staff_id INTEGER,
        status TEXT NOT NULL,
        cleaning_minutes INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY (room_id) REFERENCES rooms(id),
        FOREIGN KEY (staff_id) REFERENCES staff(id)
    );

    CREATE TABLE checklist_items (
        id INTEGER PRIMARY KEY,
        task_id INTEGER NOT NULL,
        item TEXT NOT NULL,
        completed INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (task_id) REFERENCES tasks(id)
    );
    """)

    rooms = [
        (1, 101, "Deluxe", "clean"),
        (2, 102, "Standard", "dirty"),
        (3, 103, "Suite", "inspection"),
        (4, 104, "Standard", "clean"),
        (5, 105, "Deluxe", "dirty"),
    ]

    staff = [
        (1, "EMP001", "Ananya Rao", "supervisor"),
        (2, "EMP002", "Priya Nair", "housekeeper"),
        (3, "EMP003", "Arjun Kumar", "housekeeper"),
    ]

    tasks = [
        (1, "SQL-HK001", 1, 2, "completed", 35, "2026-10-20T09:00:00"),
        (2, "SQL-HK002", 2, 3, "assigned", None, "2026-10-20T10:00:00"),
        (3, "SQL-HK003", 3, 2, "completed", 55, "2026-10-20T11:00:00"),
        (4, "SQL-HK004", 4, 3, "pending", None, "2026-10-20T12:00:00"),
        (5, "SQL-HK005", 5, 2, "in_progress", None, "2026-10-20T13:00:00"),
    ]

    checklist = [
        (1, 1, "Bathroom", 1),
        (2, 1, "Bed and linen", 1),
        (3, 1, "Floor and surfaces", 1),
        (4, 2, "Bathroom", 0),
        (5, 2, "Bed and linen", 0),
        (6, 3, "Bathroom", 1),
        (7, 3, "Bed and linen", 1),
        (8, 3, "Floor and surfaces", 0),
        (9, 4, "Bathroom", 0),
        (10, 5, "Bathroom", 1),
    ]

    connection.executemany("INSERT INTO rooms VALUES (?, ?, ?, ?)", rooms)
    connection.executemany("INSERT INTO staff VALUES (?, ?, ?, ?)", staff)
    connection.executemany("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?)", tasks)
    connection.executemany(
        "INSERT INTO checklist_items VALUES (?, ?, ?, ?)", checklist
    )

    connection.commit()

    for table in ("rooms", "staff", "tasks", "checklist_items"):
        count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
        print(f"{table}: {count} rows")

    connection.close()
    print(f"\nSQLite source created at: {DB_PATH}")


if __name__ == "__main__":
    create_source_database()
