// BTube Firebase Cloud Engine & YouTube Multi-Channel Manager
const firebaseConfig = {
  apiKey: "AIzaSyBj406IRJ1VtK84rT2HTkxQWAbQO7bYD2s",
  authDomain: "btube-5fae0.firebaseapp.com",
  projectId: "btube-5fae0",
  storageBucket: "btube-5fae0.firebasestorage.app",
  messagingSenderId: "1009386330534",
  appId: "1:1009386330534:web:357a0ad258678a54185767"
};

if (typeof firebase !== 'undefined' && !firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}

const db = (typeof firebase !== 'undefined') ? firebase.firestore() : null;
const auth = (typeof firebase !== 'undefined') ? firebase.auth() : null;

window.BTubeAPI = {
    // 1. Current Authenticated Google Account
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

    // 2. Multi-Channel: User ke saare channels list karna
    async getAllUserChannels() {
        const u = this.getAuthUser();
        if (!u) return [];

        let list = JSON.parse(localStorage.getItem('btube_channels_' + u.uid) || '[]');
        if (list.length === 0 && db) {
            try {
                const snap = await db.collection('users').doc(u.uid).collection('channels').get();
                snap.forEach(doc => list.push({ id: doc.id, ...doc.data() }));
                if (list.length > 0) {
                    localStorage.setItem('btube_channels_' + u.uid, JSON.stringify(list));
                }
            } catch(e) {}
        }
        return list;
    },

    // 3. Current Selected Active Channel
    async getActiveChannel() {
        const u = this.getAuthUser();
        if (!u) return null;

        const activeId = localStorage.getItem('btube_active_channel_id_' + u.uid);
        const channels = await this.getAllUserChannels();

        if (channels.length > 0) {
            const found = channels.find(c => c.id === activeId);
            return found || channels[0];
        }
        return null;
    },

    // 4. Switch Active Channel (Instant)
    setActiveChannel(channelId) {
        const u = this.getAuthUser();
        if (!u) return;
        localStorage.setItem('btube_active_channel_id_' + u.uid, channelId);
    },

    // 5. Create a New Channel under this Google Account
    async createNewChannel(data) {
        const u = this.getAuthUser();
        if (!u) throw new Error("Please sign in first");

        const channelObj = {
            id: 'ch_' + Date.now(),
            uid: u.uid,
            name: data.name,
            handle: data.handle.startsWith('@') ? data.handle : ('@' + data.handle),
            avatar: data.avatar || u.photo || '',
            banner: data.banner || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200',
            subscribers: 0,
            createdAt: new Date().toISOString()
        };

        // Local cache
        let list = await this.getAllUserChannels();
        list.push(channelObj);
        localStorage.setItem('btube_channels_' + u.uid, JSON.stringify(list));
        this.setActiveChannel(channelObj.id);

        // Firestore sync
        if (db) {
            db.collection('users').doc(u.uid).collection('channels').doc(channelObj.id).set(channelObj).catch(() => {});
        }

        return channelObj;
    },

    // 6. Sign In / Sign Out
    async signInWithGoogle() {
        if (!auth) return null;
        const provider = new firebase.auth.GoogleAuthProvider();
        try {
            const res = await auth.signInWithPopup(provider);
            const user = {
                uid: res.user.uid,
                name: res.user.displayName || 'BTube User',
                email: res.user.email,
                photo: res.user.photoURL || ''
            };
            localStorage.setItem('btube_user', JSON.stringify(user));
            return user;
        } catch(err) {
            console.error('Sign-in error:', err);
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
    },

    // 7. Video Upload (Active Channel se bind hota hai)
    async saveVideo(videoData) {
        const u = this.getAuthUser();
        if (!u) throw new Error("Please sign in first");
        const activeCh = await this.getActiveChannel();

        return await db.collection('videos').add({
            ...videoData,
            userId: u.uid,
            channelId: activeCh ? activeCh.id : 'default',
            channel: activeCh ? activeCh.name : u.name,
            channelAvatar: activeCh ? activeCh.avatar : u.photo,
            createdAt: firebase.firestore.FieldValue.serverTimestamp()
        });
    },

    async getFeed(type = 'all') {
        let items = [];
        if (db) {
            try {
                const fetchPromise = db.collection('videos').get();
                const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject('timeout'), 2500));
                const snap = await Promise.race([fetchPromise, timeoutPromise]);
                snap.forEach(doc => items.push({ id: doc.id, ...doc.data() }));
            } catch(e) {}
        }
        items.sort((a, b) => (b.createdAt?.seconds || 0) - (a.createdAt?.seconds || 0));
        if (type === 'all') return items;
        return items.filter(item => (item.type || 'video').toLowerCase() === type.toLowerCase());
    },

    async getVideoById(docId) {
        if (db && docId) {
            try {
                const doc = await db.collection('videos').doc(docId).get();
                if (doc.exists) return { id: doc.id, ...doc.data() };
            } catch(e) {}
        }
        return null;
    },

    async recordView(docId) {
        if (!db || !docId) return;
        try {
            await db.collection('videos').doc(docId).update({
                views: firebase.firestore.FieldValue.increment(1)
            });
        } catch(e) {}
    }
};
