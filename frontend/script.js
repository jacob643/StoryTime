const textDisplay = document.getElementById('textDisplay');
const inputBox = document.getElementById('inputBox');
const messageDiv = document.getElementById('message');

let textContent = textDisplay.innerText;
let timeTakenSeconds = 0;
let startTime = null;
let speed = 0;
let sessionId = null;
let simulatedCpm = null;
let simulatedDeviation = 0;

let splitBoundaries = [];
let splitTimestamps = [];
let retryAction = null;
let paragraphJustCompleted = false;

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

function applyDarkMode(enabled) {
    if (enabled) {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
    const cb = document.getElementById('optDarkMode');
    if (cb) cb.checked = enabled;
    localStorage.setItem('storytime-dark-mode', enabled ? '1' : '0');
}

function initDarkMode() {
    const stored = localStorage.getItem('storytime-dark-mode');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const enabled = stored !== null ? stored === '1' : prefersDark;
    applyDarkMode(enabled);
    document.getElementById('optDarkMode')?.addEventListener('change', (e) => {
        applyDarkMode(e.target.checked);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initDarkMode();
    reset();
});

function reset() {
    sessionId = null;
    simulatedCpm = null;
    simulatedDeviation = 0;
    paragraphJustCompleted = false;
    textContent = '';
    textDisplay.innerText = '';
    textDisplay.className = '';
    inputBox.value = '';
    inputBox.disabled = true;
    initialPromptInput.value = '';
    initialPromptInput.focus();
    messageDiv.textContent = 'Enter a story prompt and send';
    messageDiv.className = 'neutral';
    timeTakenSeconds = 0;
    speed = 0;
    startTime = null;
    document.getElementById('historyEntries').querySelectorAll('.history-item').forEach(el => el.remove());
    document.getElementById('lastParagraph').textContent = '';
    resetSplitTracking();
}

function addHistory(text, timeTaken, speedCpm, outcomeTier, outcomeLabel, splitSpeeds) {
    const historyContainer = document.getElementById('historyEntries');

    const historyItem = document.createElement('div');
    historyItem.classList.add('history-item');

    const textElement = document.createElement('div');
    textElement.classList.add('history-text');
    const cropped = text.length > 20 ? text.slice(0, 20) + '[...]' : text;
    textElement.textContent = cropped;

    const metaElement = document.createElement('div');
    metaElement.classList.add('history-meta');
    const speedType = document.querySelector('input[name="speedType"]:checked').value;
    let displaySpeed = speedCpm;
    if (speedType !== 'cpm') {
        displaySpeed /= 5;
    }
    let meta = `${outcomeLabel} | ${displaySpeed.toFixed(1)} ${speedType.toUpperCase()} | ${timeTaken.toFixed(2)}s`;
    if (splitSpeeds && splitSpeeds.length > 0) {
        const formatted = splitSpeeds.map(s => s.toFixed(1)).join(', ');
        meta += ` [${formatted}]`;
    }
    metaElement.textContent = meta;

    historyItem.appendChild(textElement);
    historyItem.appendChild(metaElement);
    historyContainer.appendChild(historyItem);
    historyContainer.scrollTop = historyContainer.scrollHeight;
}

function updateStoryContext(text) {
    document.getElementById('lastParagraph').textContent = text;
}

function updateTierChart(tier, boundaries) {
    document.querySelectorAll('.tier-segment').forEach(el => el.classList.remove('active'));
    const seg = document.querySelector(`.tier-segment[data-tier="${tier}"]`);
    if (seg) seg.classList.add('active');

    if (boundaries && boundaries.length >= 4) {
        for (let i = 0; i < 4; i++) {
            const b = document.querySelector(`.tier-boundary[data-index="${i}"]`);
            if (b) b.textContent = `${boundaries[i]} CPM`;
        }
    }
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
}

function GetSpeedDisplay() {
    const speedType = document.querySelector('input[name="speedType"]:checked').value;
    let displaySpeed = speed;
    if (speedType !== 'cpm') {
        displaySpeed /= 5;
    }
    return `${displaySpeed.toFixed(1)} ${speedType.toUpperCase()}`;
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

    retryAction = () => fetchNextParagraph(completedText, speedCpm, splitSpeeds);

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
        addHistory(completedText, timeTakenSeconds, speedCpm, data.outcome_tier, data.outcome_label, splitSpeeds);
        updateStoryContext(completedText);
        updateTierChart(data.outcome_tier, data.tier_boundaries);
        sessionId = data.session_id;
        textContent = data.response;
        textDisplay.innerText = textContent;
        textDisplay.className = '';
        inputBox.value = '';
        startTime = null;
        paragraphJustCompleted = true;
        messageDiv.textContent = 'paragraph over! take a breather';
        messageDiv.className = 'neutral';
        inputBox.focus();
        initSplits(textContent);
        retryAction = null;
    } catch (error) {
        showError(error.message, retryAction);
    }
}

function showError(message, retryFn) {
    textDisplay.innerHTML = '';
    textDisplay.className = 'error';
    messageDiv.innerHTML = `<p class="error-text">${escapeHtml(message)}</p>`;
    if (message.includes('503') || message.includes('LLM provider error') || message.includes('Connection refused')) {
        messageDiv.innerHTML +=
            '<p class="error-hint">Cannot reach the AI model. ' +
            '<a href="/getting_started.html" target="_blank">Getting Started guide</a> has setup and troubleshooting instructions.</p>';
    }
    if (retryFn) {
        const btn = document.createElement('button');
        btn.textContent = 'Retry';
        btn.className = 'retry-btn';
        btn.addEventListener('click', () => { messageDiv.className = ''; retryFn(); });
        messageDiv.appendChild(btn);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

function CheckFinishedSentence() {
    if (inputBox.value === textContent) {
        CalculateSpeed();
        const splitSpeeds = computeSplitSpeeds();
        const displaySpeed = simulatedCpm !== null ? simulatedCpm : speed;
        fetchNextParagraph(textContent, displaySpeed, splitSpeeds);
    }
}

function startTypingTimer() {
    if (startTime === null) {
        startTime = new Date();
    }
}

inputBox.addEventListener('input', () => {
    if (paragraphJustCompleted && inputBox.value.length > 0) {
        paragraphJustCompleted = false;
        messageDiv.textContent = 'Typing away...';
        messageDiv.className = 'success';
    }
    startTypingTimer();
    updateSplitTimestamps();
    CheckFinishedSentence();
    updateTextDisplay();
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

document.getElementById('setupLink').addEventListener('click', () => {
    window.open('/getting_started.html', '_blank');
});

function safeVal(v, fallback) {
    return (v === null || v === undefined || v === '' || v !== v) ? fallback : v;
}

function buildFixedThresholdInputs(thresholds) {
    fixedThresholdsContainer.innerHTML = '';
    for (let i = 0; i < thresholds.length; i++) {
        const low = safeVal(thresholds[i][0], 0);
        const high = safeVal(thresholds[i][1], 9999);
        const row = document.createElement('div');
        row.innerHTML =
            `<label>Tier ${i}: low <input type="number" class="ft-low" step="1" min="0" value="${low}" /></label>` +
            `<label>high <input type="number" class="ft-high" step="1" min="0" value="${high}" /></label>`;
        fixedThresholdsContainer.appendChild(row);
    }
}

async function loadSettings() {
    try {
        const r = await fetch('/api/settings');
        if (!r.ok) throw new Error('Failed to load settings');
        const s = await r.json();
        document.getElementById('optScoringMode').value = s.scoring_mode;
        document.getElementById('optMinStddev').value = s.min_stddev_cpm;
        document.getElementById('optTier0Sigma').value = s.tier_0_max_sigma;
        document.getElementById('optTier1Sigma').value = s.tier_1_max_sigma;
        document.getElementById('optTier2Sigma').value = s.tier_2_max_sigma;
        document.getElementById('optTier3Sigma').value = s.tier_3_max_sigma;
        document.getElementById('wordCountInput').value = s.paragraph_word_count;
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

function safeParseFloat(v, fallback) {
    const n = parseFloat(v);
    return isNaN(n) ? fallback : n;
}

function safeParseInt(v, fallback) {
    const n = parseInt(v, 10);
    return isNaN(n) ? fallback : n;
}

function collectSettings() {
    const ftLow = fixedThresholdsContainer.querySelectorAll('.ft-low');
    const ftHigh = fixedThresholdsContainer.querySelectorAll('.ft-high');
    const fixedThresholds = [];
    for (let i = 0; i < ftLow.length; i++) {
        fixedThresholds.push([
            safeParseFloat(ftLow[i].value, 0),
            safeParseFloat(ftHigh[i].value, 9999),
        ]);
    }
    const outcomeDirections = {};
    for (let t = 0; t <= 4; t++) {
        const el = document.getElementById('optDirection' + t);
        if (el) outcomeDirections[t] = el.value;
    }
    return {
        scoring_mode: document.getElementById('optScoringMode').value,
        paragraph_word_count: safeParseInt(document.getElementById('wordCountInput').value, 80),
        min_stddev_cpm: safeParseFloat(document.getElementById('optMinStddev').value, 10),
        tier_0_max_sigma: safeParseFloat(document.getElementById('optTier0Sigma').value, -1.5),
        tier_1_max_sigma: safeParseFloat(document.getElementById('optTier1Sigma').value, -0.5),
        tier_2_max_sigma: safeParseFloat(document.getElementById('optTier2Sigma').value, 0.5),
        tier_3_max_sigma: safeParseFloat(document.getElementById('optTier3Sigma').value, 1.5),
        fixed_thresholds: fixedThresholds,
        target_split_size: safeParseInt(document.getElementById('optTargetSplit').value, 50),
        min_split_size: safeParseInt(document.getElementById('optMinSplit').value, 30),
        default_avg_cpm: safeParseFloat(document.getElementById('optDefaultAvgCpm').value, 300),
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
        messageDiv.textContent = 'Settings saved.';
        messageDiv.className = 'success';
        settingsPanel.classList.add('collapsed');
    } catch (e) {
        messageDiv.textContent = 'Settings save error: ' + e.message;
        messageDiv.className = 'error';
    }
});

document.getElementById('resetSettings').addEventListener('click', async () => {
    const defaults = {
        scoring_mode: 'split',
        character_amount: 200,
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
        settingsPanel.classList.add('collapsed');
        await loadSettings();
        messageDiv.textContent = 'Settings reset to defaults.';
        messageDiv.className = 'success';
    } catch (e) {
        messageDiv.textContent = 'Settings reset error: ' + e.message;
        messageDiv.className = 'error';
    }
});

// prompt and LLM side.

const restartButton = document.getElementById('restartButton');
const initialPromptInput = document.getElementById('initialPrompt');

restartButton.addEventListener('click', () => {
    sendPrompt(initialPromptInput.value);
});

initialPromptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        sendPrompt(initialPromptInput.value);
    }
});

async function sendSimulate(cpm, deviation) {
    simulatedCpm = cpm;
    simulatedDeviation = deviation || 0;
    const range = simulatedDeviation > 0 ? ` ±${simulatedDeviation}` : '';

    if (!textContent) {
        initialPromptInput.value = 'a skateboard with a soul trying to find its home';
        messageDiv.textContent = `Starting simulation at ${cpm}${range} CPM...`;
        messageDiv.className = 'simulation';
        fetch('/api/restart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initial_prompt: initialPromptInput.value }),
        })
            .then(r => { if (!r.ok) throw new Error(`Server error: ${r.status}`); return r.json(); })
            .then(data => {
                sessionId = data.session_id;
                textContent = data.response;
                textDisplay.innerText = textContent;
                textDisplay.className = 'simulation';
                inputBox.disabled = false;
                initSplits(textContent);
                updateTierChart(data.outcome_tier, data.tier_boundaries);
                sendSimulate(cpm, deviation);
            })
            .catch(error => {
                messageDiv.textContent = `Simulation error: ${error.message}`;
                messageDiv.className = 'error';
                simulatedCpm = null;
                simulatedDeviation = 0;
            });
        return;
    }

    messageDiv.textContent = `[SIMULATION ${cpm}${range} CPM]`;
    messageDiv.className = 'simulation';
    startTime = new Date();
    inputBox.value = textContent;
    const splitSpeeds = computeSplitSpeeds();
    fetchNextParagraph(textContent, simulatedCpm, splitSpeeds);
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

    sessionId = null;
    const promptText = prompt;
    retryAction = () => sendPrompt(promptText);
    messageDiv.textContent = 'Starting story...';
    messageDiv.className = 'neutral';

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
        paragraphJustCompleted = true;
        messageDiv.textContent = 'Story ready, start typing the first paragraph.';
        messageDiv.className = 'neutral';
        inputBox.disabled = false;
        inputBox.focus();
        initSplits(textContent);
        updateTierChart(data.outcome_tier, data.tier_boundaries);
        retryAction = null;
    } catch (error) {
        showError(error.message, retryAction);
    }
}
