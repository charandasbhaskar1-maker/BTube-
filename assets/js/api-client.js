/**
 * BTube Central Cloud Engine, State Sync & Identity Manager
 */

const API_BASE_URL = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://127.0.0.1:8000"
    : "https://btube-api.onrender.com";

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

// Official Fallback Feed Items
const OFFICIAL_FEED_ITEMS = [
    {
        id: "vid_welcome_01",
        title: "Welcome to BTube - India's PWA Video Platform",
        channel: "BTube Official",
        avatar: "",
        thumb: "https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=800",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        duration: "03:45",
        views: 1200,
        type: "video"
    },
    {
        id: "short_welcome_01",
        title: "First Look at BTube Shorts #btube #shorts",
        channel: "BTube Official",
        avatar: "",
        thumb: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        duration: "00:45",
        views: 3500,
        type: "short"
    }
];

window.BTubeAPI = {
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
        if (!u) {
            const localSaved = localStorage.getItem('btube_active_channel');
            return localSaved ? JSON.parse(localSaved) : null;
        }

        const channels = await this.getAllUserChannels();
        const activeId = localStorage.getItem('btube_active_channel_id_' + u.uid);
        const match = channels.find(c => c.id === activeId);
        return match || channels[0];
    },

    setActiveChannel(channelId) {
        const u = this.getAuthUser();
        if (u) {
            localStorage.setItem('btube_active_channel_id_' + u.uid, channelId);
        }
        this.getAllUserChannels().then(list => {
            const ch = list.find(c => c.id === channelId);
            if (ch) {
                localStorage.setItem('btube_active_channel', JSON.stringify(ch));
                window.BTubeState.syncUI();
            }
        });
    },

    async getFeed(type = 'all') {
        let items = [];
        try {
            const apiRes = await fetch(`${API_BASE_URL}/api/videos/feed`);
            if (apiRes.ok) {
                const apiVideos = await apiRes.json();
                if (apiVideos && apiVideos.length > 0) items = apiVideos;
            }
        } catch(e) {}

        if (items.length === 0 && db) {
            try {
                const pFetch = db.collection('videos').get();
                const pTimeout = new Promise((_, rej) => setTimeout(() => rej('timeout'), 1800));
                const snap = await Promise.race([pFetch, pTimeout]);
                snap.forEach(doc => items.push({ id: doc.id, ...doc.data() }));
            } catch(e) {}
        }

        if (items.length === 0) {
            items = [...OFFICIAL_FEED_ITEMS];
        }

        if (type === 'all') return items;
        return items.filter(i => (i.type || (i.is_shorts ? 'short' : 'video')).toLowerCase() === type.toLowerCase());
    }
};

// Global Channel Identity Bridge (Sabhi Pages ke liye)
window.BTubeState = {
    getActiveChannel() {
        const local = localStorage.getItem('btube_active_channel');
        if (local) {
            try { return JSON.parse(local); } catch(e){}
        }

        const u = window.BTubeAPI.getAuthUser();
        if (u) {
            try {
                const activeId = localStorage.getItem('btube_active_channel_id_' + u.uid);
                const list = JSON.parse(localStorage.getItem('btube_channels_' + u.uid) || '[]');
                const match = list.find(c => c.id === activeId) || list[0];
                if (match) return match;
            } catch(e){}
            return {
                id: 'ch_' + u.uid,
                name: u.name,
                handle: '@' + u.name.toLowerCase().replace(/[^a-z0-9]/g, ''),
                avatar: u.photo || '',
                subscribers: 0
            };
        }

        return {
            id: 'ch_default',
            name: 'Karan Bhaskar',
            handle: '@karanbhaskar',
            avatar: '',
            subscribers: 0
        };
    },

    syncUI() {
        const ch = this.getActiveChannel();
        const displayName = ch ? (ch.name || 'BT') : 'BT';
        const initial = displayName.substring(0, 2).toUpperCase();
        const avatarUrl = ch ? (ch.avatar || '') : '';

        const topAv = document.getElementById('topNavAvatar');
        const botAv = document.getElementById('bottomNavAvatar');

        if (avatarUrl) {
            const imgTag = `<img src="${avatarUrl}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`;
            if (topAv) topAv.innerHTML = imgTag;
            if (botAv) botAv.innerHTML = imgTag;
        } else {
            if (topAv) topAv.innerText = initial;
            if (botAv) botAv.innerText = initial;
        }
    }
};

window.addEventListener('DOMContentLoaded', () => {
    if (window.BTubeState) {
        window.BTubeState.syncUI();
    }
});
