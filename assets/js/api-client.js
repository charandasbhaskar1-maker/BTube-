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

window.BTubeAPI = {
    // 1. Current Logged-in User
    getUser() {
        if (!auth) return null;
        return auth.currentUser || JSON.parse(localStorage.getItem('btube_user') || 'null');
    },

    // 2. Google One-Tap Sign In
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
            console.error('Google Sign-in failed:', err);
            // Fallback Guest/Quick Prompt for testing
            const fallbackName = prompt("Apna Naam daalein login ke liye:", "User");
            if (fallbackName) {
                const guestUser = { uid: 'u_' + Date.now(), name: fallbackName, email: '', photo: '' };
                localStorage.setItem('btube_user', JSON.stringify(guestUser));
                return guestUser;
            }
            return null;
        }
    },

    // 3. Sign Out
    async signOut() {
        if (auth) await auth.signOut();
        localStorage.removeItem('btube_user');
        window.location.reload();
    },

    // 4. Feed & Single Video Fetch
    async getFeed(type = 'all') {
        if (!db) return [];
        try {
            const snap = await db.collection('videos').get();
            let items = [];
            snap.forEach(doc => items.push({ id: doc.id, ...doc.data() }));
            items.sort((a, b) => (b.createdAt?.seconds || 0) - (a.createdAt?.seconds || 0));
            if (type === 'all') return items;
            return items.filter(item => (item.type || 'video').toLowerCase() === type.toLowerCase());
        } catch(e) {
            return [];
        }
    },

    async getVideoById(docId) {
        if (!db || !docId) return null;
        const doc = await db.collection('videos').doc(docId).get();
        return doc.exists ? { id: doc.id, ...doc.data() } : null;
    },

    // 5. Protected Upload: Sirf login hone par
    async saveVideo(videoData) {
        const u = this.getUser();
        if (!u) throw new Error("Video upload karne ke liye login zaroori hai!");
        return await db.collection('videos').add({
            ...videoData,
            userId: u.uid,
            channel: u.name,
            createdAt: firebase.firestore.FieldValue.serverTimestamp()
        });
    },

    // 6. View Counter
    async recordView(docId) {
        if (!db || !docId) return;
        try {
            await db.collection('videos').doc(docId).update({
                views: firebase.firestore.FieldValue.increment(1)
            });
        } catch(e) {}
    }
};
