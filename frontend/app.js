document.addEventListener('DOMContentLoaded', async () => {
    // 1. Sync User Avatar from authenticated profile / active channel
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

    // 3. Initial Real Feed Load
    await loadMainFeed();
});

// Sync bottom nav avatar circle dynamically from current account
function syncUserNavAvatar() {
    const authUser = window.BTubeAPI ? window.BTubeAPI.getAuthUser() : JSON.parse(localStorage.getItem('btube_user') || 'null');
    const bottomAvatar = document.getElementById('bottomNavInits');
    
    if (!bottomAvatar) return;

    if (authUser && authUser.photo) {
        bottomAvatar.innerHTML = `<img src="${authUser.photo}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`;
    } else {
        const name = authUser?.name || 'User';
        const inits = name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        bottomAvatar.innerText = inits;
    }
}

// State container for real Firestore data (Zero Demo Videos)
let allFeedVideos = [];

// Load Real Feed from Firestore Cloud
async function loadMainFeed() {
    allFeedVideos = [];

    if (window.BTubeAPI && typeof window.BTubeAPI.getFeed === "function") {
        try {
            const apiVideos = await window.BTubeAPI.getFeed("all");
            if (apiVideos && Array.isArray(apiVideos)) {
                allFeedVideos = apiVideos;
            }
        } catch (e) {
            console.error("Firestore feed fetch error:", e);
        }
    }

    renderFeed(allFeedVideos);
}

// Filter feed on category chip tap
function filterFeedByCategory(category) {
    if (!category || category === "All") {
        renderFeed(allFeedVideos);
        return;
    }

    const filtered = allFeedVideos.filter(v => {
        const cat = (v.category || v.type || '').toLowerCase();
        return cat.includes(category.toLowerCase());
    });

    renderFeed(filtered);
}

// Render video cards inside feed container
function renderFeed(videos) {
    const feedContainer = document.querySelector('.feed-videos-list') || 
                          document.getElementById('mainVideosFeed') || 
                          document.querySelector('main');
    
    if (!feedContainer) return;

    if (!videos || videos.length === 0) {
        feedContainer.innerHTML = `
            <div style="padding: 60px 16px; text-align: center; color: #888;">
                <svg viewBox="0 0 24 24" style="width: 48px; height: 48px; fill: #444; margin-bottom: 12px;">
                    <path d="M10 18v-6l5 3-5 3zm7-15H7c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H7V5h10v14z"/>
                </svg>
                <h3 style="font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 6px;">No videos available</h3>
                <p style="font-size: 13px; color: #666; margin-bottom: 16px;">Be the first to upload a video or Short to BTube.</p>
                <a href="../pages/upload.html" style="background: #e50914; color: #fff; padding: 8px 18px; border-radius: 20px; text-decoration: none; font-size: 13px; font-weight: 700;">+ Upload</a>
            </div>
        `;
        return;
    }

    feedContainer.innerHTML = videos.map(v => {
        const initial = (v.channel || 'BTube')[0].toUpperCase();
        const avatarMarkup = v.channelAvatar 
            ? `<img src="${v.channelAvatar}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">` 
            : initial;

        return `
            <article class="feed-video-card" onclick="openWatchPage('${v.id}', '${encodeURIComponent(v.title || '')}', '${encodeURIComponent(v.channel || '')}', '${encodeURIComponent(v.videoUrl || '')}')" style="cursor: pointer; margin-bottom: 16px;">
                <div style="position: relative; width: 100%; aspect-ratio: 16 / 9; background: #202020; border-radius: 10px; overflow: hidden;">
                    <img src="${v.thumb || 'https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=600'}" alt="${v.title || 'Video'}" style="width: 100%; height: 100%; object-fit: cover;" loading="lazy">
                    <span style="position: absolute; bottom: 6px; right: 6px; background: rgba(0,0,0,0.85); font-size: 10px; font-weight: 700; padding: 2px 5px; border-radius: 4px; color: #fff;">
                        ${v.duration || '03:45'}
                    </span>
                </div>
                <div style="display: flex; gap: 12px; padding: 10px 4px;">
                    <div style="width: 36px; height: 36px; border-radius: 50%; background: #e50914; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 13px; color: #fff; flex-shrink: 0; overflow: hidden;">
                        ${avatarMarkup}
                    </div>
                    <div style="flex: 1; min-width: 0;">
                        <h4 style="font-size: 14px; font-weight: 600; line-height: 1.35; color: #fff; margin-bottom: 3px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                            ${v.title || 'Untitled'}
                        </h4>
                        <div style="font-size: 12px; color: #888;">
                            <span>${v.channel || 'BTube Creator'}</span> • <span>${v.views || 0} views</span>
                        </div>
                    </div>
                </div>
            </article>
        `;
    }).join("");
}

// Watch navigation & record view count
function openWatchPage(id, encTitle, encChannel, encUrl) {
    if (window.BTubeAPI && typeof window.BTubeAPI.recordView === "function") {
        window.BTubeAPI.recordView(id);
    }
    window.location.href = `../pages/watch.html?id=${id}&title=${encTitle}&channel=${encChannel}&videoUrl=${encUrl}`;
}
