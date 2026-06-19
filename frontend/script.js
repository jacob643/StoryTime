const textDisplay = document.getElementById('textDisplay');
const inputBox = document.getElementById('inputBox');
const messageDiv = document.getElementById('message');
const timeTakenDiv = document.getElementById('timeTaken');
const speedDiv = document.getElementById('speed');

let textContent = textDisplay.innerText;
let timeTakenSeconds = 0;
let startTime = null;
let speed = 0;
let sessionId = null;

let splitBoundaries = [];
let splitTimestamps = [];

function computeSplits(text) {
    const target = 50;
    const min = 30;
    const boundaries = [];
    let i = 0;
    while (i < text.length) {
        let end = Math.min(i + target, text.length);
        const remaining = text.length - end;
        if (remaining > 0 && remaining < min) {
            end = text.length;
        }
        boundaries.push(end);
        i = end;
    }
    return boundaries;
}

function resetSplitTracking() {
    splitBoundaries = [];
    splitTimestamps = [];
}

function initSplits(text) {
    splitBoundaries = computeSplits(text);
    splitTimestamps = new Array(splitBoundaries.length).fill(null);
}

function updateSplitTimestamps() {
    const pos = inputBox.value.length;
    for (let i = 0; i < splitBoundaries.length; i++) {
        if (pos >= splitBoundaries[i] && splitTimestamps[i] === null) {
            splitTimestamps[i] = new Date();
        }
    }
}

function computeSplitSpeeds() {
    if (splitTimestamps.length === 0 || !startTime) return [];
    const speeds = [];
    let prevTime = startTime;
    let prevPos = 0;
    for (let i = 0; i < splitBoundaries.length; i++) {
        const splitChars = splitBoundaries[i] - prevPos;
        const splitTime = splitTimestamps[i];
        if (!splitTime) continue;
        const minutes = (splitTime - prevTime) / 60000;
        if (minutes <= 0) continue;
        speeds.push(splitChars / minutes);
        prevTime = splitTime;
        prevPos = splitBoundaries[i];
    }
    return speeds;
}

window.onload = () => {
    reset();
};

document.addEventListener('DOMContentLoaded', () => {
    reset();
});

function reset() {
    sessionId = null;
    textContent = '';
    textDisplay.innerText = '';
    textDisplay.className = '';
    inputBox.value = '';
    inputBox.disabled = true;
    initialPromptInput.value = '';
    initialPromptInput.focus();
    llmResponseDiv.textContent = 'Enter a story prompt and click Send.';
    llmResponseDiv.className = '';
    timeTakenDiv.textContent = '';
    speedDiv.textContent = '';
    timeTakenSeconds = 0;
    speed = 0;
    startTime = null;
    document.getElementById('history').innerHTML = '';
    resetSplitTracking();
}

function addHistory(text, timeTaken, speedCpm, outcomeTier, outcomeLabel) {
    const historyContainer = document.getElementById('history');

    const historyItem = document.createElement('div');
    historyItem.classList.add('history-item');

    const textElement = document.createElement('p');
    textElement.textContent = text;

    const metaElement = document.createElement('p');
    const speedType = document.querySelector('input[name="speedType"]:checked').value;
    let displaySpeed = speedCpm;
    if (speedType !== 'cpm') {
        displaySpeed /= 5;
    }
    metaElement.textContent = `${timeTaken.toFixed(2)}s | ${displaySpeed.toFixed(1)} ${speedType.toUpperCase()} | ${outcomeLabel}`;

    historyItem.appendChild(textElement);
    historyItem.appendChild(metaElement);
    historyContainer.appendChild(historyItem);
    historyContainer.scrollTop = historyContainer.scrollHeight;
}

function updateTextDisplay() {
    const inputText = inputBox.value;
    let displayedText = '';

    for (let i = 0; i < textContent.length; i++) {
        const char = textContent[i];
        const inputChar = inputText[i] || '';

        if (inputChar === char) {
            displayedText += `<span style="background-color: green; color: black;">${char}</span>`;
        } else if (inputChar !== '' && inputChar !== char) {
            displayedText += `<span style="background-color: red; color: black;">${char}</span>`;
        } else {
            displayedText += `<span>${char}</span>`;
        }
    }

    textDisplay.innerHTML = displayedText;
}

function GetTimeTakenDisplay() {
    return `${timeTakenSeconds.toFixed(2)} seconds`;
}

function CalculateSpeed() {
    const endTime = new Date();
    timeTakenSeconds = (endTime - startTime) / 1000;
    const timeTakenMinutes = timeTakenSeconds / 60;
    const numChars = textContent.length;
    speed = numChars / timeTakenMinutes;
    timeTakenDiv.textContent = `Last paragraph time taken: ${GetTimeTakenDisplay()}`;
    UpdateSpeed();
}

function GetSpeedDisplay() {
    const speedType = document.querySelector('input[name="speedType"]:checked').value;
    let displaySpeed = speed;
    if (speedType !== 'cpm') {
        displaySpeed /= 5;
    }
    return `${displaySpeed.toFixed(1)} ${speedType.toUpperCase()}`;
}

function UpdateSpeed() {
    speedDiv.textContent = `Last typing speed: ${GetSpeedDisplay()}`;
}

async function fetchNextParagraph(completedText, speedCpm, splitSpeeds) {
    if (!sessionId) return;

    const body = {
        prompt: completedText,
        session_id: sessionId,
        speed_cpm: speedCpm,
    };
    if (splitSpeeds && splitSpeeds.length > 0) {
        body.split_speeds = splitSpeeds;
    }

    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        addHistory(completedText, timeTakenSeconds, speedCpm, data.outcome_tier, data.outcome_label);
        sessionId = data.session_id;
        textContent = data.response;
        textDisplay.innerText = textContent;
        textDisplay.className = '';
        inputBox.value = '';
        startTime = null;
        inputBox.focus();
        initSplits(textContent);
    } catch (error) {
        textDisplay.innerText = `Error: ${error.message}`;
        textDisplay.className = 'error';
    }
}

function CheckFinishedSentence() {
    if (inputBox.value === textContent) {
        CalculateSpeed();
        const splitSpeeds = computeSplitSpeeds();
        fetchNextParagraph(textContent, speed, splitSpeeds);
    }
}

function ShowCongrats() {
    messageDiv.textContent = 'Congratulations!';
    messageDiv.style.display = 'block';
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 5000);
}

function startTypingTimer() {
    if (startTime === null) {
        startTime = new Date();
    }
}

inputBox.addEventListener('input', () => {
    startTypingTimer();
    updateSplitTimestamps();
    CheckFinishedSentence();
    updateTextDisplay();
});

document.querySelectorAll('input[name="speedType"]').forEach(radio => {
    radio.addEventListener('change', () => {
        UpdateSpeed();
    });
});

// prompt and LLM side.

const restartButton = document.getElementById('restartButton');
const initialPromptInput = document.getElementById('initialPrompt');
const llmResponseDiv = document.getElementById('llmResponse');

restartButton.addEventListener('click', () => {
    sendPrompt(initialPromptInput.value);
});

async function sendPrompt(prompt) {
    if (!prompt.trim()) return;

    sessionId = null;
    llmResponseDiv.textContent = 'Starting story...';
    llmResponseDiv.className = '';

    try {
        const response = await fetch('/api/restart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initial_prompt: prompt }),
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        sessionId = data.session_id;
        textContent = data.response;
        textDisplay.innerText = textContent;
        textDisplay.className = '';
        inputBox.value = '';
        startTime = null;
        llmResponseDiv.textContent = 'Story started — type the paragraph above.';
        llmResponseDiv.className = 'success';
        inputBox.disabled = false;
        inputBox.focus();
        initSplits(textContent);
    } catch (error) {
        llmResponseDiv.textContent = `Error: ${error.message}`;
        llmResponseDiv.className = 'error';
    }
}
