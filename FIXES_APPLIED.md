# BTube ZIP patch notes

## Updated in this build
- Fixed FastAPI router imports to match the actual `backend/auth` and `backend/api` folders.
- Unified backend upload storage paths and stopped exposing the upload directory through a public static-file mount.
- Added a real root `index.html` from the supplied frontend home page and registered the PWA service worker.
- Replaced demo-feed fallback with real API/Firestore records only.
- Added missing API-client methods for Google sign-in, token storage, feed normalization, upload, details, views, edit, delete, and creator uploads.
- Connected video and Shorts upload pages to authenticated chunk upload + backend metadata creation; removed sample-video and temporary `blob:` upload fallbacks.
- Added backend video detail, creator-only listing, edit, and delete routes with active-channel ownership checks.
- Corrected HTTP Range streaming and removed the sample.mp4 fallback.
- Corrected Shorts type filtering and removed its sample playback fallback.
- Changed visual safety scanning to report `Review Required` when no trained classifier is configured instead of falsely declaring the file clean.
- Added PWA icon files and reduced service-worker cache deletion to BTube-owned caches.
- Added backend setup requirements and deployment configuration notes to README.

## Before production deployment
- Set `DATABASE_URL` to persistent PostgreSQL, `BTUBE_ENV=production`, a unique `BTUBE_SECRET_KEY` (32+ characters), and `GOOGLE_CLIENT_ID` to the Firebase/Google Web OAuth client ID.
- If the API is not hosted at `https://btube-api.onrender.com`, update `API_BASE_URL` in `assets/js/api-client.js`.
- Configure persistent disk/object storage. Local uploads on ephemeral hosting may be lost after a redeploy/restart.
- SafeShield still has no trained image classifier; it does not provide an automated visual safety verdict.
- CopyScan is still a small registry-based check, not a full audio fingerprinting system.
- Payment routes still need a real payment provider, verified webhooks, idempotency, and payout-provider integration before being used for real money.
- A full runtime test still requires installing `backend/requirements.txt` and setting deployment credentials. Static Python and JavaScript syntax checks passed in this environment.
