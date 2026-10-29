
from datetime import datetime, timezone

from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError

MONGO_URI = "mongodb://127.0.0.1:27017/?replicaSet=rs0"
DB_NAME = "hotel_housekeeping"

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]

rooms = db["masterData"]
users = db["users"]
tasks = db["transactions"]


# -------------------------
# ROOM CRUD
# -------------------------

def get_rooms(status=None):
    query = {}

    if status:
        query["housekeeping_status"] = status

    return list(
        rooms.find(query).sort("room_number", ASCENDING)
    )


def create_room(
    room_number,
    room_type,
    floor,
    capacity,
    price_per_night,
):
    room = {
        "room_number": int(room_number),
        "type": room_type,
        "floor": int(floor),
        "capacity": int(capacity),
        "price_per_night": float(price_per_night),
        "housekeeping_status": "clean",
        "amenities": [],
        "created_at": datetime.now(timezone.utc),
    }

    try:
        result = rooms.insert_one(room)
        return str(result.inserted_id)
    except DuplicateKeyError:
        raise ValueError(
            f"Room {room_number} already exists."
        )


def update_room(room_number, updates):
    allowed_fields = {
        "type",
        "floor",
        "capacity",
        "price_per_night",
        "amenities",
    }

    if not updates or not set(updates).issubset(allowed_fields):
        raise ValueError("Invalid room update fields.")

    result = rooms.update_one(
        {"room_number": int(room_number)},
        {"$set": updates},
    )

    return result.modified_count


def delete_room(room_number):
    # Protect rooms with associated housekeeping history.
    room = rooms.find_one(
        {"room_number": int(room_number)},
        {"_id": 1},
    )

    if room is None:
        return False

    if tasks.find_one({"room_id": room["_id"]}):
        raise ValueError(
            "Cannot delete this room because it has "
            "housekeeping task history."
        )

    result = rooms.delete_one({"_id": room["_id"]})
    return result.deleted_count == 1


# -------------------------
# STAFF CRUD
# -------------------------

def get_staff(active_only=True):
    query = {"active": True} if active_only else {}

    return list(
        users.find(query).sort("employee_id", ASCENDING)
    )


def create_staff(employee_id, name, role):
    result = users.insert_one({
        "employee_id": employee_id,
        "name": name,
        "role": role,
        "active": True,
        "created_at": datetime.now(timezone.utc),
    })

    return str(result.inserted_id)


def update_staff(employee_id, updates):
    allowed_fields = {"name", "role", "active"}

    if not updates or not set(updates).issubset(allowed_fields):
        raise ValueError("Invalid staff update fields.")

    result = users.update_one(
        {"employee_id": employee_id},
        {"$set": updates},
    )

    return result.modified_count


# -------------------------
# TASK READ OPERATIONS
# -------------------------

def get_tasks(status=None, limit=100):
    query = {}

    if status:
        query["status"] = status

    limit = max(1, min(int(limit), 500))

    return list(
        tasks.find(query)
        .sort("created_at", -1)
        .limit(limit)
    )


def get_summary():
    return {
        "total_rooms": rooms.count_documents({}),
        "total_staff": users.count_documents({"active": True}),
        "total_tasks": tasks.count_documents({}),
        "completed_tasks": tasks.count_documents({
            "status": "completed"
        }),
        "pending_tasks": tasks.count_documents({
            "status": "pending"
        }),
    }
