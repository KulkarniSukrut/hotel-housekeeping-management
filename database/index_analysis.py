
from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError

URI = "mongodb://127.0.0.1:27017/?replicaSet=rs0"
DB_NAME = "hotel_housekeeping"
INDEX_NAME = "transaction_status_date_idx"

client = MongoClient(URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]
tasks = db.transactions



def run_explain(label):
    query = {
        "find": "transactions",
        "filter": {"status": "completed"},
        "sort": {"created_at": -1},
        "limit": 10,
    }

    explanation = db.command({
        "explain": query,
        "verbosity": "executionStats",
    })

    stats = explanation["executionStats"]
    winning_plan = explanation["queryPlanner"]["winningPlan"]

    print(f"\n--- {label} ---")
    print("Execution time (ms):", stats["executionTimeMillis"])
    print("Documents examined:", stats["totalDocsExamined"])
    print("Documents returned:", stats["nReturned"])
    print("Keys examined:", stats["totalKeysExamined"])
    print("Winning plan:", winning_plan)

    return stats



try:
    client.admin.command("ping")

    # Ensure the index exists before beginning.
    tasks.create_index(
        [("status", 1), ("created_at", DESCENDING)],
        name=INDEX_NAME,
    )

    # Baseline: run without the target compound index.
    tasks.drop_index(INDEX_NAME)
    before = run_explain("BEFORE INDEX")

    # Optimized: restore the compound index.
    tasks.create_index(
        [("status", 1), ("created_at", DESCENDING)],
        name=INDEX_NAME,
    )
    after = run_explain("AFTER INDEX")

    print("\n--- COMPARISON ---")
    print(
        "Documents examined before:",
        before["totalDocsExamined"],
    )
    print(
        "Documents examined after:",
        after["totalDocsExamined"],
    )
    print(
        "Keys examined after:",
        after["totalKeysExamined"],
    )

    if after["totalDocsExamined"] < before["totalDocsExamined"]:
        print("Fewer documents examined after indexing.")
    else:
        print(
            "No reduction in documents examined for this dataset. "
            "Inspect both winning plans and consider dataset size."
        )

finally:
    # Restore the required index even if the comparison fails.
    try:
        tasks.create_index(
            [("status", 1), ("created_at", DESCENDING)],
            name=INDEX_NAME,
        )
    except PyMongoError as error:
        print("WARNING: Could not restore the index:", error)

    client.close()
