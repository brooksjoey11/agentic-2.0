#!/usr/bin/env python3
"""
Create Admin User Script
Promotes a user to admin role
"""

import asyncio
import asyncpg
import os
import sys
from getpass import getpass


async def create_admin():
    """Create admin user"""
    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        db_url = "postgresql://agentic:agentic123@localhost:5432/agentic"
    
    # Get email from command line or prompt
    if len(sys.argv) > 1:
        email = sys.argv[1]
    else:
        email = input("Enter user email to promote to admin: ")
    
    # Connect to database
    conn = await asyncpg.connect(db_url)
    
    try:
        # Check if user exists
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE email = $1",
            email
        )
        
        if not user:
            print(f"❌ User {email} not found")
            return
        
        # Update role
        await conn.execute(
            "UPDATE users SET role = 'admin', updated_at = NOW() WHERE email = $1",
            email
        )
        
        print(f"✅ User {email} promoted to admin")
        
        # Log audit entry
        await conn.execute("""
            INSERT INTO conversations (session_id, role, content, metadata)
            VALUES ($1, $2, $3, $4)
        """,
            "system",
            "system",
            f"User {email} promoted to admin",
            {"action": "create_admin", "email": email}
        )
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(create_admin())