#!/usr/bin/env python3
"""create-admin.py — create an initial admin user in the database."""
import asyncio
import os
import sys

# Ensure project root is on the path when run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.orchestrator.auth import get_password_hash
from src.orchestrator.db.database import AsyncSessionLocal
from sqlalchemy import text


async def create_admin(username: str, password: str) -> None:
    hashed = get_password_hash(password)
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                "INSERT INTO users (username, hashed_password, is_admin) "
                "VALUES (:username, :hashed_password, TRUE) "
                "ON CONFLICT (username) DO NOTHING"
            ),
            {"username": username, "hashed_password": hashed},
        )
        await session.commit()
    print(f"Admin user '{username}' created (or already exists).")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--username", default="admin", help="Admin username")
    parser.add_argument("--password", required=True, help="Admin password")
    args = parser.parse_args()

    asyncio.run(create_admin(args.username, args.password))
