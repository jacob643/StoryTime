import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
PORT = 9876
URL = f"http://127.0.0.1:{PORT}"


@pytest.fixture(scope="module")
def server():
    env = os.environ.copy()
    env["STORYTIME_PORT"] = str(PORT)
    proc = subprocess.Popen(
        [sys.executable, "-m", "backend.main"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        try:
            httpx.get(f"{URL}/", timeout=2)
            break
        except httpx.RequestError:
            time.sleep(0.5)
    else:
        proc.kill()
        raise RuntimeError("Server did not start in time")
    yield
    proc.kill()
    proc.wait()


def test_page_loads_without_errors(server, page):
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(URL)
    assert page.title() == "Story Time!"
    assert page.locator("#initialPrompt").is_visible()
    assert page.locator("#restartButton").is_visible()
    assert page.locator("#llmResponse").is_visible()
    assert len(errors) == 0, f"Console errors: {errors}"


def test_send_prompt_displays_response(server, page):
    fake_text = "A brave warrior set out on a journey..."

    def handle_route(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "response": fake_text,
                "session_id": "test-123",
                "outcome_tier": 2,
                "outcome_label": "neutral",
            }),
        )

    page.route("**/api/*", handle_route)

    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    page.goto(URL)
    page.fill("#initialPrompt", "Tell me a story")
    page.click("#restartButton")

    page.wait_for_function(
        f'document.getElementById("textDisplay").textContent === "{fake_text}"',
        timeout=5000,
    )
    assert page.locator("#textDisplay").text_content() == fake_text
    assert len(errors) == 0, f"Console errors: {errors}"


def test_full_game_loop(server, page):
    first_paragraph = "A brave warrior set out on a journey..."
    second_paragraph = "The dragon appeared before him."

    call_count = 0

    def handle_route(route):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            body = json.dumps({
                "response": first_paragraph,
                "session_id": "test-session",
                "outcome_tier": 2,
                "outcome_label": "neutral",
            })
        else:
            body = json.dumps({
                "response": second_paragraph,
                "session_id": "test-session",
                "outcome_tier": 3,
                "outcome_label": "positive",
            })
        route.fulfill(status=200, content_type="application/json", body=body)

    page.route("**/api/*", handle_route)

    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    page.goto(URL)
    page.fill("#initialPrompt", "Tell me a story")
    page.click("#restartButton")

    page.wait_for_function(
        f'document.getElementById("textDisplay").textContent === "{first_paragraph}"',
        timeout=5000,
    )

    page.fill("#inputBox", first_paragraph)

    page.wait_for_function(
        f'document.getElementById("textDisplay").textContent === "{second_paragraph}"',
        timeout=5000,
    )

    history_items = page.locator("#history .history-item")
    assert history_items.count() >= 1
    assert "positive" in history_items.first.text_content()

    assert len(errors) == 0, f"Console errors: {errors}"
