You are building FootNote — an AI-augmented book reader that detects references to music, visual art, and film within book text, then surfaces them as interactive inline experiences.

## Architecture
- **client/**: React + TypeScript (Vite) — EPUB reader UI, media cards, mini-player, lightbox
- **server/**: Node.js + Express + TypeScript — AI recognition (Claude API), media resolution (Spotify, YouTube, Wikimedia), SQLite cache
- Monorepo with npm workspaces

## Key Decisions
- Web first, wrap in Electron/React Native later
- Multi-modal media: AI classifies references → routes to Spotify (music), YouTube (video), web images (art)
- On-demand AI analysis per page, cached after first read
- User EPUBs + public domain (Project Gutenberg) for demo

## Running
- `npm run dev` — starts both client (port 5173) and server (port 3001)
- Client proxies /api/* requests to the server
- Requires ANTHROPIC_API_KEY. Optional: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, YOUTUBE_API_KEY

## Stack
React 18, TypeScript, Vite, epub.js, Express, Claude API (Sonnet), Spotify Web API, YouTube Data API v3, Wikimedia Commons API, better-sqlite3
