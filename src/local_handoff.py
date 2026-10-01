"""Loopback-only browser launcher for the authenticated OOD preparation flow."""

import os
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, abort, make_response, render_template, request

LOCAL_HOST = "127.0.0.1"
DEFAULT_LOCAL_HANDOFF_ORIGIN = "http://127.0.0.1:8765"


def _origin_parts(value, *, setting_name):
    try:
        parts = urlsplit(value)
        port = parts.port
    except (AttributeError, TypeError, ValueError):
        raise ValueError(f"{setting_name} must be a valid origin")
    return parts, port


def validate_local_origin(value):
    """Validate the exact localhost origin allowed to message the OOD page."""
    parts, port = _origin_parts(value, setting_name="LOCAL_HANDOFF_ORIGIN")
    if (
        parts.scheme != "http"
        or parts.hostname != LOCAL_HOST
        or parts.username is not None
        or parts.password is not None
        or parts.path not in ("",)
        or parts.query
        or parts.fragment
        or port is None
        or not 1 <= port <= 65535
    ):
        raise ValueError(
            "LOCAL_HANDOFF_ORIGIN must be an http://127.0.0.1 origin with a port"
        )
    return f"http://{LOCAL_HOST}:{port}"


def validate_portal_prepare_url(value):
    """Validate a fixed HTTPS OOD preparation URL without redirect fields."""
    parts, _port = _origin_parts(value, setting_name="OOD_PREPARE_URL")
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or not parts.path.endswith("/prepare")
        or parts.query
        or parts.fragment
    ):
        raise ValueError("OOD_PREPARE_URL must be a fixed HTTPS URL ending in /prepare")
    return value


def portal_prepare_url(app):
    """Return the fixed, validated OOD preparation URL."""
    return app.config["OOD_PREPARE_URL"]


def create_app(config=None):
    """Create the local launcher; it serves UI only and never stores input."""
    asset_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        static_folder=str(asset_root / "static"),
        template_folder=str(asset_root / "templates"),
    )
    app.config.from_mapping(
        OOD_PREPARE_URL=os.environ.get("HB_PASSENGER_OOD_PREPARE_URL"),
        LOCAL_HANDOFF_ORIGIN=os.environ.get(
            "HB_PASSENGER_LOCAL_HANDOFF_ORIGIN",
            DEFAULT_LOCAL_HANDOFF_ORIGIN,
        ),
    )
    if config is not None:
        app.config.update(config)

    app.config["OOD_PREPARE_URL"] = validate_portal_prepare_url(
        app.config.get("OOD_PREPARE_URL")
    )
    app.config["LOCAL_HANDOFF_ORIGIN"] = validate_local_origin(
        app.config.get("LOCAL_HANDOFF_ORIGIN")
    )

    @app.before_request
    def restrict_to_loopback_host():
        # Flask's development server binds only to loopback in serve(); require
        # the canonical host too, avoiding use through attacker-controlled Host.
        expected_host = urlsplit(app.config["LOCAL_HANDOFF_ORIGIN"]).netloc
        if request.host != expected_host:
            abort(400)

    @app.get("/")
    def launcher():
        response = make_response(
            render_template(
                "local_handoff.html",
                portal_prepare_url=app.config["OOD_PREPARE_URL"],
                local_handoff_origin=app.config["LOCAL_HANDOFF_ORIGIN"],
            )
        )
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; connect-src 'self'; "
            "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
        )
        return response

    return app


def serve():
    """Run the local launcher on its configured loopback address and port."""
    app = create_app()
    port = urlsplit(app.config["LOCAL_HANDOFF_ORIGIN"]).port
    app.run(host=LOCAL_HOST, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    serve()
