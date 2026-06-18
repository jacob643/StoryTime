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

//prompt and LLM side.

const initialPrompt = "write the first paragraph of an adventure story about a young warrior trying to find a legendary artefact said to give it's user unlimited power. Don't write anything else than that first paragraph.";
const promptsContinuation = [
    "the main character should fin himself in an even worse situation, with no clear way out. Please continue one more paragraph of the story with this very negative outcome. Don't write anything else than that last paragraph.",
    "the main character should encounter a significant setback that makes his journey more difficult. Please continue one more paragraph of the story with this negative outcome. Don't write anything else than that last paragraph.",
    "the main character should face a minor challenge but manage to continue without major issues. Please continue one more paragraph of the story with this neutral outcome. Don't write anything else than that last paragraph.",
    "the main character should experience a small success that aids him on his journey. Please continue one more paragraph of the story with this positive outcome. Don't write anything else than that last paragraph.",
    "the main character should discover something that greatly improves his situation and advances him significantly on his journey. Please continue one more paragraph of the story with this very positive outcome. Don't write anything else than that last paragraph."
];
// now continue the story with another short paragraph in familiar english. A tangible, very positive event occurs during the paragraph, the main character should still be moving toward their initial goal.

const restartButton = document.getElementById('restartButton');
const initialPromptInput = document.getElementById('initialPrompt');

restartButton.addEventListener('click', () => {
    sendPrompt(initialPromptInput.value);
});

async function sendPrompt(prompt) {
    const url = 'http://127.0.0.1:11434';

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prompt: prompt })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Response from LLM:', data.message);
    } catch (error) {
        console.error('Error:', error);
    }
}