import logging
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models.user import User, AuthProvider
from app.auth.security import get_password_hash

logger = logging.getLogger("shopmate.auth.migration")

def migrate_users_table():
    """
    Safely migrates the users table to ensure required authentication columns exist:
    - password_hash
    - auth_provider
    - profile_image
    Also ensures existing user records have password_hash populated and auth_provider set.
    """
    logger.info("Checking authentication schema for 'users' table...")
    try:
        with engine.connect() as conn:
            # Check existing columns
            # For SQLite:
            try:
                res = conn.execute(text("PRAGMA table_info(users)"))
                existing_cols = [row[1] for row in res.fetchall()]
            except Exception:
                # Fallback for PostgreSQL/other DBs
                res = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"
                ))
                existing_cols = [row[0] for row in res.fetchall()]

            if not existing_cols:
                logger.info("Users table does not exist yet. Will be created on model init.")
                return

            # Add missing columns
            if "password_hash" not in existing_cols:
                logger.info("Adding column 'password_hash' to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR"))
                conn.commit()

            if "auth_provider" not in existing_cols:
                logger.info("Adding column 'auth_provider' to users table...")
                conn.execute(text(f"ALTER TABLE users ADD COLUMN auth_provider VARCHAR DEFAULT '{AuthProvider.LOCAL.value}'"))
                conn.commit()

            if "profile_image" not in existing_cols:
                logger.info("Adding column 'profile_image' to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN profile_image VARCHAR"))
                conn.commit()

            # Copy hashed_password into password_hash if password_hash is null
            if "hashed_password" in existing_cols and "password_hash" in existing_cols:
                conn.execute(text(
                    "UPDATE users SET password_hash = hashed_password WHERE (password_hash IS NULL OR password_hash = '') AND hashed_password IS NOT NULL"
                ))
                conn.commit()

            # Set auth_provider to 'local' where null
            conn.execute(text(
                f"UPDATE users SET auth_provider = '{AuthProvider.LOCAL.value}' WHERE auth_provider IS NULL OR auth_provider = ''"
            ))
            conn.commit()

            # Check and upgrade legacy test accounts (admin, support, niranjan) to robust bcrypt hashes if needed
            known_accounts = [
                ("admin@shopmate.ai", "admin123"),
                ("support@shopmate.ai", "support123"),
                ("niranjan@shopmate.ai", "niranjan123")
            ]
            for email, default_pw in known_accounts:
                user_row = conn.execute(text("SELECT id, password_hash FROM users WHERE email = :email"), {"email": email}).fetchone()
                if user_row:
                    uid, phash = user_row[0], user_row[1]
                    if not phash or not phash.startswith("$2b$"):
                        new_bcrypt = get_password_hash(default_pw)
                        conn.execute(
                            text("UPDATE users SET password_hash = :nh WHERE id = :uid"),
                            {"nh": new_bcrypt, "uid": uid}
                        )
                        conn.commit()
                        logger.info(f"Updated user {email} password_hash to bcrypt.")

        logger.info("Authentication schema migration completed successfully.")
    except Exception as e:
        logger.error(f"Error during auth users migration: {e}")

if __name__ == "__main__":
    migrate_users_table()
