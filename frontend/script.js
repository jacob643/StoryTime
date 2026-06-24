const textDisplay = document.getElementById('textDisplay');
const inputBox = document.getElementById('inputBox');
const messageDiv = document.getElementById('message');

const MSG_WELCOME = "Welcome to Story Time! Type each paragraph to drive the story forward. Faster typing leads to brighter outcomes.";
const MSG_OLLAMA_DOWN = "Ollama is not running. Open Setup to install or start a model.";
const MSG_PROMPT_READY = "Enter a story prompt";

async function checkStartupHealth() {
    try {
        const r = await fetch('/api/health');
        if (!r.ok) return;
        const data = await r.json();
        const firstVisit = data.first_visit;
        const ollamaRunning = data.ollama_running;
        if (firstVisit && !ollamaRunning) {
            messageDiv.textContent = MSG_WELCOME + "\n\n" + MSG_OLLAMA_DOWN;
            messageDiv.className = 'neutral';
        } else if (firstVisit && ollamaRunning) {
            messageDiv.textContent = MSG_WELCOME + "\n\n" + MSG_PROMPT_READY;
            messageDiv.className = 'neutral';
        } else if (!firstVisit && !ollamaRunning) {
            messageDiv.textContent = MSG_OLLAMA_DOWN;
            messageDiv.className = 'error';
        }
    } catch (_) {
        // server not reachable — keep whatever reset() set
    }
}

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
const historyData = [];
let _cachedCpmThresholds = null;

const SETTINGS_DEFAULTS = {
    paragraph_word_count: 40,
    scoring_mode: 'split',
    min_stddev_cpm: 10,
    tier_3_max_sigma: 1.5,
    tier_2_max_sigma: 0.5,
    tier_1_max_sigma: -0.5,
    tier_0_max_sigma: -1.5,
    target_split_size: 50,
    min_split_size: 30,
    temperature: 2,
    top_k: 40,
    top_p: 0.9,
    ollama_model: 'llama3.2',
    ignore_case: false,
};

const DEFAULT_FIXED_THRESHOLDS_CPM = [300, 350, 400, 450];

function refreshDefaultButtons() {
    document.querySelectorAll('.default-btn').forEach(btn => {
        const field = btn.dataset.field;
        const input = document.getElementById(field) || btn.parentElement.querySelector('.ft-boundary');
        if (!input) return;
        let def;
        if (btn.dataset.defaultCpm) {
            def = cpmToDisplay(parseFloat(btn.dataset.defaultCpm));
            btn.textContent = `default: ${def} ${getSpeedUnit()}`;
        } else {
            def = btn.dataset.default;
            btn.textContent = `default: ${def}`;
        }
        const cur = input.value;
        let match = false;
        if (input.tagName === 'SELECT') {
            match = cur === def;
        } else {
            const curNum = parseFloat(cur);
            const defNum = parseFloat(def);
            if (!isNaN(curNum) && !isNaN(defNum)) {
                match = Math.abs(curNum - defNum) < 0.0001;
            } else {
                match = cur === def;
            }
        }
        btn.disabled = match;
    });
}

function getActiveSpeedType() {
    return document.querySelector('input[name="speedType"]:checked')?.value || 'cpm';
}

function cpmToDisplay(cpm) {
    return getActiveSpeedType() === 'wpm' ? cpm / 5 : cpm;
}

function displayToCpm(value) {
    return getActiveSpeedType() === 'wpm' ? value * 5 : value;
}

function getSpeedUnit() {
    return getActiveSpeedType() === 'wpm' ? 'WPM' : 'CPM';
}

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
    splitTimestamps = [];
}

function initSplits(text) {
    splitBoundaries = computeSplits(text);
    splitTimestamps = [];
}

function updateSplitTimestamps() {
    const pos = inputBox.value.length;
    for (let i = 0; i < splitBoundaries.length; i++) {
        if (pos >= splitBoundaries[i] && splitTimestamps.length <= i) {
            splitTimestamps.push(new Date());
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
    document.documentElement.classList.toggle('dark-mode', enabled);
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
    checkStartupHealth();
    document.querySelectorAll('input[name="speedType"]').forEach(el => {
        el.addEventListener('change', () => {
            rebuildHistoryDisplay();
            refreshTierChartFromSettings();
            document.querySelectorAll('.ft-unit').forEach(u => {
                u.textContent = `(${getSpeedUnit()})`;
            });
            const minStddevInput = document.getElementById('optMinStddev');
            if (minStddevInput && minStddevInput.dataset.cpm) {
                minStddevInput.value = cpmToDisplay(parseFloat(minStddevInput.dataset.cpm));
            }
            const minStddevUnit = document.getElementById('optMinStddevUnit');
            if (minStddevUnit) minStddevUnit.textContent = getSpeedUnit();
            if (_cachedCpmThresholds) {
                buildFixedThresholdInputs(_cachedCpmThresholds);
            }
            refreshDefaultButtons();
        });
    });
    document.getElementById('settingsSections').addEventListener('click', (e) => {
        const btn = e.target.closest('.default-btn');
        if (!btn) return;
        const field = btn.dataset.field;
        const input = document.getElementById(field) || btn.parentElement.querySelector('.ft-boundary');
        if (!input) return;
        if (btn.dataset.defaultCpm) {
            input.value = cpmToDisplay(parseFloat(btn.dataset.defaultCpm));
            if (input.dataset) input.dataset.cpm = btn.dataset.defaultCpm;
        } else {
            input.value = btn.dataset.default;
        }
        refreshDefaultButtons();
    });
    document.getElementById('refreshModels').addEventListener('click', async () => {
        const current = document.getElementById('optModel')?.value || 'llama3.2';
        await buildModelSelector(current);
        refreshDefaultButtons();
    });
    document.getElementById('settingsSections').addEventListener('input', (e) => {
        if (e.target.closest('.default-btn')) return;
        refreshDefaultButtons();
    });
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
    retryButton.disabled = true;
    inputWasEmpty = true;
    initialPromptInput.value = '';
    initialPromptInput.focus();
    messageDiv.textContent = 'Enter a story prompt';
    messageDiv.className = 'neutral';
    timeTakenSeconds = 0;
    speed = 0;
    startTime = null;
    document.getElementById('historyEntries').querySelectorAll('.history-item').forEach(el => el.remove());
    historyData.length = 0;
    document.getElementById('lastParagraph').textContent = '';
    resetSplitTracking();
}

function buildHistoryItem(data) {
    const { text, timeTaken, speedCpm, outcomeTier, outcomeLabel, splitSpeeds } = data;
    const item = document.createElement('div');
    item.classList.add('history-item');

    const textElement = document.createElement('div');
    textElement.classList.add('history-text');
    const cropped = text.length > 20 ? text.slice(0, 20) + '[...]' : text;
    textElement.textContent = cropped;

    const metaElement = document.createElement('div');
    metaElement.classList.add('history-meta');
    let meta = `${outcomeLabel} | ${cpmToDisplay(speedCpm).toFixed(1)} ${getSpeedUnit()} | ${timeTaken.toFixed(2)}s`;
    if (splitSpeeds && splitSpeeds.length > 0) {
        const formatted = splitSpeeds.map(s => cpmToDisplay(s).toFixed(1)).join(', ');
        meta += ` [${formatted}]`;
    }
    metaElement.textContent = meta;

    item.appendChild(textElement);
    item.appendChild(metaElement);
    return item;
}

function rebuildHistoryDisplay() {
    const container = document.getElementById('historyEntries');
    container.innerHTML = '';
    for (const data of historyData) {
        container.prepend(buildHistoryItem(data));
    }
}

function addHistory(text, timeTaken, speedCpm, outcomeTier, outcomeLabel, splitSpeeds) {
    historyData.push({ text, timeTaken, speedCpm, outcomeTier, outcomeLabel, splitSpeeds });
    const item = buildHistoryItem(historyData[historyData.length - 1]);
    item.classList.add('history-item-new');
    const container = document.getElementById('historyEntries');
    container.prepend(item);
    container.scrollTop = 0;
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
            if (b) b.textContent = `${cpmToDisplay(boundaries[i])} ${getSpeedUnit()}`;
        }
    }
}

async function refreshTierChartFromSettings() {
    try {
        const r = await fetch('/api/settings/boundaries');
        if (!r.ok) return;
        const data = await r.json();
        updateTierChart(-1, data.boundaries);
    } catch (_) {}
}

function autoScrollTextDisplay() {
    const container = document.getElementById('textDisplayContainer');
    if (!container) return;
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
    if (isNearBottom) {
        container.scrollTop = container.scrollHeight;
    }
}

function updateTextDisplay() {
    const inputText = inputBox.value;
    const ignoreCase = document.getElementById('optIgnoreCase')?.checked || false;
    let displayedText = '';

    let firstError = -1;
    for (let i = 0; i < textContent.length; i++) {
        const inputChar = inputText[i];
        if (inputChar === undefined) break;
        const char = textContent[i];
        const match = ignoreCase
            ? inputChar.toLowerCase() === char.toLowerCase()
            : inputChar === char;
        if (!match) {
            firstError = i;
            break;
        }
    }

    for (let i = 0; i < textContent.length; i++) {
        const char = textContent[i];
        const inputChar = inputText[i];

        if (inputChar === undefined) {
            displayedText += `<span>${char}</span>`;
        } else if (firstError >= 0 && i >= firstError) {
            displayedText += `<span style="background-color: red; color: black;">${char}</span>`;
        } else {
            const match = ignoreCase
                ? inputChar.toLowerCase() === char.toLowerCase()
                : inputChar === char;
            if (match) {
                displayedText += `<span style="background-color: green; color: black;">${char}</span>`;
            } else {
                displayedText += `<span style="background-color: red; color: black;">${char}</span>`;
            }
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
    return `${cpmToDisplay(speed).toFixed(1)} ${getSpeedUnit()}`;
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
        retryButton.disabled = true;
        inputWasEmpty = true;
        messageDiv.textContent = 'paragraph over! take a breather';
        messageDiv.className = 'neutral';
        inputBox.focus();
        initSplits(textContent);
        retryAction = null;
        autoScrollTextDisplay();
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
    const ignoreCase = document.getElementById('optIgnoreCase')?.checked || false;
    const isComplete = ignoreCase
        ? inputBox.value.toLowerCase() === textContent.toLowerCase()
        : inputBox.value === textContent;
    if (isComplete) {
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

function retryParagraph() {
    inputBox.value = '';
    startTime = null;
    paragraphJustCompleted = false;
    resetSplitTracking();
    retryButton.disabled = true;
    messageDiv.textContent = 'Input cleared, retype the paragraph below';
    messageDiv.className = 'neutral';
    inputBox.focus();
    updateTextDisplay();
}

const retryButton = document.getElementById('retryButton');
retryButton.addEventListener('click', retryParagraph);

let inputWasEmpty = true;

inputBox.addEventListener('input', () => {
    const isEmpty = inputBox.value.length === 0;
    if (isEmpty) {
        if (!inputWasEmpty) {
            startTime = null;
            paragraphJustCompleted = false;
            resetSplitTracking();
            messageDiv.textContent = 'Input cleared, retype the paragraph below';
            messageDiv.className = 'neutral';
        }
        retryButton.disabled = true;
    } else {
        retryButton.disabled = false;
    }
    inputWasEmpty = isEmpty;

    if (!isEmpty && (paragraphJustCompleted || messageDiv.textContent === 'Input cleared, retype the paragraph below')) {
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

const BUG_REPORT_URL = 'https://github.com/anomalyco/storytime/issues';
const SUPPORT_URL = 'https://github.com/sponsors/anomalyco';

document.getElementById('setupLink').addEventListener('click', () => {
    window.open('/getting_started.html', '_blank');
});

document.getElementById('bugReportLink').addEventListener('click', () => {
    window.open(BUG_REPORT_URL, '_blank');
});

document.getElementById('supportLink').addEventListener('click', () => {
    window.open(SUPPORT_URL, '_blank');
});

document.getElementById('optScoringMode').addEventListener('change', (e) => {
    updateScoringSectionVisibility(e.target.value);
});

function safeVal(v, fallback) {
    return (v === null || v === undefined || v === '' || v !== v) ? fallback : v;
}

function buildFixedThresholdInputs(thresholds) {
    fixedThresholdsContainer.innerHTML = '';
    // 4 boundary inputs — tier-chart style, centered, with tier labels stacked vertically
    const tierNames = [
        { tier: 4, name: 'very positive' },
        { tier: 3, name: 'positive' },
        { tier: 2, name: 'neutral' },
        { tier: 1, name: 'negative' },
        { tier: 0, name: 'very negative' },
    ];
    // thresholds is [b0, b1, b2, b3] ascending CPM; convert to display then reverse
    const boundaries = thresholds.map(v => cpmToDisplay(v)).reverse();

    for (let i = 0; i < tierNames.length; i++) {
        const label = document.createElement('div');
        label.className = 'ft-tier-label';
        label.textContent = `${tierNames[i].name} (tier ${tierNames[i].tier})`;
        fixedThresholdsContainer.appendChild(label);
        if (i < boundaries.length) {
            const row = document.createElement('div');
            row.className = 'ft-row';
            const inp = document.createElement('input');
            inp.type = 'number';
            inp.className = 'ft-boundary';
            inp.step = '1';
            inp.min = '0';
            inp.value = safeVal(boundaries[i], 30);
            row.appendChild(inp);
            const unit = document.createElement('span');
            unit.className = 'ft-unit';
            unit.textContent = `(${getSpeedUnit()})`;
            row.appendChild(unit);
            const defaultCpm = DEFAULT_FIXED_THRESHOLDS_CPM[DEFAULT_FIXED_THRESHOLDS_CPM.length - 1 - i];
            const btn = document.createElement('button');
            btn.className = 'default-btn';
            btn.dataset.field = 'ft-boundary-' + i;
            btn.dataset.defaultCpm = defaultCpm;
            btn.textContent = `default: ${cpmToDisplay(defaultCpm)} ${getSpeedUnit()}`;
            row.appendChild(btn);
            fixedThresholdsContainer.appendChild(row);
        }
    }
}

async function buildModelSelector(currentModel) {
    const container = document.getElementById('modelSelectorContainer');
    container.innerHTML = '';
    const defaultModel = 'llama3.2';
    let models = [];
    try {
        const r = await fetch('/api/models');
        const data = await r.json();
        const ollama = data.providers.find(p => p.provider === 'ollama');
        if (ollama && ollama.models && ollama.models.length > 0) {
            models = ollama.models;
        }
    } catch (_) {}
    if (models.length > 0) {
        const sel = document.createElement('select');
        sel.id = 'optModel';
        sel.style.width = '100%';
        for (const m of models) {
            const opt = document.createElement('option');
            opt.value = m;
            opt.textContent = m;
            sel.appendChild(opt);
        }
        if (currentModel && models.includes(currentModel)) {
            sel.value = currentModel;
        }
        container.appendChild(sel);
    } else {
        const inp = document.createElement('input');
        inp.type = 'text';
        inp.id = 'optModel';
        inp.style.width = '100%';
        inp.value = currentModel || defaultModel;
        container.appendChild(inp);
    }
}

async function loadSettings() {
    try {
        const r = await fetch('/api/settings');
        if (!r.ok) throw new Error('Failed to load settings');
        const s = await r.json();
        const mode = s.scoring_mode;
        document.getElementById('optScoringMode').value = mode;
        const minStddevInput = document.getElementById('optMinStddev');
        minStddevInput.value = cpmToDisplay(s.min_stddev_cpm);
        minStddevInput.dataset.cpm = s.min_stddev_cpm;
        const minStddevUnit = document.getElementById('optMinStddevUnit');
        if (minStddevUnit) minStddevUnit.textContent = getSpeedUnit();
        document.getElementById('optTier3Sigma').value = s.tier_3_max_sigma;
        document.getElementById('optTier2Sigma').value = s.tier_2_max_sigma;
        document.getElementById('optTier1Sigma').value = s.tier_1_max_sigma;
        document.getElementById('optTier0Sigma').value = s.tier_0_max_sigma;
        document.getElementById('wordCountInput').value = s.paragraph_word_count;
        document.getElementById('optTargetSplit').value = s.target_split_size;
        document.getElementById('optMinSplit').value = s.min_split_size;
        document.getElementById('optTemperature').value = s.temperature;
        document.getElementById('optTopK').value = s.top_k;
        document.getElementById('optTopP').value = s.top_p;
        _cachedCpmThresholds = s.fixed_thresholds;
        buildFixedThresholdInputs(s.fixed_thresholds);
        outcomeDirectionsData = {};
        for (let t = 0; t <= 4; t++) {
            const dirs = s.outcome_directions[t.toString()];
            outcomeDirectionsData[t] = Array.isArray(dirs) && dirs.length > 0 ? [...dirs] : [...DEFAULT_PHRASINGS[t]];
        }
        currentTierForPrompts = 0;
        document.getElementById('tierPromptSelector').value = '0';
        renderTierPrompts();
        await buildModelSelector(s.ollama_model);
        document.getElementById('optIgnoreCase').checked = s.ignore_case;
        updateScoringSectionVisibility(mode);
        refreshDefaultButtons();
    } catch (e) {
        console.error('loadSettings:', e);
    }
}

function updateScoringSectionVisibility(mode) {
    const adaptiveSection = document.getElementById('sectionAdaptiveParams');
    const fixedSection = document.getElementById('sectionFixedThresholds');
    if (adaptiveSection) adaptiveSection.style.display = mode === 'split' ? '' : 'none';
    if (fixedSection) fixedSection.style.display = mode === 'fixed' ? '' : 'none';
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
    const boundaries = fixedThresholdsContainer.querySelectorAll('.ft-boundary');
    // collect 4 boundary values (display order: descending); flip to ascending
    const b = [];
    for (const inp of boundaries) b.push(displayToCpm(safeParseFloat(inp.value, 30)));
    b.reverse();
    const fixedThresholds = b;
    saveCurrentTierPrompts();
    const outcomeDirections = {};
    for (let t = 0; t <= 4; t++) {
        outcomeDirections[t] = outcomeDirectionsData[t] || [''];
    }
    return {
        scoring_mode: document.getElementById('optScoringMode').value,
        paragraph_word_count: safeParseInt(document.getElementById('wordCountInput').value, 40),
        min_stddev_cpm: displayToCpm(safeParseFloat(document.getElementById('optMinStddev').value, 10)),
        tier_0_max_sigma: safeParseFloat(document.getElementById('optTier0Sigma').value, -1.5),
        tier_1_max_sigma: safeParseFloat(document.getElementById('optTier1Sigma').value, -0.5),
        tier_2_max_sigma: safeParseFloat(document.getElementById('optTier2Sigma').value, 0.5),
        tier_3_max_sigma: safeParseFloat(document.getElementById('optTier3Sigma').value, 1.5),
        fixed_thresholds: fixedThresholds,
        target_split_size: safeParseInt(document.getElementById('optTargetSplit').value, 50),
        min_split_size: safeParseInt(document.getElementById('optMinSplit').value, 30),
        temperature: Math.max(0, safeParseFloat(document.getElementById('optTemperature').value, 2)),
        top_k: Math.max(0, safeParseInt(document.getElementById('optTopK').value, 40)),
        top_p: Math.min(1, Math.max(0, safeParseFloat(document.getElementById('optTopP').value, 0.9))),
        outcome_directions: outcomeDirections,
        ollama_model: (document.getElementById('optModel') || {}).value || 'llama3.2',
        ignore_case: document.getElementById('optIgnoreCase').checked,
    };
}

// tier prompt dynamic UI

const DEFAULT_PHRASINGS = {
    0: [
        'an even worse situation with no clear way out',
        'disaster strikes without warning',
        'everything falls apart in the worst possible way',
        'a catastrophic turn no one expected',
        'the situation deteriorates into chaos',
        'hope fades as things go from bad to worse',
        'a devastating blow changes everything',
        'the bottom falls out of the situation',
        'darkness closes in from all sides',
        'an irreversible tragedy unfolds',
    ],
    1: [
        'a significant setback that makes things more difficult',
        'an obstacle appears that complicates the journey',
        'a painful loss that must be endured',
        'circumstances take a turn for the worse',
        'a difficult challenge tests resolve',
        'progress is halted by unexpected trouble',
        'a costly mistake has serious consequences',
        'the path forward becomes more treacherous',
        'a troubling revelation changes the stakes',
        'trust is broken and must be rebuilt',
    ],
    2: [
        'a minor challenge that the protagonist pushes through',
        'a small hurdle that requires some effort',
        'the journey continues with a moment of uncertainty',
        'a brief moment of tension arises and passes',
        'there is a slight bump in the road ahead',
        'an ordinary obstacle turns into a learning moment',
        'a simple test of patience presents itself',
        'things remain steady with a touch of difficulty',
        'a passing inconvenience slows things down',
        'a mild complication arises but seems manageable',
    ],
    3: [
        'a small success that aids the journey',
        'a helpful coincidence brightens the path',
        'a minor victory boosts morale and momentum',
        'an unexpected advantage presents itself',
        'kindness from an unlikely source changes things',
        'a piece of luck shifts the situation slightly',
        'a small discovery proves useful',
        'things go better than expected for a moment',
        'a brief moment of triumph lifts the spirit',
        'a gentle wind of fortune pushes things forward',
    ],
    4: [
        'a great improvement to the situation, a significant advance',
        'a remarkable breakthrough changes the game entirely',
        'fortune smiles in an extraordinary way',
        'an incredible opportunity presents itself',
        'things come together better than anyone could hope',
        'a stunning victory leaves everyone in awe',
        'the path clears in a truly unexpected way',
        'a gift of fate changes the direction of the story',
        'triumph emerges from the struggle in grand fashion',
        'a brilliant stroke of genius leads to great success',
    ],
};

let outcomeDirectionsData = {};
let currentTierForPrompts = 0;

function getTierPhrasings(tier) {
    return outcomeDirectionsData[tier] || DEFAULT_PHRASINGS[tier] || [''];
}

function renderTierPrompts() {
    const list = document.getElementById('tierPromptList');
    if (!list) return;
    const phrasings = getTierPhrasings(currentTierForPrompts);
    list.innerHTML = '';
    for (let i = 0; i < phrasings.length; i++) {
        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.gap = '4px';
        row.style.marginBottom = '4px';
        row.style.alignItems = 'center';
        if (phrasings.length > 1) {
            const minus = document.createElement('button');
            minus.textContent = '−';
            minus.type = 'button';
            minus.name = 'tierPromptRemove';
            minus.addEventListener('click', () => {
                saveCurrentTierPrompts();
                outcomeDirectionsData[currentTierForPrompts].splice(i, 1);
                renderTierPrompts();
            });
            row.appendChild(minus);
        }
        const wrap = document.createElement('div');
        wrap.style.flex = '1';
        wrap.style.display = 'flex';
        const input = document.createElement('input');
        input.type = 'text';
        input.value = phrasings[i];
        input.name = 'tierPromptPhrasing';
        input.style.width = '100%';
        input.style.boxSizing = 'border-box';
        input.style.marginLeft = '0';
        input.dataset.index = i;
        wrap.appendChild(input);
        row.appendChild(wrap);
        list.appendChild(row);
    }
    // empty trailing input for add-on-type
    const trail = document.createElement('div');
    trail.style.display = 'flex';
    trail.style.gap = '4px';
    trail.style.alignItems = 'center';
    const trailWrap = document.createElement('div');
    trailWrap.style.flex = '1';
    trailWrap.style.display = 'flex';
    const trailInput = document.createElement('input');
    trailInput.type = 'text';
    trailInput.placeholder = 'type a new phrasing…';
    trailInput.name = 'tierPromptPhrasing';
    trailInput.style.width = '100%';
    trailInput.style.boxSizing = 'border-box';
    trailInput.style.marginLeft = '0';
    trailInput.dataset.trail = '1';
    trailWrap.appendChild(trailInput);
    trail.appendChild(trailWrap);
    list.appendChild(trail);
}

function saveCurrentTierPrompts() {
    const list = document.getElementById('tierPromptList');
    if (!list) return;
    const inputs = list.querySelectorAll('input:not([data-trail])');
    const phrasings = [];
    for (const inp of inputs) {
        const val = inp.value.trim();
        if (val) phrasings.push(val);
    }
    if (phrasings.length === 0) phrasings.push('');
    outcomeDirectionsData[currentTierForPrompts] = phrasings;
}

// register tier prompt event listeners (run after the first DOMContentLoaded handler)
document.addEventListener('DOMContentLoaded', function initTierPrompts() {
    const sel = document.getElementById('tierPromptSelector');
    if (sel) {
        sel.addEventListener('change', () => {
            saveCurrentTierPrompts();
            currentTierForPrompts = parseInt(sel.value, 10);
            renderTierPrompts();
        });
    }
    // add-on-type / delete-if-empty via delegation
    const list = document.getElementById('tierPromptList');
    if (list) {
        list.addEventListener('input', (e) => {
            const target = e.target;
            if (target.nodeName !== 'INPUT') return;

            if (target.dataset.trail === '1' && target.value.trim()) {
                const typed = target.value.trim();
                saveCurrentTierPrompts();
                if (!Array.isArray(outcomeDirectionsData[currentTierForPrompts])) {
                    outcomeDirectionsData[currentTierForPrompts] = [];
                }
                outcomeDirectionsData[currentTierForPrompts].push(typed);
                const targetScrollTop = list.parentElement?.scrollTop;
                renderTierPrompts();
                const container = document.getElementById('tierPromptList');
                const allInputs = container.querySelectorAll('input');
                if (targetScrollTop !== undefined) {
                    list.parentElement.scrollTop = targetScrollTop;
                }
                // focus the last REAL input (the one just populated), not the trailing one
                const focusIdx = allInputs.length - 2;
                if (focusIdx >= 0) allInputs[focusIdx].focus();
            } else if (!target.dataset.trail && !target.value.trim()) {
                // real phrasing input erased empty — delete it only if it's the last one
                const realInputs = list.querySelectorAll('input:not([data-trail])');
                const lastReal = realInputs[realInputs.length - 1];
                if (target === lastReal) {
                    const arr = outcomeDirectionsData[currentTierForPrompts];
                    if (Array.isArray(arr) && arr.length > 0) {
                        arr.pop();
                        renderTierPrompts();
                        const newInputs = list.querySelectorAll('input');
                        if (newInputs.length) newInputs[newInputs.length - 1].focus();
                    }
                }
            }
        });
    }
});

document.getElementById('saveSettings').addEventListener('click', async () => {
    try {
        const body = collectSettings();
        const r = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!r.ok) throw new Error('Failed to save settings');
        const minStddevInput = document.getElementById('optMinStddev');
        if (minStddevInput) minStddevInput.dataset.cpm = body.min_stddev_cpm;
        _cachedCpmThresholds = body.fixed_thresholds;
        messageDiv.textContent = 'Settings saved.';
        messageDiv.className = 'success';
        settingsPanel.classList.add('collapsed');
        refreshTierChartFromSettings();
    } catch (e) {
        messageDiv.textContent = 'Settings save error: ' + e.message;
        messageDiv.className = 'error';
    }
});

document.getElementById('resetSettings').addEventListener('click', async () => {
    try {
        const r = await fetch('/api/settings/reset', { method: 'POST' });
        if (!r.ok) throw new Error('Failed to reset settings');
        settingsPanel.classList.add('collapsed');
        await loadSettings();
        refreshTierChartFromSettings();
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
    const range = simulatedDeviation > 0 ? ` ±${cpmToDisplay(simulatedDeviation)}` : '';

    if (!textContent) {
        initialPromptInput.value = 'a skateboard with a soul trying to find its home';
        messageDiv.textContent = `Starting simulation at ${cpmToDisplay(cpm)}${range} ${getSpeedUnit()}...`;
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

    messageDiv.textContent = `[SIMULATION ${cpmToDisplay(cpm)}${range} ${getSpeedUnit()}]`;
    messageDiv.className = 'simulation';
    startTime = new Date();
    inputBox.value = textContent;
    const splitSpeeds = computeSplitSpeeds();
    await fetchNextParagraph(textContent, simulatedCpm, splitSpeeds);
    simulatedCpm = null;
    simulatedDeviation = 0;
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
        retryButton.disabled = true;
        inputWasEmpty = true;
        messageDiv.textContent = 'Story ready, start typing the first paragraph.';
        messageDiv.className = 'neutral';
        inputBox.disabled = false;
        inputBox.focus();
        initSplits(textContent);
        updateTierChart(data.outcome_tier, data.tier_boundaries);
        autoScrollTextDisplay();
        retryAction = null;
    } catch (error) {
        showError(error.message, retryAction);
    }
}
