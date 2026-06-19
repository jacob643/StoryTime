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
let simulatedCpm = null;
let simulatedDeviation = 0;

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
    if (simulatedCpm !== null) {
        const count = Math.max(splitBoundaries.length, 1);
        const speeds = [];
        for (let i = 0; i < count; i++) {
            const variation = simulatedDeviation > 0 ? (Math.random() * 2 - 1) * simulatedDeviation : 0;
            speeds.push(Math.max(1, simulatedCpm + variation));
        }
        return speeds;
    }
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
    simulatedCpm = null;
    simulatedDeviation = 0;
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

// settings panel

const settingsToggle = document.getElementById('settingsToggle');
const settingsPanel = document.getElementById('settingsPanel');
const fixedThresholdsContainer = document.getElementById('fixedThresholdsContainer');

settingsToggle.addEventListener('click', () => {
    settingsPanel.classList.toggle('collapsed');
    if (!settingsPanel.classList.contains('collapsed')) {
        loadSettings();
    }
});

function buildFixedThresholdInputs(thresholds) {
    fixedThresholdsContainer.innerHTML = '';
    for (let i = 0; i < thresholds.length; i++) {
        const row = document.createElement('div');
        row.innerHTML =
            `<label>Tier ${i}: low <input type="number" class="ft-low" step="1" min="0" value="${thresholds[i][0]}" /></label>` +
            `<label>high <input type="number" class="ft-high" step="1" min="0" value="${thresholds[i][1]}" /></label>`;
        fixedThresholdsContainer.appendChild(row);
    }
}

async function loadSettings() {
    try {
        const r = await fetch('/api/settings');
        if (!r.ok) throw new Error('Failed to load settings');
        const s = await r.json();
        document.getElementById('optScoringMode').value = s.scoring_mode;
        document.getElementById('optMinData').value = s.min_data;
        document.getElementById('optMinStddev').value = s.min_stddev_cpm;
        document.getElementById('optTier0Sigma').value = s.tier_0_max_sigma;
        document.getElementById('optTier1Sigma').value = s.tier_1_max_sigma;
        document.getElementById('optTier2Sigma').value = s.tier_2_max_sigma;
        document.getElementById('optTier3Sigma').value = s.tier_3_max_sigma;
        document.getElementById('optTargetSplit').value = s.target_split_size;
        document.getElementById('optMinSplit').value = s.min_split_size;
        document.getElementById('optDefaultAvgCpm').value = s.default_avg_cpm;
        buildFixedThresholdInputs(s.fixed_thresholds);
        for (let t = 0; t <= 4; t++) {
            const el = document.getElementById('optDirection' + t);
            if (el) el.value = s.outcome_directions[t.toString()] || '';
        }
    } catch (e) {
        console.error('loadSettings:', e);
    }
}

function collectSettings() {
    const ftLow = fixedThresholdsContainer.querySelectorAll('.ft-low');
    const ftHigh = fixedThresholdsContainer.querySelectorAll('.ft-high');
    const fixedThresholds = [];
    for (let i = 0; i < ftLow.length; i++) {
        fixedThresholds.push([parseFloat(ftLow[i].value), parseFloat(ftHigh[i].value)]);
    }
    const outcomeDirections = {};
    for (let t = 0; t <= 4; t++) {
        const el = document.getElementById('optDirection' + t);
        if (el) outcomeDirections[t] = el.value;
    }
    return {
        scoring_mode: document.getElementById('optScoringMode').value,
        min_data: parseInt(document.getElementById('optMinData').value),
        min_stddev_cpm: parseFloat(document.getElementById('optMinStddev').value),
        tier_0_max_sigma: parseFloat(document.getElementById('optTier0Sigma').value),
        tier_1_max_sigma: parseFloat(document.getElementById('optTier1Sigma').value),
        tier_2_max_sigma: parseFloat(document.getElementById('optTier2Sigma').value),
        tier_3_max_sigma: parseFloat(document.getElementById('optTier3Sigma').value),
        fixed_thresholds: fixedThresholds,
        target_split_size: parseInt(document.getElementById('optTargetSplit').value),
        min_split_size: parseInt(document.getElementById('optMinSplit').value),
        default_avg_cpm: parseFloat(document.getElementById('optDefaultAvgCpm').value),
        outcome_directions: outcomeDirections,
    };
}

document.getElementById('saveSettings').addEventListener('click', async () => {
    try {
        const r = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(collectSettings()),
        });
        if (!r.ok) throw new Error('Failed to save settings');
        llmResponseDiv.textContent = 'Settings saved.';
        llmResponseDiv.className = 'success';
    } catch (e) {
        llmResponseDiv.textContent = 'Settings save error: ' + e.message;
        llmResponseDiv.className = 'error';
    }
});

document.getElementById('resetSettings').addEventListener('click', async () => {
    const defaults = {
        scoring_mode: 'split',
        min_data: 3,
        min_stddev_cpm: 10,
        tier_0_max_sigma: -1.5,
        tier_1_max_sigma: -0.5,
        tier_2_max_sigma: 0.5,
        tier_3_max_sigma: 1.5,
        fixed_thresholds: [[0, 30], [30, 50], [50, 75], [75, 100], [100, 9999]],
        target_split_size: 50,
        min_split_size: 30,
        default_avg_cpm: 300,
        outcome_directions: {
            0: 'an even worse situation with no clear way out',
            1: 'a significant setback that makes things more difficult',
            2: 'a minor challenge that the protagonist pushes through',
            3: 'a small success that aids the journey',
            4: 'a great improvement to the situation, a significant advance',
        },
    };
    try {
        const r = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(defaults),
        });
        if (!r.ok) throw new Error('Failed to reset settings');
        await loadSettings();
        llmResponseDiv.textContent = 'Settings reset to defaults.';
        llmResponseDiv.className = 'success';
    } catch (e) {
        llmResponseDiv.textContent = 'Settings reset error: ' + e.message;
        llmResponseDiv.className = 'error';
    }
});

// prompt and LLM side.

const restartButton = document.getElementById('restartButton');
const initialPromptInput = document.getElementById('initialPrompt');
const llmResponseDiv = document.getElementById('llmResponse');

restartButton.addEventListener('click', () => {
    sendPrompt(initialPromptInput.value);
});

async function sendSimulate(cpm, deviation) {
    simulatedCpm = cpm;
    simulatedDeviation = deviation || 0;
    sessionId = null;
    const range = simulatedDeviation > 0 ? ` ±${simulatedDeviation}` : '';
    llmResponseDiv.textContent = `Starting simulation at ${cpm}${range} CPM...`;
    llmResponseDiv.className = 'simulation';

    try {
        const response = await fetch('/api/restart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initial_prompt: `Simulated story at ${cpm} CPM.` }),
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        sessionId = data.session_id;
        textContent = data.response;
        textDisplay.innerText = textContent;
        textDisplay.className = 'simulation';
        inputBox.value = '';
        startTime = null;
        inputBox.disabled = false;
        inputBox.focus();
        initSplits(textContent);
        llmResponseDiv.textContent =
            `[SIMULATION ${cpm}${range} CPM] Type the paragraph — split speeds will be faked.`;
        llmResponseDiv.className = 'simulation';
    } catch (error) {
        llmResponseDiv.textContent = `Simulation error: ${error.message}`;
        llmResponseDiv.className = 'error';
        simulatedCpm = null;
        simulatedDeviation = 0;
    }
}

window.simulate = function(cpm, deviation) {
    if (cpm === undefined) {
        console.log('Usage: simulate(cpm, [deviation])');
        return;
    }
    sendSimulate(cpm, deviation || 0);
};

async function sendPrompt(prompt) {
    if (!prompt.trim()) return;

    const simMatch = prompt.trim().match(/^\/simulate\s+(\d+(?:\.\d+)?)(?:\s+(\d+(?:\.\d+)?))?\s*$/i);
    if (simMatch) {
        await sendSimulate(parseFloat(simMatch[1]), simMatch[2] ? parseFloat(simMatch[2]) : 0);
        return;
    }

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
