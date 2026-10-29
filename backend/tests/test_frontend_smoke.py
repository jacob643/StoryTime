import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


PORT = _free_port()
URL = f"http://127.0.0.1:{PORT}"


def _settings_payload(initial_prompt_template, continuation_prompt_template):
    return {
        "scoring_mode": "split",
        "min_stddev_cpm": 10,
        "tier_0_max_sigma": -1.5,
        "tier_1_max_sigma": -0.5,
        "tier_2_max_sigma": 0.5,
        "tier_3_max_sigma": 1.5,
        "paragraph_word_count": 40,
        "initial_prompt_template": initial_prompt_template,
        "continuation_prompt_template": continuation_prompt_template,
        "target_split_size": 50,
        "temperature": 2,
        "top_k": 40,
        "top_p": 0.9,
        "fixed_thresholds": [30, 50, 75, 100],
        "outcome_directions": {
            "0": ["bad"], "1": ["worse"], "2": ["neutral"],
            "3": ["good"], "4": ["great"],
        },
        "ollama_model": "llama3.2:latest",
        "ignore_case": False,
        "fetch_trigger_pct": 75,
    }


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
    assert page.locator("#storyContext").count() == 0
    assert len(errors) == 0, f"Console errors: {errors}"


def test_fetch_trigger_pct_clamped_on_load(server, page):
    def handle_route(route):
        if route.request.url.endswith("/api/health"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"first_visit": False, "ollama_running": True}))
            return
        if route.request.url.endswith("/api/settings"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"fetch_trigger_pct": 250}))
            return
        if route.request.url.endswith("/api/settings/boundaries"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"boundaries": [30, 50, 75, 100]}))
            return

    page.route("**/api/*", handle_route)
    page.goto(URL)

    page.wait_for_function(
        'document.getElementById("optFetchPct").value === "100"',
        timeout=5000,
    )
    assert page.evaluate("fetchTriggerPct") == 100


def test_prompt_templates_load_restore_and_save(server, page):
    settings_payload = _settings_payload(
        "CUSTOM OPEN {premise}",
        "CUSTOM CONT {history}",
    )
    captured = {}

    def handle_route(route):
        url = route.request.url
        if url.endswith("/api/health"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"first_visit": False, "ollama_running": True}))
            return
        if url.endswith("/api/settings/boundaries"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"boundaries": [30, 50, 75, 100]}))
            return
        if url.endswith("/api/models"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"ollama_running": False, "models": []}))
            return
        if url.endswith("/api/settings") and route.request.method == "POST":
            captured["body"] = json.loads(route.request.post_data)
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps(settings_payload))
            return
        if url.endswith("/api/settings"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps(settings_payload))
            return
        route.fulfill(status=200, content_type="application/json", body="{}")

    page.route("**/api/*", handle_route)
    page.goto(URL)
    page.click("#settingsToggle")
    page.wait_for_function(
        'document.getElementById("optInitialPromptTemplate").value === "CUSTOM OPEN {premise}"',
        timeout=5000,
    )
    assert page.locator("#optContinuationPromptTemplate").input_value() == "CUSTOM CONT {history}"

    page.click("#resetInitialPromptTemplate")
    assert page.evaluate(
        "document.getElementById('optInitialPromptTemplate').value === DEFAULT_INITIAL_PROMPT_TEMPLATE"
    )
    page.click("#resetContinuationPromptTemplate")
    assert page.evaluate(
        "document.getElementById('optContinuationPromptTemplate').value === DEFAULT_CONTINUATION_PROMPT_TEMPLATE"
    )

    page.fill("#optInitialPromptTemplate", "SAVE OPEN {premise} {style}")
    page.fill("#optContinuationPromptTemplate", "SAVE CONT {premise} {history} {direction}")
    with page.expect_request(
        lambda req: req.method == "POST" and req.url.endswith("/api/settings")
    ) as request_info:
        page.click("#saveSettings")

    body = json.loads(request_info.value.post_data)
    assert body["initial_prompt_template"] == "SAVE OPEN {premise} {style}"
    assert body["continuation_prompt_template"] == "SAVE CONT {premise} {history} {direction}"
    assert captured["body"]["initial_prompt_template"] == "SAVE OPEN {premise} {style}"


def test_prompt_previews_update_and_preserve_unknown_tokens(server, page):
    settings_payload = _settings_payload(
        "Open {premise} words={max_words} tier={tier}",
        "Cont {premise}\n{history}words={max_words} tier={tier}",
    )
    preview_calls = []

    def handle_route(route):
        url = route.request.url
        if url.endswith("/api/health"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"first_visit": False, "ollama_running": True}))
            return
        if url.endswith("/api/settings/boundaries"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"boundaries": [30, 50, 75, 100]}))
            return
        if url.endswith("/api/models"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"ollama_running": False, "models": []}))
            return
        if url.endswith("/api/settings/preview"):
            data = json.loads(route.request.post_data)
            preview_calls.append(data)
            tier = "3" if data["kind"] == "continuation" else "2"
            rendered = (
                data["template"]
                .replace("{premise}", "PREVIEW_PREMISE")
                .replace("{history}", "HISTORY BLOCK\n\n")
                .replace("{direction}", "PREVIEW_DIRECTION")
                .replace("{tier}", tier)
                .replace("{max_words}", str(data["max_words"]))
            )
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"preview": rendered}))
            return
        if url.endswith("/api/settings"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps(settings_payload))
            return
        route.fulfill(status=200, content_type="application/json", body="{}")

    page.route("**/api/**", handle_route)
    page.goto(URL)
    page.click("#settingsToggle")
    page.wait_for_function(
        'document.getElementById("initialPromptPreview").textContent.includes("PREVIEW_PREMISE")',
        timeout=5000,
    )
    page.wait_for_function(
        'document.getElementById("continuationPromptPreview").textContent.includes("HISTORY BLOCK")',
        timeout=5000,
    )
    initial_text = page.locator("#initialPromptPreview").text_content()
    continuation_text = page.locator("#continuationPromptPreview").text_content()
    assert "words=40" in initial_text
    assert "tier=2" in initial_text
    assert "tier=3" in continuation_text

    preview_calls.clear()
    page.fill(
        "#optInitialPromptTemplate",
        "Live {premise} words={max_words} {style} tier={tier}",
    )
    page.wait_for_function(
        'document.getElementById("initialPromptPreview").textContent.includes("{style}")',
        timeout=5000,
    )
    initial_text = page.locator("#initialPromptPreview").text_content()
    assert "PREVIEW_PREMISE" in initial_text
    assert "{style}" in initial_text
    assert any(
        call["kind"] == "initial"
        and call["template"] == "Live {premise} words={max_words} {style} tier={tier}"
        for call in preview_calls
    )

    preview_calls.clear()
    page.fill("#wordCountInput", "55")
    page.wait_for_function(
        'document.getElementById("initialPromptPreview").textContent.includes("words=55")',
        timeout=5000,
    )
    assert any(call["max_words"] == 55 for call in preview_calls)


def test_fetch_trigger_pct_clamped_on_save(server, page):
    def handle_route(route):
        if route.request.url.endswith("/api/health"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"first_visit": False, "ollama_running": True}))
            return
        if route.request.url.endswith("/api/settings/boundaries"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"boundaries": [30, 50, 75, 100]}))
            return
        if route.request.url.endswith("/api/settings"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"fetch_trigger_pct": 75}))
            return

    page.route("**/api/*", handle_route)
    page.goto(URL)

    for typed, expected in (("250", 100), ("-5", 10)):
        with page.expect_request(
            lambda req: req.method == "POST" and req.url.endswith("/api/settings")
        ) as request_info:
            page.evaluate(
                """(value) => {
                    document.getElementById('optFetchPct').value = value;
                    document.getElementById('saveSettings').click();
                }""",
                typed,
            )
        body = json.loads(request_info.value.post_data)
        assert body["fetch_trigger_pct"] == expected
        page.wait_for_function(
            f'document.getElementById("optFetchPct").value === "{expected}"',
            timeout=5000,
        )
        assert page.locator("#optFetchPct").input_value() == str(expected)


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
        if route.request.url.endswith("/api/settings"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"scoring_mode": "split", "fetch_trigger_pct": 75}))
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
        f'document.getElementById("textDisplay").textContent.includes("{second_paragraph}")',
        timeout=5000,
    )

    history_items = page.locator("#history .history-item")
    assert history_items.count() >= 1
    assert "positive" in history_items.first.text_content()

    assert second_call_body is not None
    assert second_call_body["splits"] is not None
    assert len(second_call_body["splits"]) > 0

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
    assert "Enter a story prompt" in msg, f"Expected prompt hint, got: {msg}"
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


def _start_story(page, first_paragraph, second_paragraph=None):
    call_count = 0
    captured = {"body": None}

    def handle_route(route):
        nonlocal call_count
        if route.request.url.endswith("/api/health"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"first_visit": False, "ollama_running": True}))
            return
        if route.request.url.endswith("/api/settings"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"scoring_mode": "split", "fetch_trigger_pct": 75}))
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
            if captured["body"] is None:
                captured["body"] = json.loads(route.request.post_data)
            body = json.dumps({
                "response": second_paragraph or "The dragon appeared before him.",
                "session_id": "test-session",
                "outcome_tier": 2,
                "outcome_label": "neutral",
                "tier_boundaries": [30, 50, 75, 100],
            })
        route.fulfill(status=200, content_type="application/json", body=body)

    page.route("**/api/*", handle_route)
    page.goto(URL)
    page.fill("#initialPrompt", "Tell me a story")
    page.click("#restartButton")
    page.wait_for_function(
        f'document.getElementById("textDisplay").textContent === "{first_paragraph}"',
        timeout=5000,
    )
    return captured


def test_paragraphs_render_as_separate_blocks(server, page):
    first_paragraph = "A brave warrior set out on a journey..."
    second_paragraph = "The dragon appeared before him."

    _start_story(page, first_paragraph, second_paragraph)

    page.type("#inputBox", "   ", delay=5)
    assert page.locator("#inputBox").input_value() == ""
    assert page.evaluate("consumedChars") == 0

    page.type("#inputBox", first_paragraph, delay=5)

    page.wait_for_function(
        f'document.getElementById("textDisplay").textContent.includes("{second_paragraph}")',
        timeout=5000,
    )
    page.wait_for_function(
        'document.querySelectorAll("#completedText .completed-p").length === 1',
        timeout=5000,
    )

    assert page.evaluate("textContent") == second_paragraph

    completed = page.locator("#completedText .completed-p").first
    assert completed.text_content() == first_paragraph
    assert completed.evaluate("el => getComputedStyle(el).display") == "block"
    assert page.evaluate(
        "getComputedStyle(document.getElementById('completedText')).display"
    ) == "block"
    assert page.evaluate(
        "getComputedStyle(document.getElementById('pendingSpan')).display"
    ) == "block"

    completed_box = completed.bounding_box()
    current_box = page.locator("#untypedSpan").bounding_box()
    assert current_box["y"] > completed_box["y"] + completed_box["height"]


def test_auto_pause_badge_after_idle(server, page):
    first_paragraph = "A brave warrior set out on a journey..."

    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    _start_story(page, first_paragraph)

    page.type("#inputBox", "A brave warrior", delay=1)
    assert not page.locator("#pauseBadge.visible").is_visible()

    page.wait_for_selector("#pauseBadge.visible", timeout=7000)
    assert page.locator("#pauseButton").text_content().strip() == "⏸ Pause"
    assert page.locator("#pauseButton").is_disabled()

    page.type("#inputBox", " set", delay=1)
    assert not page.locator("#pauseBadge.visible").is_visible()
    assert not page.locator("#pauseButton").is_disabled()
    assert len(errors) == 0, f"Console errors: {errors}"


def test_manual_pause_only_pauses_button_disabled(server, page):
    first_paragraph = "A brave warrior set out on a journey..."

    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    _start_story(page, first_paragraph)

    assert not page.locator("#pauseButton").is_disabled()

    page.type("#inputBox", "A brave warrior", delay=1)

    page.click("#pauseButton")
    assert page.locator("#pauseButton").text_content().strip() == "⏸ Pause"
    assert page.locator("#pauseButton").is_disabled()
    assert page.locator("#pauseBadge.visible").is_visible()

    page.click("#pauseButton", force=True)
    assert page.locator("#pauseBadge.visible").is_visible()

    page.keyboard.press("Escape")
    assert page.locator("#pauseButton").is_disabled()
    assert page.locator("#pauseBadge.visible").is_visible()

    page.type("#inputBox", " set", delay=1)
    assert not page.locator("#pauseButton").is_disabled()
    assert not page.locator("#pauseBadge.visible").is_visible()
    assert len(errors) == 0, f"Console errors: {errors}"


def test_manual_pause_counts_from_last_keystroke(server, page):
    first_paragraph = "A brave warrior set out on a journey..."

    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    captured = _start_story(page, first_paragraph)

    page.type("#inputBox", "A brave ", delay=1)
    page.wait_for_timeout(2000)
    page.click("#pauseButton")
    page.wait_for_timeout(3000)

    type_char = """() => {
        const text = textContent;
        const pos = consumedChars + inputBox.value.length;
        inputBox.value += text.charAt(pos);
        inputBox.dispatchEvent(new Event('input'));
    }"""
    for _ in range(len("warrior set out on a journey...")):
        page.evaluate(type_char)

    deadline = time.time() + 5
    while captured["body"] is None and time.time() < deadline:
        time.sleep(0.1)
    assert captured["body"] is not None, "Fetch for the next paragraph never fired"

    splits = captured["body"]["splits"]
    assert len(splits) == 1, f"Expected one split covering the pause, got {splits}"
    assert splits[0]["char_count"] == 30
    assert splits[0]["speed_cpm"] > 1000, (
        f"Manual pause should count from the last keystroke, got {splits[0]['speed_cpm']}"
    )
    assert len(errors) == 0, f"Console errors: {errors}"


def test_pause_excluded_from_cpm(server, page):
    first_paragraph = "A brave warrior set out on a journey..."

    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    captured = _start_story(page, first_paragraph)

    page.type("#inputBox", "A brave ", delay=1)
    page.wait_for_timeout(6500)
    page.type("#inputBox", "warrior set out on a journey...", delay=1)

    deadline = time.time() + 5
    while captured["body"] is None and time.time() < deadline:
        time.sleep(0.1)
    assert captured["body"] is not None, "Fetch for the next paragraph never fired"

    splits = captured["body"]["splits"]
    assert len(splits) == 1, f"Expected one split covering the pause, got {splits}"
    assert splits[0]["char_count"] == 30
    assert splits[0]["speed_cpm"] > 1000, (
        f"Pause time should be excluded from CPM, got {splits[0]['speed_cpm']}"
    )
    assert len(errors) == 0, f"Console errors: {errors}"


def test_history_time_excludes_idle_pause(server, page):
    first_paragraph = "A brave warrior set out on a journey..."

    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    _start_story(page, first_paragraph)

    page.type("#inputBox", "A brave ", delay=1)
    page.wait_for_timeout(6500)

    type_char = """() => {
        const text = textContent;
        const pos = consumedChars + inputBox.value.length;
        inputBox.value += text.charAt(pos);
        inputBox.dispatchEvent(new Event('input'));
    }"""
    for _ in range(len("warrior set out on a journey...")):
        page.evaluate(type_char)

    page.wait_for_selector(".history-item", timeout=5000)
    speed_text = page.locator(".history-item .history-speed").first.text_content()
    m = re.search(r"Time: ([\d.]+)s", speed_text)
    assert m, f"Could not parse time from: {speed_text}"
    time_taken = float(m.group(1))
    assert time_taken < 3.0, (
        f"History time should exclude the idle pause (split time used), got {time_taken}s"
    )
    assert len(errors) == 0, f"Console errors: {errors}"


def test_split_cpm_interval_correction(server, page):
    first_paragraph = "A lone keeper watched the waves every morning from the lighthouse, noting each wave in aged journal."
    assert len(first_paragraph) == 100
    second_paragraph = "The dragon appeared before him."

    captured = {"body": None}
    call_count = 0

    def handle_route(route):
        nonlocal call_count
        if route.request.url.endswith("/api/health"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"first_visit": False, "ollama_running": True}))
            return
        if route.request.url.endswith("/api/settings"):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"scoring_mode": "split", "fetch_trigger_pct": 75}))
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
            captured["body"] = json.loads(route.request.post_data)
            body = json.dumps({
                "response": second_paragraph,
                "session_id": "test-session",
                "outcome_tier": 2,
                "outcome_label": "neutral",
                "tier_boundaries": [30, 50, 75, 100],
            })
        route.fulfill(status=200, content_type="application/json", body=body)

    page.route("**/api/*", handle_route)
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    page.clock.install()
    page.goto(URL)
    page.fill("#initialPrompt", "Tell me a story")
    page.click("#restartButton")

    deadline = time.time() + 5
    while time.time() < deadline:
        if page.evaluate('document.getElementById("textDisplay").textContent') == first_paragraph:
            break
        time.sleep(0.1)
    else:
        raise AssertionError("Story did not load in time")

    page.clock.pause_at(page.evaluate("Date.now()"))

    type_char = """() => {
        const text = textContent;
        const pos = consumedChars + inputBox.value.length;
        inputBox.value += text.charAt(pos);
        inputBox.dispatchEvent(new Event('input'));
    }"""

    for _ in range(75):
        page.evaluate(type_char)
        page.clock.run_for(100)

    deadline = time.time() + 5
    while captured["body"] is None and time.time() < deadline:
        time.sleep(0.1)
    assert captured["body"] is not None, "Fetch for the next paragraph never fired"

    splits = captured["body"]["splits"]
    assert len(splits) == 2, f"Expected two splits, got {splits}"
    assert splits[0]["char_count"] == 50
    assert 590 < splits[0]["speed_cpm"] < 610, (
        f"First split should be interval-corrected to ~600 CPM, got {splits[0]['speed_cpm']}"
    )
    assert splits[1]["char_count"] == 25
    assert 590 < splits[1]["speed_cpm"] < 610, (
        f"Second split should not be over-corrected, got {splits[1]['speed_cpm']}"
    )
    assert len(errors) == 0, f"Console errors: {errors}"
