// BTube Central Cloud Engine & Instant State Sync
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

// Built-in initial videos (Zero screen freeze)
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

    async getFeed(type = 'all') {
        let items = [];
        
        // Fast Firestore Fetch with 1.8s Timeout Fallback
        if (db) {
            try {
                const pFetch = db.collection('videos').get();
                const pTimeout = new Promise((_, rej) => setTimeout(() => rej('timeout'), 1800));
                const snap = await Promise.race([pFetch, pTimeout]);
                snap.forEach(doc => items.push({ id: doc.id, ...doc.data() }));
            } catch(e) {
                console.warn('Feed fetch fallback:', e);
            }
        }

        if (items.length === 0) {
            items = [...OFFICIAL_FEED_ITEMS];
        }

        if (type === 'all') return items;
        return items.filter(i => (i.type || 'video').toLowerCase() === type.toLowerCase());
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
            return user;
        } catch(e) {
            console.error(e);
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
        if (auth) await auth.signOut();
        window.location.reload();
    }
};
