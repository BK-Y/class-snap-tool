import argparse
import os

from web.app import app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run class-snap-tool web app")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"), help="Host to bind")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "5000")),
        help="Port to bind",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=os.getenv("DEBUG", "1") in {"1", "true", "True"},
        help="Enable debug mode",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
