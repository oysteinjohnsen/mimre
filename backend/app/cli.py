"""Admin commands (run on the server). There is no public sign-up; accounts are created here.

    uv run python -m app.cli create-user you@example.com
    uv run python -m app.cli set-password you@example.com
    uv run python -m app.cli set-email old@example.com new@example.com
    uv run python -m app.cli list-users
    uv run python -m app.cli delete-user someone@example.com

Passwords are asked for interactively (or read from stdin with --password-stdin).
These commands connect as the database owner (ADMIN_DATABASE_URL).
"""

import argparse
import getpass
import sys

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session

from app.auth import MIN_PASSWORD_LENGTH, hash_password
from app.config import settings
from app.models import AuthSession, Person, User


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass.getpass("Password: ")
        if getpass.getpass("Repeat password: ") != password:
            sys.exit("Passwords don't match.")
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    return password


def _find(session: Session, email: str) -> User:
    user = session.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        sys.exit(f"No user with email {email}.")
    return user


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Mimre admin commands")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("create-user", help="create an account")
    p.add_argument("email")
    p.add_argument("--password-stdin", action="store_true")
    p = sub.add_parser("set-password", help="set a new password (logs out all devices)")
    p.add_argument("email")
    p.add_argument("--password-stdin", action="store_true")
    p = sub.add_parser("set-email", help="change an account's email")
    p.add_argument("email")
    p.add_argument("new_email")
    sub.add_parser("list-users", help="list accounts")
    p = sub.add_parser("delete-user", help="delete an account and ALL its data")
    p.add_argument("email")
    p.add_argument("--yes", action="store_true", help="don't ask for confirmation")
    args = parser.parse_args(argv)

    engine = create_engine(settings.admin_database_url)
    with Session(engine) as session:
        if args.command == "create-user":
            email = args.email.strip().lower()
            if "@" not in email:
                sys.exit("That doesn't look like an email address.")
            if session.scalar(select(User).where(User.email == email)):
                sys.exit(f"A user with email {email} already exists.")
            session.add(User(email=email, password_hash=hash_password(_read_password(args.password_stdin))))
            session.commit()
            print(f"Created user {email}.")

        elif args.command == "set-password":
            user = _find(session, args.email)
            user.password_hash = hash_password(_read_password(args.password_stdin))
            user.failed_logins = 0
            user.locked_until = None
            session.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
            session.commit()
            print(f"Password updated for {user.email}; all devices logged out.")

        elif args.command == "set-email":
            user = _find(session, args.email)
            new_email = args.new_email.strip().lower()
            if session.scalar(select(User).where(User.email == new_email)):
                sys.exit(f"A user with email {new_email} already exists.")
            user.email = new_email
            session.commit()
            print(f"Email changed to {new_email}.")

        elif args.command == "list-users":
            rows = session.execute(
                select(User.email, User.created_at, User.last_login_at, func.count(Person.id))
                .outerjoin(Person, Person.owner_id == User.id)
                .group_by(User.id)
                .order_by(User.created_at)
            )
            for email, created, last_login, people in rows:
                last = last_login.strftime("%Y-%m-%d %H:%M") if last_login else "never"
                print(f"{email:40} people: {people:<5} created: {created:%Y-%m-%d}  last login: {last}")

        elif args.command == "delete-user":
            user = _find(session, args.email)
            if not args.yes and input(f"Delete {user.email} and ALL their data? Type the email to confirm: ") != user.email:
                sys.exit("Not confirmed.")
            session.delete(user)
            session.commit()
            print(f"Deleted {user.email} and their data.")


if __name__ == "__main__":
    main()
