
from datetime import datetime, timedelta, timezone
from random import Random

from pymongo import MongoClient, ASCENDING

URI = "mongodb://127.0.0.1:27017/?replicaSet=rs0"
DB_NAME = "hotel_housekeeping"

rng = Random(42)
now = datetime.now(timezone.utc)

STAFF = [
    ("EMP001", "Ananya Rao", "manager"),
    ("EMP002", "Rahul Sharma", "supervisor"),
    ("EMP003", "Priya Nair", "housekeeper"),
    ("EMP004", "Arjun Kumar", "housekeeper"),
    ("EMP005", "Meera Iyer", "housekeeper"),
    ("EMP006", "Karan Singh", "housekeeper"),
    ("EMP007", "Sneha Das", "housekeeper"),
    ("EMP008", "Vikram Joshi", "housekeeper"),
]

ROOM_TYPES = ["Standard", "Deluxe", "Suite"]
ROOM_STATUSES = ["clean", "dirty", "in_progress", "inspection"]

TASK_STATUSES = ["completed", "assigned", "in_progress", "pending"]
PRIORITIES = ["low", "medium", "high"]


def seed_database():
    client = MongoClient(URI)
    db = client[DB_NAME]

    try:
        # Idempotent staff seeding: update matching employees,
        # insert missing employees, and retain their _id values.
        for employee_id, name, role in STAFF:
            db.users.update_one(
                {"employee_id": employee_id},
                {
                    "$set": {
                        "name": name,
                        "role": role,
                        "active": True,
                    },
                    "$setOnInsert": {
                        "created_at": now,
                    },
                },
                upsert=True,
            )

        # Create room records only if the room number is absent.
        for number in range(101, 131):
            db.masterData.update_one(
                {"room_number": number},
                {
                    "$setOnInsert": {
                        "type": rng.choice(ROOM_TYPES),
                        "floor": number // 100,
                        "capacity": 2 if number % 3 else 4,
                        "price_per_night": rng.choice(
                            [2500, 3500, 5000, 7500]
                        ),
                        "housekeeping_status": rng.choice(
                            ROOM_STATUSES
                        ),
                        "amenities": rng.sample(
                            ["WiFi", "TV", "AC", "Mini Bar", "Balcony"],
                            k=3,
                        ),
                        "created_at": now,
                    }
                },
                upsert=True,
            )

        staff_ids = {
            user["employee_id"]: user["_id"]
            for user in db.users.find(
                {},
                {"employee_id": 1}
            )
        }

        room_ids = {
            room["room_number"]: room["_id"]
            for room in db.masterData.find(
                {},
                {"room_number": 1}
            )
        }

        # Create 60 tasks, each with a stable unique identifier.
        for number in range(1, 61):
            status = rng.choice(TASK_STATUSES)
            created_at = now - timedelta(
                days=rng.randint(0, 29),
                hours=rng.randint(0, 23),
            )

            employee_id, _, _ = rng.choice(STAFF[2:])
            room_number = rng.randint(101, 130)

            duration = (
                rng.randint(15, 75)
                if status == "completed"
                else None
            )

            db.transactions.update_one(
                {"transaction_id": f"HK{number:04d}"},
                {
                    "$setOnInsert": {
                        "transaction_id": f"HK{number:04d}",
                        "type": "housekeeping",
                        "room_id": room_ids[room_number],
                        "room_number": room_number,
                        "assigned_to": staff_ids[employee_id],
                        "employee_id": employee_id,
                        "status": status,
                        "priority": rng.choice(PRIORITIES),
                        "cleaning_minutes": duration,
                        "checklist": [
                            {
                                "item": "Bed and linen",
                                "completed": status == "completed",
                            },
                            {
                                "item": "Bathroom",
                                "completed": status == "completed",
                            },
                            {
                                "item": "Floor and surfaces",
                                "completed": status == "completed",
                            },
                        ],
                        "created_at": created_at,
                        "completed_at": (
                            created_at + timedelta(minutes=duration)
                            if duration is not None
                            else None
                        ),
                    }
                },
                upsert=True,
            )

        # Add a few sample activity events.
        for number in range(1, 11):
            db.activities.update_one(
                {"activity_id": f"ACT{number:04d}"},
                {
                    "$setOnInsert": {
                        "activity_id": f"ACT{number:04d}",
                        "action": "sample_data_created",
                        "description": "Seed dataset activity",
                        "created_at": now,
                    }
                },
                upsert=True,
            )

        print("Seed completed successfully!")
        print("Users:", db.users.count_documents({}))
        print("Rooms:", db.masterData.count_documents({}))
        print("Housekeeping tasks:", db.transactions.count_documents({}))
        print("Activities:", db.activities.count_documents({}))

    finally:
        client.close()


if __name__ == "__main__":
    seed_database()
