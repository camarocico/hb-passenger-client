"""Contract tests for the loopback ORCA launcher page."""

from urllib.parse import urlsplit

import pytest


@pytest.fixture
def local_app():
    from src.local_handoff import create_app

    return create_app(
        {
            "TESTING": True,
            "OOD_PREPARE_URL": (
                "https://portal.hb.hpc.rug.nl/pun/dev/hb-passenger/prepare"
            ),
            "LOCAL_HANDOFF_ORIGIN": "http://127.0.0.1:8765",
        }
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://portal.hb.hpc.rug.nl/pun/dev/hb-passenger/prepare",
        "https://user:password@portal.hb.hpc.rug.nl/prepare",
        "https://portal.hb.hpc.rug.nl/prepare?next=https://attacker.invalid",
        "https://portal.hb.hpc.rug.nl/prepare#fragment",
        "//portal.hb.hpc.rug.nl/prepare",
    ],
)
def test_local_launcher_rejects_unsafe_portal_urls(url):
    from src.local_handoff import create_app

    with pytest.raises(ValueError, match="OOD_PREPARE_URL"):
        create_app(
            {
                "TESTING": True,
                "OOD_PREPARE_URL": url,
                "LOCAL_HANDOFF_ORIGIN": "http://127.0.0.1:8765",
            }
        )


@pytest.mark.parametrize(
    "origin",
    [
        "http://0.0.0.0:8765",
        "http://192.168.1.10:8765",
        "https://127.0.0.1:8765",
        "http://127.0.0.1:8765/path",
    ],
)
def test_local_launcher_rejects_non_loopback_or_non_origin_values(origin):
    from src.local_handoff import create_app

    with pytest.raises(ValueError, match="LOCAL_HANDOFF_ORIGIN"):
        create_app(
            {
                "TESTING": True,
                "OOD_PREPARE_URL": (
                    "https://portal.hb.hpc.rug.nl/pun/dev/hb-passenger/prepare"
                ),
                "LOCAL_HANDOFF_ORIGIN": origin,
            }
        )


def test_local_launcher_page_selects_one_input_and_targets_configured_portal(
    local_app,
):
    page = local_app.test_client().get("/", base_url="http://127.0.0.1:8765")
    body = page.get_data(as_text=True)

    assert page.status_code == 200
    assert 'type="file"' in body
    assert 'accept=".inp"' in body
    assert "Run on Habrok" in body
    assert ("https://portal.hb.hpc.rug.nl/pun/dev/hb-passenger/prepare") in body
    assert "127.0.0.1:8765" in body
    assert page.headers["Cache-Control"] == "no-store"


def test_launcher_does_not_accept_a_request_selected_portal(local_app):
    response = local_app.test_client().get(
        "/?portal=https://attacker.invalid/prepare",
        base_url="http://127.0.0.1:8765",
    )

    assert response.status_code == 200
    assert "attacker.invalid" not in response.get_data(as_text=True)


def test_local_server_host_is_fixed_to_loopback():
    from src.local_handoff import LOCAL_HOST

    assert LOCAL_HOST == "127.0.0.1"


def test_configured_portal_url_has_no_open_redirect_components(local_app):
    from src.local_handoff import portal_prepare_url

    url = urlsplit(portal_prepare_url(local_app))

    assert url.scheme == "https"
    assert url.hostname == "portal.hb.hpc.rug.nl"
    assert url.path == "/pun/dev/hb-passenger/prepare"
    assert not url.username
    assert not url.password
    assert not url.query
    assert not url.fragment
