/**
 * BTube API client. Real backend data only; no sample/demo videos.
 */
const API_BASE_URL = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://127.0.0.1:8000"
    : "https://btube-api.onrender.com";

const firebaseConfig = {
    apiKey: "AIzaSyBj406IRJ1VtK84rT2HTkxQWAbOQ7bYD2s",
    authDomain: "btube-5fae0.firebaseapp.com",
    projectId: "btube-5fae0",
    storageBucket: "btube-5fae0.firebasestorage.app",
    messagingSenderId: "1009386330534",
    appId: "1:1009386330534:web:357a0ad258678a54185767"
};

if (typeof firebase !== "undefined" && !firebase.apps.length) {
    try { firebase.initializeApp(firebaseConfig); } catch (e) { console.error("Firebase initialization failed", e); }
}
const db = (typeof firebase !== "undefined" && firebase.firestore) ? firebase.firestore() : null;
const auth = (typeof firebase !== "undefined" && firebase.auth) ? firebase.auth() : null;

function btubeToken() {
    return localStorage.getItem("btube_access_token") || "";
}
function authHeaders(extra = {}) {
    const token = btubeToken();
    return { ...extra, ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}
async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers: authHeaders({ ...(options.headers || {}) })
    });
    let data = null;
    try { data = await response.json(); } catch (_) {}
    if (!response.ok) {
        const message = data && (data.detail || data.message) ? (data.detail || data.message) : `Request failed (${response.status})`;
        throw new Error(message);
    }
    return data;
}
function absoluteMediaUrl(url) {
    if (!url) return "";
    if (/^(blob:|data:)/i.test(url)) return "";
    if (/^https?:\/\//i.test(url)) return url;
    return `${API_BASE_URL}${url.startsWith("/") ? "" : "/"}${url}`;
}
function normalizeVideo(v = {}) {
    const id = v.id || v.video_id || v.videoId || "";
    const isShort = v.is_shorts === true || v.isShorts === true || String(v.type || "").toLowerCase() === "short";
    let url = v.videoUrl || v.video_url || v.stream_url || "";
    if (url.startsWith("/api/videos/")) url = `${API_BASE_URL}${url}`;
    else if (url.startsWith("/uploads/") && id) url = `${API_BASE_URL}/api/videos/${encodeURIComponent(id)}/stream`;
    else if (url.startsWith("/uploads/")) url = absoluteMediaUrl(url);
    return {
        ...v,
        id,
        title: v.title || v.name || "Untitled",
        description: v.description || "",
        type: isShort ? "short" : "video",
        is_shorts: isShort,
        videoUrl: url,
        thumb: v.thumb || v.thumbnail_url || v.thumbnailUrl || "",
        thumbnail_url: v.thumbnail_url || v.thumb || "",
        channel: v.channel || v.channel_name || v.channelName || "BTube Creator",
        channelAvatar: v.channelAvatar || v.channel_avatar || v.avatar_url || v.avatar || "",
        channelId: v.channelId || v.channel_id || "",
        views: Number(v.views ?? v.views_count ?? 0),
        likes: Number(v.likes ?? v.likes_count ?? 0),
        duration: v.duration || (v.duration_seconds ? String(v.duration_seconds) : "")
    };
}

window.BTubeAPI = {
    getAuthUser() {
        if (auth && auth.currentUser) {
            return {
                uid: auth.currentUser.uid,
                id: localStorage.getItem("btube_user_id") || auth.currentUser.uid,
                name: auth.currentUser.displayName || "BTube User",
                email: auth.currentUser.email || "",
                photo: auth.currentUser.photoURL || ""
            };
        }
        try { return JSON.parse(localStorage.getItem("btube_user") || "null"); }
        catch (_) { return null; }
    },

    async signInWithGoogle() {
        if (!auth) throw new Error("Firebase Auth is not available on this page.");
        const provider = new firebase.auth.GoogleAuthProvider();
        const result = await auth.signInWithPopup(provider);
        const credential = firebase.auth.GoogleAuthProvider.credentialFromResult(result);
        const googleIdToken = credential && credential.idToken;
        if (!googleIdToken) throw new Error("Google sign-in did not return an ID token.");
        const data = await fetch(`${API_BASE_URL}/api/auth/google`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id_token: googleIdToken, preferred_channel_name: result.user.displayName || "BTube Creator" })
        }).then(async r => {
            const body = await r.json().catch(() => ({}));
            if (!r.ok) throw new Error(body.detail || `Sign-in failed (${r.status})`);
            return body;
        });
        localStorage.setItem("btube_access_token", data.access_token);
        localStorage.setItem("btube_user_id", data.user?.id || data.user_id || "");
        const user = data.user || {
            id: data.user_id,
            uid: result.user.uid,
            email: result.user.email,
            name: data.active_channel?.name || result.user.displayName || "BTube User",
            photo: result.user.photoURL || ""
        };
        localStorage.setItem("btube_user", JSON.stringify({
            uid: user.uid || result.user.uid,
            id: user.id || data.user_id,
            email: user.email || result.user.email,
            name: user.name || result.user.displayName || "BTube User",
            photo: user.photo || result.user.photoURL || ""
        }));
        if (data.active_channel) {
            const ch = {
                id: data.active_channel.id,
                uid: user.uid || result.user.uid,
                name: data.active_channel.name,
                handle: data.active_channel.handle,
                avatar: user.photo || result.user.photoURL || "",
                subscribers: 0
            };
            localStorage.setItem("btube_active_channel", JSON.stringify(ch));
            localStorage.setItem("btube_active_channel_id_" + (user.uid || result.user.uid), ch.id);
        }
        if (window.BTubeState) window.BTubeState.syncUI();
        return this.getAuthUser();
    },

    async signOut() {
        if (auth) {
            try { await auth.signOut(); } catch (_) {}
        }
        ["btube_access_token", "btube_user_id", "btube_user", "btube_active_channel"].forEach(k => localStorage.removeItem(k));
        if (window.BTubeState) window.BTubeState.syncUI();
    },

    async getAllUserChannels() {
        if (!btubeToken()) return [];
        try { return await apiRequest("/api/auth/channels/me"); }
        catch (_) { return []; }
    },

    async getActiveChannel() {
        try {
            const local = JSON.parse(localStorage.getItem("btube_active_channel") || "null");
            if (local) return local;
        } catch (_) {}
        const user = this.getAuthUser();
        if (!user) return null;
        const channels = await this.getAllUserChannels();
        if (channels.length) {
            const activeId = localStorage.getItem("btube_active_channel_id_" + (user.uid || user.id));
            const active = channels.find(c => c.id === activeId) || channels.find(c => c.is_active) || channels[0];
            const channel = { ...active, uid: user.uid || user.id, avatar: active.avatar || active.avatar_url || "" };
            localStorage.setItem("btube_active_channel", JSON.stringify(channel));
            return channel;
        }
        return null;
    },

    async setActiveChannel(channelId) {
        if (btubeToken()) {
            try {
                const data = await apiRequest("/api/auth/channels/switch", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ channel_id: channelId })
                });
                if (data.access_token) localStorage.setItem("btube_access_token", data.access_token);
                if (data.active_channel) {
                    const user = this.getAuthUser() || {};
                    const ch = { ...data.active_channel, uid: user.uid || user.id, avatar: user.photo || "" };
                    localStorage.setItem("btube_active_channel", JSON.stringify(ch));
                }
            } catch (e) {
                console.error("Channel switch failed:", e);
                throw e;
            }
        }
        localStorage.setItem("btube_active_channel_id_" + ((this.getAuthUser() || {}).uid || (this.getAuthUser() || {}).id || "guest"), channelId);
        if (window.BTubeState) window.BTubeState.syncUI();
    },

    async createNewChannel(name, handle, avatarUrl = "") {
        const data = await apiRequest("/api/auth/channels/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ channel_name: name, channel_handle: handle, avatar_url: avatarUrl || null })
        });
        return data;
    },

    async getFeed(type = "all") {
        let apiItems = [];
        try {
            const category = type === "all" ? "" : `?category=${encodeURIComponent(type)}`;
            const result = await apiRequest(`/api/videos/feed${category}`);
            if (Array.isArray(result)) apiItems = result;
        } catch (e) {
            console.error("BTube backend feed unavailable:", e.message);
        }

        // Firestore is a secondary source for already-persisted records only. Demo videos are never inserted.
        if (!apiItems.length && db) {
            try {
                const snap = await db.collection("videos").get();
                snap.forEach(doc => apiItems.push({ id: doc.id, ...doc.data() }));
            } catch (e) {
                console.warn("Firestore feed unavailable:", e.message || e);
            }
        }
        let items = apiItems.map(normalizeVideo).filter(v => v.id && v.videoUrl);
        if (type === "short") items = items.filter(v => v.is_shorts || v.type === "short");
        if (type === "video") items = items.filter(v => !v.is_shorts && v.type !== "short");
        return items;
    },

    async getMyVideos() {
        const result = await apiRequest("/api/videos/mine");
        return Array.isArray(result) ? result.map(normalizeVideo) : [];
    },

    async getVideoById(id) {
        if (!id) return null;
        try {
            return normalizeVideo(await apiRequest(`/api/videos/${encodeURIComponent(id)}`));
        } catch (e) {
            if (db) {
                try {
                    const doc = await db.collection("videos").doc(id).get();
                    if (doc.exists) return normalizeVideo({ id: doc.id, ...doc.data() });
                } catch (_) {}
            }
            throw e;
        }
    },

    async saveVideo(payload, file) {
        if (!btubeToken()) throw new Error("Upload करने के लिए पहले BTube में Google से sign in करें.");
        if (!(file instanceof Blob) || !file.size) throw new Error("कृपया असली video file चुनें; अस्थायी preview URL अपलोड नहीं हो सकता.");
        const uploadId = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : `up_${Date.now()}_${Math.random().toString(16).slice(2)}`;
        const chunkSize = 1024 * 1024;
        const totalChunks = Math.ceil(file.size / chunkSize);
        let completed = null;

        for (let index = 0; index < totalChunks; index++) {
            const chunk = file.slice(index * chunkSize, Math.min(file.size, (index + 1) * chunkSize));
            completed = await apiRequest("/api/videos/upload-chunk", {
                method: "POST",
                headers: {
                    "Content-Type": "application/octet-stream",
                    "X-Upload-ID": uploadId,
                    "X-Chunk-Index": String(index),
                    "X-Total-Chunks": String(totalChunks),
                    "X-File-Name": file.name
                },
                body: chunk
            });
            if (index < totalChunks - 1 && completed.status !== "chunk_received") {
                throw new Error("Upload chunk sequence was not accepted.");
            }
        }
        if (!completed || completed.status !== "completed" || !completed.video_url) {
            throw new Error("The server did not finish assembling the uploaded video.");
        }

        const seconds = Number(payload.duration_seconds) ||
            (typeof payload.duration === "number" ? payload.duration : (() => {
                const parts = String(payload.duration || "").split(":").map(Number);
                return parts.length === 2 ? parts[0] * 60 + parts[1] : 60;
            })());
        const thumb = /^https?:\/\//i.test(payload.thumb || payload.thumbnail_url || "")
            ? (payload.thumb || payload.thumbnail_url) : null;
        const body = {
            title: String(payload.title || payload.name || "Untitled").slice(0, 120),
            description: String(payload.description || ""),
            category: payload.category || "All",
            video_url: completed.video_url,
            thumbnail_url: thumb,
            duration_seconds: Math.max(1, Math.floor(seconds || 60)),
            is_shorts: payload.is_shorts === true || payload.type === "short",
            visibility: payload.visibility || "Public"
        };
        const created = await apiRequest("/api/videos/upload", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        return normalizeVideo({
            ...created,
            ...body,
            videoUrl: `${API_BASE_URL}/api/videos/${encodeURIComponent(created.video_id)}/stream`,
            channel: payload.channel || (await this.getActiveChannel())?.name || "BTube Creator",
            channelAvatar: payload.channelAvatar || "",
            thumb: thumb || "",
            views: 0
        });
    },

    async recordView(id) {
        const player = document.querySelector("video");
        if (!id || !player || player.dataset.btubeViewTracking === "1") return;
        player.dataset.btubeViewTracking = "1";
        let sent = false;
        const send = () => {
            if (sent) return;
            const watched = Math.max(0, Number(player.currentTime) || 0);
            if (watched < 1) return;
            sent = true;
            fetch(`${API_BASE_URL}/api/videos/${encodeURIComponent(id)}/view`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ watch_seconds: watched }),
                keepalive: true
            }).catch(() => {});
        };
        player.addEventListener("ended", send, { once: true });
        window.addEventListener("pagehide", send, { once: true });
    },

    async updateVideo(id, updates) {
        const body = { ...updates };
        if (body.thumb !== undefined && body.thumbnail_url === undefined) body.thumbnail_url = body.thumb;
        delete body.thumb;
        return normalizeVideo(await apiRequest(`/api/videos/${encodeURIComponent(id)}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        }));
    },

    async deleteVideo(id) {
        return apiRequest(`/api/videos/${encodeURIComponent(id)}`, { method: "DELETE" });
    }
};

window.BTubeState = {
    getActiveChannel() {
        try {
            const local = localStorage.getItem("btube_active_channel");
            if (local) return JSON.parse(local);
        } catch (_) {}
        const u = window.BTubeAPI.getAuthUser();
        if (!u) return null;
        return {
            id: "ch_" + (u.id || u.uid),
            uid: u.uid || u.id,
            name: u.name || "BTube Creator",
            handle: "@" + String(u.name || "user").toLowerCase().replace(/[^a-z0-9_]/g, "").slice(0, 24),
            avatar: u.photo || "",
            subscribers: 0
        };
    },
    syncUI() {
        const ch = this.getActiveChannel();
        const u = window.BTubeAPI.getAuthUser();
        const displayName = (ch && ch.name) || (u && u.name) || "BT";
        const initial = displayName.substring(0, 2).toUpperCase();
        const avatarUrl = (ch && (ch.avatar || ch.avatar_url)) || (u && u.photo) || "";
        const topAv = document.getElementById("topNavAvatar");
        const botAv = document.getElementById("bottomNavAvatar");
        const setAvatar = (node) => {
            if (!node) return;
            node.replaceChildren();
            if (avatarUrl) {
                const img = document.createElement("img");
                img.src = avatarUrl;
                img.alt = "Profile";
                img.referrerPolicy = "no-referrer";
                node.appendChild(img);
            } else {
                node.textContent = initial;
            }
        };
        setAvatar(topAv);
        setAvatar(botAv);
    }
};
window.addEventListener("DOMContentLoaded", () => window.BTubeState.syncUI());
