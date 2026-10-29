
import sqlite3
from pathlib import Path

from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError

SQLITE_PATH = Path(__file__).resolve().parents[1] / "rdbms_source.db"
MONGO_URI = "mongodb://127.0.0.1:27017/?replicaSet=rs0"
MONGO_DB = "hotel_housekeeping"


def migrate_data():
    if not SQLITE_PATH.exists():
        raise FileNotFoundError(
            f"SQLite source not found: {SQLITE_PATH}. "
            "Run python -m database.create_rdbms_source first."
        )

    sql = sqlite3.connect(SQLITE_PATH)
    sql.row_factory = sqlite3.Row
    mongo = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

    try:
        mongo.admin.command("ping")
        db = mongo[MONGO_DB]

        # Extract relational tables.
        rooms = [dict(row) for row in sql.execute(
            "SELECT * FROM rooms ORDER BY id"
        )]
        staff = [dict(row) for row in sql.execute(
            "SELECT * FROM staff ORDER BY id"
        )]
        tasks = [dict(row) for row in sql.execute(
            "SELECT * FROM tasks ORDER BY id"
        )]
        checklist_rows = [dict(row) for row in sql.execute(
            "SELECT * FROM checklist_items ORDER BY id"
        )]

        # Transform checklist rows into embedded arrays grouped by task.
        checklist_by_task = {}
        for item in checklist_rows:
            checklist_by_task.setdefault(item["task_id"], []).append({
                "item": item["item"],
                "completed": bool(item["completed"]),
            })

        # Transform relational primary keys into stable MongoDB identifiers.
        room_docs = []
        for room in rooms:
            room_docs.append({
                "_id": f"SQL-ROOM-{room['id']}",
                "source_id": room["id"],
                "room_number": room["room_number"],
                "room_type": room["room_type"],
                "housekeeping_status": room["housekeeping_status"],
                "migration_source": "SQLite",
            })

        staff_docs = []
        for person in staff:
            staff_docs.append({
                "_id": f"SQL-STAFF-{person['id']}",
                "source_id": person["id"],
                "employee_id": person["employee_id"],
                "name": person["name"],
                "role": person["role"],
                "migration_source": "SQLite",
            })

        task_docs = []
        for task in tasks:
            task_docs.append({
                "_id": f"SQL-TASK-{task['id']}",
                "source_id": task["id"],
                "task_code": task["task_code"],
                "room_id": f"SQL-ROOM-{task['room_id']}",
                "staff_id": (
                    f"SQL-STAFF-{task['staff_id']}"
                    if task["staff_id"] is not None
                    else None
                ),
                "status": task["status"],
                "cleaning_minutes": task["cleaning_minutes"],
                "created_at": task["created_at"],
                "checklist": checklist_by_task.get(task["id"], []),
                "migration_source": "SQLite",
            })

        # Load using upserts so rerunning the migration does not duplicate data.
        collections = {
            "migration_rooms": room_docs,
            "migration_staff": staff_docs,
            "migration_tasks": task_docs,
        }

        print("\n--- MIGRATION ---")
        for collection_name, documents in collections.items():
            collection = db[collection_name]
            for document in documents:
                collection.replace_one(
                    {"_id": document["_id"]},
                    document,
                    upsert=True,
                )
            print(f"{collection_name}: loaded {len(documents)} documents")

        # Indexes for common lookups.
        db.migration_rooms.create_index(
            [("room_number", ASCENDING)],
            unique=True,
            name="migration_room_number_unique",
        )
        db.migration_staff.create_index(
            [("employee_id", ASCENDING)],
            unique=True,
            name="migration_employee_id_unique",
        )
        db.migration_tasks.create_index(
            [("room_id", ASCENDING)],
            name="migration_task_room_idx",
        )
        db.migration_tasks.create_index(
            [("staff_id", ASCENDING)],
            name="migration_task_staff_idx",
        )

        # Verify document counts and relationship integrity.
        expected = {
            "migration_rooms": len(rooms),
            "migration_staff": len(staff),
            "migration_tasks": len(tasks),
        }

        print("\n--- VERIFICATION ---")
        counts_match = True
        for collection_name, expected_count in expected.items():
            actual_count = db[collection_name].count_documents({
                "migration_source": "SQLite"
            })
            passed = actual_count == expected_count
            counts_match = counts_match and passed
            print(
                f"{collection_name}: source={expected_count}, "
                f"destination={actual_count}, "
                f"{'PASS' if passed else 'FAIL'}"
            )

        room_ids = {
            document["_id"]
            for document in db.migration_rooms.find(
                {}, {"_id": 1}
            )
        }
        staff_ids = {
            document["_id"]
            for document in db.migration_staff.find(
                {}, {"_id": 1}
            )
        }

        invalid_room_refs = db.migration_tasks.count_documents({
            "migration_source": "SQLite",
            "room_id": {"$nin": list(room_ids)},
        })
        invalid_staff_refs = db.migration_tasks.count_documents({
            "migration_source": "SQLite",
            "staff_id": {"$ne": None, "$nin": list(staff_ids)},
        })

        embedded_items = sum(
            len(task.get("checklist", []))
            for task in db.migration_tasks.find(
                {"migration_source": "SQLite"},
                {"checklist": 1},
            )
        )

        print(f"Invalid room references: {invalid_room_refs}")
        print(f"Invalid staff references: {invalid_staff_refs}")
        print(f"Embedded checklist items: {embedded_items}")

        if (
            counts_match
            and invalid_room_refs == 0
            and invalid_staff_refs == 0
            and embedded_items == len(checklist_rows)
        ):
            print("\nMIGRATION VERIFICATION PASSED")
        else:
            print("\nMIGRATION VERIFICATION FAILED")

    except (sqlite3.Error, PyMongoError) as error:
        print(f"Migration error: {error}")
        raise
    finally:
        sql.close()
        mongo.close()


if __name__ == "__main__":
    migrate_data()
