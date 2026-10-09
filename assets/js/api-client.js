// BTube Firebase Cloud Engine & State Manager
const firebaseConfig = {
  apiKey: "AIzaSyBj406IRJ1VtK84rT2HTkxQWAbQO7bYD2s",
  authDomain: "btube-5fae0.firebaseapp.com",
  projectId: "btube-5fae0",
  storageBucket: "btube-5fae0.firebasestorage.app",
  messagingSenderId: "1009386330534",
  appId: "1:1009386330534:web:357a0ad258678a54185767",
  measurementId: "G-1FP3E5G3VZ"
};

// Initialize Firebase SDK
if (typeof firebase !== 'undefined' && !firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}

const db = (typeof firebase !== 'undefined') ? firebase.firestore() : null;

window.BTubeAPI = {
    // 1. Fetch All Videos & Shorts from Firestore
    async getFeed(type = 'all') {
        if (!db) return [];
        try {
            let ref = db.collection('videos').orderBy('createdAt', 'desc');
            const snap = await ref.get();
            let items = [];
            snap.forEach(doc => {
                items.push({ id: doc.id, ...doc.data() });
            });

            if (type === 'all') return items;
            return items.filter(item => (item.type || 'video').toLowerCase() === type.toLowerCase());
        } catch (err) {
            console.warn('Firestore fetch failed, using offline fallback', err);
            return [];
        }
    },

    // 2. Fetch Single Video By Document ID
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

    // 3. Upload New Video / Short to Cloud
    async uploadVideo(videoData) {
        if (!db) throw new Error('Firestore not initialized');
        const docRef = await db.collection('videos').add({
            title: videoData.title || 'Untitled Video',
            description: videoData.description || '',
            type: videoData.type || 'video', // 'video' or 'short'
            videoUrl: videoData.videoUrl,
            thumb: videoData.thumb || 'https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=800',
            channel: videoData.channel || 'Charandas Bhaskar',
            views: 0,
            visibility: videoData.visibility || 'Public',
            duration: videoData.duration || '03:15',
            createdAt: firebase.firestore.FieldValue.serverTimestamp()
        });
        return docRef.id;
    },

    // 4. Update / Edit Video
    async updateVideo(docId, updateData) {
        if (!db || !docId) return false;
        await db.collection('videos').doc(docId).update(updateData);
        return true;
    },

    // 5. Delete Video
    async deleteVideo(docId) {
        if (!db || !docId) return false;
        await db.collection('videos').doc(docId).delete();
        return true;
    },

    // 6. View Counter Increment
    async recordView(docId) {
        if (!db || !docId) return;
        try {
            await db.collection('videos').doc(docId).update({
                views: firebase.firestore.FieldValue.increment(1)
            });
        } catch(e) {}
    }
};
