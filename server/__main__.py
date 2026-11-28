"""Run with: python -m server [run|status|stop]."""

import argparse
import json
import logging

from server.config import ConfigurationError, load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Local JARVIS headless server")
    parser.add_argument("command", nargs="?", choices=("run", "status", "stop", "setup-owner"), default="run")
    parser.add_argument("--wait", type=float, default=0)
    parser.add_argument("--no-console", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.wait <= 60:
        parser.error("--wait must be between 0 and 60 seconds")
    try:
        settings = load_settings()
    except ConfigurationError as error:
        print(json.dumps({"level": "ERROR", "event": "configuration_error", "detail": str(error)}))
        return 2

    from server.control import RuntimeControl, control_command
    if args.command == "setup-owner":
        import getpass
        import sys
        from server.database import Database
        from server.security.service import SecurityService
        from server.security.types import AuthError
        if not sys.stdin.isatty():
            print("Gebruik een interactieve PowerShell voor de lokale eigenaarssetup.")
            return 2
        try:
            with RuntimeControl(settings):
                database = Database(settings.database_path)
                database.initialize()
                security = SecurityService(database, settings)
                if security.store.owner():
                    print("De eigenaar is al ingesteld; bestaande gegevens zijn niet gewijzigd.")
                    return 2
                username = input("Gebruikersnaam [owner]: ").strip() or "owner"
                password = getpass.getpass("Nieuw wachtwoord (minimaal 12 tekens): ")
                confirmation = getpass.getpass("Herhaal wachtwoord: ")
                if password != confirmation:
                    print("Wachtwoorden komen niet overeen; geen account aangemaakt.")
                    return 2
                security.setup_owner(username, password)
                print("Eigenaar aangemaakt. Start de server en log in op http://127.0.0.1:8765/login.")
                return 0
        except AuthError as error:
            print(error.message)
            return 2
        except (RuntimeError, OSError):
            print("Setup kon niet starten. Stop eerst de eigen JARVIS-server en probeer opnieuw.")
            return 2
    if args.command != "run":
        return control_command(settings, args.command, args.wait)

    from server.app import create_app
    from server.logging_config import close_logging, configure_logging
    import uvicorn

    handlers = []
    try:
        handlers = configure_logging(settings, console=not args.no_console)
        with RuntimeControl(settings) as control:
            server = None

            def stop():
                server.should_exit = True

            app = create_app(
                settings, instance_id=control.record["instance_id"],
                control_token=control.record["token"], shutdown=stop,
            )
            configuration = uvicorn.Config(
                app, host=settings.host, port=settings.port, workers=1,
                loop="asyncio", http="h11", ws="websockets-sansio", lifespan="on",
                ws_max_size=65536,ws_max_queue=4,ws_ping_interval=20,ws_ping_timeout=20,
                log_config=None, access_log=False, proxy_headers=False,
                server_header=False, timeout_graceful_shutdown=5,
                limit_concurrency=32,
            )
            server = uvicorn.Server(configuration)
            server.run()
            return 0 if server.started else 1
    except KeyboardInterrupt:
        # Uvicorn first completes its lifespan and then restores/re-raises SIGINT.
        return 0
    except (Exception, SystemExit) as error:
        logging.getLogger("jarvis.server").error("server_failed", extra={"error_type": type(error).__name__})
        if not handlers:
            print(json.dumps({"level": "ERROR", "event": "server_failed", "error_type": type(error).__name__}))
        return 1
    finally:
        close_logging(handlers)


if __name__ == "__main__":
    raise SystemExit(main())
