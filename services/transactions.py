
from datetime import datetime, timezone
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import PyMongoError

URI = "mongodb://127.0.0.1:27017/?replicaSet=rs0"
DB_NAME = "hotel_housekeeping"

client = MongoClient(URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]


def assign_housekeeping_task(room_number, employee_id):
    """
    Atomically update a room and create its housekeeping task.
    Both writes commit together or are rolled back together.
    """

    transaction_id = f"HK-{uuid4().hex[:12].upper()}"
    now = datetime.now(timezone.utc)

    try:
        with client.start_session() as session:
            with session.start_transaction():
                room = db.masterData.find_one(
                    {"room_number": int(room_number)},
                    session=session,
                )

                if room is None:
                    raise ValueError("Room does not exist.")

                employee = db.users.find_one(
                    {
                        "employee_id": employee_id,
                        "active": True,
                        "role": "housekeeper",
                    },
                    session=session,
                )

                if employee is None:
                    raise ValueError(
                        "Active housekeeping employee not found."
                    )

                if room["housekeeping_status"] in {
                    "in_progress",
                    "inspection",
                }:
                    raise ValueError(
                        "Room is already being cleaned or inspected."
                    )

                result = db.masterData.update_one(
                    {
                        "_id": room["_id"],
                        "housekeeping_status": room[
                            "housekeeping_status"
                        ],
                    },
                    {
                        "$set": {
                            "housekeeping_status": "in_progress"
                        }
                    },
                    session=session,
                )

                if result.modified_count != 1:
                    raise ValueError(
                        "Room status changed; retry the assignment."
                    )

                task = {
                    "transaction_id": transaction_id,
                    "type": "housekeeping",
                    "room_id": room["_id"],
                    "room_number": int(room_number),
                    "assigned_to": employee["_id"],
                    "employee_id": employee_id,
                    "status": "in_progress",
                    "priority": "medium",
                    "cleaning_minutes": None,
                    "checklist": [
                        {"item": "Bed and linen", "completed": False},
                        {"item": "Bathroom", "completed": False},
                        {
                            "item": "Floor and surfaces",
                            "completed": False,
                        },
                    ],
                    "created_at": now,
                    "completed_at": None,
                }

                db.transactions.insert_one(
                    task,
                    session=session,
                )

        return {
            "success": True,
            "transaction_id": transaction_id,
            "message": "Task assigned successfully.",
        }

    except ValueError:
        raise
    except PyMongoError as error:
        raise RuntimeError(
            f"Housekeeping transaction failed: {error}"
        ) from error


if __name__ == "__main__":
    print(
        "Transaction service loaded. "
        "Use assign_housekeeping_task() to create a task."
    )
