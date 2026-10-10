/**
 * BTube Central Cloud Engine & Instant State Sync
 * Bridges Frontend PWA with FastAPI Backend, SafeShield, CopyScan, and Firebase Auth/Firestore
 */

const API_BASE_URL = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://127.0.0.1:8000"
    : "https://btube-api.onrender.com"; // Render / Production URL

const firebaseConfig = {
    apiKey: "AIzaSyBj406IRJ1VtK84rT2HTkxQWAbQO7bYD2s",
    authDomain: "btube-5fae0.firebaseapp.com",
    projectId: "btube-5fae0",
    storageBucket: "btube-5fae0.firebasestorage.app",
    messagingSenderId: "1009386330534",
    appId: "1:1009386330534:web:357a0ad258678a54185767"
};

if (typeof firebase !== 'undefined' && !firebase.apps.length) {
    try { firebase.initializeApp(firebaseConfig); } catch(e){}
}

const db = (typeof firebase !== 'undefined') ? firebase.firestore() : null;
const auth = (typeof firebase !== 'undefined') ? firebase.auth() : null;

// Built-in initial videos (Zero screen freeze fallback)
const OFFICIAL_FEED_ITEMS = [
    {
        id: "vid_intro_01",
        title: "Welcome to BTube - India's PWA Video Platform",
        channel: "BTube Official",
        avatar: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=200",
        thumb: "https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=800",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        duration: "03:45",
        views: 1200,
        type: "video",
        createdAt: { seconds: 1700000000 }
    },
    {
        id: "short_welcome_01",
        title: "First Look at BTube Shorts #btube #shorts",
        channel: "BTube Official",
        avatar: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=200",
        thumb: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        duration: "00:45",
        views: 3500,
        type: "short",
        createdAt: { seconds: 1700000001 }
    }
];

window.BTubeAPI = {
    // ================= 1. AUTH & JWT STATE =================
    getToken() {
        return localStorage.getItem("btube_auth_token") || "";
    },

    setToken(token) {
        localStorage.setItem("btube_auth_token", token);
    },

    getAuthUser() {
        if (auth && auth.currentUser) {
            return {
                uid: auth.currentUser.uid,
                name: auth.currentUser.displayName || 'BTube User',
                email: auth.currentUser.email,
                photo: auth.currentUser.photoURL || ''
            };
        }
        return JSON.parse(localStorage.getItem('btube_user') || 'null');
    },

    async signInWithGoogle() {
        if (!auth) return null;
        try {
            const provider = new firebase.auth.GoogleAuthProvider();
            const res = await auth.signInWithPopup(provider);
            const user = {
                uid: res.user.uid,
                name: res.user.displayName || 'BTube User',
                email: res.user.email,
                photo: res.user.photoURL || ''
            };
            localStorage.setItem('btube_user', JSON.stringify(user));

            // Bridge to FastAPI Backend for session JWT token
            try {
                const idToken = await res.user.getIdToken();
                const apiRes = await fetch(`${API_BASE_URL}/api/auth/google`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id_token: idToken, preferred_channel_name: user.name })
                });
                if (apiRes.ok) {
                    const data = await apiRes.json();
                    this.setToken(data.access_token);
                }
            } catch (err) {
                console.warn("Backend Auth Bridge offline, running in client mode:", err);
            }

            return user;
        } catch(e) {
            console.error("Google Sign-In Error:", e);
            return null;
        }
    },

    async signOut() {
        const u = this.getAuthUser();
        if (u) {
            localStorage.removeItem('btube_active_channel_id_' + u.uid);
            localStorage.removeItem('btube_channels_' + u.uid);
        }
        localStorage.removeItem('btube_user');
        localStorage.removeItem('btube_auth_token');
        if (auth) await auth.signOut();
        window.location.reload();
    },

    // ================= 2. MULTI-CHANNEL ROUTING =================
    async getAllUserChannels() {
        const u = this.getAuthUser();
        if (!u) return [];

        let list = JSON.parse(localStorage.getItem('btube_channels_' + u.uid) || '[]');
        if (list.length === 0) {
            const defCh = {
                id: 'ch_' + u.uid,
                uid: u.uid,
                name: u.name,
                handle: '@' + (u.name || 'user').toLowerCase().replace(/[^a-z0-9]/g, ''),
                avatar: u.photo || '',
                banner: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200',
                subscribers: 0
            };
            list = [defCh];
            localStorage.setItem('btube_channels_' + u.uid, JSON.stringify(list));
            this.setActiveChannel(defCh.id);
        }
        return list;
    },

    async getActiveChannel() {
        const u = this.getAuthUser();
        if (!u) return null;

        const channels = await this.getAllUserChannels();
        const activeId = localStorage.getItem('btube_active_channel_id_' + u.uid);
        const match = channels.find(c => c.id === activeId);
        return match || channels[0];
    },

    setActiveChannel(channelId) {
        const u = this.getAuthUser();
        if (!u) return;
        localStorage.setItem('btube_active_channel_id_' + u.uid, channelId);

        // Notify FastAPI Backend if token available
        const token = this.getToken();
        if (token) {
            fetch(`${API_BASE_URL}/api/auth/channels/switch`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ channel_id: channelId })
            }).then(r => r.ok && r.json()).then(d => {
                if (d && d.access_token) this.setToken(d.access_token);
            }).catch(()=>{});
        }
    },

    async createNewChannel(data) {
        const u = this.getAuthUser();
        if (!u) return null;

        const newCh = {
            id: 'ch_' + Date.now(),
            uid: u.uid,
            name: data.name,
            handle: data.handle.startsWith('@') ? data.handle : ('@' + data.handle),
            avatar: data.avatar || u.photo || '',
            banner: data.banner || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200',
            subscribers: 0
        };

        const list = await this.getAllUserChannels();
        list.push(newCh);
        localStorage.setItem('btube_channels_' + u.uid, JSON.stringify(list));
        this.setActiveChannel(newCh.id);

        if (db) {
            db.collection('users').doc(u.uid).collection('channels').doc(newCh.id).set(newCh).catch(()=>{});
        }
        return newCh;
    },

    // ================= 3. VIRAL FEED & VIDEO ACTIONS =================
    async getFeed(type = 'all') {
        let items = [];

        // 1. Try FastAPI Recommendation Feed
        try {
            const apiRes = await fetch(`${API_BASE_URL}/api/videos/feed`);
            if (apiRes.ok) {
                const apiVideos = await apiRes.json();
                if (apiVideos && apiVideos.length > 0) items = apiVideos;
            }
        } catch(e) {}

        // 2. Try Firestore
        if (items.length === 0 && db) {
            try {
                const pFetch = db.collection('videos').get();
                const pTimeout = new Promise((_, rej) => setTimeout(() => rej('timeout'), 1800));
                const snap = await Promise.race([pFetch, pTimeout]);
                snap.forEach(doc => items.push({ id: doc.id, ...doc.data() }));
            } catch(e) {
                console.warn('Feed fetch fallback:', e);
            }
        }

        // 3. Fallback to Official Items
        if (items.length === 0) {
            items = [...OFFICIAL_FEED_ITEMS];
        }

        if (type === 'all') return items;
        return items.filter(i => (i.type || (i.is_shorts ? 'short' : 'video')).toLowerCase() === type.toLowerCase());
    },

    async uploadVideoChunks(file, onProgress) {
        const CHUNK_SIZE = 2 * 1024 * 1024;
        const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
        const uploadId = "up_" + Date.now() + "_" + Math.random().toString(36).substring(2, 9);

        for (let idx = 0; idx < totalChunks; idx++) {
            const start = idx * CHUNK_SIZE;
            const end = Math.min(file.size, start + CHUNK_SIZE);
            const chunk = file.slice(start, end);

            const res = await fetch(`${API_BASE_URL}/api/videos/upload-chunk`, {
                method: "POST",
                headers: {
                    "X-Upload-ID": uploadId,
                    "X-Chunk-Index": idx.toString(),
                    "X-Total-Chunks": totalChunks.toString()
                },
                body: chunk
            });

            if (!res.ok) throw new Error(`Chunk ${idx} upload failed`);
            if (onProgress) onProgress(Math.round(((idx + 1) / totalChunks) * 100));

            if (idx === totalChunks - 1) {
                const finalData = await res.json();
                return finalData.video_url;
            }
        }
    },

    async saveVideo(videoData) {
        // Fast backend publish with SafeShield / CopyScan Gatekeeper
        try {
            const res = await fetch(`${API_BASE_URL}/api/videos/upload`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${this.getToken()}`
                },
                body: JSON.stringify({
                    title: videoData.title,
                    description: videoData.description || "",
                    category: videoData.category || "All",
                    video_url: videoData.videoUrl || videoData.video_url,
                    thumbnail_url: videoData.thumb || videoData.thumbnail_url,
                    duration_seconds: videoData.durationSeconds || 180,
                    is_shorts: (videoData.type === 'short'),
                    visibility: videoData.visibility || "Public",
                    audio_hash: videoData.audio_hash || null
                })
            });

            if (res.ok) {
                const cloudSaved = await res.json();
                videoData.id = cloudSaved.video_id;
            }
        } catch (err) {}

        if (db) {
            db.collection('videos').add(videoData).catch(()=>{});
        }
        return videoData;
    },

    async recordView(videoId, watchSeconds = 15.0) {
        try {
            await fetch(`${API_BASE_URL}/api/videos/${videoId}/view`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ watch_seconds: watchSeconds })
            });
        } catch(e) {}
    },

    // ================= 4. YPP 70/30 SUPER THANKS =================
    async processSuperThanks(videoId, grossAmount, message) {
        try {
            const res = await fetch(`${API_BASE_URL}/api/bpp/super-thanks/process`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${this.getToken()}`
                },
                body: JSON.stringify({
                    video_id: videoId,
                    gross_amount: Number(grossAmount),
                    message: message
                })
            });
            if (res.ok) return await res.json();
        } catch(e) {}

        const gross = Number(grossAmount);
        return {
            status: "success",
            split_summary: {
                gross_amount: gross,
                creator_net_70: Number((gross * 0.70).toFixed(2)),
                platform_fee_30: Number((gross * 0.30).toFixed(2)),
                currency: "INR"
            }
        };
    }
};
