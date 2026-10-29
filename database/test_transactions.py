
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from services.transactions import assign_housekeeping_task

URI = "mongodb://127.0.0.1:27017/?replicaSet=rs0"
DB_NAME = "hotel_housekeeping"

client = MongoClient(URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]


def test_commit():
    # Select a room that can be assigned.
    room = db.masterData.find_one({
        "housekeeping_status": {"$in": ["clean", "dirty"]}
    })

    employee = db.users.find_one({
        "active": True,
        "role": "housekeeper",
    })

    if room is None or employee is None:
        print("COMMIT TEST SKIPPED: no eligible room or staff.")
        return

    room_number = room["room_number"]
    employee_id = employee["employee_id"]

    print("\n--- COMMIT TEST ---")
    print("Room:", room_number)
    print("Employee:", employee_id)

    result = assign_housekeeping_task(room_number, employee_id)

    updated_room = db.masterData.find_one(
        {"room_number": room_number}
    )
    if updated_room is None:
        raise AssertionError("Room not found after commit.")
    
    saved_task = db.transactions.find_one(
        {"transaction_id": result["transaction_id"]}
    )
    if saved_task is None:
        raise AssertionError("Task was not persisted after commit.")

    assert updated_room["housekeeping_status"] == "in_progress"
    assert saved_task is not None
    assert saved_task["status"] == "in_progress"

    print("Task:", result["transaction_id"])
    print("Room status:", updated_room["housekeeping_status"])
    print("Task persisted:", saved_task is not None)
    print("COMMIT TEST PASSED")


def test_rollback():
    # Choose a separate room so the commit test remains untouched.
    room = db.masterData.find_one({
        "housekeeping_status": {"$in": ["clean", "dirty"]}
    })

    if room is None:
        print("ROLLBACK TEST SKIPPED: no eligible room.")
        return

    room_id = room["_id"]
    original_status = room["housekeeping_status"]

    print("\n--- ROLLBACK TEST ---")
    print("Room:", room["room_number"])
    print("Original status:", original_status)

    try:
        with client.start_session() as session:
            with session.start_transaction():
                db.masterData.update_one(
                    {"_id": room_id},
                    {"$set": {
                        "housekeeping_status": "rollback_test"
                    }},
                    session=session,
                )

                # Deliberately fail before commit.
                raise RuntimeError("Intentional rollback test")

    except RuntimeError as error:
        if str(error) != "Intentional rollback test":
            raise
        print("Expected error:", error)

    final_room = db.masterData.find_one({"_id": room_id})
    if final_room is None:
        raise AssertionError("Room disappeared during rollback test.")

    assert final_room["housekeeping_status"] == original_status
    print("Final status:", final_room["housekeeping_status"])
    print("Original status restored:", True)
    print("ROLLBACK TEST PASSED")


if __name__ == "__main__":
    try:
        client.admin.command("ping")
        test_commit()
        test_rollback()
    except (AssertionError, PyMongoError, RuntimeError) as error:
        print("TEST FAILED:", error)
        raise
    finally:
        client.close()
