const EMOTION_COLORS = {
  joy: "#c4833a", sadness: "#4a6741", neutral: "#8a7b6a",
  anger: "#b54e2a", fear: "#9b5e7a", surprise: "#c4857a", disgust: "#6b7b4a"
};

let allNarratives = [];
let filteredNarratives = [];
let allNarrators = [];
let allThemes = [];
let allLocations = [];

async function initAnalysisPage() {
  await Auth.fetchCurrentUser();
  updateLoggedInUI();
  await loadData();
  populateFilters();
  renderOverview();
}

function updateLoggedInUI() {
  const adminLinks = document.querySelectorAll('.admin-only');
  adminLinks.forEach(link => {
    link.style.display = Auth.isAdmin() ? '' : 'none';
  });
}

async function loadData() {
  try {
    const response = await API.narratives.list({ limit: 500 });
    allNarratives = response.narratives || response || [];
    allNarratives = allNarratives.map(transformNarrative);
    filteredNarratives = [...allNarratives];
    
    extractFilterOptions();
    updateStats();
  } catch (error) {
    console.error('Failed to load data:', error);
    Auth.showNotification('Failed to load analysis data', 'error');
  }
}

function transformNarrative(apiData) {
  const emotionDist = apiData.narrator_profile?.emotion_distribution || {};
  const emotions = Object.entries(emotionDist).map(([label, value]) => ({
    label,
    pct: Math.round(value * 100),
    color: EMOTION_COLORS[label] || "#8a7b6a"
  })).sort((a, b) => b.pct - a.pct).slice(0, 4);
  
  return {
    id: apiData.id,
    title: apiData.title || 'Untitled',
    narrator_name: apiData.narrator_name || 'Unknown',
    location: apiData.location || 'Unknown',
    duration: apiData.duration_sec || 0,
    dominant_emotion: apiData.narrator_profile?.dominant_emotion || 'neutral',
    themes: apiData.themes?.map(t => typeof t === 'string' ? t : t.name) || [],
    created_at: apiData.created_at ? new Date(apiData.created_at) : new Date(),
    status: apiData.status || 'complete',
    emotions: emotions.length > 0 ? emotions : [{ label: "neutral", pct: 100, color: "#8a7b6a" }],
    age: apiData.narrator_profile?.estimated_age,
    gender: apiData.narrator_profile?.gender
  };
}

function extractFilterOptions() {
  const narratorSet = new Set();
  const themeSet = new Set();
  const locationSet = new Set();
  
  allNarratives.forEach(n => {
    if (n.narrator_name) narratorSet.add(n.narrator_name);
    if (n.location) locationSet.add(n.location);
    n.themes.forEach(t => themeSet.add(t));
  });
  
  allNarrators = Array.from(narratorSet).sort();
  allThemes = Array.from(themeSet).sort();
  allLocations = Array.from(locationSet).sort();
}

function populateFilters() {
  const narratorSelect = document.getElementById('filterNarrator');
  const themeSelect = document.getElementById('filterTheme');
  const locationSelect = document.getElementById('filterLocation');
  
  allNarrators.forEach(name => {
    narratorSelect.innerHTML += `<option value="${name}">${name}</option>`;
  });
  
  allThemes.forEach(theme => {
    themeSelect.innerHTML += `<option value="${theme}">${theme}</option>`;
  });
  
  allLocations.forEach(loc => {
    locationSelect.innerHTML += `<option value="${loc}">${loc}</option>`;
  });
}

function applyAnalysisFilters() {
  const narrator = document.getElementById('filterNarrator').value;
  const emotion = document.getElementById('filterEmotion').value;
  const theme = document.getElementById('filterTheme').value;
  const location = document.getElementById('filterLocation').value;
  const dateFrom = document.getElementById('filterDateFrom').value;
  const dateTo = document.getElementById('filterDateTo').value;
  const durationMin = parseInt(document.getElementById('durationMin').value);
  const durationMax = parseInt(document.getElementById('durationMax').value);
  
  filteredNarratives = allNarratives.filter(n => {
    if (narrator && n.narrator_name !== narrator) return false;
    if (emotion && n.dominant_emotion !== emotion) return false;
    if (theme && !n.themes.includes(theme)) return false;
    if (location && n.location !== location) return false;
    if (dateFrom && n.created_at < new Date(dateFrom)) return false;
    if (dateTo && n.created_at > new Date(dateTo + 'T23:59:59')) return false;
    if (n.duration < durationMin || n.duration > durationMax) return false;
    return true;
  });
  
  updateStats();
  renderCurrentTab();
}

function updateDurationLabel() {
  const min = parseInt(document.getElementById('durationMin').value);
  const max = parseInt(document.getElementById('durationMax').value);
  const label = document.getElementById('durationLabel');
  
  const formatSec = (s) => s >= 60 ? `${Math.floor(s/60)}min` : `${s}s`;
  label.textContent = `${formatSec(min)} — ${max >= 600 ? '10min+' : formatSec(max)}`;
  
  applyAnalysisFilters();
}

function clearAnalysisFilters() {
  document.getElementById('filterNarrator').value = '';
  document.getElementById('filterEmotion').value = '';
  document.getElementById('filterTheme').value = '';
  document.getElementById('filterLocation').value = '';
  document.getElementById('filterDateFrom').value = '';
  document.getElementById('filterDateTo').value = '';
  document.getElementById('durationMin').value = 0;
  document.getElementById('durationMax').value = 600;
  updateDurationLabel();
  
  filteredNarratives = [...allNarratives];
  updateStats();
  renderCurrentTab();
}

function updateStats() {
  document.getElementById('statTotal').textContent = filteredNarratives.length;
  
  const uniqueNarrators = new Set(filteredNarratives.map(n => n.narrator_name)).size;
  document.getElementById('statNarrators').textContent = uniqueNarrators;
  
  const avgDuration = filteredNarratives.length > 0
    ? Math.round(filteredNarratives.reduce((sum, n) => sum + n.duration, 0) / filteredNarratives.length)
    : 0;
  document.getElementById('statAvgDuration').textContent = formatDuration(avgDuration);
  
  const totalDuration = filteredNarratives.reduce((sum, n) => sum + n.duration, 0);
  const hours = Math.floor(totalDuration / 3600);
  const mins = Math.floor((totalDuration % 3600) / 60);
  document.getElementById('statTotalDuration').textContent = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
}

function formatDuration(sec) {
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

function switchAnalysisTab(tabName) {
  document.querySelectorAll('.analysis-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.tab === tabName);
  });
  
  document.querySelectorAll('.analysis-tab-content').forEach(content => {
    content.classList.toggle('active', content.id === `tab-${tabName}`);
  });
  
  renderCurrentTab();
}

function renderCurrentTab() {
  const activeTab = document.querySelector('.analysis-tab.active');
  if (!activeTab) return;
  
  switch (activeTab.dataset.tab) {
    case 'overview':
      renderOverview();
      break;
    case 'emotions':
      renderEmotionsTab();
      break;
    case 'narrators':
      renderNarratorsTab();
      break;
    case 'timeline':
      renderTimelineTab();
      break;
  }
}

function renderOverview() {
  renderEmotionDistribution();
  renderThemesChart();
  renderTimelineChart();
}

function renderEmotionDistribution() {
  const container = document.getElementById('emotionDistChart');
  if (!container) return;
  
  const emotionCounts = {};
  Object.keys(EMOTION_COLORS).forEach(e => emotionCounts[e] = 0);
  
  filteredNarratives.forEach(n => {
    if (emotionCounts.hasOwnProperty(n.dominant_emotion)) {
      emotionCounts[n.dominant_emotion]++;
    }
  });
  
  const total = filteredNarratives.length || 1;
  const maxCount = Math.max(...Object.values(emotionCounts), 1);
  
  container.innerHTML = `
    <div class="bar-chart">
      ${Object.entries(emotionCounts).map(([emotion, count]) => `
        <div class="bar-row">
          <div class="bar-label">${emotion}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:${(count/maxCount)*100}%;background:${EMOTION_COLORS[emotion]}"></div>
          </div>
          <div class="bar-value">${count} (${Math.round(count/total*100)}%)</div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderThemesChart() {
  const container = document.getElementById('themesChart');
  if (!container) return;
  
  const themeCounts = {};
  filteredNarratives.forEach(n => {
    n.themes.forEach(t => {
      themeCounts[t] = (themeCounts[t] || 0) + 1;
    });
  });
  
  const sorted = Object.entries(themeCounts).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const maxCount = sorted[0]?.[1] || 1;
  
  if (sorted.length === 0) {
    container.innerHTML = '<div class="empty-state">No themes found</div>';
    return;
  }
  
  container.innerHTML = `
    <div class="bar-chart">
      ${sorted.map(([theme, count]) => `
        <div class="bar-row">
          <div class="bar-label">${theme}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:${(count/maxCount)*100}%"></div>
          </div>
          <div class="bar-value">${count}</div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderTimelineChart() {
  const container = document.getElementById('timelineChart');
  if (!container) return;
  
  const monthCounts = {};
  filteredNarratives.forEach(n => {
    const monthKey = n.created_at.toISOString().slice(0, 7);
    monthCounts[monthKey] = (monthCounts[monthKey] || 0) + 1;
  });
  
  const sorted = Object.entries(monthCounts).sort((a, b) => a[0].localeCompare(b[0]));
  const maxCount = Math.max(...sorted.map(s => s[1]), 1);
  
  if (sorted.length === 0) {
    container.innerHTML = '<div class="empty-state">No data available</div>';
    return;
  }
  
  container.innerHTML = `
    <div class="timeline-bars">
      ${sorted.map(([month, count]) => `
        <div class="timeline-bar-col">
          <div class="timeline-bar-fill" style="height:${(count/maxCount)*100}%"></div>
          <div class="timeline-bar-label">${month.slice(5)}</div>
          <div class="timeline-bar-value">${count}</div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderEmotionsTab() {
  renderEmotionBars();
  renderEmotionHeatmap();
}

function renderEmotionBars() {
  const container = document.getElementById('emotionBars');
  if (!container) return;
  
  const avgEmotions = {};
  Object.keys(EMOTION_COLORS).forEach(e => avgEmotions[e] = 0);
  
  filteredNarratives.forEach(n => {
    n.emotions.forEach(e => {
      if (avgEmotions.hasOwnProperty(e.label)) {
        avgEmotions[e.label] += e.pct;
      }
    });
  });
  
  const count = filteredNarratives.length || 1;
  Object.keys(avgEmotions).forEach(e => {
    avgEmotions[e] = Math.round(avgEmotions[e] / count);
  });
  
  const maxAvg = Math.max(...Object.values(avgEmotions), 1);
  
  container.innerHTML = `
    <div class="bar-chart">
      ${Object.entries(avgEmotions).map(([emotion, avg]) => `
        <div class="bar-row">
          <div class="bar-label">${emotion}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:${avg}%;background:${EMOTION_COLORS[emotion]}"></div>
          </div>
          <div class="bar-value">${avg}%</div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderEmotionHeatmap() {
  const container = document.getElementById('emotionHeatmap');
  if (!container) return;
  
  const narratorEmotions = {};
  filteredNarratives.forEach(n => {
    if (!narratorEmotions[n.narrator_name]) {
      narratorEmotions[n.narrator_name] = { total: 0, emotions: {} };
      Object.keys(EMOTION_COLORS).forEach(e => narratorEmotions[n.narrator_name].emotions[e] = 0);
    }
    narratorEmotions[n.narrator_name].total++;
    narratorEmotions[n.narrator_name].emotions[n.dominant_emotion]++;
  });
  
  const narrators = Object.entries(narratorEmotions)
    .sort((a, b) => b[1].total - a[1].total)
    .slice(0, 10);
  
  if (narrators.length === 0) {
    container.innerHTML = '<div class="empty-state">No narrator data</div>';
    return;
  }
  
  container.innerHTML = `
    <div class="heatmap">
      <div class="heatmap-row heatmap-header">
        <div class="heatmap-cell header">Narrator</div>
        ${Object.keys(EMOTION_COLORS).map(e => `<div class="heatmap-cell header">${e.slice(0,3)}</div>`).join('')}
      </div>
      ${narrators.map(([name, data]) => `
        <div class="heatmap-row">
          <div class="heatmap-cell label">${name.slice(0, 15)}</div>
          ${Object.entries(data.emotions).map(([emotion, count]) => {
            const intensity = data.total > 0 ? count / data.total : 0;
            return `<div class="heatmap-cell" style="background:${EMOTION_COLORS[emotion]};opacity:${0.2 + intensity * 0.8}" title="${emotion}: ${count}">${count}</div>`;
          }).join('')}
        </div>
      `).join('')}
    </div>
  `;
}

function renderNarratorsTab() {
  renderNarratorList();
  renderLocationChart();
}

function renderNarratorList() {
  const container = document.getElementById('narratorList');
  if (!container) return;
  
  const narratorStats = {};
  filteredNarratives.forEach(n => {
    if (!narratorStats[n.narrator_name]) {
      narratorStats[n.narrator_name] = { count: 0, totalDuration: 0, emotions: {}, locations: new Set() };
    }
    narratorStats[n.narrator_name].count++;
    narratorStats[n.narrator_name].totalDuration += n.duration;
    narratorStats[n.narrator_name].emotions[n.dominant_emotion] = (narratorStats[n.narrator_name].emotions[n.dominant_emotion] || 0) + 1;
    narratorStats[n.narrator_name].locations.add(n.location);
  });
  
  const sorted = Object.entries(narratorStats).sort((a, b) => b[1].count - a[1].count);
  
  if (sorted.length === 0) {
    container.innerHTML = '<div class="empty-state">No narrators found</div>';
    return;
  }
  
  container.innerHTML = `
    <div class="narrator-stats-list">
      ${sorted.map(([name, stats]) => {
        const topEmotion = Object.entries(stats.emotions).sort((a, b) => b[1] - a[1])[0];
        return `
          <div class="narrator-stat-card">
            <div class="narrator-stat-header">
              <span class="narrator-stat-name">${name}</span>
              <span class="narrator-stat-count">${stats.count} narratives</span>
            </div>
            <div class="narrator-stat-details">
              <span>Total: ${formatDuration(stats.totalDuration)}</span>
              <span>Locations: ${stats.locations.size}</span>
              ${topEmotion ? `<span style="color:${EMOTION_COLORS[topEmotion[0]]}">Top: ${topEmotion[0]}</span>` : ''}
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

function renderLocationChart() {
  const container = document.getElementById('locationChart');
  if (!container) return;
  
  const locationCounts = {};
  filteredNarratives.forEach(n => {
    locationCounts[n.location] = (locationCounts[n.location] || 0) + 1;
  });
  
  const sorted = Object.entries(locationCounts).sort((a, b) => b[1] - a[1]).slice(0, 10);
  const maxCount = sorted[0]?.[1] || 1;
  
  if (sorted.length === 0) {
    container.innerHTML = '<div class="empty-state">No location data</div>';
    return;
  }
  
  container.innerHTML = `
    <div class="bar-chart">
      ${sorted.map(([location, count]) => `
        <div class="bar-row">
          <div class="bar-label">${location}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:${(count/maxCount)*100}%"></div>
          </div>
          <div class="bar-value">${count}</div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderTimelineTab() {
  renderRecordingTimeline();
  renderStatusBreakdown();
}

function renderRecordingTimeline() {
  const container = document.getElementById('recordingTimeline');
  if (!container) return;
  
  const dayCounts = {};
  filteredNarratives.forEach(n => {
    const dayKey = n.created_at.toISOString().slice(0, 10);
    dayCounts[dayKey] = (dayCounts[dayKey] || 0) + 1;
  });
  
  const sorted = Object.entries(dayCounts).sort((a, b) => a[0].localeCompare(b[0]));
  
  if (sorted.length === 0) {
    container.innerHTML = '<div class="empty-state">No recordings yet</div>';
    return;
  }
  
  const maxCount = Math.max(...sorted.map(s => s[1]), 1);
  
  container.innerHTML = `
    <div class="timeline-streak">
      ${sorted.map(([day, count]) => `
        <div class="timeline-day" style="background-color:rgba(196,131,58,${0.1 + (count/maxCount)*0.9})" title="${day}: ${count} narratives">
          <span class="day-count">${count}</span>
        </div>
      `).join('')}
    </div>
  `;
}

function renderStatusBreakdown() {
  const container = document.getElementById('statusBreakdown');
  if (!container) return;
  
  const statusCounts = { complete: 0, pending: 0, processing: 0, failed: 0 };
  filteredNarratives.forEach(n => {
    const status = n.status || 'complete';
    statusCounts[status] = (statusCounts[status] || 0) + 1;
  });
  
  const total = filteredNarratives.length || 1;
  
  container.innerHTML = `
    <div class="status-grid">
      <div class="status-item complete">
        <div class="status-value">${statusCounts.complete}</div>
        <div class="status-label">Complete</div>
      </div>
      <div class="status-item pending">
        <div class="status-value">${statusCounts.pending}</div>
        <div class="status-label">Pending</div>
      </div>
      <div class="status-item processing">
        <div class="status-value">${statusCounts.processing}</div>
        <div class="status-label">Processing</div>
      </div>
      <div class="status-item failed">
        <div class="status-value">${statusCounts.failed}</div>
        <div class="status-label">Failed</div>
      </div>
    </div>
  `;
}

function toggleMobileMenu() {
  const nav = document.querySelector('nav');
  const toggle = document.querySelector('.mobile-menu-toggle');
  const isOpen = nav.classList.toggle('mobile-open');
  toggle.classList.toggle('active', isOpen);
  toggle.setAttribute('aria-expanded', isOpen);
}

document.addEventListener('DOMContentLoaded', initAnalysisPage);
