"""Apply reviewed central schema upgrades using explicit local configuration."""

import argparse
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser(description="Aplicar migraciones PostgreSQL/PostGIS")
    parser.add_argument("--env-file", help="Configuracion privada local; no incluir en Git")
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=False)
    command.upgrade(Config("alembic.ini"), "head")


if __name__ == "__main__":
    main()
