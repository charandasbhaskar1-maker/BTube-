// BTube Firebase Cloud Engine & Global Channel Identity Manager
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
    // 1. Current Auth User
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

    // 2. Fetch User Channel Profile (Firestore synced)
    async getUserChannel() {
        const authUser = this.getAuthUser();
        if (!authUser) return null;

        // Pehle local cache check karo for high speed
        const cached = localStorage.getItem('btube_channel_profile_' + authUser.uid);
        if (cached) {
            const data = JSON.parse(cached);
            // Async background sync with Firestore
            if (db) {
                db.collection('users').doc(authUser.uid).get().then(doc => {
                    if (doc.exists) {
                        localStorage.setItem('btube_channel_profile_' + authUser.uid, JSON.stringify(doc.data()));
                    }
                }).catch(() => {});
            }
            return data;
        }

        // Firestore se fetch
        if (db) {
            try {
                const doc = await db.collection('users').doc(authUser.uid).get();
                if (doc.exists) {
                    const data = doc.data();
                    localStorage.setItem('btube_channel_profile_' + authUser.uid, JSON.stringify(data));
                    return data;
                }
            } catch(e) {
                console.warn("Channel fetch error:", e);
            }
        }
        return null; // Channel abhi bana nahi hai
    },

    // 3. Create or Update Channel Profile
    async saveUserChannel(channelData) {
        const authUser = this.getAuthUser();
        if (!authUser) throw new Error("Please sign in first");

        const payload = {
            uid: authUser.uid,
            name: channelData.name || authUser.name,
            handle: channelData.handle || ('@' + (channelData.name || authUser.name).toLowerCase().replace(/[^a-z0-9]/g, '')),
            avatar: channelData.avatar || authUser.photo || '',
            banner: channelData.banner || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200',
            bio: channelData.bio || 'Welcome to my official BTube channel!',
            subscribers: channelData.subscribers || 0,
            hasChannel: true,
            updatedAt: firebase.firestore.FieldValue.serverTimestamp()
        };

        if (db) {
            await db.collection('users').doc(authUser.uid).set(payload, { merge: true });
        }
        localStorage.setItem('btube_channel_profile_' + authUser.uid, JSON.stringify(payload));
        return payload;
    },

    // 4. Google One-Tap Sign In & Auto Check Channel
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
        if (u) localStorage.removeItem('btube_channel_profile_' + u.uid);
        localStorage.removeItem('btube_user');
        if (auth) await auth.signOut();
        window.location.reload();
    },

    // 5. Protected Upload: User ke actual channel name ke sath upload hota hai
    async saveVideo(videoData) {
        const authUser = this.getAuthUser();
        if (!authUser) throw new Error("Upload ke liye sign-in zaroori hai!");
        const ch = await this.getUserChannel();
        const chName = ch ? ch.name : authUser.name;
        const chAvatar = ch ? ch.avatar : authUser.photo;

        return await db.collection('videos').add({
            ...videoData,
            userId: authUser.uid,
            channel: chName,
            channelAvatar: chAvatar,
            createdAt: firebase.firestore.FieldValue.serverTimestamp()
        });
    },

    // 6. Global Feeds
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
