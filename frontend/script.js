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

async function fetchNextParagraph(completedText, speedCpm) {
    if (!sessionId) return;

    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: completedText,
                session_id: sessionId,
                speed_cpm: speedCpm,
            }),
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
        inputBox.focus();
    } catch (error) {
        textDisplay.innerText = `Error: ${error.message}`;
        textDisplay.className = 'error';
    }
}

function CheckFinishedSentence() {
    if (inputBox.value === textContent) {
        CalculateSpeed();

        const completedText = textContent;
        const speedCpm = speed;

        addHistory(completedText, timeTakenSeconds, speedCpm, 0, 'typing...');

        fetchNextParagraph(completedText, speedCpm);
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
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt }),
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
    } catch (error) {
        llmResponseDiv.textContent = `Error: ${error.message}`;
        llmResponseDiv.className = 'error';
    }
}
