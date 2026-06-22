import json
import os
import re
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
    assert page.locator("#message").is_visible()
    assert len(errors) == 0, f"Console errors: {errors}"


def test_send_prompt_displays_response(server, page):
    fake_text = "A brave warrior set out on a journey..."

    def handle_route(route):
        if route.request.url.endswith("/api/health"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"first_visit": False, "ollama_running": True}))
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "response": fake_text,
                "session_id": "test-123",
                "outcome_tier": 2,
                "outcome_label": "neutral",
                "tier_boundaries": [30, 50, 75, 100],
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
    second_call_body = None

    def handle_route(route):
        nonlocal call_count, second_call_body
        if route.request.url.endswith("/api/health"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"first_visit": False, "ollama_running": True}))
            return
        call_count += 1
        if call_count == 1:
            body = json.dumps({
                "response": first_paragraph,
                "session_id": "test-session",
                "outcome_tier": 2,
                "outcome_label": "neutral",
                "tier_boundaries": [30, 50, 75, 100],
            })
        else:
            second_call_body = json.loads(route.request.post_data)
            body = json.dumps({
                "response": second_paragraph,
                "session_id": "test-session",
                "outcome_tier": 3,
                "outcome_label": "positive",
                "tier_boundaries": [30, 50, 75, 100],
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

    page.type("#inputBox", first_paragraph, delay=5)

    page.wait_for_function(
        f'document.getElementById("textDisplay").textContent === "{second_paragraph}"',
        timeout=5000,
    )

    history_items = page.locator("#history .history-item")
    assert history_items.count() >= 1
    assert "positive" in history_items.first.text_content()

    assert second_call_body is not None
    assert second_call_body["split_speeds"] is not None
    assert len(second_call_body["split_speeds"]) > 0

    assert len(errors) == 0, f"Console errors: {errors}"


def _strip_newlines(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def test_startup_message_ollama_down(server, page):
    def handle_route(route):
        if route.request.url.endswith("/api/health"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"first_visit": False, "ollama_running": False}))
            return
    page.route("**/api/*", handle_route)
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(URL)
    msg = _strip_newlines(page.locator("#message").text_content())
    assert "Ollama is not running" in msg, f"Expected Ollama-down message, got: {msg}"
    assert len(errors) == 0, f"Console errors: {errors}"


def test_startup_message_first_visit(server, page):
    def handle_route(route):
        if route.request.url.endswith("/api/health"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"first_visit": True, "ollama_running": True}))
            return
    page.route("**/api/*", handle_route)
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(URL)
    msg = _strip_newlines(page.locator("#message").text_content())
    assert "Welcome to Story Time" in msg, f"Expected welcome message, got: {msg}"
    assert "Enter a story prompt and send" in msg, f"Expected prompt hint, got: {msg}"
    assert len(errors) == 0, f"Console errors: {errors}"


def test_ollama_down_503_retry(server, page):
    call_count = 0

    def handle_route(route):
        nonlocal call_count
        if route.request.url.endswith("/api/health"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"first_visit": False, "ollama_running": True}))
            return
        call_count += 1
        route.fulfill(status=503, content_type="application/json",
                      body=json.dumps({"detail": "LLM provider error: Connection refused"}))

    page.route("**/api/*", handle_route)
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    page.goto(URL)
    page.fill("#initialPrompt", "Tell me a story")
    page.click("#restartButton")

    page.wait_for_function(
        'document.querySelector(".retry-btn") !== null', timeout=5000
    )
    msg = page.locator("#message").text_content()
    assert "Cannot reach the AI model" in msg, f"Expected getting-started hint, got: {msg}"
    assert call_count >= 1
    # Browser logs the 503 as a console error, which is expected — skip error check
