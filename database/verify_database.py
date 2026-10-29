
from services.housekeeping import (
    get_rooms,
    get_staff,
    get_tasks,
    get_summary,
)

print("HOTEL HOUSEKEEPING — BACKEND CHECK")
print("=" * 40)

summary = get_summary()

for key, value in summary.items():
    print(f"{key.replace('_', ' ').title()}: {value}")

print("\nFirst 3 rooms:")
for room in get_rooms()[:3]:
    print(
        room["room_number"],
        room["type"],
        room["housekeeping_status"],
    )

print("\nFirst 3 staff members:")
for staff in get_staff()[:3]:
    print(
        staff["employee_id"],
        staff["name"],
        staff["role"],
    )

print("\nFirst 3 housekeeping tasks:")
for task in get_tasks(limit=3):
    print(
        task["transaction_id"],
        task["room_number"],
        task["status"],
    )

print("\nBackend verification complete.")
