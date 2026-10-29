
from pymongo import MongoClient, DESCENDING

MONGO_URI = "mongodb://127.0.0.1:27017/?replicaSet=rs0"
DB_NAME = "hotel_housekeeping"

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]


def pipeline_1_top_5_rooms_by_task_count():
    """Top five rooms by housekeeping task count."""
    return list(db.transactions.aggregate([
        {"$group": {
            "_id": "$room_number",
            "task_count": {"$sum": 1},
        }},
        {"$sort": {"task_count": -1, "_id": 1}},
        {"$limit": 5},
    ]))


def pipeline_2_tasks_by_status_total():
    """Group tasks by status and calculate totals."""
    return list(db.transactions.aggregate([
        {"$group": {
            "_id": "$status",
            "total_tasks": {"$sum": 1},
        }},
        {"$sort": {"total_tasks": -1}},
    ]))


def pipeline_3_average_cleaning_time():
    """Average cleaning duration for completed tasks."""
    return list(db.transactions.aggregate([
        {"$match": {
            "status": "completed",
            "cleaning_minutes": {"$ne": None},
        }},
        {"$group": {
            "_id": None,
            "average_cleaning_minutes": {
                "$avg": "$cleaning_minutes"
            },
        }},
    ]))


def pipeline_4_min_max_cleaning_time():
    """Minimum and maximum completed cleaning durations."""
    return list(db.transactions.aggregate([
        {"$match": {
            "status": "completed",
            "cleaning_minutes": {"$ne": None},
        }},
        {"$group": {
            "_id": None,
            "minimum_minutes": {"$min": "$cleaning_minutes"},
            "maximum_minutes": {"$max": "$cleaning_minutes"},
        }},
    ]))


def pipeline_5_task_status_counts():
    """Count tasks per status, largest group first."""
    return list(db.transactions.aggregate([
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
        }},
        {"$sort": {"count": -1}},
        {"$limit": 1},
    ]))


def pipeline_6_top_5_employees_by_completed_tasks():
    """Top five employees by completed housekeeping tasks."""
    return list(db.transactions.aggregate([
        {"$match": {"status": "completed"}},
        {"$group": {
            "_id": "$employee_id",
            "completed_tasks": {"$sum": 1},
        }},
        {"$sort": {"completed_tasks": -1, "_id": 1}},
        {"$limit": 5},
        {"$lookup": {
            "from": "users",
            "localField": "_id",
            "foreignField": "employee_id",
            "as": "employee",
        }},
        {"$unwind": {
            "path": "$employee",
            "preserveNullAndEmptyArrays": True,
        }},
        {"$project": {
            "_id": 0,
            "employee_id": "$_id",
            "employee_name": "$employee.name",
            "completed_tasks": 1,
        }},
    ]))


def pipeline_7_paginated_task_report(page=1, page_size=10):
    """Paginated task report using skip and limit."""
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 100))
    skip_count = (page - 1) * page_size

    return list(db.transactions.aggregate([
        {"$sort": {"created_at": -1, "_id": 1}},
        {"$skip": skip_count},
        {"$limit": page_size},
        {"$project": {
            "_id": 0,
            "transaction_id": 1,
            "room_number": 1,
            "employee_id": 1,
            "status": 1,
            "created_at": 1,
        }},
    ]))


def pipeline_8_checklist_statistics():
    """Unwind task checklists and count completion per item."""
    return list(db.transactions.aggregate([
        {"$unwind": "$checklist"},
        {"$group": {
            "_id": "$checklist.item",
            "total_occurrences": {"$sum": 1},
            "completed_occurrences": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$checklist.completed", True]},
                        1,
                        0,
                    ]
                }
            },
        }},
        {"$sort": {"total_occurrences": -1, "_id": 1}},
    ]))


def pipeline_9_employee_task_lists():
    """Use push for task lists and addToSet for unique statuses."""
    return list(db.transactions.aggregate([
        {"$group": {
            "_id": "$employee_id",
            "task_ids": {"$push": "$transaction_id"},
            "unique_statuses": {"$addToSet": "$status"},
            "total_tasks": {"$sum": 1},
        }},
        {"$sort": {"total_tasks": -1, "_id": 1}},
    ]))


def pipeline_10_room_task_report():
    """Join rooms with their housekeeping tasks."""
    return list(db.masterData.aggregate([
        {"$lookup": {
            "from": "transactions",
            "localField": "_id",
            "foreignField": "room_id",
            "as": "housekeeping_tasks",
        }},
        {"$project": {
            "_id": 0,
            "room_number": 1,
            "room_type": "$type",
            "housekeeping_status": 1,
            "total_tasks": {"$size": "$housekeeping_tasks"},
            "task_statuses": "$housekeeping_tasks.status",
        }},
        {"$sort": {"room_number": 1}},
    ]))


PIPELINES = {
    1: pipeline_1_top_5_rooms_by_task_count,
    2: pipeline_2_tasks_by_status_total,
    3: pipeline_3_average_cleaning_time,
    4: pipeline_4_min_max_cleaning_time,
    5: pipeline_5_task_status_counts,
    6: pipeline_6_top_5_employees_by_completed_tasks,
    7: pipeline_7_paginated_task_report,
    8: pipeline_8_checklist_statistics,
    9: pipeline_9_employee_task_lists,
    10: pipeline_10_room_task_report,
}


if __name__ == "__main__":
    try:
        client.admin.command("ping")

        for number, function in PIPELINES.items():
            print(f"\n{'=' * 60}")
            print(f"PIPELINE {number}: {function.__doc__}")
            print("=" * 60)

            if number == 7:
                results = function(page=1, page_size=5)
            else:
                results = function()

            for document in results[:10]:
                print(document)

            if not results:
                print("No matching records.")

    finally:
        client.close()
