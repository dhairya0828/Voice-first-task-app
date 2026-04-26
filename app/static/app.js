const state = {
    token: localStorage.getItem("voice_task_token") || "",
    currentUser: null,
    recognition: null,
    isListening: false,
    suppressRecognitionUpdates: false,
    manualStopRequested: false,
    autoStopTriggered: false,
    silenceTimer: null,
    finalTranscript: "",
};

const elements = {
    authSection: document.getElementById("auth-section"),
    appSection: document.getElementById("app-section"),
    authStatus: document.getElementById("auth-status"),
    voiceStatus: document.getElementById("voice-status"),
    interpretationOutput: document.getElementById("interpretation-output"),
    currentUser: document.getElementById("current-user"),
    tasksBody: document.getElementById("tasks-body"),
    statusFilter: document.getElementById("task-status-filter"),
    voiceInput: document.getElementById("voice-input"),
    startMicBtn: document.getElementById("start-mic-btn"),
    stopMicBtn: document.getElementById("stop-mic-btn"),
};

const API_BASE_URL = (() => {
    const raw = (window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) || "";
    return raw.endsWith("/") ? raw.slice(0, -1) : raw;
})();
const SILENCE_AUTO_STOP_MS = 2000;
const SILENCE_AUTO_STOP_SECONDS = SILENCE_AUTO_STOP_MS / 1000;

function setStatus(node, message, type = "") {
    node.textContent = message || "";
    node.className = `status ${type}`.trim();
}

function updateMicControls() {
    if (!elements.startMicBtn || !elements.stopMicBtn) return;
    elements.startMicBtn.disabled = state.isListening;
    elements.stopMicBtn.disabled = !state.isListening;
    elements.startMicBtn.setAttribute("aria-pressed", state.isListening ? "true" : "false");
}

function sleep(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function stopMicCaptureIfActive() {
    if (!state.recognition || !state.isListening) {
        return;
    }

    state.manualStopRequested = true;
    state.autoStopTriggered = false;
    if (state.silenceTimer) {
        window.clearTimeout(state.silenceTimer);
        state.silenceTimer = null;
    }

    try {
        state.recognition.stop();
    } catch {
        state.isListening = false;
        updateMicControls();
        return;
    }

    const waitUntil = Date.now() + 2500;
    while (state.isListening && Date.now() < waitUntil) {
        await sleep(50);
    }

    if (state.isListening) {
        try {
            state.recognition.abort();
        } catch {}
        await sleep(60);
    }

    if (state.isListening) {
        state.isListening = false;
        updateMicControls();
    }
}

async function api(path, { method = "GET", body = null, form = false } = {}) {
    const headers = {};

    if (state.token) {
        headers.Authorization = `Bearer ${state.token}`;
    }

    let payload;
    if (body !== null) {
        if (form) {
            headers["Content-Type"] = "application/x-www-form-urlencoded";
            payload = body;
        } else {
            headers["Content-Type"] = "application/json";
            payload = JSON.stringify(body);
        }
    }

    const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
    const response = await fetch(url, { method, headers, body: payload });
    let data = {};

    try {
        data = await response.json();
    } catch {
        data = {};
    }

    if (!response.ok) {
        const detail = data.detail || "Request failed";
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }

    return data;
}

function showAuth() {
    elements.authSection.classList.remove("hidden");
    elements.appSection.classList.add("hidden");
}

function showApp() {
    elements.authSection.classList.add("hidden");
    elements.appSection.classList.remove("hidden");
    elements.currentUser.textContent = `Logged in as ${state.currentUser?.email || ""}`;
}

function formatUtc(value) {
    if (!value) return "-";
    const dt = new Date(value);
    return dt.toISOString().replace("T", " ").slice(0, 16);
}

function createTaskActionButton(action, taskId, label) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.action = action;
    button.dataset.id = String(taskId);
    button.textContent = label;
    return button;
}

function renderTasks(tasks) {
    elements.tasksBody.textContent = "";

    if (!tasks.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 5;
        cell.textContent = "No tasks found.";
        row.appendChild(cell);
        elements.tasksBody.appendChild(row);
        return;
    }

    tasks.forEach((task) => {
        const row = document.createElement("tr");

        const titleCell = document.createElement("td");
        const strong = document.createElement("strong");
        strong.textContent = task.title;
        titleCell.appendChild(strong);
        const desc = document.createElement("div");
        desc.className = "muted";
        desc.textContent = task.description || "";
        titleCell.appendChild(desc);

        const dueCell = document.createElement("td");
        dueCell.textContent = formatUtc(task.due_date);

        const statusCell = document.createElement("td");
        const statusBadge = document.createElement("span");
        statusBadge.className = `badge ${task.status}`;
        statusBadge.textContent = task.status;
        statusCell.appendChild(statusBadge);

        const delayCell = document.createElement("td");
        delayCell.textContent = String(task.delayed_count);

        const actionCell = document.createElement("td");
        if (task.status === "pending") {
            const actionRow = document.createElement("div");
            actionRow.className = "action-row";
            actionRow.appendChild(createTaskActionButton("complete", task.id, "Complete"));
            actionRow.appendChild(createTaskActionButton("cancel", task.id, "Cancel"));
            actionRow.appendChild(createTaskActionButton("delay", task.id, "Delay"));
            actionCell.appendChild(actionRow);
        } else {
            actionCell.textContent = "-";
        }

        row.appendChild(titleCell);
        row.appendChild(dueCell);
        row.appendChild(statusCell);
        row.appendChild(delayCell);
        row.appendChild(actionCell);

        elements.tasksBody.appendChild(row);
    });
}

function drawStatusChart(statusDistribution) {
    const canvas = document.getElementById("status-chart");
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const entries = Object.entries(statusDistribution || {});
    if (!entries.length) return;

    const max = Math.max(...entries.map(([, value]) => value), 1);
    const barWidth = 90;
    const gap = 20;
    const startX = 30;
    const baseY = 180;
    const palette = ["#0d63ff", "#19a15f", "#c62828", "#a66b00"];

    entries.forEach(([label, value], index) => {
        const x = startX + index * (barWidth + gap);
        const h = (value / max) * 120;
        const y = baseY - h;

        ctx.fillStyle = palette[index % palette.length];
        ctx.fillRect(x, y, barWidth, h);

        ctx.fillStyle = "#1b2430";
        ctx.font = "12px Arial";
        ctx.fillText(String(value), x + 35, y - 8);
        ctx.fillText(label.replace("_", " "), x, baseY + 18);
    });
}

function drawTrendChart(trend) {
    const canvas = document.getElementById("trend-chart");
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!trend || !trend.length) return;

    const values = trend.map((point) => point.completed);
    const max = Math.max(...values, 1);
    const minX = 35;
    const maxX = canvas.width - 20;
    const minY = 20;
    const maxY = canvas.height - 35;

    ctx.strokeStyle = "#d4d9e2";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(minX, maxY);
    ctx.lineTo(maxX, maxY);
    ctx.stroke();

    const stepX = (maxX - minX) / Math.max(trend.length - 1, 1);

    ctx.strokeStyle = "#0d63ff";
    ctx.lineWidth = 2;
    ctx.beginPath();

    trend.forEach((point, index) => {
        const x = minX + index * stepX;
        const normalized = point.completed / max;
        const y = maxY - normalized * (maxY - minY);

        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);

        ctx.fillStyle = "#0d63ff";
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fill();
    });
    ctx.stroke();

    ctx.fillStyle = "#5c6674";
    ctx.font = "11px Arial";
    ctx.fillText("14d ago", minX, maxY + 16);
    ctx.fillText("today", maxX - 28, maxY + 16);
}

async function refreshTasks() {
    const selectedStatus = elements.statusFilter.value;
    const query = selectedStatus ? `?status=${selectedStatus}` : "";
    const tasks = await api(`/api/tasks${query}`);
    renderTasks(tasks);
}

async function refreshAnalytics() {
    const data = await api("/api/analytics/dashboard");

    document.getElementById("kpi-pending").textContent = data.summary.pending_tasks;
    document.getElementById("kpi-on-time").textContent = data.summary.tasks_completed_on_time;
    document.getElementById("kpi-late").textContent = data.summary.tasks_completed_late;
    document.getElementById("kpi-delayed").textContent = data.summary.tasks_delayed;
    document.getElementById("kpi-cancelled").textContent = data.summary.tasks_cancelled;

    drawStatusChart(data.status_distribution);
    drawTrendChart(data.completion_trend);
}

async function refreshAll() {
    await Promise.all([refreshTasks(), refreshAnalytics()]);
}

async function onRegister(event) {
    event.preventDefault();
    setStatus(elements.authStatus, "");

    const payload = {
        email: document.getElementById("register-email").value,
        password: document.getElementById("register-password").value,
        full_name: document.getElementById("register-full-name").value || null,
    };

    try {
        await api("/api/auth/register", { method: "POST", body: payload });
        setStatus(elements.authStatus, "Registration successful. Please login.", "success");
        event.target.reset();
    } catch (error) {
        setStatus(elements.authStatus, error.message, "error");
    }
}

async function onLogin(event) {
    event.preventDefault();
    setStatus(elements.authStatus, "");

    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    try {
        const result = await api("/api/auth/login", { method: "POST", body: formData.toString(), form: true });
        state.token = result.access_token;
        localStorage.setItem("voice_task_token", state.token);
        await hydrateSession();
        setStatus(elements.authStatus, "", "");
    } catch (error) {
        setStatus(elements.authStatus, error.message, "error");
    }
}

async function hydrateSession() {
    state.currentUser = await api("/api/auth/me");
    showApp();
    await refreshAll();
}

function logout() {
    state.token = "";
    state.currentUser = null;
    localStorage.removeItem("voice_task_token");
    showAuth();
}

async function onCreateTask(event) {
    event.preventDefault();

    const dueDateInput = document.getElementById("task-due-date").value;
    const dueDateISO = dueDateInput ? new Date(dueDateInput).toISOString() : null;

    const payload = {
        title: document.getElementById("task-title").value,
        description: document.getElementById("task-description").value || null,
        due_date: dueDateISO,
    };

    try {
        await api("/api/tasks", { method: "POST", body: payload });
        event.target.reset();
        await refreshAll();
    } catch (error) {
        setStatus(elements.voiceStatus, error.message, "error");
    }
}

async function onTaskAction(event) {
    const target = event.target;
    if (!(target instanceof HTMLButtonElement)) return;

    const action = target.dataset.action;
    const id = target.dataset.id;
    if (!action || !id) return;

    try {
        if (action === "complete") {
            await api(`/api/tasks/${id}/complete`, { method: "PATCH" });
        } else if (action === "cancel") {
            await api(`/api/tasks/${id}/cancel`, { method: "PATCH" });
        } else if (action === "delay") {
            const daysRaw = prompt("Delay by how many days?", "1");
            if (!daysRaw) return;
            const days = Number(daysRaw);
            if (!Number.isFinite(days) || days < 1) {
                throw new Error("Please enter a valid positive number of days");
            }
            await api(`/api/tasks/${id}/delay`, { method: "PATCH", body: { days } });
        }

        await refreshAll();
    } catch (error) {
        setStatus(elements.voiceStatus, error.message, "error");
    }
}

function setupVoiceRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const startButton = elements.startMicBtn;
    const stopButton = elements.stopMicBtn;

    if (!SpeechRecognition) {
        startButton.disabled = true;
        stopButton.disabled = true;
        setStatus(elements.voiceStatus, "Speech recognition is not available in this browser. You can still type commands.", "error");
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.continuous = true;
    recognition.maxAlternatives = 1;

    const clearSilenceTimer = () => {
        if (state.silenceTimer) {
            window.clearTimeout(state.silenceTimer);
            state.silenceTimer = null;
        }
    };

    const scheduleSilenceStop = () => {
        clearSilenceTimer();
        state.silenceTimer = window.setTimeout(() => {
            if (!state.isListening || !state.recognition) return;
            state.autoStopTriggered = true;
            state.manualStopRequested = false;
            try {
                state.recognition.stop();
            } catch {
                state.isListening = false;
                updateMicControls();
            }
        }, SILENCE_AUTO_STOP_MS);
    };

    recognition.onstart = () => {
        state.isListening = true;
        state.manualStopRequested = false;
        state.autoStopTriggered = false;
        scheduleSilenceStop();
        updateMicControls();
        setStatus(elements.voiceStatus, "Listening... speak now.");
    };

    recognition.onresult = (event) => {
        if (state.suppressRecognitionUpdates) {
            return;
        }

        let interimTranscript = "";

        for (let i = event.resultIndex; i < event.results.length; i += 1) {
            const result = event.results[i];
            const segment = result && result[0] && result[0].transcript ? result[0].transcript : "";
            if (!segment) continue;

            if (result.isFinal) {
                state.finalTranscript = `${state.finalTranscript} ${segment}`.trim();
            } else {
                interimTranscript = `${interimTranscript} ${segment}`.trim();
            }
        }

        const combined = `${state.finalTranscript} ${interimTranscript}`.trim();
        elements.voiceInput.value = combined;
        scheduleSilenceStop();
    };

    recognition.onerror = (event) => {
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
            setStatus(elements.voiceStatus, "Microphone permission denied. Allow mic access in browser settings.", "error");
            return;
        }

        if (event.error === "audio-capture") {
            setStatus(elements.voiceStatus, "No microphone detected. Connect a mic and try again.", "error");
            return;
        }

        if (event.error === "no-speech") {
            setStatus(elements.voiceStatus, "No speech detected. Keep speaking or press Stop when done.");
            return;
        }

        if (event.error !== "aborted") {
            setStatus(elements.voiceStatus, "Microphone capture failed. You can type the command instead.", "error");
        }
    };

    recognition.onend = () => {
        clearSilenceTimer();
        state.isListening = false;
        updateMicControls();
        if (state.autoStopTriggered) {
            setStatus(elements.voiceStatus, `Microphone auto-stopped after ${SILENCE_AUTO_STOP_SECONDS} seconds of silence.`);
        } else {
            setStatus(elements.voiceStatus, "Microphone stopped.");
        }
        state.autoStopTriggered = false;
        state.manualStopRequested = false;
    };

    startButton.addEventListener("click", () => {
        if (state.isListening) return;

        clearSilenceTimer();
        state.suppressRecognitionUpdates = false;
        state.manualStopRequested = false;
        state.autoStopTriggered = false;
        state.finalTranscript = elements.voiceInput.value.trim();
        updateMicControls();

        try {
            recognition.start();
        } catch (error) {
            updateMicControls();
            const message = error && error.message ? error.message : "Microphone is busy. Try again.";
            setStatus(elements.voiceStatus, message, "error");
        }
    });

    stopButton.addEventListener("click", () => {
        clearSilenceTimer();
        state.manualStopRequested = true;
        state.autoStopTriggered = false;

        if (state.isListening) {
            recognition.stop();
            return;
        }
        updateMicControls();
        setStatus(elements.voiceStatus, "Microphone is already stopped.");
    });

    state.recognition = recognition;
    updateMicControls();
}

async function onInterpret() {
    const text = document.getElementById("voice-input").value.trim();
    if (!text) {
        setStatus(elements.voiceStatus, "Type or speak a command first.", "error");
        return;
    }

    try {
        const interpretation = await api("/api/voice/interpret", { method: "POST", body: { text } });
        elements.interpretationOutput.textContent = JSON.stringify(interpretation, null, 2);
        if (interpretation.warnings.length) {
            setStatus(elements.voiceStatus, interpretation.warnings.join(" | "), "error");
        } else {
            setStatus(elements.voiceStatus, `Interpretation confidence: ${Math.round(interpretation.confidence * 100)}%`, "success");
        }
    } catch (error) {
        setStatus(elements.voiceStatus, error.message, "error");
    }
}

async function onExecute() {
    const text = document.getElementById("voice-input").value.trim();
    if (!text) {
        setStatus(elements.voiceStatus, "Type or speak a command first.", "error");
        return;
    }

    try {
        state.suppressRecognitionUpdates = true;
        await stopMicCaptureIfActive();

        let result = await api("/api/voice/execute", { method: "POST", body: { text, force: false } });

        if (result.requires_confirmation) {
            const reason = result.confirmation_reason || "This command looks ambiguous.";
            const confirmed = window.confirm(`${reason}\n\nPress OK to continue anyway.`);
            if (!confirmed) {
                elements.interpretationOutput.textContent = JSON.stringify(result.interpretation, null, 2);
                setStatus(elements.voiceStatus, "Execution cancelled. You can edit the command and try again.");
                return;
            }

            result = await api("/api/voice/execute", { method: "POST", body: { text, force: true } });
        }

        elements.interpretationOutput.textContent = JSON.stringify(result.interpretation, null, 2);
        setStatus(elements.voiceStatus, result.message, "success");
        elements.voiceInput.value = "";
        state.finalTranscript = "";
        await refreshAll();
    } catch (error) {
        setStatus(elements.voiceStatus, error.message, "error");
    } finally {
        window.setTimeout(() => {
            state.suppressRecognitionUpdates = false;
        }, 150);
    }
}

function bindEvents() {
    document.getElementById("register-form").addEventListener("submit", onRegister);
    document.getElementById("login-form").addEventListener("submit", onLogin);
    document.getElementById("logout-btn").addEventListener("click", logout);

    document.getElementById("task-form").addEventListener("submit", onCreateTask);
    document.getElementById("interpret-btn").addEventListener("click", onInterpret);
    document.getElementById("execute-btn").addEventListener("click", onExecute);

    elements.statusFilter.addEventListener("change", refreshTasks);
    elements.tasksBody.addEventListener("click", onTaskAction);
}

async function bootstrap() {
    bindEvents();
    setupVoiceRecognition();

    if (!state.token) {
        showAuth();
        return;
    }

    try {
        await hydrateSession();
    } catch {
        logout();
    }
}

bootstrap();
