"""Run as an administrator: python -m scripts.manage_staff add EMAIL"""
import argparse
from getpass import getpass
from sqlalchemy import update, delete, select
from sqlalchemy.exc import IntegrityError
from lostfound.config import load_settings
from lostfound.database import connect_database, initialize, accounts_table, sessions_table
from lostfound.auth import provision_account, hash_password

def main():
    parser = argparse.ArgumentParser(description="Provision/revoke staff. Passwords are never command-line arguments.")
    parser.add_argument("action", choices=["add", "disable", "reset-password"])
    parser.add_argument("email")
    parser.add_argument("--microsoft-identity", help="Approved tenant UUID:object UUID")
    args = parser.parse_args()
    engine = connect_database(load_settings().database_url)
    initialize(engine)
    try:
        if args.action == "add":
            password = None
            if not args.microsoft_identity:
                password = getpass("New app password (not your HKU password): ")
                if password != getpass("Repeat password: "):
                    raise ValueError("Passwords do not match.")
            provision_account(engine, args.email, password, args.microsoft_identity)
        else:
            with engine.begin() as conn:
                account = conn.execute(select(accounts_table).where(
                    accounts_table.c.email == args.email.strip().lower())).mappings().first()
                if not account:
                    raise ValueError("Account not found.")
                changes = {"active": 0}
                if args.action == "reset-password":
                    password = getpass("New app password: ")
                    if password != getpass("Repeat password: "):
                        raise ValueError("Passwords do not match.")
                    changes = dict(password_hash=hash_password(password), failed_attempts=0, locked_until=0)
                conn.execute(update(accounts_table).where(accounts_table.c.id == account["id"]).values(**changes))
                conn.execute(delete(sessions_table).where(sessions_table.c.account_id == account["id"]))
        print("Staff account updated.")
    except IntegrityError:
        raise SystemExit("An account with that email or Microsoft identity already exists.")
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
