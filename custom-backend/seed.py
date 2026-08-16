"""
Seed script — creates 3 test users with profiles and files.
Run with: python seed.py

Safe to run multiple times: existing users are skipped, not duplicated.
"""

from datetime import datetime

from app.database import SessionLocal, Base, engine
from app.models import User, File
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Make sure tables exist (harmless if they already do)
Base.metadata.create_all(bind=engine)

SEED_USERS = [
    {
        "email": "alice@example.com",
        "password": "Password123!",
        "full_name": "Alice Nakamura",
        "display_name": "alice",
        "bio": "Product designer who likes clean UIs.",
        "files": [
            {"file_name": "resume_alice.pdf", "mime_type": "application/pdf", "size_bytes": 84213,
             "content": "This is a mock PDF resume for Alice."},
            {"file_name": "profile_photo.jpg", "mime_type": "image/jpeg", "size_bytes": 231044,
             "content": "(binary image content stand-in)"},
        ],
    },
    {
        "email": "bob@example.com",
        "password": "Password123!",
        "full_name": "Bob Alvarez",
        "display_name": "bob",
        "bio": "Backend engineer, coffee enthusiast.",
        "files": [
            {"file_name": "project_notes.txt", "mime_type": "text/plain", "size_bytes": 5210,
             "content": "Project notes: remember to fix the login bug."},
            {"file_name": "invoice_march.pdf", "mime_type": "application/pdf", "size_bytes": 62890,
             "content": "(mock invoice PDF content)"},
        ],
    },
    {
        "email": "carol@example.com",
        "password": "Password123!",
        "full_name": "Carol Whitfield",
        "display_name": "carol",
        "bio": "QA lead focused on security testing.",
        "files": [
            {"file_name": "test_plan.docx", "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             "size_bytes": 41200, "content": "(mock test plan doc content)"},
            {"file_name": "vacation.png", "mime_type": "image/png", "size_bytes": 512300,
             "content": "(binary image content stand-in)"},
        ],
    },
]


def run():
    db = SessionLocal()
    try:
        for entry in SEED_USERS:
            existing = db.query(User).filter(User.email == entry["email"]).first()
            if existing:
                print(f"SKIP  {entry['email']} (already exists)")
                continue

            user = User(
                email=entry["email"],
                password_hash=pwd_context.hash(entry["password"]),
                full_name=entry["full_name"],
                display_name=entry["display_name"],
                bio=entry["bio"],
                role="user",
                created_at=datetime.utcnow(),
            )
            db.add(user)
            db.flush()  # get user.id before creating files

            for f in entry["files"]:
                db.add(File(
                    owner_id=user.id,
                    file_name=f["file_name"],
                    mime_type=f["mime_type"],
                    size_bytes=f["size_bytes"],
                    content=f["content"],
                    uploaded_at=datetime.utcnow(),
                ))

            db.commit()
            print(f"CREATED {entry['email']} with {len(entry['files'])} files")

        print("\nSeed complete. Test credentials (all use the same password):")
        for entry in SEED_USERS:
            print(f"  {entry['email']} / {entry['password']}")
    finally:
        db.close()


if __name__ == "__main__":
    run()