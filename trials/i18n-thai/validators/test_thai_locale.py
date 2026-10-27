"""Checks that the generated app offers Thai (th) as a language.

The page is opened with a Thai browser locale. A WaveMaker app that supports
Thai then loads its Thai message bundle and shows Thai text.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import sync_playwright

TARGET_URL = os.environ["HOLODECK_TARGET_URL"]
TIMEOUT_MS = int(os.getenv("HOLODECK_TIMEOUT_MS", "60000"))
ARTIFACT_DIR = Path(os.getenv("HOLODECK_ARTIFACT_DIR", "artifacts"))

# A Thai message bundle, e.g. .../i18n/th.json or .../th_TH.json
THAI_BUNDLE = re.compile(r"(^|[/_.-])th([_-][A-Za-z]{2})?\.json(\?|$)", re.IGNORECASE)
# Characters of the Thai Unicode block
THAI_TEXT = re.compile(r"[฀-๿]")


@pytest.fixture()
def thai_page(request):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    bundles: list[dict] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(locale="th-TH", viewport={"width": 1440, "height": 900})
        auth_cookie = os.getenv("HOLODECK_AUTH_COOKIE", "").strip()
        if auth_cookie:
            context.add_cookies(
                [
                    {
                        "name": os.getenv("HOLODECK_AUTH_COOKIE_NAME", "auth_cookie"),
                        "value": auth_cookie,
                        "domain": urlparse(TARGET_URL).hostname,
                        "path": "/",
                    }
                ]
            )
        page = context.new_page()
        page.set_default_timeout(TIMEOUT_MS)

        def record_response(response) -> None:
            if THAI_BUNDLE.search(urlparse(response.url).path):
                bundles.append({"url": response.url, "status": response.status})

        page.on("response", record_response)
        page.goto(TARGET_URL, wait_until="networkidle", timeout=TIMEOUT_MS)
        yield {"page": page, "bundles": bundles}

        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "-", request.node.name)
        page.screenshot(path=str(ARTIFACT_DIR / f"{safe_name}.png"), full_page=True)
        context.close()
        browser.close()


def test_thai_bundle_loads(thai_page):
    bundles = thai_page["bundles"]
    assert bundles, "No Thai (th) message bundle was requested when the page opened with a Thai locale"
    ok = [b for b in bundles if b["status"] < 400]
    assert ok, f"The Thai message bundle failed to load: {bundles}"


def test_thai_text_shown(thai_page):
    text = thai_page["page"].locator("body").inner_text()
    assert THAI_TEXT.search(text), "No Thai text is shown on the page with a Thai locale"
