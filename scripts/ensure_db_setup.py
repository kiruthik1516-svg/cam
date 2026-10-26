"""Database verification and setup helper for Stage 2 & 3."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import engine  # noqa: E402
from sqlalchemy import text  # noqa: E402


def setup():
    print("Connecting to database...")
    with engine.begin() as conn:
        # 1. Ensure camera IPC56 exists
        conn.execute(
            text("""
            INSERT INTO cameras (id, name, zone, status)
            VALUES ('IPC56', 'RO Water Treatment Plant Rooftop', 'Rooftop Entrance', 'online')
            ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, zone = EXCLUDED.zone;
        """)
        )
        print("Camera 'IPC56' registered / verified.")

        # 2. Check detections table count
        res = conn.execute(text("SELECT count(*) FROM detections")).scalar()
        print(f"Current total detections in DB: {res}")


if __name__ == "__main__":
    setup()

