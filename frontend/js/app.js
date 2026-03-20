const EMOTION_COLORS = {
  joy: "#c4833a", sadness: "#4a6741", neutral: "#8a7b6a",
  anger: "#b54e2a", fear: "#9b5e7a", surprise: "#c4857a", disgust: "#6b7b4a"
};

let allNarratives = [];
let filteredNarratives = [];
let isLoading = false;
let currentNarrativeId = null;
let filterTimeout = null;

function showLoading(show) {
  isLoading = show;
  const grid = document.getElementById('narrativeGrid');
  if (show) {
    grid.innerHTML = `
      <div class="loading-state" style="grid-column:1/-1;text-align:center;padding:3rem;">
        <div class="skeleton-loader" style="display:flex;gap:1rem;justify-content:center;">
          ${Array(4).fill().map(() => `
            <div class="skeleton-card" style="width:280px;">
              <div class="skeleton-thumb"></div>
              <div class="skeleton-body">
                <div class="skeleton-line"></div>
                <div class="link skeleton-line" style="width:60%;"></div>
                <div class="skeleton-line" style="width:80%;"></div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }
}

function showError(message) {
  const grid = document.getElementById('narrativeGrid');
  grid.innerHTML = `
    <div class="error-state" style="grid-column:1/-1;text-align:center;padding:3rem;">
      <div style="color:var(--terracotta);margin-bottom:1rem;">${message}</div>
      <button class="btn-secondary" onclick="loadNarratives()">Retry</button>
    </div>
  `;
}

function transformNarrative(apiData) {
  const emotionDist = apiData.narrator_profile?.emotion_distribution || {};
  const emotions = Object.entries(emotionDist).map(([label, value]) => ({
    label,
    pct: Math.round(value * 100),
    color: EMOTION_COLORS[label] || "#8a7b6a"
  })).sort((a, b) => b.pct - a.pct).slice(0, 4);
  
  const emojis = ['👩', '👨', '👴', '👵', '🧑', '👩🏾', '👨🏾', '👵🏽', '👴🏻', '👩🏻'];
  const emojiIndex = Math.abs(hashCode(apiData.id || '')) % emojis.length;
  
  return {
    id: apiData.id,
    title: apiData.title || 'Untitled',
    narrator_name: apiData.narrator_name || 'Unknown',
    location: apiData.location || 'Unknown',
    duration: apiData.duration_sec || 0,
    dominant_emotion: apiData.narrator_profile?.dominant_emotion || 'neutral',
    themes: apiData.themes?.map(t => typeof t === 'string' ? t : t.name) || [],
    excerpt: apiData.transcript?.text?.slice(0, 120) || 'No transcript available...',
    transcript: apiData.transcript?.text || 'Transcript not available.',
    emoji: emojis[emojiIndex],
    age: apiData.narrator_profile?.estimated_age || 0,
    gender: apiData.narrator_profile?.gender || 'Unknown',
    confidence: apiData.narrator_profile?.detection_confidence || 0,
    emotions: emotions.length > 0 ? emotions : [
      {label: "neutral", pct: 100, color: "#8a7b6a"}
    ]
  };
}

function hashCode(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return hash;
}

async function loadNarratives() {
  const cacheKey = 'narratives_cache';
  const cacheExpiry = 5 * 60 * 1000;
  
  const cached = localStorage.getItem(cacheKey);
  if (cached) {
    try {
      const { timestamp, data } = JSON.parse(cached);
      if (Date.now() - timestamp < cacheExpiry) {
        allNarratives = data;
        filteredNarratives = [...allNarratives];
        renderNarratives();
        updateStats();
        fetchFreshData();
        return;
      }
    } catch (e) {
      console.log('Cache parse error, fetching fresh');
    }
  }
  
  showLoading(true);
  
  try {
    const response = await API.narratives.list({ limit: 50 });
    
    if (response.narratives) {
      allNarratives = response.narratives.map(transformNarrative);
    } else if (Array.isArray(response)) {
      allNarratives = response.map(transformNarrative);
    } else {
      allNarratives = [];
    }
    
    localStorage.setItem(cacheKey, JSON.stringify({
      timestamp: Date.now(),
      data: allNarratives
    }));
    
    filteredNarratives = [...allNarratives];
    renderNarratives();
    updateStats();
  } catch (error) {
    console.error('Failed to load narratives:', error);
    showError(`Failed to load narratives: ${error.message}`);
  }
}

async function fetchFreshData() {
  try {
    const response = await API.narratives.list({ limit: 50 });
    if (response.narratives) {
      allNarratives = response.narratives.map(transformNarrative);
    } else if (Array.isArray(response)) {
      allNarratives = response.map(transformNarrative);
    }
    localStorage.setItem('narratives_cache', JSON.stringify({
      timestamp: Date.now(),
      data: allNarratives
    }));
    filteredNarratives = [...allNarratives];
    renderNarratives();
    updateStats();
  } catch (error) {
    console.error('Failed to refresh data:', error);
  }
}

async function updateStats() {
  try {
    const stats = await API.stats.get();
    
    document.getElementById('statNarratives').textContent = stats.total_narratives || allNarratives.length;
    
    const narrators = new Set(allNarratives.map(n => n.narrator_name)).size;
    document.getElementById('statNarrators').textContent = stats.unique_narrators || narrators;
    
    document.getElementById('archiveCount').textContent = `${filteredNarratives.length} stories`;
  } catch (error) {
    console.error('Failed to load stats:', error);
    document.getElementById('statNarratives').textContent = allNarratives.length;
    const narrators = new Set(allNarratives.map(n => n.narrator_name)).size;
    document.getElementById('statNarrators').textContent = narrators;
    document.getElementById('archiveCount').textContent = `${filteredNarratives.length} stories`;
  }
}

function renderNarratives() {
  const grid = document.getElementById('narrativeGrid');
  
  if (filteredNarratives.length === 0) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1;text-align:center;padding:3rem;">
        <div style="font-family:'DM Mono',monospace;color:var(--mid);font-size:0.8rem;margin-bottom:1rem;">
          ${Auth.isLoggedIn() ? "You haven't uploaded any narratives yet." : "No narratives found"}
        </div>
        <button class="btn-primary" onclick="document.getElementById('upload').scrollIntoView({behavior:'smooth'})">
          ${Auth.isLoggedIn() ? 'Record a Narrative' : 'Login to Record'}
        </button>
      </div>
    `;
    return;
  }
  
  grid.innerHTML = filteredNarratives.map(n => `
    <div class="narrative-card" onclick="openModal('${n.id}')" role="listitem" tabindex="0" 
         onkeypress="if(event.key==='Enter')openModal('${n.id}')" 
         aria-label="${n.title} by ${n.narrator_name}">
      <div class="card-thumb" style="background:linear-gradient(135deg,${getDarkColor(n.dominant_emotion)} 0%,#1a1008 100%)">
        <div class="thumb-face">${n.emoji}</div>
        <div class="card-duration">${formatDuration(n.duration)}</div>
        <div class="card-emotion-badge" style="background:${EMOTION_COLORS[n.dominant_emotion]}22;color:${EMOTION_COLORS[n.dominant_emotion]};border:1px solid ${EMOTION_COLORS[n.dominant_emotion]}44">
          ${n.dominant_emotion}
        </div>
      </div>
      <div class="card-body">
        <div class="card-title">${n.title}</div>
        <div class="card-narrator">${n.narrator_name} · ${n.location}</div>
        <div class="card-excerpt">"${n.excerpt}"</div>
        <div class="card-tags">
          ${n.themes.map(t => `<span class="tag">${t}</span>`).join('')}
        </div>
      </div>
    </div>
  `).join('');
  
  document.getElementById('archiveCount').textContent = `${filteredNarratives.length} stories`;
}

function getDarkColor(emotion) {
  const map = {joy:"#3a2005",sadness:"#0f2015",neutral:"#1a1a1a",anger:"#2a0a05",fear:"#1f0a1f",surprise:"#2a1020"};
  return map[emotion] || "#1a1010";
}

function formatDuration(sec) {
  const m = Math.floor(sec/60), s = Math.floor(sec%60);
  return `${m}:${String(s).padStart(2,'0')}`;
}

function debounceFilter() {
  if (filterTimeout) clearTimeout(filterTimeout);
  filterTimeout = setTimeout(filterNarratives, 300);
}

async function filterNarratives() {
  const q = document.getElementById('searchInput').value.toLowerCase();
  const emotion = document.getElementById('emotionFilter').value;
  const theme = document.getElementById('themeFilter').value;
  const sort = document.getElementById('sortSelect')?.value || 'newest';
  const myNarrativesOnly = document.getElementById('myNarrativesFilter')?.checked || false;
  
  updateFilterTags(q, emotion, theme);
  saveFiltersToURL(q, emotion, theme, sort);
  
  if (q.length > 2) {
    try {
      const response = await API.search.query(q, 'all');
      if (response.results) {
        filteredNarratives = response.results.map(transformNarrative);
      } else {
        filteredNarratives = [];
      }
    } catch (error) {
      console.error('Search failed:', error);
      filteredNarratives = allNarratives.filter(n => {
        const matchQ = !q || n.title.toLowerCase().includes(q) ||
                       n.narrator_name.toLowerCase().includes(q) ||
                       n.transcript.toLowerCase().includes(q);
        const matchE = !emotion || n.dominant_emotion === emotion;
        const matchT = !theme || n.themes.includes(theme);
        return matchQ && matchE && matchT;
      });
    }
  } else {
    filteredNarratives = allNarratives.filter(n => {
      const matchE = !emotion || n.dominant_emotion === emotion;
      const matchT = !theme || n.themes.includes(theme);
      return matchE && matchT;
    });
  }
  
  sortNarratives(sort);
  
  renderNarratives();
}

let narrativeCache = {};

async function openModal(id) {
  currentNarrativeId = id;
  let n = narrativeCache[id] || allNarratives.find(x => x.id === id);
  
  if (!n) {
    try {
      document.getElementById('narrativeModal').classList.add('open');
      document.getElementById('modalTitle').textContent = 'Loading...';
      document.getElementById('modalNarrator').textContent = '';
      
      const response = await API.narratives.get(id);
      n = transformNarrative(response);
      narrativeCache[id] = n;
    } catch (error) {
      console.error('Failed to load narrative:', error);
      document.getElementById('modalTitle').textContent = 'Error loading narrative';
      document.getElementById('modalNarrator').textContent = error.message;
      return;
    }
  }
  
  document.getElementById('modalTitle').textContent = n.title;
  document.getElementById('modalNarrator').textContent = `${n.narrator_name} · ${n.location}`;
  document.getElementById('modalDuration').textContent = formatDuration(n.duration);
  document.getElementById('modalTranscript').innerHTML = `<p>${n.transcript}</p>`;
  
  const bar = document.getElementById('modalEmotionBar');
  bar.innerHTML = n.emotions.map(e => `
    <div class="timeline-segment" style="width:${e.pct}%;background:${e.color}" title="${e.label}: ${e.pct}%">
      ${e.pct > 10 ? e.label : ''}
    </div>
  `).join('');
  
  document.getElementById('modalTags').innerHTML = n.themes.map(t =>
    `<span class="tag">${t}</span>`).join('');
  
  document.getElementById('modalProfile').innerHTML = `
    <div class="profile-stat">
      <span class="profile-stat-value">${n.age || '—'}</span>
      <span class="profile-stat-label">Est. Age</span>
    </div>
    <div class="profile-stat">
      <span class="profile-stat-value">${n.gender || '—'}</span>
      <span class="profile-stat-label">Gender</span>
    </div>
    <div class="profile-stat">
      <span class="profile-stat-value">${n.confidence ? (n.confidence*100).toFixed(0) + '%' : '—'}</span>
      <span class="profile-stat-label">Detection</span>
    </div>
    <div class="profile-stat">
      <span class="profile-stat-value">${n.dominant_emotion || '—'}</span>
      <span class="profile-stat-label">Dominant Emotion</span>
    </div>
  `;
  
  document.getElementById('narrativeModal').classList.add('open');
}

function closeModal(e) {
  if (e.target === document.getElementById('narrativeModal')) closeModalDirect();
}

function closeModalDirect() {
  document.getElementById('narrativeModal').classList.remove('open');
}

function switchTab(name) {
  document.querySelectorAll('.panel-tab').forEach((t,i) => {
    const tabs = ['emotion','vocal','profile','gradcam'];
    t.classList.toggle('active', tabs[i] === name);
  });
  document.querySelectorAll('.panel-content').forEach(c => c.classList.remove('active'));
  document.getElementById(`tab-${name}`).classList.add('active');
}

function renderEmotionTimeline() {
  const segments = [
    {label:"neutral",pct:20,color:"#8a7b6a"},
    {label:"joy",pct:28,color:"#c4833a"},
    {label:"sadness",pct:22,color:"#4a6741"},
    {label:"neutral",pct:10,color:"#8a7b6a"},
    {label:"surprise",pct:10,color:"#c4857a"},
    {label:"joy",pct:10,color:"#c4833a"},
  ];
  document.getElementById('emotionTimeline').innerHTML = segments.map(s =>
    `<div class="timeline-segment" style="width:${s.pct}%;background:${s.color}" title="${s.label}">${s.pct>10?s.label:''}</div>`
  ).join('');
  
  const vadSegs = [
    {active:true,pct:22,label:"voice"},
    {active:false,pct:4,label:"pause"},
    {active:true,pct:22,label:"voice"},
    {active:false,pct:3,label:"pause"},
    {active:true,pct:26,label:"voice"},
    {active:false,pct:4,label:"pause"},
    {active:true,pct:19,label:"voice"},
  ];
  document.getElementById('vadTimeline').innerHTML = vadSegs.map(s =>
    `<div class="timeline-segment" style="width:${s.pct}%;background:${s.active?'#4a6741':'rgba(0,0,0,0.1)'};color:${s.active?'white':'#8a7b6a'}">${s.active&&s.pct>10?'voice':''}</div>`
  ).join('');
  
  const congruence = [
    {pct:15,level:0.6},{pct:25,level:0.85},{pct:20,level:0.72},
    {pct:15,level:0.55},{pct:15,level:0.88},{pct:10,level:0.79}
  ];
  document.getElementById('congruenceTimeline').innerHTML = congruence.map(s => {
    const intensity = Math.round(s.level * 255);
    const color = `rgb(${intensity}, ${Math.round(intensity*0.5)}, 0)`;
    return `<div class="timeline-segment" style="width:${s.pct}%;background:${color}" title="${Math.round(s.level*100)}% congruence">${s.pct>10?Math.round(s.level*100)+'%':''}</div>`;
  }).join('');
}

function renderEmotionChart() {
  const emotions = [
    {label:"Joy",pct:38,color:"#c4833a"},
    {label:"Neutral",pct:29,color:"#8a7b6a"},
    {label:"Sadness",pct:15,color:"#4a6741"},
    {label:"Surprise",pct:11,color:"#c4857a"},
    {label:"Anger",pct:4,color:"#b54e2a"},
    {label:"Fear",pct:2,color:"#9b5e7a"},
    {label:"Disgust",pct:1,color:"#6b7b4a"},
  ];
  
  const chart = document.getElementById('emotionChart');
  chart.innerHTML = emotions.map((e, i) => `
    <div class="emotion-col">
      <div class="emotion-column-bar" style="background:${e.color};height:${e.pct*2}px;"></div>
      <div style="font-family:'DM Mono',monospace;font-size:0.55rem;text-transform:uppercase;letter-spacing:0.04em;color:var(--mid);text-align:center;margin-top:0.25rem">${e.label}</div>
      <div style="font-family:'DM Mono',monospace;font-size:0.6rem;color:${e.color};text-align:center">${e.pct}%</div>
    </div>
  `).join('');
}

function renderMFCC() {
  const mfcc = [-312,87,-42,24,-15,9,-4,2,-2,1,-1,0,-0];
  const max = 312;
  const el = document.getElementById('mfccViz');
  if (!el) return;
  el.innerHTML = mfcc.map((v, i) => {
    const h = Math.abs(v) / max * 38;
    const color = v > 0 ? '#c4833a' : '#4a6741';
    return `<div style="flex:1;height:${h}px;background:${color};border-radius:1px;opacity:0.8" title="MFCC ${i+1}: ${v.toFixed(1)}"></div>`;
  }).join('');
}

function renderHeroWave() {
  const el = document.getElementById('heroWave');
  if (!el) return;
  const heights = [0.3,0.6,0.9,0.5,0.8,1,0.7,0.4,0.9,0.6,0.3,0.8,0.5,0.7,0.4,0.9,0.6,0.3,0.7,1,0.5,0.8,0.4,0.6];
  el.innerHTML = heights.map((h,i) => `
    <div class="waveform-bar" style="height:${h*100}%;animation-delay:${i*0.05}s"></div>
  `).join('');
}

function triggerUpload() {
  document.getElementById('videoInput').click();
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  const maxSize = 2 * 1024 * 1024 * 1024;
  if (file.size > maxSize) {
    showUploadError('File too large. Maximum size is 2GB.');
    return;
  }
  
  const validTypes = ['video/mp4', 'video/quicktime', 'video/webm', 'video/x-msvideo', 'video/x-matroska'];
  if (!validTypes.includes(file.type)) {
    showUploadError('Invalid file type. Please upload MP4, MOV, WebM, AVI, or MKV.');
    return;
  }
  
  const el = document.getElementById('selectedFile');
  el.innerHTML = `✓ ${file.name} (${formatFileSize(file.size)}) <button class="remove-file" onclick="removeFile(event)">×</button>`;
  el.classList.add('show');
  
  document.getElementById('dropzone').classList.add('has-file');
  document.getElementById('nextStep1').disabled = false;
  clearUploadError();
}

function removeFile(e) {
  e.stopPropagation();
  document.getElementById('videoInput').value = '';
  document.getElementById('selectedFile').classList.remove('show');
  document.getElementById('selectedFile').innerHTML = '';
  document.getElementById('dropzone').classList.remove('has-file');
  document.getElementById('nextStep1').disabled = true;
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}

function showUploadError(message) {
  const el = document.getElementById('uploadError');
  el.textContent = message;
  el.classList.add('show');
}

function clearUploadError() {
  const el = document.getElementById('uploadError');
  el.classList.remove('show');
}

let currentStep = 1;

function goToStep(step) {
  if (step === 2 && !document.getElementById('videoInput').files[0]) {
    showUploadError('Please select a video file first.');
    return;
  }
  
  document.querySelectorAll('.upload-step-content').forEach(el => el.style.display = 'none');
  document.getElementById(`step${step}Content`).style.display = 'block';
  
  document.querySelectorAll('.upload-step').forEach(el => {
    const stepNum = parseInt(el.dataset.step);
    el.classList.remove('active', 'completed');
    if (stepNum < step) el.classList.add('completed');
    if (stepNum === step) el.classList.add('active');
  });
  
  currentStep = step;
}

function validateForm() {
  const title = document.getElementById('fTitle').value.trim();
  const titleError = document.getElementById('fTitleError');
  const titleInput = document.getElementById('fTitle');
  
  if (!title) {
    titleError.textContent = 'Title is required';
    titleError.style.display = 'block';
    titleInput.classList.add('error');
    return false;
  }
  
  titleError.style.display = 'none';
  titleInput.classList.remove('error');
  return true;
}

async function submitNarrative() {
  const isAuthenticated = await Auth.requireAuth(true);
  if (!isAuthenticated) {
    return;
  }
  
  if (!validateForm()) {
    return;
  }
  
  const videoFile = document.getElementById('videoInput').files[0];
  const title = document.getElementById('fTitle').value || "Untitled Narrative";
  const narrator = document.getElementById('fNarrator').value || "Anonymous";
  const location = document.getElementById('fLocation').value || "";
  const themes = document.getElementById('fThemes').value || "";
  const transcript = document.getElementById('fTranscript').value || "";
  
  if (!videoFile) {
    Auth.showNotification('Please select a video file to upload.', 'error');
    goToStep(1);
    return;
  }
  
  goToStep(3);
  
  const formData = new FormData();
  formData.append('video', videoFile);
  formData.append('title', title);
  formData.append('narrator_name', narrator);
  formData.append('location', location);
  formData.append('themes', themes);
  formData.append('transcript', transcript);
  
  try {
    updateProcessingDisplay('Uploading video...', 'Preparing your file for analysis...', 10);
    
    const response = await API.narratives.upload(formData);
    const narrativeId = response.narrative_id;
    
    await pollProcessingStatusWithUI(narrativeId);
    
    await loadNarratives();
    
    updateProcessingDisplay('Analysis complete!', 'Your narrative has been processed and archived.', 100);
    
    setTimeout(() => {
      document.getElementById('archive').scrollIntoView({behavior:'smooth'});
      resetForm();
      goToStep(1);
    }, 2000);
    
  } catch (error) {
    console.error('Upload failed:', error);
    updateProcessingDisplay('Upload failed', error.message, 0, true);
  }
}

function updateProcessingDisplay(stage, desc, progress, isError = false) {
  document.getElementById('processingStage').textContent = stage;
  document.getElementById('processingStage').style.color = isError ? 'var(--terracotta)' : 'var(--ink)';
  document.getElementById('processingDesc').textContent = desc;
  document.getElementById('stepProgressFill').style.width = `${progress}%`;
  document.getElementById('stepProgressFill').style.background = isError ? 'var(--terracotta)' : '';
  document.getElementById('progressPct').textContent = `${progress}%`;
}

async function pollProcessingStatusWithUI(narrativeId) {
  const stages = {
    'queued': { text: 'Queued for processing...', desc: 'Waiting in queue', pct: 15 },
    'extracting_audio': { text: 'Extracting audio...', desc: 'Isolating audio track from video', pct: 25 },
    'transcribing': { text: 'Transcribing...', desc: 'Converting speech to text with Whisper ASR', pct: 40 },
    'analyzing_facial': { text: 'Analyzing facial features...', desc: 'Detecting emotions with DeepFace', pct: 55 },
    'analyzing_audio': { text: 'Analyzing vocal patterns...', desc: 'Extracting audio features with Librosa', pct: 70 },
    'fusing': { text: 'Running multimodal fusion...', desc: 'Combining all analysis results', pct: 85 },
    'complete': { text: 'Analysis complete!', desc: 'All processing finished', pct: 100 },
    'failed': { text: 'Processing failed', desc: 'An error occurred during processing', pct: 0 }
  };
  
  let attempts = 0;
  const maxAttempts = 300;
  
  while (attempts < maxAttempts) {
    attempts++;
    
    try {
      const status = await API.narratives.status(narrativeId);
      const stage = stages[status.status] || stages[status.processing_stage] || { text: 'Processing...', desc: 'Please wait', pct: 50 };
      
      const progress = status.progress || stage.pct;
      updateProcessingDisplay(stage.text, stage.desc, progress);
      
      if (status.status === 'complete') {
        return true;
      }
      
      if (status.status === 'failed' || status.processing_error) {
        throw new Error(status.processing_error || 'Processing failed');
      }
      
      await new Promise(r => setTimeout(r, 2000));
    } catch (error) {
      if (error.status === 404) {
        await new Promise(r => setTimeout(r, 2000));
        continue;
      }
      throw error;
    }
  }
  
  throw new Error('Processing timed out');
}

let lastFailedNarrativeId = null;

async function retryUpload(narrativeId) {
  if (!narrativeId) {
    Auth.showNotification('Cannot retry: narrative ID not available', 'error');
    return;
  }
  
  const banner = document.getElementById('processingBanner');
  banner.classList.add('show');
  banner.style.display = 'flex';
  document.getElementById('processingText').textContent = 'Retrying processing...';
  document.getElementById('progressFill').style.width = '5%';
  document.getElementById('progressFill').style.backgroundColor = '';
  
  try {
    const response = await API.narratives.upload(formData);
    const narrativeId = response.narrative_id;
    const identifiedNarrator = response.identified_narrator;
    
    if (identifiedNarrator) {
      const narratorInfo = identifiedNarrator.is_new ? 
        ` (New narrator: ${identifiedNarrator.name || 'Unknown'})` :
        ` (Matched: ${identifiedNarrator.name || 'Unknown'} - ${(identifiedNarrator.confidence * 100).toFixed(0)}% confidence)`;
      Auth.showNotification(narratorInfo, 'info');
    }
    
    await pollProcessingStatus(narrativeId);
    await loadNarratives();
    
    document.getElementById('processingText').textContent = '✓ Analysis complete!';
    document.getElementById('progressFill').style.width = '100%';
    
    setTimeout(() => {
      banner.classList.remove('show');
      banner.style.display = 'none';
      document.getElementById('progressFill').style.width = '0%';
      document.getElementById('archive').scrollIntoView({behavior:'smooth'});
      resetForm();
    }, 1500);
  } catch (error) {
    console.error('Retry failed:', error);
    Auth.showNotification(`Retry failed: ${error.message}`, 'error');
    banner.classList.remove('show');
    banner.style.display = 'none';
  }
}

async function pollProcessingStatus(narrativeId) {
  const stages = {
    'queued': { text: 'Queued for processing...', pct: 15 },
    'extracting_audio': { text: 'Extracting audio from video...', pct: 25 },
    'transcribing': { text: 'Transcribing with Whisper ASR...', pct: 40 },
    'analyzing_facial': { text: 'Analyzing facial features with DeepFace...', pct: 55 },
    'analyzing_audio': { text: 'Analyzing vocal patterns with Librosa...', pct: 70 },
    'fusing': { text: 'Running multimodal fusion...', pct: 85 },
    'complete': { text: '✓ Analysis complete!', pct: 100 },
    'failed': { text: 'Processing failed', pct: 0 }
  };
  
  let attempts = 0;
  const maxAttempts = 300;
  
  while (attempts < maxAttempts) {
    attempts++;
    
    try {
      const status = await API.narratives.status(narrativeId);
      const stage = stages[status.status] || stages[status.processing_stage] || { text: 'Processing...', pct: 50 };
      
      document.getElementById('processingText').textContent = stage.text;
      const progress = status.progress || stage.pct;
      document.getElementById('progressFill').style.width = `${progress}%`;
      
      if (status.narrator_match) {
        const narratorInfo = document.createElement('div');
        narratorInfo.style.cssText = 'margin-left:0.5rem;padding:0.25rem 0.5rem;background:rgba(196,131,58,0.1);border-radius:4px;font-family:DM Mono,monospace;font-size:0.7rem;color:var(--amber);';
        narratorInfo.innerHTML = `👤 Narrator: ${status.narrator_match.name} (${Math.round(status.narrator_match.confidence * 100)}% match)`;
        document.getElementById('processingText').appendChild(narratorInfo);
      }
      
      if (status.status === 'complete') {
        return true;
      }
      
      if (status.status === 'failed' || status.processing_error) {
        throw new Error(status.processing_error || 'Processing failed');
      }
      
      await new Promise(r => setTimeout(r, 2000));
    } catch (error) {
      if (error.status === 404) {
        await new Promise(r => setTimeout(r, 2000));
        continue;
      }
      throw error;
    }
  }
  
  throw new Error('Processing timed out');
}

function resetForm() {
  ['fTitle','fNarrator','fLocation','fThemes','fTranscript'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  
  const selectedFile = document.getElementById('selectedFile');
  if (selectedFile) {
    selectedFile.classList.remove('show');
    selectedFile.innerHTML = '';
  }
  
  const videoInput = document.getElementById('videoInput');
  if (videoInput) videoInput.value = '';
  
  const dropzone = document.getElementById('dropzone');
  if (dropzone) dropzone.classList.remove('has-file');
  
  const nextBtn = document.getElementById('nextStep1');
  if (nextBtn) nextBtn.disabled = true;
  
  clearUploadError();
}

document.addEventListener('DOMContentLoaded', async () => {
  await Auth.fetchCurrentUser();
  updateLoggedInUI();
  loadNarratives();
  renderEmotionTimeline();
  renderEmotionChart();
  renderHeroWave();
  setTimeout(renderMFCC, 300);
  setupRateLimitIndicator();
  setupOfflineIndicator();
  loadFiltersFromURL();
  checkHashNavigation();
});

function updateLoggedInUI() {
  const loggedInFilters = document.getElementById('loggedInFilters');
  if (loggedInFilters) {
    loggedInFilters.style.display = Auth.isLoggedIn() ? 'block' : 'none';
  }
  
  const adminLinks = document.querySelectorAll('.admin-only');
  adminLinks.forEach(link => {
    link.style.display = Auth.isAdmin() ? '' : 'none';
  });
  
  if (typeof Auth.updateAuthGatedElements === 'function') {
    Auth.updateAuthGatedElements();
  }
}

function setupOfflineIndicator() {
  const indicator = document.createElement('div');
  indicator.id = 'offline-indicator';
  indicator.className = 'offline-indicator';
  indicator.innerHTML = `
    <span class="offline-icon">⚠</span>
    <span class="offline-text">You are offline</span>
  `;
  document.body.appendChild(indicator);
  
  window.addEventListener('online', () => {
    indicator.classList.remove('show');
    Auth.showNotification('Back online!', 'success');
  });
  
  window.addEventListener('offline', () => {
    indicator.classList.add('show');
  });
}

function checkHashNavigation() {
  const hash = window.location.hash;
  if (hash.startsWith('#narrative-')) {
    const id = hash.replace('#narrative-', '');
    setTimeout(() => openModal(id), 500);
  }
}

function setupRateLimitIndicator() {
  let container = document.getElementById('rate-limit-indicator');
  if (!container) {
    container = document.createElement('div');
    container.id = 'rate-limit-indicator';
    container.className = 'rate-limit-indicator';
    container.innerHTML = `
      <span class="rate-icon">⏱</span>
      <span class="rate-text">100 remaining</span>
    `;
    document.body.appendChild(container);
  }
  
  window.addEventListener('api:ratelimited', (e) => {
    const resetTime = e.detail?.resetTime;
    const waitSeconds = resetTime ? Math.ceil((resetTime * 1000 - Date.now()) / 1000) : 60;
    
    container.classList.add('warning');
    container.querySelector('.rate-text').textContent = `Rate limited - wait ${waitSeconds}s`;
    
    Auth.showNotification(`Rate limited. Please wait ${waitSeconds} seconds.`, 'error');
    
    setTimeout(() => {
      container.classList.remove('warning');
      updateRateLimitDisplay(100);
    }, waitSeconds * 1000);
  });
}

function updateRateLimitDisplay(remaining) {
  const container = document.getElementById('rate-limit-indicator');
  if (container) {
    container.querySelector('.rate-text').textContent = `${remaining} remaining`;
    
    if (remaining < 20) {
      container.classList.add('warning');
    } else {
      container.classList.remove('warning');
    }
  }
}

function sortNarratives(sortBy) {
  switch (sortBy) {
    case 'newest':
      filteredNarratives.sort((a, b) => (b.created_at || 0) - (a.created_at || 0));
      break;
    case 'oldest':
      filteredNarratives.sort((a, b) => (a.created_at || 0) - (b.created_at || 0));
      break;
    case 'duration_desc':
      filteredNarratives.sort((a, b) => b.duration - a.duration);
      break;
    case 'duration_asc':
      filteredNarratives.sort((a, b) => a.duration - b.duration);
      break;
    case 'title':
      filteredNarratives.sort((a, b) => a.title.localeCompare(b.title));
      break;
  }
}

function updateFilterTags(q, emotion, theme) {
  const container = document.getElementById('activeFilters');
  if (!container) return;
  
  const tags = [];
  if (q) tags.push({ type: 'search', label: `"${q}"`, value: q });
  if (emotion) tags.push({ type: 'emotion', label: emotion, value: emotion });
  if (theme) tags.push({ type: 'theme', label: theme, value: theme });
  
  if (tags.length === 0) {
    container.innerHTML = '';
    return;
  }
  
  container.innerHTML = `
    <div class="filter-tags">
      ${tags.map(t => `
        <button class="filter-tag" onclick="clearFilter('${t.type}')">
          ${t.label}
          <span class="filter-tag-remove">×</span>
        </button>
      `).join('')}
      <button class="filter-clear-all" onclick="clearAllFilters()">Clear all</button>
    </div>
  `;
}

function clearFilter(type) {
  switch (type) {
    case 'search':
      document.getElementById('searchInput').value = '';
      break;
    case 'emotion':
      document.getElementById('emotionFilter').value = '';
      break;
    case 'theme':
      document.getElementById('themeFilter').value = '';
      break;
  }
  filterNarratives();
}

function clearAllFilters() {
  document.getElementById('searchInput').value = '';
  document.getElementById('emotionFilter').value = '';
  document.getElementById('themeFilter').value = '';
  filterNarratives();
}

function saveFiltersToURL(q, emotion, theme, sort) {
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (emotion) params.set('emotion', emotion);
  if (theme) params.set('theme', theme);
  if (sort && sort !== 'newest') params.set('sort', sort);
  
  const newURL = params.toString() 
    ? `${window.location.pathname}?${params.toString()}`
    : window.location.pathname;
  
  window.history.replaceState({}, '', newURL);
}

function loadFiltersFromURL() {
  const params = new URLSearchParams(window.location.search);
  
  if (params.has('q')) {
    document.getElementById('searchInput').value = params.get('q');
  }
  if (params.has('emotion')) {
    document.getElementById('emotionFilter').value = params.get('emotion');
  }
  if (params.has('theme')) {
    document.getElementById('themeFilter').value = params.get('theme');
  }
  if (params.has('sort')) {
    document.getElementById('sortSelect').value = params.get('sort');
  }
  
  if (params.toString()) {
    filterNarratives();
  }
}

function shareNarrative() {
  const url = `${window.location.origin}${window.location.pathname}#narrative-${currentNarrativeId}`;
  
  if (navigator.share) {
    navigator.share({
      title: document.getElementById('modalTitle').textContent,
      text: `Oral narrative by ${document.getElementById('modalNarrator').textContent}`,
      url: url
    }).catch(() => {});
  } else if (navigator.clipboard) {
    navigator.clipboard.writeText(url).then(() => {
      Auth.showNotification('Link copied to clipboard!', 'success');
    });
  }
}

function toggleMobileMenu() {
  const nav = document.querySelector('nav');
  const toggle = document.querySelector('.mobile-menu-toggle');
  const isOpen = nav.classList.toggle('mobile-open');
  toggle.classList.toggle('active', isOpen);
  toggle.setAttribute('aria-expanded', isOpen);
}

function closeMobileMenu() {
  const nav = document.querySelector('nav');
  const toggle = document.querySelector('.mobile-menu-toggle');
  nav.classList.remove('mobile-open');
  toggle.classList.remove('active');
  toggle.setAttribute('aria-expanded', 'false');
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeMobileMenu();
    closeModalDirect();
  }
});

setInterval(() => {
  const info = API.getRateLimitInfo();
  if (info.remaining !== null) {
    updateRateLimitDisplay(info.remaining);
  }
}, 5000);
