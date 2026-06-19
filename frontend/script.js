const textDisplay = document.getElementById('textDisplay');
const inputBox = document.getElementById('inputBox');
const messageDiv = document.getElementById('message');
const timeTakenDiv = document.getElementById('timeTaken');
const speedDiv = document.getElementById('speed');
const characterAmountInput = document.getElementById('characterAmountInput');
const characterAmount = document.getElementById('characterAmount');
const possibleCharactersInput = document.getElementById('possibleCharactersInput');

let textContent = textDisplay.innerText;
let timeTakenSecondes = 0;
let startTime = null;
let speed = 0;

characterAmountInput.addEventListener('input', () => {
    characterAmount.textContent = characterAmountInput.value;
});

window.onload = () => {
    reset();
};

document.addEventListener('DOMContentLoaded', (event) => {
    reset();
});

function reset()
{
    const inputBox = document.getElementById('inputBox');
    inputBox.value = '';
    inputBox.focus();
	characterAmount.textContent = characterAmountInput.value;
	ResetSentence();
}

function addHistory(textDisplay) {
    const historyContainer = document.getElementById('history');

    const historyItem = document.createElement('div');
    historyItem.classList.add('history-item');

    const textDisplayElement = document.createElement('p');
    textDisplayElement.textContent = `Text: ${textDisplay}`;

    const timeTakenElement = document.createElement('p');
    timeTakenElement.textContent = `Time Taken: ${GetTimeTakenDisplay()}`;

    const speedElement = document.createElement('p');
    speedElement.textContent = `Speed: ${GetSpeedDisplay()}`;

    historyItem.appendChild(textDisplayElement);
    historyItem.appendChild(timeTakenElement);
    historyItem.appendChild(speedElement);

    historyContainer.appendChild(historyItem);

    historyContainer.scrollTop = historyContainer.scrollHeight;
}

function updateTextDisplay() {
    let inputText = inputBox.value;
    let displayedText = '';

    for (let i = 0; i < textContent.length; i++) {
        let char = textContent[i];
        let inputChar = inputText[i] || '';

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
    let endTime = new Date();
    timeTakenSeconds = ((endTime - startTime) / 1000);
    let timeTakenMinutes = (timeTakenSeconds / 60);
    let numChars = textContent.length;
    speed = (numChars / timeTakenMinutes);
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
    speedDiv.textContent = `Lst typing speed: ${GetSpeedDisplay()}`;
}

function CheckFinishedSentence() {
    if (inputBox.value === textContent) {
        CalculateSpeed();
        addHistory(textContent);
        LoadNextSentence();
        inputBox.value = '';
        startTime = null;
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

function ResetSentence()
{
	textContent = "Type this.";
}

function LoadNextSentence() {
    textContent = generateRandomString(characterAmountInput.value);
}

function generateRandomString(length)
{
	if (length < 1) length = 1;
	characters = possibleCharactersInput.value;
    let result = '';
    const charactersLength = characters.length;

    for (let i = 0; i < length; i++) {
        const randomIndex = Math.floor(Math.random() * charactersLength);
        result += characters[randomIndex];
    }

    return result;
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
    llmResponseDiv.textContent = 'Waiting for story...';
    llmResponseDiv.className = '';

    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        llmResponseDiv.textContent = data.response;
        llmResponseDiv.className = 'success';
    } catch (error) {
        llmResponseDiv.textContent = `Error: ${error.message}`;
        llmResponseDiv.className = 'error';
    }
}