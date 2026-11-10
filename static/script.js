const $ = id => document.getElementById(id);

const chatInput = $("chatInput");
const messages = $("messages");
const chat = $("chat");
const welcome = $("welcome");

let recorder = null;
let chunks = [];
let stream = null;
let audioUrl = null;
let toastTimer;
let currentConversationId = null;

const voiceSelect = $("voiceSelect");
const speedControl = $("speechSpeed");
const speedValue = $("speedValue");

const voiceDescriptions = {
    Kaveri: "Female voice · Kaveri",
    Pranav: "Male voice · Pranav",
    Nalini: "Voice · Nalini",
    Deepak: "Male voice · Deepak"
};

voiceSelect.addEventListener("change", () => {
    $("voiceNote").textContent =
        voiceDescriptions[voiceSelect.value] || "Selected voice";
});

speedControl.addEventListener("input", () => {
    speedValue.textContent =
        Number(speedControl.value).toFixed(2).replace(/0$/, "") + "×";
});

function toast(message) {
    const el = $("toast");
    el.textContent = message;
    el.classList.add("show");

    clearTimeout(toastTimer);

    toastTimer = setTimeout(() => {
        el.classList.remove("show");
    }, 3200);
}

function orb(state, text) {
    const area = document.querySelector(".orb-area");

    area.classList.remove("listening", "speaking");

    if (state) {
        area.classList.add(state);
    }

    $("orbStatus").textContent = text;
}

function resizeInput() {
    chatInput.style.height = "auto";

    chatInput.style.height =
        Math.min(chatInput.scrollHeight, 120) + "px";
}

function copyText(text) {
    if (navigator.clipboard?.writeText) {
        return navigator.clipboard.writeText(text);
    }

    const helper = document.createElement("textarea");
    helper.value = text;
    helper.setAttribute("readonly", "");
    helper.style.position = "fixed";
    helper.style.opacity = "0";
    document.body.append(helper);
    helper.select();
    const copied = document.execCommand("copy");
    helper.remove();
    return copied ? Promise.resolve() : Promise.reject(new Error("Copy is unavailable."));
}

async function shareText(text) {
    if (navigator.share) {
        await navigator.share({ title: "Bharat Voice AI", text });
        return "Shared";
    }

    await copyText(text);
    return "Copied to clipboard — ready to share";
}

function addResponseActions(content, text, retryValue) {
    const actions = document.createElement("div");
    actions.className = "message-actions";

    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "message-action";
    copy.textContent = "Copy";
    copy.setAttribute("aria-label", "Copy AI response");
    copy.addEventListener("click", async () => {
        try {
            await copyText(text);
            copy.textContent = "Copied";
            toast("Response copied to clipboard");
            setTimeout(() => { copy.textContent = "Copy"; }, 1600);
        } catch (error) {
            toast("Unable to copy this response");
        }
    });

    const share = document.createElement("button");
    share.type = "button";
    share.className = "message-action";
    share.textContent = "Share";
    share.setAttribute("aria-label", "Share AI response");
    share.addEventListener("click", async () => {
        try {
            toast(await shareText(text));
        } catch (error) {
            if (error.name !== "AbortError") toast("Unable to share this response");
        }
    });

    const retry = document.createElement("button");
    retry.type = "button";
    retry.className = "message-action";
    retry.textContent = "Retry";
    retry.setAttribute("aria-label", "Retry AI response");
    retry.addEventListener("click", () => {
        if (!retryValue || $("sendBtn").disabled) return;
        content.closest(".message")?.remove();
        sendMessage(retryValue, true);
    });

    actions.append(copy, share, retry);
    content.append(actions);
}

function addMessage(text, role, retryValue = "") {
    const row = document.createElement("div");
    row.className = "message " + role;

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.textContent = role === "user" ? "YOU" : "BV";

    const content = document.createElement("div");
    content.className = "msg-content";

    const label = document.createElement("div");
    label.className = "msg-label";
    label.textContent = role === "user" ? "You" : "Bharat Voice AI";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.textContent = text;

    content.append(label, bubble);
    if (role === "assistant") {
        addResponseActions(content, text, retryValue);
    }
    row.append(avatar, content);

    messages.append(row);

    chat.classList.add("visible");
    welcome.style.display = "none";

    row.scrollIntoView({
        behavior: "smooth",
        block: "nearest"
    });
}

// ===============================
// CHAT SYSTEM
// ===============================

async function sendMessage(value = chatInput.value.trim(), isRetry = false) {
    if (!value) return;

    if (!isRetry) {
        addMessage(value, "user");
    }

    chatInput.value = "";
    resizeInput();

    $("sendBtn").disabled = true;

    const pending = document.createElement("div");
    pending.className = "message";

    pending.innerHTML = `
        <div class="msg-avatar">BV</div>
        <div class="msg-content">
            <div class="msg-label">Bharat Voice AI</div>
            <div class="msg-bubble">Thinking...</div>
        </div>
    `;

    messages.append(pending);

    orb("", "Connecting to AI...");

    const controller = new AbortController();

    const timeoutId = setTimeout(() => {
        controller.abort();
    }, 45000);

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            signal: controller.signal,
            body: JSON.stringify({
                message: value,
                conversation_id: currentConversationId,
                language: $("languageSelect").value
            })
        });

        const data = await res.json();

        if (!res.ok || !data.success) {
            throw new Error(
                data.error || "AI response unavailable."
            );
        }

        pending.remove();

        currentConversationId = data.conversation_id;

        addMessage(
            data.reply || "No response received.",
            "assistant",
            value
        );

        refreshConversations();

        orb("", "Ready when you are");

    } catch (error) {
        pending.remove();

        const row = document.createElement("div");
        row.className = "message assistant";

        const avatar = document.createElement("div");
        avatar.className = "msg-avatar";
        avatar.textContent = "BV";

        const content = document.createElement("div");
        content.className = "msg-content";

        const label = document.createElement("div");
        label.className = "msg-label";
        label.textContent = "Bharat Voice AI";

        const bubble = document.createElement("div");
        bubble.className = "msg-bubble";

        bubble.textContent =
            error.name === "AbortError"
                ? "The request took longer than 45 seconds. Please try again."
                : error.message;

        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "retry-btn";
        retry.textContent = "↻ Retry";

        retry.addEventListener("click", () => {
            row.remove();
            sendMessage(value, true);
        });

        content.append(label, bubble, retry);
        row.append(avatar, content);

        messages.append(row);

        row.scrollIntoView({
            behavior: "smooth",
            block: "nearest"
        });

        orb("", "Ready when you are");

    } finally {
        clearTimeout(timeoutId);

        $("sendBtn").disabled = false;
        chatInput.focus();
    }
}

$("sendBtn").addEventListener("click", () => {
    sendMessage();
});

chatInput.addEventListener("input", resizeInput);

chatInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

document.querySelectorAll(".suggestion").forEach(button => {
    button.addEventListener("click", () => {
        sendMessage(button.dataset.prompt);
    });
});

// ===============================
// NEW CHAT
// ===============================

$("newChat").addEventListener("click", () => {
    currentConversationId = null;

    messages.innerHTML = "";

    chat.classList.remove("visible");
    welcome.style.display = "";

    chatInput.value = "";

    resizeInput();

    orb("", "Ready when you are");

    refreshConversations();
});

// ===============================
// SIDEBAR
// ===============================

$("menuBtn").addEventListener("click", () => {
    $("sidebar").classList.toggle("open");
});

document.addEventListener("click", e => {
    if (
        innerWidth <= 680 &&
        !e.target.closest("#sidebar") &&
        !e.target.closest("#menuBtn")
    ) {
        $("sidebar").classList.remove("open");
    }
});

// ===============================
// AUDIO FILE TRANSCRIPTION
// ===============================

$("audio").addEventListener("change", e => {
    $("fileName").textContent =
        e.target.files[0]?.name || "Choose an audio file";
});

$("transcribeBtn").addEventListener("click", async () => {
    const file = $("audio").files[0];

    if (!file) {
        return toast("Please choose an audio file first.");
    }

    const btn = $("transcribeBtn");
    const form = new FormData();

    form.append("audio", file);

    btn.disabled = true;
    btn.textContent = "Transcribing...";

    orb("listening", "Prisma is processing your audio...");

    try {
        const res = await fetch("/api/transcribe", {
            method: "POST",
            body: form
        });

        const raw = await res.text();

        let data;

        try {
            data = JSON.parse(raw);
        } catch {
            throw Error("Invalid server response");
        }

        if (!res.ok || data.success === false) {
            throw Error(
                data.details ||
                data.error ||
                "Transcription failed"
            );
        }

        $("transcript").value =
            data.transcript || data.text || "";

        if (!$("transcript").value) {
            throw Error("No transcript returned");
        }

        $("speechText").value = $("transcript").value;

        toast("Transcription completed");

    } catch (error) {
        toast("Transcription error: " + error.message);

    } finally {
        btn.disabled = false;
        btn.textContent = "Transcribe audio →";

        orb("", "Ready when you are");
    }
});

// ===============================
// TEXT TO SPEECH
// ===============================

$("speakBtn").addEventListener("click", async () => {
    const text = $("speechText").value.trim();

    if (!text) {
        return toast("Please enter some text first.");
    }

    const btn = $("speakBtn");

    btn.disabled = true;
    btn.textContent = "Generating voice...";

    orb("speaking", "Timbre is creating your voice...");

    try {
        const res = await fetch("/api/speak", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text,
                voice: voiceSelect.value,
                speed: Number(speedControl.value)
            })
        });

        if (!res.ok) {
            let data = {};

            try {
                data = await res.json();
            } catch {}

            throw Error(
                data.details ||
                data.error ||
                "Voice generation failed"
            );
        }

        const blob = await res.blob();

        if (audioUrl) {
            URL.revokeObjectURL(audioUrl);
        }

        audioUrl = URL.createObjectURL(blob);

        $("player").src = audioUrl;
        $("player").hidden = false;

        await $("player").play();

        toast("Voice generated successfully");

    } catch (error) {
        toast("Voice error: " + error.message);

    } finally {
        btn.disabled = false;
        btn.textContent = "Generate voice →";

        orb("", "Ready when you are");
    }
});

// ===============================
// MICROPHONE RECORDING
// ===============================

$("micBtn").addEventListener("click", async () => {
    const btn = $("micBtn");

    if (recorder && recorder.state === "recording") {
        recorder.stop();

        btn.classList.remove("recording");
        btn.textContent = "🎙";

        orb("", "Processing recording...");

        return;
    }

    if (
        !navigator.mediaDevices?.getUserMedia ||
        !window.MediaRecorder
    ) {
        return toast(
            "Microphone recording is not supported in this browser."
        );
    }

    try {
        stream = await navigator.mediaDevices.getUserMedia({
            audio: true
        });

        chunks = [];

        const mime = MediaRecorder.isTypeSupported(
            "audio/webm;codecs=opus"
        )
            ? "audio/webm;codecs=opus"
            : "";

        recorder = new MediaRecorder(
            stream,
            mime ? { mimeType: mime } : {}
        );

        recorder.ondataavailable = e => {
            if (e.data.size) {
                chunks.push(e.data);
            }
        };

        recorder.onstop = async () => {
            const blob = new Blob(chunks, {
                type: recorder.mimeType || "audio/webm"
            });

            stream.getTracks().forEach(track => track.stop());
            stream = null;

            const file = new File(
                [blob],
                "voice-note.webm",
                { type: blob.type }
            );

            const form = new FormData();

            form.append("audio", file);

            try {
                const res = await fetch("/api/transcribe", {
                    method: "POST",
                    body: form
                });

                const raw = await res.text();

                let data;

                try {
                    data = JSON.parse(raw);
                } catch {
                    throw Error("Invalid server response");
                }

                if (!res.ok || data.success === false) {
                    throw Error(
                        data.details ||
                        data.error ||
                        "Transcription failed"
                    );
                }

                chatInput.value =
                    data.transcript || data.text || "";

                resizeInput();

                chatInput.focus();

                toast(
                    "Voice converted to text. Review and send."
                );

            } catch (error) {
                toast("Microphone error: " + error.message);

            } finally {
                orb("", "Ready when you are");
            }
        };

        recorder.start();

        btn.classList.add("recording");
        btn.textContent = "■";

        orb(
            "listening",
            "Listening... tap stop when finished"
        );

    } catch (error) {
        toast("Microphone access failed: " + error.message);
    }
});

// ===============================
// SQLITE CHAT HISTORY
// ===============================

const originalAddMessage = addMessage;

async function refreshConversations() {
    try {
        const res = await fetch("/api/conversations");

        if (!res.ok) {
            throw Error("Could not load history");
        }

        const data = await res.json();

        const list = $("savedConversations");

        list.replaceChildren();

        if (
            !data.conversations ||
            data.conversations.length === 0
        ) {
            const empty = document.createElement("p");

            empty.className = "history-empty";
            empty.textContent =
                "No conversations yet. Start chatting to save one.";

            list.append(empty);

            return;
        }

        for (const conversation of data.conversations) {
            const item = document.createElement("div");

            item.className = "db-history-row";

            const button = document.createElement("button");

            button.type = "button";
            button.textContent = "◌  " + conversation.title;

            button.addEventListener("click", async () => {
                try {
                    const response = await fetch(
                        `/api/conversations/${conversation.id}/messages`
                    );

                    if (!response.ok) {
                        throw Error("Unable to open conversation");
                    }

                    const result = await response.json();

                    currentConversationId = conversation.id;

                    messages.replaceChildren();

                    chat.classList.remove("visible");
                    welcome.style.display = "";

                    result.messages.forEach(message => {
                        originalAddMessage(
                            message.content,
                            message.role
                        );
                    });

                    $("sidebar").classList.remove("open");

                } catch (error) {
                    toast(error.message);
                }
            });

            const deleteButton = document.createElement("button");

            deleteButton.type = "button";
            deleteButton.textContent = "×";
            deleteButton.title = "Delete conversation";
            deleteButton.className = "history-delete";

            deleteButton.addEventListener("click", async () => {
                if (!confirm("Delete this conversation?")) {
                    return;
                }

                const response = await fetch(
                    `/api/conversations/${conversation.id}`,
                    {
                        method: "DELETE",
                        headers: {
                            "X-CSRF-Token": window.BHARAT_CSRF
                        }
                    }
                );

                if (response.ok) {
                    if (
                        currentConversationId === conversation.id
                    ) {
                        currentConversationId = null;

                        messages.replaceChildren();

                        chat.classList.remove("visible");
                        welcome.style.display = "";
                    }

                    refreshConversations();

                } else {
                    toast("Could not delete conversation");
                }
            });

            item.append(button, deleteButton);

            list.append(item);
        }

    } catch (error) {
        toast(error.message);
    }
}

// ===============================
// LANGUAGE SETTINGS
// ===============================

const languageSelect = $("languageSelect");

languageSelect.value = "en";
localStorage.setItem("bharat_voice_ai_language", "en");

languageSelect.addEventListener("change", () => {
    localStorage.setItem(
        "bharat_voice_ai_language",
        languageSelect.value
    );

    toast("Language preference updated");
});

// ===============================
// PREMIUM MODAL
// ===============================

$("premiumBtn").addEventListener("click", () => {
    $("premiumModal").hidden = false;
});

$("closePremium").addEventListener("click", () => {
    $("premiumModal").hidden = true;
});

$("premiumModal").addEventListener("click", e => {
    if (e.target === $("premiumModal")) {
        $("premiumModal").hidden = true;
    }
});

document.addEventListener("keydown", e => {
    if (e.key === "Escape") {
        $("premiumModal").hidden = true;
    }
});

// ===============================
// INITIAL LOAD
// ===============================

refreshConversations();

// ===============================
// GENERATED LIGHT ANIMATIONS
// ===============================

(() => {
    const reduced = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    const intro = document.getElementById("introStage");

    if (intro && !reduced) {
        setTimeout(() => {
            intro.style.visibility = "hidden";
            intro.style.display = "none";
        }, 2200);
    }

    const revealEls = document.querySelectorAll(".reveal");

    if ("IntersectionObserver" in window && !reduced) {
        const observer = new IntersectionObserver(
            entries => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        observer.unobserve(entry.target);
                    }
                });
            },
            {
                threshold: 0.16,
                rootMargin: "0px 0px -8% 0px"
            }
        );

        revealEls.forEach(el => observer.observe(el));

    } else {
        revealEls.forEach(el => {
            el.classList.add("is-visible");
        });
    }

    // HERO RIBBON ANIMATION

    const hero = document.getElementById("heroRibbon");

    if (hero) {
        const ctx = hero.getContext("2d");

        let w = 0;
        let h = 0;
        let t = 0;

        let mx = 0.5;
        let my = 0.5;

        const palettes = [
            ["#6366f1", "#8b5cf6", "#22d3ee"],
            ["#818cf8", "#a78bfa", "#67e8f9"],
            ["#4f46e5", "#c084fc", "#38bdf8"]
        ];

        let palette = palettes[0];

        const resize = () => {
            const rect = hero.getBoundingClientRect();

            const d = Math.min(
                devicePixelRatio || 1,
                1.7
            );

            w = rect.width;
            h = rect.height;

            hero.width = Math.floor(w * d);
            hero.height = Math.floor(h * d);

            ctx.setTransform(d, 0, 0, d, 0, 0);
        };

        const draw = () => {
            if (!ctx) return;

            ctx.clearRect(0, 0, w, h);

            const colors = palette;

            for (let k = 0; k < 3; k++) {
                ctx.beginPath();

                for (let x = -20; x <= w + 20; x += 4) {
                    const u = x / w;

                    const y =
                        h * (0.25 + k * 0.18) +
                        Math.sin(u * 8 + t * 0.7 + k * 1.9) * h * 0.075 +
                        Math.sin(u * 17 - t * 0.43 + k) * h * 0.025 +
                        (my - 0.5) * 30 +
                        (mx - 0.5) * 20;

                    if (x === -20) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }
                }

                ctx.strokeStyle = colors[k];
                ctx.globalCompositeOperation = "screen";
                ctx.lineWidth = 12;
                ctx.lineCap = "round";
                ctx.shadowColor = colors[k];
                ctx.shadowBlur = 30;
                ctx.globalAlpha = 0.34;

                ctx.stroke();

                ctx.shadowBlur = 8;
                ctx.lineWidth = 2;
                ctx.globalAlpha = 0.8;

                ctx.stroke();
            }

            ctx.globalAlpha = 1;
            ctx.globalCompositeOperation = "source-over";

            t += 0.006;

            if (!reduced) {
                requestAnimationFrame(draw);
            }
        };

        hero.addEventListener("pointermove", e => {
            const rect = hero.getBoundingClientRect();

            mx = (e.clientX - rect.left) / rect.width;
            my = (e.clientY - rect.top) / rect.height;
        });

        hero.addEventListener("click", () => {
            palette =
                palettes[
                    (palettes.indexOf(palette) + 1) %
                    palettes.length
                ];
        });

        window.addEventListener("resize", resize);

        resize();
        draw();
    }

    // ENGINE CANVAS ANIMATIONS

    document.querySelectorAll(".engine-canvas").forEach(canvas => {
        const c = canvas.getContext("2d");

        let time = 0;

        const kind = canvas.dataset.kind;

        const draw = () => {
            const rect = canvas.getBoundingClientRect();

            const d = Math.min(
                devicePixelRatio || 1,
                2
            );

            if (
                canvas.width !== Math.floor(rect.width * d) ||
                canvas.height !== Math.floor(rect.height * d)
            ) {
                canvas.width = Math.floor(rect.width * d);
                canvas.height = Math.floor(rect.height * d);
            }

            c.setTransform(d, 0, 0, d, 0, 0);

            const w = rect.width;
            const h = rect.height;

            c.clearRect(0, 0, w, h);

            c.lineWidth = 1.4;
            c.strokeStyle = "#818cf8";
            c.fillStyle = "#818cf8";

            if (kind === "wave") {
                c.beginPath();

                for (let x = 0; x < w; x += 2) {
                    const y =
                        h / 2 +
                        Math.sin(x * 0.055 + time) *
                        Math.sin(x * 0.012 - time * 0.4) *
                        h * 0.36;

                    x ? c.lineTo(x, y) : c.moveTo(x, y);
                }

                c.stroke();

            } else if (kind === "blocks") {
                for (let y = 0; y < 2; y++) {
                    for (let x = 0; x < 22; x++) {
                        c.globalAlpha =
                            0.12 +
                            0.75 *
                            (
                                0.5 +
                                0.5 *
                                Math.sin(time * 1.5 + x * 0.55 + y * 1.8)
                            );

                        c.fillRect(
                            x * w / 22 + 1,
                            y * 30 + 3,
                            w / 22 - 3,
                            22
                        );
                    }
                }

                c.globalAlpha = 1;

            } else if (kind === "stems") {
                for (let j = 0; j < 4; j++) {
                    c.globalAlpha = 0.25 + j * 0.2;

                    c.beginPath();

                    for (let x = 0; x < w; x += 3) {
                        const y =
                            10 +
                            j * 16 +
                            Math.sin(
                                x * 0.035 +
                                time * (0.6 + j * 0.2)
                            ) * 4;

                        x ? c.lineTo(x, y) : c.moveTo(x, y);
                    }

                    c.stroke();
                }

                c.globalAlpha = 1;

            } else {
                c.beginPath();
                c.arc(w / 2, h / 2, 24, 0, Math.PI * 2);

                c.strokeStyle = "#ffffff30";
                c.stroke();

                c.beginPath();

                c.arc(
                    w / 2,
                    h / 2,
                    24,
                    -Math.PI / 2,
                    time % 6.28 - Math.PI / 2
                );

                c.strokeStyle = "#818cf8";
                c.lineWidth = 3;
                c.stroke();

                c.beginPath();
                c.arc(w / 2, h / 2, 3, 0, Math.PI * 2);
                c.fill();
            }

            time += 0.025;

            if (!reduced) {
                requestAnimationFrame(draw);
            }
        };

        draw();
    });

    // SPECTRUM ANIMATION

    const spec = document.getElementById("spectrumCanvas");

    if (spec) {
        const c = spec.getContext("2d");

        let t = 0;

        const draw = () => {
            const rect = spec.getBoundingClientRect();

            const d = Math.min(
                devicePixelRatio || 1,
                2
            );

            if (
                spec.width !== Math.floor(rect.width * d) ||
                spec.height !== Math.floor(rect.height * d)
            ) {
                spec.width = Math.floor(rect.width * d);
                spec.height = Math.floor(rect.height * d);
            }

            c.setTransform(d, 0, 0, d, 0, 0);

            const w = rect.width;
            const h = rect.height;

            const n = 72;
            const gap = 3;
            const bw = (w - 36) / n;

            c.clearRect(0, 0, w, h);

            for (let i = 0; i < n; i++) {
                const env = Math.sin(
                    (i / (n - 1)) * Math.PI
                );

                let v =
                    env *
                    (
                        0.28 +
                        0.24 * Math.sin(i * 0.31 + t) +
                        0.15 * Math.sin(i * 0.13 - t * 0.7)
                    );

                if (i >= 12 && i <= 31) {
                    v = Math.max(0.62, v);
                }

                const bh = Math.max(
                    3,
                    v * (h - 55)
                );

                c.fillStyle =
                    i >= 12 && i <= 31
                        ? "#6366f1"
                        : "rgba(255,255,255,.17)";

                c.fillRect(
                    18 + i * (bw + gap),
                    h - 30 - bh,
                    bw,
                    bh
                );
            }

            const x = 18 + 12 * (bw + gap) - 4;
            const ww = 20 * (bw + gap) + 4;

            c.strokeStyle = "#818cf8";
            c.lineWidth = 1;

            c.strokeRect(
                x,
                h - 30 - (h - 55) * 0.7 - 5,
                ww,
                (h - 55) * 0.7 + 10
            );

            const read = document.getElementById(
                "spectrumReadout"
            );

            if (read) {
                read.textContent =
                    Math.round(360 + 90 * Math.sin(t * 0.4)) +
                    " HZ";
            }

            t += 0.035;

            if (!reduced) {
                requestAnimationFrame(draw);
            }
        };

        draw();
    }
})();

// ===============================
// ACCOUNT PROFILE SYSTEM
// ===============================

const profileModal = $("profileModal");

function setAvatar(url, name) {
    const img = $("sidebarAvatar");
    const initial = $("sidebarInitial");

    if (url) {
        img.src = url;
        img.hidden = false;
        initial.hidden = true;

    } else {
        img.hidden = true;
        initial.hidden = false;

        initial.textContent =
            (name || "BV")
                .trim()
                .split(/\s+/)
                .map(x => x[0])
                .join("")
                .slice(0, 2)
                .toUpperCase() || "BV";
    }
}

async function loadProfile() {
    const res = await fetch("/api/profile");

    const data = await res.json();

    if (!res.ok || !data.success) {
        throw Error(data.error || "Could not load account");
    }

    const profile = data.profile;

    $("profileName").value = profile.name || "";
    $("profileEmail").value = profile.email || "";

    $("sidebarUserName").textContent =
        profile.name || "User";

    setAvatar(
        profile.profile_picture_url,
        profile.name
    );

    if (profile.profile_picture_url) {
        $("profilePreview").src =
            profile.profile_picture_url;

        $("profilePreview").hidden = false;
        $("profileFallback").hidden = true;

    } else {
        $("profilePreview").hidden = true;
        $("profileFallback").hidden = false;

        $("profileFallback").textContent =
            (profile.name || "BV")
                .trim()
                .split(/\s+/)
                .map(x => x[0])
                .join("")
                .slice(0, 2)
                .toUpperCase() || "BV";
    }
}

// OPEN PROFILE SETTINGS

$("profileBtn").addEventListener("click", async () => {
    profileModal.hidden = false;

    $("profileMessage").textContent = "";

    try {
        await loadProfile();

    } catch (error) {
        toast(error.message);
    }
});

// CLOSE PROFILE SETTINGS

$("closeProfile").addEventListener("click", () => {
    profileModal.hidden = true;
});

profileModal.addEventListener("click", e => {
    if (e.target === profileModal) {
        profileModal.hidden = true;
    }
});

// PROFILE PHOTO PREVIEW

$("profilePictureInput").addEventListener("change", e => {
    const file = e.target.files[0];

    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
        toast("Photo must be 5 MB or smaller.");

        e.target.value = "";

        return;
    }

    const url = URL.createObjectURL(file);

    $("profilePreview").src = url;
    $("profilePreview").hidden = false;
    $("profileFallback").hidden = true;
});

// SAVE PROFILE

$("profileForm").addEventListener("submit", async e => {
    e.preventDefault();

    const btn = $("saveProfileBtn");

    const form = new FormData(e.currentTarget);

    btn.disabled = true;
    btn.textContent = "Saving...";

    $("profileMessage").textContent = "";

    try {
        const res = await fetch("/api/profile", {
            method: "POST",
            headers: {
                "X-CSRF-Token": window.BHARAT_CSRF
            },
            body: form
        });

        const data = await res.json();

        if (!res.ok || !data.success) {
            throw Error(
                data.error || "Profile update failed"
            );
        }

        $("profileMessage").textContent =
            "Profile updated successfully.";

        $("sidebarUserName").textContent =
            data.profile.name;

        setAvatar(
            data.profile.profile_picture_url,
            data.profile.name
        );

        toast("Profile updated");

        $("profilePictureInput").value = "";

    } catch (error) {
        $("profileMessage").textContent = error.message;

        $("profileMessage").style.color = "#ff9a9a";

    } finally {
        btn.disabled = false;
        btn.textContent = "Save changes →";
    }
});

// CLOSE PROFILE WITH ESCAPE

document.addEventListener("keydown", e => {
    if (e.key === "Escape" && profileModal) {
        profileModal.hidden = true;
    }
});
