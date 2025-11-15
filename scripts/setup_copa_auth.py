#!/usr/bin/env python3
"""
Copa Airlines Authentication Setup Script

This script creates the initial authentication setup for Copa Airlines:
1. Verifies Copa Airlines tenant exists
2. Creates initial admin user
3. Generates initial API key
4. Displays credentials (SAVE THESE!)

Run this ONCE after running the database migration.

Usage:
    python scripts/setup_copa_auth.py

Environment variables required:
    NEON_DATABASE_URL - PostgreSQL connection string
"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger

from app.auth.utils import AuthDatabase
from app.core.security import generate_api_key, hash_api_key, hash_password

# Load environment variables
load_dotenv()

# Configuration
NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL")
COPA_CODE = "copa"
COPA_IATA = "CM"

# Initial admin user details
ADMIN_EMAIL = "admin@copaair.com"
ADMIN_PASSWORD = "Copa2024!Admin"  # CHANGE THIS IN PRODUCTION!
ADMIN_FIRST_NAME = "System"
ADMIN_LAST_NAME = "Administrator"

# Initial API key details
API_KEY_NAME = "Copa Airlines Production API Key"
API_KEY_ROLE = "airline_admin"


async def setup_copa_auth():
    """
    Set up Copa Airlines authentication

    Creates:
    1. Copa Airlines tenant (if not exists)
    2. Initial admin user
    3. Initial API key
    """
    if not NEON_DATABASE_URL:
        logger.error("NEON_DATABASE_URL environment variable not set")
        logger.error("Please set NEON_DATABASE_URL in your .env file")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("COPA AIRLINES AUTHENTICATION SETUP")
    logger.info("=" * 70)

    # Initialize database
    auth_db = AuthDatabase(NEON_DATABASE_URL)
    await auth_db.connect()

    try:
        # ====================================================================
        # STEP 1: Verify Copa Airlines tenant
        # ====================================================================
        logger.info("\n📋 Step 1: Verifying Copa Airlines tenant...")

        copa_airline = await auth_db.get_airline_by_code(COPA_CODE)

        if not copa_airline:
            logger.warning("Copa Airlines not found. Creating tenant...")
            copa_airline = await auth_db.create_airline(
                name="Copa Airlines",
                code=COPA_CODE,
                iata_code=COPA_IATA,
                status="active",
                max_api_keys=20,
                max_users=100
            )
            logger.success(f"✅ Created Copa Airlines tenant (ID: {copa_airline['id']})")
        else:
            logger.success(f"✅ Copa Airlines tenant found (ID: {copa_airline['id']})")

        airline_id = copa_airline['id']

        # ====================================================================
        # STEP 2: Create initial admin user
        # ====================================================================
        logger.info("\n👤 Step 2: Creating initial admin user...")
        logger.info(f"   Email: {ADMIN_EMAIL}")

        try:
            user_data = await auth_db.create_user(
                airline_id=airline_id,
                email=ADMIN_EMAIL,
                password=ADMIN_PASSWORD,
                first_name=ADMIN_FIRST_NAME,
                last_name=ADMIN_LAST_NAME,
                role="system_admin"
            )
            logger.success(f"✅ Created admin user (ID: {user_data['id']})")

            # Save user ID for API key creation
            admin_user_id = user_data['id']

        except Exception as e:
            if "duplicate key value" in str(e).lower() or "unique constraint" in str(e).lower():
                logger.warning(f"⚠️  Admin user {ADMIN_EMAIL} already exists")
                # Get existing user
                import asyncpg
                async with auth_db._pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT id FROM users WHERE email = $1",
                        ADMIN_EMAIL
                    )
                    admin_user_id = row['id'] if row else None
            else:
                raise

        # ====================================================================
        # STEP 3: Generate initial API key
        # ====================================================================
        logger.info("\n🔑 Step 3: Generating initial API key...")
        logger.info(f"   Name: {API_KEY_NAME}")
        logger.info(f"   Role: {API_KEY_ROLE}")

        api_key_record, plain_api_key = await auth_db.create_api_key(
            airline_id=airline_id,
            name=API_KEY_NAME,
            role=API_KEY_ROLE,
            created_by=admin_user_id,
            expires_days=None  # Never expires
        )

        logger.success(f"✅ Created API key (ID: {api_key_record['id']})")

        # ====================================================================
        # DISPLAY CREDENTIALS
        # ====================================================================
        logger.info("\n" + "=" * 70)
        logger.info("🎉 SETUP COMPLETE!")
        logger.info("=" * 70)
        logger.info("\n⚠️  IMPORTANT: Save these credentials securely!")
        logger.info("\n📧 ADMIN USER CREDENTIALS:")
        logger.info(f"   Email:    {ADMIN_EMAIL}")
        logger.info(f"   Password: {ADMIN_PASSWORD}")
        logger.info("   Role:     system_admin")
        logger.info("\n   👉 CHANGE THE PASSWORD after first login!")
        logger.info("   👉 Use these credentials to log in to the dashboard")

        logger.info("\n🔑 API KEY:")
        logger.info(f"   Name: {API_KEY_NAME}")
        logger.info(f"   Key:  {plain_api_key}")
        logger.info("   Role: airline_admin")
        logger.info("\n   👉 This key will NOT be shown again!")
        logger.info("   👉 Use this in the X-API-Key header for API requests")

        logger.info("\n📝 EXAMPLE API REQUEST:")
        logger.info("   curl -H 'X-API-Key: " + plain_api_key + "' \\")
        logger.info("        http://localhost:8000/api/v1/bags")

        logger.info("\n📝 EXAMPLE LOGIN REQUEST:")
        logger.info("   curl -X POST http://localhost:8000/auth/login \\")
        logger.info("        -H 'Content-Type: application/json' \\")
        logger.info(f"        -d '{{\"email\":\"{ADMIN_EMAIL}\",\"password\":\"{ADMIN_PASSWORD}\"}}'")

        logger.info("\n📚 NEXT STEPS:")
        logger.info("   1. Add to your .env file:")
        logger.info(f"      COPA_API_KEY={plain_api_key}")
        logger.info("   2. Generate JWT_SECRET and SECRET_KEY:")
        logger.info("      python -c 'import secrets; print(secrets.token_urlsafe(32))'")
        logger.info("   3. Test authentication:")
        logger.info("      python scripts/test_auth.py")
        logger.info("   4. Deploy to Railway with environment variables")

        logger.info("\n" + "=" * 70)

        # Save to file for reference
        credentials_file = Path(__file__).parent.parent / "COPA_CREDENTIALS.txt"
        with open(credentials_file, "w") as f:
            f.write("=" * 70 + "\n")
            f.write("COPA AIRLINES CREDENTIALS\n")
            f.write("=" * 70 + "\n\n")
            f.write("ADMIN USER:\n")
            f.write(f"  Email:    {ADMIN_EMAIL}\n")
            f.write(f"  Password: {ADMIN_PASSWORD}\n")
            f.write("  Role:     system_admin\n\n")
            f.write("API KEY:\n")
            f.write(f"  Name: {API_KEY_NAME}\n")
            f.write(f"  Key:  {plain_api_key}\n")
            f.write("  Role: airline_admin\n\n")
            f.write("⚠️  DELETE THIS FILE after saving credentials securely!\n")

        logger.info(f"💾 Credentials saved to: {credentials_file}")
        logger.info("   ⚠️  DELETE this file after saving credentials securely!")

    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        await auth_db.disconnect()


if __name__ == "__main__":
    logger.info("Starting Copa Airlines authentication setup...")
    asyncio.run(setup_copa_auth())
