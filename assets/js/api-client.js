// BTube Firebase Cloud Engine & State Manager
const firebaseConfig = {
  apiKey: "AIzaSyBj406IRJ1VtK84rT2HTkxQWAbQO7bYD2s",
  authDomain: "btube-5fae0.firebaseapp.com",
  projectId: "btube-5fae0",
  storageBucket: "btube-5fae0.firebasestorage.app",
  messagingSenderId: "1009386330534",
  appId: "1:1009386330534:web:357a0ad258678a54185767"
};

// Initialize Firebase SDK
if (typeof firebase !== 'undefined' && !firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}

const db = (typeof firebase !== 'undefined') ? firebase.firestore() : null;

window.BTubeAPI = {
    // 1. Fetch Real Feed directly from Firestore
    async getFeed(type = 'all') {
        if (!db) return [];
        try {
            const snap = await db.collection('videos').get();
            let items = [];
            snap.forEach(doc => {
                items.push({ id: doc.id, ...doc.data() });
            });

            // Cloud Server Timestamp Sorting
            items.sort((a, b) => {
                const tA = a.createdAt?.seconds || 0;
                const tB = b.createdAt?.seconds || 0;
                return tB - tA;
            });

            if (type === 'all') return items;
            return items.filter(item => (item.type || 'video').toLowerCase() === type.toLowerCase());
        } catch (err) {
            console.error('Firestore fetch failed:', err);
            return [];
        }
    },

    // 2. Fetch Single Video By Doc ID
    async getVideoById(docId) {
        if (!db || !docId) return null;
        try {
            const doc = await db.collection('videos').doc(docId).get();
            if (doc.exists) {
                return { id: doc.id, ...doc.data() };
            }
            return null;
        } catch (err) {
            console.error('Error fetching doc:', err);
            return null;
        }
    },

    // 3. Save New Real Video or Short to Firestore
    async saveVideo(videoData) {
        if (!db) throw new Error('Firestore not initialized');
        const docRef = await db.collection('videos').add({
            title: videoData.title || 'Untitled Video',
            description: videoData.description || '',
            category: videoData.category || 'All',
            type: videoData.type || 'video', // 'video' ya 'short'
            videoUrl: videoData.videoUrl,
            thumb: videoData.thumb || 'https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=800',
            channel: videoData.channel || (localStorage.getItem('btube_channel_name') || 'Charandas Bhaskar'),
            views: 0,
            visibility: videoData.visibility || 'Public',
            duration: videoData.duration || (videoData.type === 'short' ? '0:30' : '03:45'),
            createdAt: firebase.firestore.FieldValue.serverTimestamp()
        });
        return docRef.id;
    },

    // 4. View Counter Increment
    async recordView(docId) {
        if (!db || !docId) return;
        try {
            await db.collection('videos').doc(docId).update({
                views: firebase.firestore.FieldValue.increment(1)
            });
        } catch(e) {}
    }
};
