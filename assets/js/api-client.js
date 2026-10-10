
/* =========================================
   BTUBE API CLIENT
   Real Firebase data only — NO DEMO VIDEOS
   ========================================= */

const firebaseConfig = {
  apiKey: "AIzaSyBj406IRJ1VtK84rT2HTkxQWAbOQ7bYD2s",
  authDomain: "btube-5fae0.firebaseapp.com",
  projectId: "btube-5fae0",
  storageBucket: "btube-5fae0.firebasestorage.app",
  messagingSenderId: "1009386330534",
  appId: "1:1009386330534:web:357a0ad258678a54185767",
  measurementId: "G-1FP3E5G3VZ"
};

(function () {
  "use strict";

  if (typeof firebase === "undefined") {
    console.error("BTube: Firebase SDK is not loaded.");
    return;
  }

  if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
  }

  const db = firebase.firestore();

  function getStorage() {
    if (typeof firebase.storage !== "function") {
      throw new Error(
        "Firebase Storage SDK load nahi hua. Upload page mein firebase-storage-compat.js add karein."
      );
    }
    return firebase.storage();
  }

  function getCurrentUser() {
    try {
      return typeof firebase.auth === "function"
        ? firebase.auth().currentUser
        : null;
    } catch (_) {
      return null;
    }
  }

  function normalizeType(type) {
    return String(type || "video").toLowerCase() === "short"
      ? "short"
      : "video";
  }

  function cleanVideo(doc) {
    if (!doc || !doc.exists) return null;
    return { id: doc.id, ...doc.data() };
  }

  const api = {
    db,

    // Load real videos from Firestore. No sample/demo fallback.
    async getFeed(type = "all") {
      const snapshot = await db.collection("videos")
        .orderBy("createdAt", "desc")
        .get();

      let videos = [];
      snapshot.forEach(doc => {
        const item = { id: doc.id, ...doc.data() };

        // Hide private and unlisted videos from the public feed.
        if (item.visibility && item.visibility !== "Public") return;

        if (!item.videoUrl) return;

        if (
          type !== "all" &&
          normalizeType(item.type) !== normalizeType(type)
        ) return;

        videos.push(item);
      });

      return videos;
    },

    async getVideoById(docId) {
      if (!docId) return null;

      const doc = await db.collection("videos").doc(docId).get();
      return cleanVideo(doc);
    },

    // Upload a real File to Firebase Storage, then save its metadata.
    async uploadVideo(videoData) {
      if (!videoData || !videoData.file) {
        throw new Error("Pehle asli video file select karein.");
      }

      const file = videoData.file;

      if (!(file instanceof File)) {
        throw new Error("Selected video file valid nahi hai.");
      }

      if (!file.type || !file.type.startsWith("video/")) {
        throw new Error("Kripya valid video file select karein.");
      }

      const storage = getStorage();
      const user = getCurrentUser();
      const ownerId = user ? user.uid : null;

      const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
      const uniqueName =
        Date.now() + "_" + Math.random().toString(36).slice(2, 10) +
        "_" + safeName;

      const storagePath = "videos/" +
        (ownerId || "uploads") + "/" + uniqueName;

      const fileRef = storage.ref().child(storagePath);

      // If upload fails, do not create a fake video record.
      const uploadTask = fileRef.put(file, {
        contentType: file.type
      });

      await new Promise((resolve, reject) => {
        uploadTask.on(
          "state_changed",
          () => {},
          reject,
          resolve
        );
      });

      const videoUrl = await fileRef.getDownloadURL();

      try {
        const record = {
          title: String(videoData.title || "").trim(),
          description: String(videoData.description || "").trim(),
          type: normalizeType(videoData.type),
          videoUrl,
          storagePath,
          thumb: videoData.thumb || "",
          channel: videoData.channel || "BTube Creator",
          ownerId,
          views: 0,
          visibility: videoData.visibility || "Public",
          createdAt: firebase.firestore.FieldValue.serverTimestamp()
        };

        if (!record.title) {
          throw new Error("Video title zaroori hai.");
        }

        const docRef = await db.collection("videos").add(record);
        return { id: docRef.id, ...record, videoUrl };
      } catch (error) {
        // Avoid leaving an orphaned file if metadata saving fails.
        try {
          await fileRef.delete();
        } catch (_) {}
        throw error;
      }
    },

    async updateVideo(docId, updateData) {
      if (!docId) throw new Error("Video ID nahi mili.");

      const allowed = {};
      ["title", "description", "visibility", "thumb"].forEach(key => {
        if (Object.prototype.hasOwnProperty.call(updateData || {}, key)) {
          allowed[key] = updateData[key];
        }
      });

      if (allowed.title !== undefined && !String(allowed.title).trim()) {
        throw new Error("Title khaali nahi ho sakta.");
      }

      allowed.updatedAt =
        firebase.firestore.FieldValue.serverTimestamp();

      await db.collection("videos").doc(docId).update(allowed);
      return true;
    },

    async deleteVideo(docId) {
      if (!docId) throw new Error("Video ID nahi mili.");

      const ref = db.collection("videos").doc(docId);
      const snapshot = await ref.get();

      if (!snapshot.exists) {
        throw new Error("Video nahi mila.");
      }

      const data = snapshot.data();

      // Delete cloud file first when its path is available.
      if (data.storagePath) {
        try {
          await getStorage().ref().child(data.storagePath).delete();
        } catch (error) {
          // Missing files are okay; permission/network errors are not.
          if (error.code !== "storage/object-not-found") throw error;
        }
      }

      await ref.delete();
      return true;
    },

    async recordView(docId) {
      if (!docId) return false;

      await db.collection("videos").doc(docId).update({
        views: firebase.firestore.FieldValue.increment(1)
      });

      return true;
    },

    // Creator's videos. Requires ownerId metadata.
    async getMyVideos() {
      const user = getCurrentUser();

      if (!user) {
        throw new Error("Apni videos dekhne ke liye login zaroori hai.");
      }

      const snapshot = await db.collection("videos")
        .where("ownerId", "==", user.uid)
        .get();

      const videos = [];
      snapshot.forEach(doc => {
        videos.push({ id: doc.id, ...doc.data() });
      });

      videos.sort((a, b) => {
        const timeA = a.createdAt && a.createdAt.toMillis
          ? a.createdAt.toMillis() : 0;
        const timeB = b.createdAt && b.createdAt.toMillis
          ? b.createdAt.toMillis() : 0;
        return timeB - timeA;
      });

      return videos;
    }
  };

  window.BTubeAPI = api;
})();
