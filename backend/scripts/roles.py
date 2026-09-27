"""Grant or revoke a role from the command line, e.g. to create the first admin.

Usage: uv run python -m scripts.roles grant <username> <role>
       uv run python -m scripts.roles revoke <username> <role>
There is deliberately no API route to become admin: whoever runs this already has database
access. Changes follow the same rules as the API and are audited with no actor (null = CLI).
"""

import argparse
import asyncio
import sys

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import Database
from app.services import admin


async def run(action: str, username: str, role: str) -> int:
    db = Database(get_settings().database_url)
    try:
        async with db.sessionmaker() as session:
            change = admin.grant_role if action == "grant" else admin.revoke_role
            try:
                user = await change(session, None, username.lower(), role.lower())
            except AppError as exc:
                print(exc.detail, file=sys.stderr)
                return 1
            await session.commit()
    finally:
        await db.dispose()
    print(f"{user.username}: {', '.join(user.roles)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=["grant", "revoke"])
    parser.add_argument("username")
    parser.add_argument("role")
    args = parser.parse_args()
    return asyncio.run(run(args.action, args.username, args.role))


if __name__ == "__main__":
    sys.exit(main())
