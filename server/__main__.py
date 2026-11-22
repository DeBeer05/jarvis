"""Run with: python -m server [run|status|stop]."""

import argparse
import json
import logging

from server.config import ConfigurationError, load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Local JARVIS headless server")
    parser.add_argument("command", nargs="?", choices=("run", "status", "stop"), default="run")
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
                loop="asyncio", http="h11", ws="none", lifespan="on",
                log_config=None, access_log=False, proxy_headers=False,
                server_header=False, timeout_graceful_shutdown=5,
                limit_concurrency=32,
            )
            server = uvicorn.Server(configuration)
            server.run()
            return 0 if server.started else 1
    except (Exception, SystemExit) as error:
        logging.getLogger("jarvis.server").error("server_failed", extra={"error_type": type(error).__name__})
        if not handlers:
            print(json.dumps({"level": "ERROR", "event": "server_failed", "error_type": type(error).__name__}))
        return 1
    finally:
        close_logging(handlers)


if __name__ == "__main__":
    raise SystemExit(main())
