"""
Seed script — creates 3 test users in Appwrite (Auth) and their files
(Database documents, with per-document read permission scoped to the owner).

Run with: python seed.py
Safe to run multiple times: existing users/files are skipped, not duplicated.
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from appwrite.client import Client
from appwrite.services.users import Users
from appwrite.services.databases import Databases
from appwrite.id import ID
from appwrite.permission import Permission
from appwrite.role import Role
from appwrite.exception import AppwriteException

load_dotenv()

client = Client()
client.set_endpoint(os.getenv("APPWRITE_ENDPOINT"))
client.set_project(os.getenv("APPWRITE_PROJECT_ID"))
client.set_key(os.getenv("APPWRITE_API_KEY"))

users_service = Users(client)
databases_service = Databases(client)

DATABASE_ID = os.getenv("APPWRITE_DATABASE_ID")
FILES_COLLECTION_ID = os.getenv("APPWRITE_FILES_COLLECTION_ID")

SEED_USERS = [
    {
        "email": "alice@example.com",
        "password": "Password123!",
        "name": "Alice Nakamura",
        "files": [
            {"fileName": "resume_alice.pdf", "mimeType": "application/pdf", "sizeBytes": 84213,
             "content": "This is a mock PDF resume for Alice."},
            {"fileName": "profile_photo.jpg", "mimeType": "image/jpeg", "sizeBytes": 231044,
             "content": "(binary image content stand-in)"},
        ],
    },
    {
        "email": "bob@example.com",
        "password": "Password123!",
        "name": "Bob Alvarez",
        "files": [
            {"fileName": "project_notes.txt", "mimeType": "text/plain", "sizeBytes": 5210,
             "content": "Project notes: remember to fix the login bug."},
            {"fileName": "invoice_march.pdf", "mimeType": "application/pdf", "sizeBytes": 62890,
             "content": "(mock invoice PDF content)"},
        ],
    },
    {
        "email": "carol@example.com",
        "password": "Password123!",
        "name": "Carol Whitfield",
        "files": [
            {"fileName": "test_plan.docx", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             "sizeBytes": 41200, "content": "(mock test plan doc content)"},
            {"fileName": "vacation.png", "mimeType": "image/png", "sizeBytes": 512300,
             "content": "(binary image content stand-in)"},
        ],
    },
]


def find_existing_user(email):
    result = users_service.list(queries=[f'equal("email", ["{email}"])'])
    if result["total"] > 0:
        return result["users"][0]
    return None


def run():
    for entry in SEED_USERS:
        existing = find_existing_user(entry["email"])

        if existing:
            user_id = existing["$id"]
            print(f"SKIP user  {entry['email']} (already exists, id={user_id})")
        else:
            new_user = users_service.create(
                user_id=ID.unique(),
                email=entry["email"],
                password=entry["password"],
                name=entry["name"],
            )
            user_id = new_user["$id"]
            print(f"CREATED user {entry['email']} (id={user_id})")

        for f in entry["files"]:
            try:
                databases_service.create_document(
                    database_id=DATABASE_ID,
                    collection_id=FILES_COLLECTION_ID,
                    document_id=ID.unique(),
                    data={
                        "ownerId": user_id,
                        "fileName": f["fileName"],
                        "mimeType": f["mimeType"],
                        "sizeBytes": f["sizeBytes"],
                        "content": f["content"],
                        "uploadedAt": datetime.now(timezone.utc).isoformat(),
                    },
                    permissions=[
                        Permission.read(Role.user(user_id)),
                    ],
                )
                print(f"  + file {f['fileName']}")
            except AppwriteException as e:
                print(f"  ! skipped file {f['fileName']}: {e.message}")

    print("\nSeed complete. Test credentials (all use the same password):")
    for entry in SEED_USERS:
        print(f"  {entry['email']} / {entry['password']}")


if __name__ == "__main__":
    run()