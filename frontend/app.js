document.addEventListener('DOMContentLoaded', () => {
    // 1. Sync User Avatar (e.g. 'CB' from local channel name)
    syncUserNavAvatar();

    // 2. Chips switching & category filter
    const pills = document.querySelectorAll('.cat-pill');
    pills.forEach(pill => {
        pill.addEventListener('click', () => {
            pills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            const selectedCategory = pill.innerText.trim();
            filterFeedByCategory(selectedCategory);
        });
    });

    // 3. Initial Feed Load
    loadMainFeed();
});

// Sync bottom nav avatar circle
function syncUserNavAvatar() {
    const savedName = localStorage.getItem('btube_channel_name') || 'Charandas Bhaskar';
    const parts = savedName.trim().split(' ');
    let inits = parts[0][0];
    if (parts.length > 1) inits += parts[1][0];

    const bottomAvatar = document.getElementById('bottomNavInits');
    if (bottomAvatar) {
        bottomAvatar.innerText = inits.toUpperCase();
    }
}

// Global video registry (Default Feed + Uploaded Videos)
const DEFAULT_VIDEOS = [
    {
        id: "vid-1",
        title: "Chhattisgarhi Panthi Song • Special Cultural Video 2026",
        channel: "Charandas Bhaskar",
        views: "210K views",
        time: "2 weeks ago",
        duration: "05:42",
        thumb: "https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=600",
        category: "Music"
    },
    {
        id: "vid-2",
        title: "Typewriter Banjo with Magnetic Pickups Full Making Guide",
        channel: "Charandas Bhaskar",
        views: "45K views",
        time: "1 month ago",
        duration: "14:10",
        thumb: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600",
        category: "Banjo"
    },
    {
        id: "vid-3",
        title: "Morning Commute & Village Lifestyle Daily Vlog #42",
        channel: "The Bhaskar Vlog",
        views: "8.4K views",
        time: "3 days ago",
        duration: "06:25",
        thumb: "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=600",
        category: "Vlog"
    },
    {
        id: "vid-4",
        title: "Hareli Festival Folk Song • Farm Life & Nature Melody",
        channel: "Charandas Bhaskar",
        views: "98K views",
        time: "1 week ago",
        duration: "04:18",
        thumb: "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=600",
        category: "Music"
    }
];

let allFeedVideos = [...DEFAULT_VIDEOS];

// Load Feed (includes locally uploaded video from upload-video.html)
async function loadMainFeed() {
    // Check if new video was uploaded recently
    const lastUploadedTitle = localStorage.getItem('btube_last_edited_title');
    const lastUploadedThumb = localStorage.getItem('btube_temp_edit_thumb');
    const lastUploadedVis = localStorage.getItem('btube_last_edited_vis') || 'Public';

    if (lastUploadedTitle && lastUploadedVis === 'Public') {
        const alreadyExists = allFeedVideos.some(v => v.title === lastUploadedTitle);
        if (!alreadyExists) {
            allFeedVideos.unshift({
                id: "user-new-vid",
                title: lastUploadedTitle,
                channel: localStorage.getItem('btube_channel_name') || 'Charandas Bhaskar',
                views: "1 view",
                time: "Just now",
                duration: "03:15",
                thumb: lastUploadedThumb || "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600",
                category: "Music"
            });
        }
    }

    // Try fetching from backend API if online
    if (window.BTubeAPI && typeof window.BTubeAPI.getHomeFeed === "function") {
        try {
            const apiVideos = await window.BTubeAPI.getHomeFeed("All");
            if (apiVideos && apiVideos.length > 0) {
                allFeedVideos = apiVideos;
            }
        } catch (e) {
            console.log("Offline mode: Using internal feed storage.");
        }
    }

    renderFeed(allFeedVideos);
}

// Filter feed on chip tap
function filterFeedByCategory(category) {
    if (category === "All") {
        renderFeed(allFeedVideos);
        return;
    }

    const filtered = allFeedVideos.filter(v => {
        if (!v.category) return false;
        return v.category.toLowerCase().includes(category.toLowerCase()) || 
               category.toLowerCase().includes(v.category.toLowerCase());
    });

    renderFeed(filtered);
}

// Render video cards inside feed container
function renderFeed(videos) {
    const feedContainer = document.querySelector('.feed-videos-list') || 
                          document.getElementById('mainVideosFeed') || 
                          document.querySelector('main');
    
    if (!feedContainer) return;

    if (videos.length === 0) {
        feedContainer.innerHTML = `
            <div style="padding: 40px 16px; text-align: center; color: #888;">
                <p>Is category me abhi koi video nahi hai.</p>
            </div>
        `;
        return;
    }

    feedContainer.innerHTML = videos.map(v => `
        <article class="feed-video-card" onclick="openWatchPage('${v.id}', '${encodeURIComponent(v.title)}', '${encodeURIComponent(v.channel || 'BTube Creator')}')" style="cursor: pointer; margin-bottom: 16px;">
            <div style="position: relative; width: 100%; aspect-ratio: 16 / 9; background: #202020; border-radius: 10px; overflow: hidden;">
                <img src="${v.thumb || v.thumbnail_url || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600'}" alt="${v.title}" style="width: 100%; height: 100%; object-fit: cover;" loading="lazy">
                <span style="position: absolute; bottom: 6px; right: 6px; background: rgba(0,0,0,0.85); font-size: 10px; font-weight: 700; padding: 2px 5px; border-radius: 4px; color: #fff;">
                    ${v.duration || '04:15'}
                </span>
            </div>
            <div style="display: flex; gap: 12px; padding: 10px 4px;">
                <div style="width: 36px; height: 36px; border-radius: 50%; background: #e50914; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 13px; color: #fff; flex-shrink: 0;">
                    ${(v.channel || 'CB')[0].toUpperCase()}
                </div>
                <div style="flex: 1; min-width: 0;">
                    <h4 style="font-size: 14px; font-weight: 600; line-height: 1.35; color: #fff; margin-bottom: 3px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                        ${v.title}
                    </h4>
                    <div style="font-size: 12px; color: #888;">
                        <span>${v.channel || 'Charandas Bhaskar'}</span> • <span>${v.views || '1K views'}</span> • <span>${v.time || 'Recently'}</span>
                    </div>
                </div>
            </div>
        </article>
    `).join("");
}

// Watch navigation & credit watch time
function openWatchPage(id, encTitle, encChannel) {
    if (window.BTubeAPI && typeof window.BTubeAPI.recordView === "function") {
        window.BTubeAPI.recordView(id, 60);
    }
    window.location.href = `../pages/watch.html?id=${id}&title=${encTitle}&channel=${encChannel}`;
}
