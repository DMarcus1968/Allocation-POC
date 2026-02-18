# FootNote — AI-Augmented Book Reader

## Vision
A digital book reader that uses AI to recognize references to music, visual art, film, and other media within the text, then surfaces those references as interactive, inline experiences — so readers can *hear the song*, *see the painting*, or *watch the clip* without ever leaving the page.

---

## The Problem
Books about art — music biographies, art history, cultural criticism — constantly reference works the reader should experience to fully understand the story. Today, readers must:
1. Notice the reference
2. Leave the book
3. Open a separate app (Spotify, YouTube, etc.)
4. Search for the work
5. Return to the book and find their place

This breaks immersion and most readers simply skip it, losing a crucial dimension of the text.

## The Solution
An intelligent reader that:
- **Detects** media references in text using AI (songs, albums, artists, paintings, films, etc.)
- **Resolves** those references to playable/viewable media on real services (Spotify, YouTube, Apple Music, museum APIs)
- **Presents** inline media controls so readers can experience the work without leaving the page

---

## Key User Stories

1. *Reading Bruce Springsteen's "Born to Run" memoir.* The text mentions "Darkness on the Edge of Town." A subtle indicator appears. Tap it, and the album starts playing in a mini-player at the bottom of the screen while you keep reading.

2. *Reading "Just Kids" by Patti Smith.* She describes seeing a Modigliani painting. A tap reveals the painting in an overlay, with attribution and museum source.

3. *Reading "And They All Sang" by Studs Terkel.* A passage discusses Louis Armstrong's "West End Blues." A link surfaces the specific recording on YouTube or Spotify.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  Reader UI (Frontend)            │
│  ┌───────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Book       │  │ Media    │  │ Mini Player  │  │
│  │ Renderer   │  │ Markers  │  │ / Overlay    │  │
│  └───────────┘  └──────────┘  └──────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              Backend / API Layer                  │
│  ┌───────────────┐  ┌────────────────────────┐   │
│  │ AI Recognition│  │ Media Resolution       │   │
│  │ Engine        │  │ Service                │   │
│  │ (Claude API)  │  │ (Spotify/YT/Apple/etc) │   │
│  └───────────────┘  └────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

### Component Breakdown

### 1. Book Renderer (Frontend)
- **Format support**: EPUB (primary), PDF (stretch goal)
- **Rendering**: Parse EPUB → HTML/CSS, render with pagination or scroll
- **Platform decision needed** (see Open Questions)

### 2. AI Media Recognition Engine
- Takes a passage of text (e.g., a chapter or page)
- Uses an LLM (Claude API) to identify media references and classify them:
  - `music` — song, album, artist, performance
  - `visual_art` — painting, sculpture, photograph
  - `film` — movie, documentary, TV show
  - `literary` — book, poem (lower priority)
- Returns structured data:
  ```json
  {
    "references": [
      {
        "text_span": "Darkness on the Edge of Town",
        "start_offset": 1423,
        "end_offset": 1452,
        "type": "music",
        "entity": {
          "title": "Darkness on the Edge of Town",
          "artist": "Bruce Springsteen",
          "kind": "album",
          "year": 1978
        },
        "confidence": 0.95
      }
    ]
  }
  ```
- **Caching**: Results are cached per book/chapter so the AI is only called once per passage

### 3. Media Resolution Service
- Takes a recognized entity and finds it on one or more services
- **Music**: Spotify Web API, Apple Music API, YouTube Data API
- **Visual art**: Wikimedia Commons, Met Museum Open Access API, Google Arts & Culture
- **Film**: YouTube, TMDB (The Movie Database)
- Returns playable/viewable URIs and metadata (thumbnail, duration, preview URL)
- **Fallback chain**: If Spotify has no result, try Apple Music, then YouTube

### 4. Inline Media Experience (Frontend)
The AI determines the **best medium** for each reference and routes to the appropriate provider:
- **Music** → **Spotify**: Mini-player bar at bottom of screen (play/pause, track info, progress). 30-second previews for MVP, full playback for premium users later.
- **Video** → **YouTube**: Embedded iframe player for film clips, concert footage, documentaries, music videos
- **Images/Photos** → **Web image display**: Lightbox overlay showing paintings, photographs, album art with attribution and source
- **Film references**: Trailer via YouTube embed; metadata from TMDB

---

## Technical Stack (Proposed)

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | **React + TypeScript** | Wide ecosystem, component model fits reader UI |
| Book parsing | **epub.js** or **readium** | Mature EPUB rendering libraries |
| AI Engine | **Claude API (Anthropic)** | Best at nuanced entity recognition in literary context |
| Backend API | **Node.js + Express** (or Next.js API routes) | JS full-stack, fast to prototype |
| Music APIs | **Spotify Web API**, **YouTube Data API v3** | Best coverage for music |
| Art APIs | **Met Museum Open Access**, **Wikimedia Commons** | Free, high-quality art images |
| Database | **SQLite** (prototype) → **PostgreSQL** (production) | Cache recognized entities and resolved media |
| Auth | **OAuth 2.0** (for Spotify/Apple Music user accounts) | Required for playback SDKs |

---

## Phased Development Plan

### Phase 1 — Foundation (MVP)
**Goal**: A working web reader that can display an EPUB and recognize media references (music, art, film) in a single book, routing each to the appropriate media provider.

- [ ] Project scaffolding (React + TypeScript + Node.js web app)
- [ ] EPUB parser and basic book renderer (pagination, chapters, bookmarks)
- [ ] AI recognition pipeline: send page text to Claude API, get back structured media references with type classification (music / visual_art / film)
- [ ] Highlight recognized references in the text with subtle, type-aware markers
- [ ] Click a marker → show a card with entity info (title, artist/creator, year, type)
- [ ] Media routing: resolve references to the right provider based on type:
  - Music → Spotify Web API search + 30-second preview playback
  - Video/Film → YouTube Data API search + embedded iframe player
  - Art/Photos → Web image search + lightbox overlay with attribution
- [ ] Basic caching layer (don't re-analyze the same page)
- [ ] Include a few public domain books (Project Gutenberg) for demo/testing

**Test book**: Bruce Springsteen's *Born to Run* (EPUB)

### Phase 2 — Richer Media & Playback
- [ ] Full Spotify Web Playback SDK integration (for logged-in premium users)
- [ ] YouTube fallback player for non-Spotify users
- [ ] Persistent mini-player bar (music continues while reading)
- [ ] Visual art support: recognize painting/artwork references, fetch images
- [ ] Film/documentary references: link to trailers via YouTube/TMDB
- [ ] Improved UI: smoother animations, configurable marker styles, dark mode

### Phase 3 — Intelligence & Polish
- [ ] Pre-process entire book on import (batch AI analysis)
- [ ] "Media timeline" view: see all references in a book as a browsable list
- [ ] Context-aware resolution (e.g., distinguish between "Yesterday" the Beatles song vs. the word "yesterday")
- [ ] User preferences: preferred music service, auto-play settings
- [ ] Multiple book format support (PDF via pdf.js)
- [ ] Offline mode: cache resolved media metadata for offline reading

### Phase 4 — Platform & Social
- [ ] Mobile-responsive / PWA or React Native port
- [ ] Share a "media moment" (book passage + linked media) socially
- [ ] Community annotations: users can confirm/correct/add media links
- [ ] Publisher API: authors/publishers can embed verified media links in EPUBs

---

## Decisions (Resolved)

| Question | Decision | Notes |
|----------|----------|-------|
| **Q1: Platform** | **Web first, wrap later** | Start as a React web app. Wrap in Electron (desktop) or React Native (mobile) in later phases. |
| **Q2: Media Playback** | **Multi-modal, AI-routed** | AI classifies each reference by type and routes to the best provider: **Spotify** for music, **YouTube** for video, **web images** for art/photos. |
| **Q3: AI Processing** | **On-demand per page** | Analyze text as the reader navigates. Cache results so each passage is only analyzed once. |
| **Q4: Book Source** | **Both** | User-supplied DRM-free EPUBs + public domain books (Project Gutenberg) for demo/testing. |
| **Q5: Name** | **FootNote** | A play on musical notes, book footnotes, and "noting" media references. |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| AI misidentifies references (false positives) | Confidence thresholds; let users dismiss/correct |
| AI misses subtle references (false negatives) | Iterative prompt tuning; user can manually tag |
| Spotify/YouTube API rate limits | Aggressive caching; batch resolution |
| API costs (Claude) for large books | Process once, cache forever; chunk text efficiently |
| DRM-protected EPUBs can't be parsed | Clearly scope to DRM-free EPUBs for prototype |
| Music licensing / legal gray areas | Use official APIs (previews are licensed); deep-link to services |

---

## Next Steps (Ready to Build)
1. ~~Finalize open questions~~ ✅ All resolved
2. Create project scaffolding and repository structure
3. Build the EPUB renderer (book display + pagination)
4. Build the AI recognition pipeline (Claude API + type classification)
5. Build the media resolution service (Spotify + YouTube + image routing)
6. Integrate media cards and players into the reader UI
7. Add public domain demo books and test end-to-end
