/**
 * BTube Central API Client & Engine Bridge
 * Connects frontend views with FastAPI backend, SafeShield, CopyScan and BPP
 */

// Localhost during development, or change to Render/Cloud URL in production
const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : "https://btube-api.onrender.com"; // Cloud URL placeholder

const BTubeAPI = {
    // 1. Get Auth Token
    getToken() {
        return localStorage.getItem("btube_auth_token") || "";
    },

    setToken(token) {
        localStorage.setItem("btube_auth_token", token);
    },

    // 2. Fetch Viral Ranked Feed
    async getHomeFeed(category = "All") {
        try {
            const url = `${API_BASE_URL}/api/videos/feed${category !== 'All' ? `?category=${encodeURIComponent(category)}` : ''}`;
            const res = await fetch(url);
            if (!res.ok) throw new Error("Feed fetch failed");
            return await res.json();
        } catch (err) {
            console.warn("API Offline, falling back to local cached feed:", err);
            return JSON.parse(localStorage.getItem("btube_local_videos") || "[]");
        }
    },

    // 3. Upload Video with SafeShield & CopyScan Gatekeeper
    async uploadVideo(videoData) {
        try {
            const res = await fetch(`${API_BASE_URL}/api/videos/upload`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${this.getToken()}`
                },
                body: JSON.stringify(videoData)
            });

            const data = await res.json();
            if (!res.ok) {
                // Returns SafeShield block or validation error message
                return { success: false, error: data.detail || "Upload rejected by safety engine." };
            }

            return { success: true, data: data };
        } catch (err) {
            console.warn("Backend not reached, storing in local fallback:", err);
            // Local fallback simulation
            const localVideos = JSON.parse(localStorage.getItem("btube_local_videos") || "[]");
            localVideos.unshift(videoData);
            localStorage.setItem("btube_local_videos", JSON.stringify(localVideos));
            return { success: true, localOnly: true, data: videoData };
        }
    },

    // 4. Record View and Watch Time (Updates BPP Watch Hours)
    async recordView(videoId, watchSeconds) {
        try {
            await fetch(`${API_BASE_URL}/api/videos/${videoId}/view?watch_seconds=${watchSeconds}`, {
                method: "POST"
            });
        } catch (err) {
            console.warn("View record failed:", err);
        }
    },

    // 5. Fetch Real-time BPP Creator Monetization Stats
    async getBppDashboard() {
        try {
            const res = await fetch(`${API_BASE_URL}/api/bpp/dashboard`, {
                headers: {
                    "Authorization": `Bearer ${this.getToken()}`
                }
            });
            if (!res.ok) throw new Error("Could not load BPP stats");
            return await res.json();
        } catch (err) {
            // Demo fallback if user is offline or not logged in yet
            return {
                channel_name: localStorage.getItem("btube_channel_name") || "Charandas Bhaskar",
                current_tier: "Not Eligible",
                metrics: {
                    subscribers: 245,
                    watch_hours: 140.0,
                    shorts_views: 45000
                },
                compliance: {
                    "2fa_enabled": true,
                    "active_strikes": 0
                },
                wallet: {
                    total_earnings_inr: 0.0,
                    payout_upi_id: ""
                }
            };
        }
    }
};

window.BTubeAPI = BTubeAPI;
