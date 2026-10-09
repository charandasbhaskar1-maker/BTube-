/**
 * BTube Central API Client & Bridge
 * Connects Frontend UI with FastAPI Backend, SafeShield AI, CopyScan & BPP Monetization.
 */

const API_BASE_URL = window.location.origin.includes("localhost") 
    ? "http://127.0.0.1:8000" 
    : window.location.origin;

const BTubeAPI = {
    // 1. Get Auth Token
    getAuthToken() {
        return localStorage.getItem("btube_token") || "mock_dev_token";
    },

    // 2. Fetch Viral Ranked Feed (Homepage & Categories)
    async getHomeFeed(category = "All") {
        try {
            const url = category && category !== "All" 
                ? `${API_BASE_URL}/api/videos/feed?category=${encodeURIComponent(category)}`
                : `${API_BASE_URL}/api/videos/feed`;

            const res = await fetch(url);
            if (!res.ok) throw new Error("Feed network error");
            return await res.json();
        } catch (err) {
            console.warn("Using offline feed cache.");
            return null;
        }
    },

    // 3. Upload Video with SafeShield & CopyScan Audit
    async uploadVideo(videoPayload) {
        try {
            const token = this.getAuthToken();
            const res = await fetch(`${API_BASE_URL}/api/videos/upload`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(videoPayload)
            });

            const data = await res.json();
            if (!res.ok) {
                return {
                    success: false,
                    error: data.detail || "Video upload failed due to policy guidelines."
                };
            }

            return {
                success: true,
                data: data
            };
        } catch (err) {
            // Local fallback simulation if running purely client-side
            const isNsfw = ["sex", "xxx", "porn", "gandi", "adult"].some(w => 
                (videoPayload.title + " " + (videoPayload.description || "")).toLowerCase().includes(w)
            );

            if (isNsfw) {
                return {
                    success: false,
                    error: "SafeShield Block: Video contains adult/vulgar content violating BTube Community Standards."
                };
            }

            const hasClaim = videoPayload.title.toLowerCase().includes("banjo");
            return {
                success: true,
                data: {
                    status: "success",
                    video_id: "local_" + Date.now(),
                    safeshield: "Clean",
                    copyscan: hasClaim ? "Claimed" : "Original",
                    claim_notice: hasClaim ? "Audio matched with 'Dhun AI Waveform'. Revenue redirected." : null,
                    is_monetized: !hasClaim
                }
            };
        }
    },

    // 4. Record View & Credit Watch Hours
    async recordView(videoId, watchSeconds = 30) {
        try {
            await fetch(`${API_BASE_URL}/api/videos/${videoId}/view?watch_seconds=${watchSeconds}`, {
                method: "POST"
            });
        } catch (err) {
            // Offline local progress
            let currentHours = parseFloat(localStorage.getItem("btube_watch_hours") || "1240.5");
            currentHours += (watchSeconds / 3600);
            localStorage.setItem("btube_watch_hours", currentHours.toFixed(2));
        }
    },

    // 5. Toggle Like
    async toggleLike(videoId) {
        try {
            const res = await fetch(`${API_BASE_URL}/api/videos/${videoId}/like`, {
                method: "POST"
            });
            return await res.json();
        } catch (err) {
            return { likes_count: 1 };
        }
    },

    // 6. Post Comment with SafeShield Profanity Verification
    async postComment(videoId, commentText) {
        try {
            const res = await fetch(`${API_BASE_URL}/api/videos/${videoId}/comment`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ comment_text: commentText })
            });

            const data = await res.json();
            if (!res.ok) {
                return { success: false, error: data.detail };
            }
            return { success: true, data: data };
        } catch (err) {
            return { success: true, data: { comment_text: commentText } };
        }
    },

    // 7. Get Channel Monetization & BPP Metrics
    async getMonetizationStatus() {
        try {
            const token = this.getAuthToken();
            const res = await fetch(`${API_BASE_URL}/api/monetization/status`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            return await res.json();
        } catch (err) {
            return {
                subscribers: 1250,
                watch_hours: parseFloat(localStorage.getItem("btube_watch_hours") || "4120.5"),
                shorts_views_90d: 11200000,
                is_eligible: true,
                payout_upi: "charandas@upi"
            };
        }
    }
};

window.BTubeAPI = BTubeAPI;
