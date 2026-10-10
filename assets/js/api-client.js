// BTube Firebase Cloud Engine & Auth Manager
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

// Official Default Videos (Never hangs on loading screen)
const DEFAULT_OFFICIAL_VIDEOS = [
    {
        id: "btube_official_01",
        title: "BTube Official Platform Introduction",
        name: "BTube Official Platform Introduction",
        channel: "BTube Official",
        duration: "03:45",
        views: 120,
        type: "video",
        visibility: "Public",
        thumb: "https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=800",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
    },
    {
        id: "btube_short_01",
        title: "Welcome to BTube Shorts #shorts",
        name: "Welcome to BTube Shorts #shorts",
        channel: "BTube Official",
        duration: "00:45",
        views: 350,
        type: "short",
        visibility: "Public",
        thumb: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
    }
];

window.BTubeAPI = {
    getUser() {
        if (auth && auth.currentUser) {
            return {
                uid: auth.currentUser.uid,
                name: auth.currentUser.displayName || 'BTube User',
                displayName: auth.currentUser.displayName || 'BTube User',
                email: auth.currentUser.email,
                photo: auth.currentUser.photoURL || ''
            };
        }
        return JSON.parse(localStorage.getItem('btube_user') || 'null');
    },

    async signInWithGoogle() {
        if (!auth) return null;
        const provider = new firebase.auth.GoogleAuthProvider();
        try {
            const res = await auth.signInWithPopup(provider);
            const user = {
                uid: res.user.uid,
                name: res.user.displayName || 'BTube User',
                displayName: res.user.displayName || 'BTube User',
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
        if (auth) await auth.signOut();
        localStorage.removeItem('btube_user');
        window.location.reload();
    },

    async getFeed(type = 'all') {
        let items = [];
        if (db) {
            try {
                // Timeout promise so UI never freezes on loading
                const fetchPromise = db.collection('videos').get();
                const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject('timeout'), 2500));
                
                const snap = await Promise.race([fetchPromise, timeoutPromise]);
                snap.forEach(doc => items.push({ id: doc.id, ...doc.data() }));
            } catch(e) {
                console.warn('Firestore fetch fallback:', e);
            }
        }

        if (items.length === 0) {
            items = [...DEFAULT_OFFICIAL_VIDEOS];
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
        return DEFAULT_OFFICIAL_VIDEOS.find(v => v.id === docId) || DEFAULT_OFFICIAL_VIDEOS[0];
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
