"""Create or update an application user.

Usage:
    python -m scripts.create_user --employee-id admin --role admin
    python -m scripts.create_user --employee-id alice --role employee --password-stdin
"""

import argparse
import getpass
import sys

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.repos.user_repository import UserRepository


VALID_ROLES = {"admin", "employee"}


def _read_password(args) -> str:
    if args.password_stdin:
        return sys.stdin.readline().rstrip("\n")

    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")

    if password != confirmation:
        raise SystemExit("Passwords do not match")

    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters")

    return password


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or update a CloudMentor user",
    )
    parser.add_argument(
        "--employee-id",
        required=True,
    )
    parser.add_argument(
        "--role",
        choices=sorted(VALID_ROLES),
        default="employee",
    )
    parser.add_argument(
        "--display-name",
        default=None,
    )
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read the password from stdin instead of prompting",
    )
    parser.add_argument(
        "--deactivate",
        action="store_true",
    )
    args = parser.parse_args()

    db = SessionLocal()

    try:
        repo = UserRepository(db)
        user = repo.get_by_employee_id(
            args.employee_id
        )

        if user is None:
            password = _read_password(args)
            repo.create(
                employee_id=args.employee_id,
                password_hash=hash_password(password),
                role=args.role,
                display_name=args.display_name,
            )
            print(
                f"Created user {args.employee_id} "
                f"with role {args.role}"
            )
        else:
            if args.deactivate:
                repo.set_active(user=user, is_active=False)
                print(f"Deactivated user {args.employee_id}")
                return 0

            password = _read_password(args)
            repo.update_password(
                user=user,
                password_hash=hash_password(password),
            )
            user.role = args.role
            if args.display_name is not None:
                user.display_name = args.display_name
            db.commit()
            print(
                f"Updated user {args.employee_id} "
                f"with role {args.role}"
            )
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
