
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

MONGO_URI = "mongodb://127.0.0.1:27017/?replicaSet=rs0"
DATABASE_NAME = "hotel_housekeeping"

COLLECTIONS = [
    "users",
    "masterData",
    "transactions",
    "activities",
    "reports",
]


def setup_database():
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000
    )

    try:
        client.admin.command("ping")
        db = client[DATABASE_NAME]

        print("Connected to MongoDB successfully.")

        for name in COLLECTIONS:
            if name not in db.list_collection_names():
                db.create_collection(name)
                print(f"Created collection: {name}")
            else:
                print(f"Collection already exists: {name}")

        # Staff lookup and role filtering
        db.users.create_index(
            [("employee_id", ASCENDING)],
            unique=True,
            name="employee_id_unique"
        )
        db.users.create_index(
            [("role", ASCENDING), ("active", ASCENDING)],
            name="role_active_idx"
        )

        # Room identification and status queries
        db.masterData.create_index(
            [("room_number", ASCENDING)],
            unique=True,
            name="room_number_unique"
        )
        db.masterData.create_index(
            [("type", ASCENDING), ("housekeeping_status", ASCENDING)],
            name="room_type_status_idx"
        )

        # Housekeeping transaction queries and reports
        db.transactions.create_index(
            [("transaction_id", ASCENDING)],
            unique=True,
            name="transaction_id_unique"
        )
        db.transactions.create_index(
            [("status", ASCENDING), ("created_at", DESCENDING)],
            name="transaction_status_date_idx"
        )
        db.transactions.create_index(
            [("room_id", ASCENDING), ("created_at", DESCENDING)],
            name="room_history_idx"
        )

        # Audit history
        db.activities.create_index(
            [("created_at", DESCENDING)],
            name="activity_date_idx"
        )

        print("\nDatabase setup completed!")
        print("Database:", DATABASE_NAME)
        print("Collections:", db.list_collection_names())
        print("Indexes created successfully.")

    except PyMongoError as error:
        print("Database setup failed:", error)
        raise

    finally:
        client.close()


if __name__ == "__main__":
    setup_database()
