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
                ("admin@shopmate.ai", "admin", "admin123", "admin"),
                ("support@shopmate.ai", "support", "support123", "support"),
                ("niranjan@shopmate.ai", "niranjan", "niranjan123", "customer")
            ]
            for email, uname, default_pw, role_val in known_accounts:
                user_row = conn.execute(
                    text("SELECT id, password_hash, hashed_password FROM users WHERE email = :email OR username = :uname"),
                    {"email": email, "uname": uname}
                ).fetchone()
                if user_row:
                    uid, phash, hpass = user_row[0], user_row[1], user_row[2]
                    needs_update = not (phash and phash.startswith("$2b$") and hpass and hpass.startswith("$2b$"))
                    if needs_update:
                        new_bcrypt = get_password_hash(default_pw)
                        conn.execute(
                            text("UPDATE users SET password_hash = :nh, hashed_password = :nh WHERE id = :uid"),
                            {"nh": new_bcrypt, "uid": uid}
                        )
                        conn.commit()
                        logger.info(f"Synchronized user {email} ({uname}) password hashes to bcrypt.")

            # Ensure all users have both password_hash and hashed_password set
            conn.execute(text("UPDATE users SET password_hash = hashed_password WHERE (password_hash IS NULL OR password_hash = '') AND hashed_password IS NOT NULL"))
            conn.execute(text("UPDATE users SET hashed_password = password_hash WHERE (hashed_password IS NULL OR hashed_password = '') AND password_hash IS NOT NULL"))
            conn.commit()

        logger.info("Authentication schema migration completed successfully.")
    except Exception as e:
        logger.error(f"Error during auth users migration: {e}")

if __name__ == "__main__":
    migrate_users_table()
