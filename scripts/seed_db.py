import os
import uuid
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://uw:uw@localhost:5433/uw")
engine = create_engine(DATABASE_URL)

def seed():
    with engine.begin() as conn:
        # Create 3 sample deals
        for i in range(3):
            deal_id = str(uuid.uuid4())
            stage = "underwriting" if i == 0 else "doc_collection"
            conn.execute(text("""
                INSERT INTO deals (id, stage, created_at) 
                VALUES (:id, :stage, NOW())
                ON CONFLICT (id) DO NOTHING
            """), {"id": deal_id, "stage": stage})
    print("? Seeded 3 sample deals into the database.")
    print("?? Start the UI with: uv run uvicorn src.uw.api.main:app --reload")

if __name__ == "__main__":
    seed()
