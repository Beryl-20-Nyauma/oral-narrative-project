# Frontend Update Plan

**Goal:** Connect frontend to backend API (currently uses mock data)

---

## Priority 1: Core API Integration

### Replace Mock Data with API Calls

| File | Function | Change |
|------|----------|--------|
| `js/app.js` | `renderNarratives()` | Fetch from `GET /api/narratives` |
| `js/app.js` | `openModal(id)` | Fetch from `GET /api/narratives/{id}` |
| `js/app.js` | `filterNarratives()` | Use `GET /api/narratives?emotion=...&theme=...` |
| `js/app.js` | `submitNarrative()` | POST to `/api/narratives/upload` with FormData |

### New API Service Layer

Create `js/api.js`:
```javascript
const API_BASE = '/api';

async function apiGet(endpoint) { ... }
async function apiPost(endpoint, data) { ... }
async function apiUpload(endpoint, formData) { ... }
```

---

## Priority 2: Upload Flow

### Current State (Fake)
- Simulates progress with `setTimeout`
- No actual file upload

### Target State (Real)
1. User selects video file
2. POST `/api/narratives/upload` with:
   - video file (multipart/form-data)
   - title, narrator_name, location, themes, transcript
3. Response returns `{ narrative_id, task_id, status_url }`
4. Poll `GET /api/narratives/{id}/status` for progress
5. Show real progress:
   - "Extracting audio..."
   - "Analyzing facial features..."
   - "Running multimodal fusion..."
6. On complete, add narrative to grid

### WebSocket (Optional Enhancement)
- Connect to WebSocket for real-time progress updates
- Endpoint: `ws://localhost:8000/ws/progress/{narrative_id}`

---

## Priority 3: Search

### Current State (Fake)
- Client-side filter on mock data array

### Target State (Real)
- Use `GET /api/search?q=...&field=...`
- Fields: all, narrator, emotion, theme, keyword

```javascript
async function searchNarratives(query, field = 'all') {
  return apiGet(`/search?q=${encodeURIComponent(query)}&field=${field}`);
}
```

---

## Priority 4: Authentication UI

### New Components Needed

| Component | Endpoints |
|-----------|-----------|
| Login Form | `POST /api/auth/login` |
| Register Form | `POST /api/auth/register` |
| User Menu | `GET /api/auth/me` |
| Logout Button | `POST /api/auth/logout` |

### Auth State Management
```javascript
let authToken = localStorage.getItem('token');
let currentUser = null;

async function login(email, password) { ... }
async function register(email, password, fullName) { ... }
async function logout() { ... }
async function fetchCurrentUser() { ... }
```

### UI Changes
- Add "Login" button to nav (when not logged in)
- Add user dropdown to nav (when logged in)
- Show user name, logout option
- Protect upload route (require auth)

---

## Priority 5: Narrator Features

### Narrator Identification

| Feature | Endpoint | UI Location |
|---------|----------|-------------|
| View narrators | `GET /api/narrators` | New "Narrators" page |
| Narrator detail | `GET /api/narrators/{id}` | Click from list |
| Register narrator | `POST /api/narrators/register` | Upload reference image |
| Identify from upload | Automatic via `/api/narratives/upload` | Show matched narrator |

### UI Components
- Narrator list page with face thumbnails
- Narrator profile cards showing:
  - Name
  - Number of narratives
  - First/last seen dates
  - Reference image

---

## Priority 6: Stats Dashboard

### Current State
- Hardcoded numbers in stats bar

### Target State
- Fetch from `GET /api/stats`
- Show real:
  - Narratives count
  - Unique narrators
  - Avg duration
  - Emotion distribution

### New: Admin Dashboard
- Link to `/api/stats/benchmark`
- Show:
  - Database query times
  - Redis latency
  - ML inference times
  - GPU utilization

---

## Priority 7: Real-time Updates

### Processing Status Polling
```javascript
async function pollProcessingStatus(narrativeId) {
  const status = await apiGet(`/narratives/${narrativeId}/status`);
  updateProgressBar(status.progress);
  if (status.status !== 'complete') {
    setTimeout(() => pollProcessingStatus(narrativeId), 2000);
  }
}
```

### Queue Status (Admin)
- Show Celery worker count
- Active tasks
- Queue depth

---

## Priority 8: Error Handling

### API Error Display
- Show toast notifications for errors
- Handle 401 (redirect to login)
- Handle 429 (rate limited - show wait time)
- Handle 500 (show retry option)

### Rate Limiting
```javascript
// Show remaining requests in UI
if (response.headers['x-ratelimit-remaining']) {
  showRateLimitInfo(response.headers['x-ratelimit-remaining']);
}
```

---

## Priority 9: Performance Optimizations

### Caching
- Cache narrative list in localStorage
- Cache narrator profiles
- Invalidate on mutations

### Optimistic UI
- Add narrative to grid immediately on upload
- Update with real data when processing complete

---

## Implementation Order

1. **Phase 1: Core CRUD** (2-3 days)
   - [ ] Create `js/api.js` service layer
   - [ ] Replace mock narratives with API fetch
   - [ ] Connect search to API
   - [ ] Connect upload to API with FormData

2. **Phase 2: Real Upload Flow** (2 days)
   - [ ] Implement status polling
   - [ ] Show real progress stages
   - [ ] Handle upload errors

3. **Phase 3: Authentication** (2 days)
   - [ ] Login/Register forms
   - [ ] Token management
   - [ ] Protected routes

4. **Phase 4: Narrator Features** (2 days)
   - [ ] Narrator list page
   - [ ] Narrator identification display
   - [ ] Narrator rename UI

5. **Phase 5: Stats & Admin** (1 day)
   - [ ] Real stats from API
   - [ ] Benchmark display
   - [ ] Queue status

6. **Phase 6: Polish** (1 day)
   - [ ] Error handling
   - [ ] Loading states
   - [ ] Rate limit UI

---

## File Structure After Updates

```
frontend/
├── index.html
├── css/
│   └── styles.css
├── js/
│   ├── app.js          # Main app logic
│   ├── api.js          # API service layer (NEW)
│   ├── auth.js         # Authentication logic (NEW)
│   └── upload.js       # Upload handling (NEW)
└── pages/
    ├── narratives.html  # Narrative archive (NEW)
    ├── narrators.html   # Narrator list (NEW)
    └── admin.html       # Admin dashboard (NEW)
```

---

## Estimated Effort

| Phase | Effort | Priority |
|-------|--------|----------|
| Core CRUD | 2-3 days | HIGH |
| Upload Flow | 2 days | HIGH |
| Authentication | 2 days | MEDIUM |
| Narrator Features | 2 days | MEDIUM |
| Stats & Admin | 1 day | LOW |
| Polish | 1 day | LOW |
| **Total** | **10-11 days** | |
