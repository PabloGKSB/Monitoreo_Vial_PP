"""Start the single-process inspection API on loopback."""

import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="API local de inspeccion de recorridos")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--central", action="store_true", help="Exigir Supabase JWT y PostgreSQL")
    parser.add_argument("--env-file", help="Archivo local de configuracion, nunca incluirlo en Git")
    args = parser.parse_args()
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file, override=False)
    target = "src.central_api:app_from_env" if args.central else "src.api:app"
    uvicorn.run(target, factory=args.central, host="127.0.0.1", port=args.port, workers=1)


if __name__ == "__main__":
    main()
