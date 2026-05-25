/* ============================================
   SmallFarm Global — Main Application
   Data loading, UI control, interactions
   ============================================ */

(function () {
  'use strict';

  // ── State ──────────────────────────────────
  let allProjects = [];
  let filteredProjects = [];
  let statsData = {};
  let newsData = [];
  let papersData = [];
  let compareList = []; // max 4
  let activeResearchTab = 'papers';

  // ── Data Loading ──────────────────────────
  async function loadJSON(url) {
    try {
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (e) {
      console.warn(`Failed to load ${url}:`, e);
      return null;
    }
  }

  async function initData() {
    const [projects, stats, news, papers] = await Promise.all([
      loadJSON('data/projects.json'),
      loadJSON('data/stats.json'),
      loadJSON('data/news.json'),
      loadJSON('data/papers.json')
    ]);

    allProjects = projects || [];
    statsData = stats || {};
    newsData = news || [];
    papersData = papers || [];
    filteredProjects = [...allProjects];

    renderDashboard();
    renderProjectsGrid();
    populateFilters();
    renderBottleneckSection();
    renderSuccessSection();
    renderResearchSection();
    initScrollAnimations();
  }

  // ── Dashboard ─────────────────────────────
  function renderDashboard() {
    // Stats count-up
    animateCountUp('stat-projects', statsData.total_projects || allProjects.length);
    animateCountUp('stat-countries', statsData.total_countries || countUniqueCountries());
    animateCountUp('stat-beneficiaries', Math.round((statsData.total_beneficiaries || sumBeneficiaries()) / 10000), '万人');
    animateCountUp('stat-income', statsData.avg_income_change_pct || calcAvgIncome(), '%', '+');

    // Map
    initMap();

    // Timeline
    renderTimeline();

    // Last updated
    const lastUpdate = statsData.last_updated || new Date().toISOString().slice(0, 10);
    const footerUpdate = document.getElementById('footer-last-update');
    if (footerUpdate) footerUpdate.textContent = `最終更新: ${lastUpdate}`;
  }

  function countUniqueCountries() {
    const countries = new Set();
    allProjects.forEach(p => {
      (p.country || []).forEach(c => { if (c !== 'Multiple') countries.add(c); });
    });
    return countries.size;
  }

  function sumBeneficiaries() {
    return allProjects.reduce((s, p) => s + (p.outcomes?.beneficiaries_total || 0), 0);
  }

  function calcAvgIncome() {
    const valid = allProjects.filter(p => p.outcomes?.income_change_pct);
    if (!valid.length) return 0;
    return Math.round(valid.reduce((s, p) => s + p.outcomes.income_change_pct, 0) / valid.length);
  }

  // ── Count-up Animation ────────────────────
  function animateCountUp(elementId, target, suffix = '', prefix = '') {
    const el = document.getElementById(elementId);
    if (!el) return;

    const duration = 2000;
    const start = performance.now();

    function update(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      const current = Math.round(eased * target);
      el.textContent = prefix + current.toLocaleString() + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
  }

  // ── Map ───────────────────────────────────
  function initMap() {
    const mapEl = document.getElementById('world-map');
    if (!mapEl || mapEl._leaflet_id) return;

    const map = L.map('world-map', {
      center: [10, 20],
      zoom: 2.5,
      minZoom: 2,
      maxZoom: 8,
      zoomControl: true,
      attributionControl: false,
      scrollWheelZoom: true
    });

    // Base dark tiles (no labels for clean look)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd',
      maxZoom: 19
    }).addTo(map);

    // Bright label overlay for readability
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd',
      maxZoom: 19,
      pane: 'overlayPane'
    }).addTo(map);

    // Group projects by coordinates (approximate)
    const locationMap = {};
    allProjects.forEach(p => {
      if (!p.coordinates) return;
      const key = `${p.coordinates.lat.toFixed(1)}_${p.coordinates.lng.toFixed(1)}`;
      if (!locationMap[key]) {
        locationMap[key] = { lat: p.coordinates.lat, lng: p.coordinates.lng, projects: [] };
      }
      locationMap[key].projects.push(p);
    });

    Object.values(locationMap).forEach(loc => {
      const count = loc.projects.length;
      const size = Math.min(20 + count * 8, 48);

      const icon = L.divIcon({
        className: 'custom-marker',
        html: `<div style="width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center;">${count}</div>`,
        iconSize: [size, size]
      });

      const marker = L.marker([loc.lat, loc.lng], { icon }).addTo(map);

      const popupHtml = loc.projects.map(p =>
        `<div class="map-popup-title">${p.flag || ''} ${p.name}</div>
         <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:4px;">${p.implementer} | ${p.start_year}年〜</div>`
      ).join('<hr style="border-color:rgba(148,163,184,0.15);margin:6px 0;">');

      marker.bindPopup(`<div style="max-height:200px;overflow-y:auto;">${popupHtml}</div>`, {
        maxWidth: 300,
        closeButton: true
      });

      marker.on('click', () => {
        if (loc.projects.length === 1) {
          // Could optionally open modal
        }
      });
    });
  }

  // ── Timeline ──────────────────────────────
  function renderTimeline() {
    const container = document.getElementById('timeline');
    if (!container) return;

    const items = statsData.timeline || generateDefaultTimeline();
    container.innerHTML = items.slice(0, 5).map(item => `
      <div class="timeline-item">
        <div class="timeline-dot"></div>
        <div class="timeline-date">${item.date}</div>
        <div class="timeline-title">${item.title}</div>
        <div class="timeline-desc">${item.description}</div>
      </div>
    `).join('');
  }

  function generateDefaultTimeline() {
    return allProjects
      .sort((a, b) => (b.last_updated || '').localeCompare(a.last_updated || ''))
      .slice(0, 5)
      .map(p => ({
        date: p.last_updated || '2025-01-01',
        title: `${p.name} データ更新`,
        description: p.description_ja ? p.description_ja.slice(0, 60) + '...' : ''
      }));
  }

  // ── Filters ───────────────────────────────
  function populateFilters() {
    // Implementer filter
    const implementers = [...new Set(allProjects.map(p => p.implementer))].sort();
    const select = document.getElementById('filter-implementer');
    if (select) {
      implementers.forEach(imp => {
        const opt = document.createElement('option');
        opt.value = imp;
        opt.textContent = imp;
        select.appendChild(opt);
      });
    }
  }

  function getActiveFilters() {
    return {
      search: (document.getElementById('search-input')?.value || '').toLowerCase().trim(),
      region: document.getElementById('filter-region')?.value || '',
      approach: document.getElementById('filter-approach')?.value || '',
      implementer: document.getElementById('filter-implementer')?.value || '',
      climate: document.getElementById('filter-climate')?.value || '',
      status: document.getElementById('filter-status')?.value || ''
    };
  }

  function applyFilters() {
    const f = getActiveFilters();

    filteredProjects = allProjects.filter(p => {
      // Text search
      if (f.search) {
        const searchable = [
          p.name, p.name_ja, p.implementer,
          ...(p.country || []), ...(p.country_ja || []),
          ...(p.tags || []), ...(p.target_crops || []),
          p.description_en || '', p.description_ja || ''
        ].join(' ').toLowerCase();
        if (!searchable.includes(f.search)) return false;
      }
      if (f.region && p.region !== f.region) return false;
      if (f.approach && !(p.approach || []).includes(f.approach)) return false;
      if (f.implementer && p.implementer !== f.implementer) return false;
      if (f.climate && p.climate_relevance !== f.climate) return false;
      if (f.status && p.status !== f.status) return false;
      return true;
    });

    renderProjectsGrid();
    renderActiveFilterTags(f);
  }

  function renderActiveFilterTags(f) {
    const container = document.getElementById('active-filters');
    if (!container) return;

    const tagMap = {
      region: { label: '地域', value: f.region },
      approach: { label: 'アプローチ', value: f.approach },
      implementer: { label: '実施機関', value: f.implementer },
      climate: { label: '気候変動', value: f.climate },
      status: { label: '状態', value: f.status }
    };

    const tags = Object.entries(tagMap)
      .filter(([, v]) => v.value)
      .map(([key, v]) => `
        <span class="filter-tag">
          ${v.label}: ${v.value}
          <span class="remove" data-filter="${key}">✕</span>
        </span>
      `);

    container.innerHTML = tags.join('');

    container.querySelectorAll('.remove').forEach(btn => {
      btn.addEventListener('click', () => {
        const filterKey = btn.dataset.filter;
        const select = document.getElementById(`filter-${filterKey}`);
        if (select) {
          select.value = '';
          applyFilters();
        }
      });
    });
  }

  // ── Projects Grid ─────────────────────────
  function renderProjectsGrid() {
    const grid = document.getElementById('projects-grid');
    const countEl = document.getElementById('result-count');
    if (!grid) return;

    if (countEl) {
      countEl.innerHTML = `<strong>${filteredProjects.length}</strong> / ${allProjects.length} プロジェクト表示中`;
    }

    if (filteredProjects.length === 0) {
      grid.innerHTML = `
        <div class="no-results" style="grid-column: 1/-1;">
          <div class="icon">🔍</div>
          <h3>該当するプロジェクトがありません</h3>
          <p>検索条件を変更してください</p>
        </div>`;
      return;
    }

    grid.innerHTML = filteredProjects.map(p => renderProjectCard(p)).join('');

    // Attach event listeners
    grid.querySelectorAll('.project-card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('.btn-compare') || e.target.closest('.btn')) return;
        openProjectModal(card.dataset.id);
      });
    });

    grid.querySelectorAll('.btn-detail').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        openProjectModal(btn.dataset.id);
      });
    });

    grid.querySelectorAll('.btn-compare').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleCompare(btn.dataset.id);
      });
    });

    // Fade in animation
    grid.querySelectorAll('.project-card').forEach((card, i) => {
      card.style.opacity = '0';
      card.style.transform = 'translateY(20px)';
      setTimeout(() => {
        card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        card.style.opacity = '1';
        card.style.transform = 'translateY(0)';
      }, i * 60);
    });
  }

  function renderProjectCard(p) {
    const climateLevel = { high: 3, medium: 2, low: 1, none: 0 }[p.climate_relevance] || 0;
    const climateDots = Array.from({ length: 3 }, (_, i) =>
      `<span class="climate-dot${i < climateLevel ? ' filled' : ''}"></span>`
    ).join('');

    const statusClass = p.status === 'active' ? 'status-active' : p.status === 'completed' ? 'status-completed' : 'status-ongoing';
    const statusLabel = p.status === 'active' ? '実施中' : p.status === 'completed' ? '完了' : '進行中';

    const isInCompare = compareList.includes(p.id);

    return `
      <div class="project-card" data-id="${p.id}">
        <div class="project-card-header">
          <div class="project-card-title">${p.flag || ''} ${p.name}</div>
          <span class="project-status ${statusClass}">${statusLabel}</span>
        </div>

        <div class="project-card-meta">
          <span>🏢 ${p.implementer}</span>
          <span>📅 ${p.start_year}年〜${p.end_year ? p.end_year + '年' : ''}</span>
          <span>🌿 ${(p.target_crops || []).slice(0, 2).join(', ')}</span>
        </div>

        <div class="project-outcomes">
          ${p.outcomes?.income_change_pct ? `<div class="outcome-item">📈 所得 <span class="outcome-value">+${p.outcomes.income_change_pct}%</span></div>` : ''}
          ${p.outcomes?.beneficiaries_total ? `<div class="outcome-item">👨‍🌾 <span class="outcome-value">${formatNumber(p.outcomes.beneficiaries_total)}</span>人</div>` : ''}
        </div>

        <div class="project-bottlenecks">
          <div class="tag-label">ボトルネック</div>
          <div class="tag-list">
            ${(p.bottlenecks || []).map(b =>
              `<span class="tag-bottleneck">${BOTTLENECK_CATEGORIES[b.category]?.icon || '⚠️'} ${BOTTLENECK_CATEGORIES[b.category]?.name_ja || b.category}</span>`
            ).join('')}
          </div>
        </div>

        <div class="project-success-factors">
          <div class="tag-label">成功要因</div>
          <div class="tag-list">
            ${(p.success_factors || []).map(s =>
              `<span class="tag-success">${SUCCESS_FACTOR_CATEGORIES[s.category]?.icon || '✅'} ${SUCCESS_FACTOR_CATEGORIES[s.category]?.name_ja || s.category}</span>`
            ).join('')}
          </div>
        </div>

        <div class="project-tags">
          ${(p.tags || []).slice(0, 5).map(t => `<span class="project-tag">#${t}</span>`).join('')}
        </div>

        <div class="climate-indicator">
          🌡️ 気候変動関連度:
          <div class="climate-dots">${climateDots}</div>
          <span>${p.climate_relevance === 'high' ? '高' : p.climate_relevance === 'medium' ? '中' : '低'}</span>
        </div>

        <div class="project-card-actions">
          <button class="btn btn-primary btn-detail" data-id="${p.id}">詳細を見る</button>
          <button class="btn btn-compare ${isInCompare ? 'added' : ''}" data-id="${p.id}">
            ${isInCompare ? '✓ 追加済み' : '＋ 比較に追加'}
          </button>
        </div>
      </div>
    `;
  }

  function formatNumber(n) {
    if (n >= 10000000) return (n / 10000000).toFixed(0) + '千万';
    if (n >= 10000) return (n / 10000).toFixed(0) + '万';
    return n.toLocaleString();
  }

  // ── Project Modal ─────────────────────────
  function openProjectModal(projectId) {
    const project = allProjects.find(p => p.id === projectId);
    if (!project) return;

    const overlay = document.getElementById('modal-overlay');
    const titleEl = document.getElementById('modal-title');
    const statusEl = document.getElementById('modal-status');
    const bodyEl = document.getElementById('modal-body');

    const statusClass = project.status === 'active' ? 'status-active' : project.status === 'completed' ? 'status-completed' : 'status-ongoing';
    const statusLabel = project.status === 'active' ? '🟢 実施中' : project.status === 'completed' ? '🔵 完了' : '🟡 進行中';

    titleEl.textContent = `${project.flag || ''} ${project.name}`;
    statusEl.innerHTML = `<span class="project-status ${statusClass}">${statusLabel}</span>`;

    bodyEl.innerHTML = `
      <div class="modal-section">
        <div class="modal-section-title">📋 概要</div>
        <p style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.7;">${project.description_ja || project.description_en || ''}</p>
      </div>

      <div class="modal-section">
        <div class="modal-section-title">📊 基本情報</div>
        <div class="modal-meta-grid">
          <div class="meta-item"><div class="meta-label">実施機関</div><div class="meta-value">${project.implementer}</div></div>
          <div class="meta-item"><div class="meta-label">対象国</div><div class="meta-value">${(project.country_ja || project.country || []).join(', ')}</div></div>
          <div class="meta-item"><div class="meta-label">地域</div><div class="meta-value">${project.region}</div></div>
          <div class="meta-item"><div class="meta-label">実施期間</div><div class="meta-value">${project.start_year}年〜${project.end_year ? project.end_year + '年' : '現在'}</div></div>
          <div class="meta-item"><div class="meta-label">対象作物</div><div class="meta-value">${(project.target_crops || []).join(', ')}</div></div>
          <div class="meta-item"><div class="meta-label">アプローチ</div><div class="meta-value">${(project.approach_ja || project.approach || []).join(', ')}</div></div>
        </div>
      </div>

      <div class="modal-section">
        <div class="modal-section-title">📈 成果</div>
        <div class="modal-meta-grid">
          ${project.outcomes?.income_change_pct ? `<div class="meta-item"><div class="meta-label">所得変化率</div><div class="meta-value" style="color: var(--accent-green); font-size: 1.2rem;">+${project.outcomes.income_change_pct}%</div></div>` : ''}
          ${project.outcomes?.beneficiaries_total ? `<div class="meta-item"><div class="meta-label">受益者数</div><div class="meta-value">${project.outcomes.beneficiaries_total.toLocaleString()}人</div></div>` : ''}
          ${project.outcomes?.participants ? `<div class="meta-item"><div class="meta-label">直接参加者</div><div class="meta-value">${project.outcomes.participants.toLocaleString()}人</div></div>` : ''}
          ${project.outcomes?.key_result ? `<div class="meta-item" style="grid-column: 1/-1;"><div class="meta-label">主な成果</div><div class="meta-value" style="font-size: 0.85rem; font-weight: 500;">${project.outcomes.key_result}</div></div>` : ''}
        </div>
      </div>

      <div class="modal-section">
        <div class="modal-section-title">⚠️ ボトルネック</div>
        <div class="bottleneck-list">
          ${(project.bottlenecks || []).map(b => `
            <div class="bottleneck-item">
              <div class="item-icon">${BOTTLENECK_CATEGORIES[b.category]?.icon || '⚠️'}</div>
              <div class="item-content">
                <div class="item-category">${BOTTLENECK_CATEGORIES[b.category]?.name_ja || b.category}</div>
                <div class="item-desc">${b.description}</div>
              </div>
              <span class="severity-badge severity-${b.severity}">${b.severity === 'high' ? '深刻' : b.severity === 'medium' ? '中程度' : '軽微'}</span>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="modal-section">
        <div class="modal-section-title">✅ 成功要因</div>
        <div class="success-list">
          ${(project.success_factors || []).map(s => `
            <div class="success-item">
              <div class="item-icon">${SUCCESS_FACTOR_CATEGORIES[s.category]?.icon || '✅'}</div>
              <div class="item-content">
                <div class="item-category">${SUCCESS_FACTOR_CATEGORIES[s.category]?.name_ja || s.category}</div>
                <div class="item-desc">${s.description}</div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="modal-section">
        <div class="modal-section-title">🏷️ タグ</div>
        <div class="tag-list">
          ${(project.tags || []).map(t => `<span class="project-tag">#${t}</span>`).join('')}
        </div>
      </div>

      ${project.ai_confidence ? `
      <div class="modal-section">
        <div class="modal-section-title">🤖 AI信頼度</div>
        <div style="display:flex;align-items:center;gap:12px;">
          <div style="flex:1;height:8px;background:var(--border);border-radius:4px;overflow:hidden;">
            <div style="height:100%;width:${project.ai_confidence}%;background:linear-gradient(90deg,var(--accent-green),var(--accent-blue));border-radius:4px;"></div>
          </div>
          <span style="font-weight:700;color:var(--accent-green);">${project.ai_confidence}%</span>
        </div>
      </div>` : ''}

      ${project.source_url ? `
      <div class="modal-section">
        <a href="${project.source_url}" target="_blank" rel="noopener" class="btn btn-primary" style="text-decoration:none;">
          🔗 ソースを見る
        </a>
      </div>` : ''}
    `;

    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeProjectModal() {
    const overlay = document.getElementById('modal-overlay');
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  // ── Bottleneck Analysis ───────────────────
  function renderBottleneckSection() {
    renderBottleneckBarChart(allProjects);
    renderBottleneckRadarChart(allProjects);
    window._heatmapProjects = allProjects;
    renderBottleneckHeatmap(allProjects);
    renderBottleneckCards();
  }

  function renderBottleneckCards() {
    const container = document.getElementById('bottleneck-cards');
    if (!container) return;

    // Count bottlenecks and collect projects
    const catData = {};
    Object.keys(BOTTLENECK_CATEGORIES).forEach(k => {
      catData[k] = { count: 0, projects: [] };
    });

    allProjects.forEach(p => {
      (p.bottlenecks || []).forEach(b => {
        if (catData[b.category]) {
          catData[b.category].count++;
          catData[b.category].projects.push(p.name);
        }
      });
    });

    const sorted = Object.entries(catData).sort((a, b) => b[1].count - a[1].count);

    container.innerHTML = sorted.map(([key, data]) => {
      const cat = BOTTLENECK_CATEGORIES[key];
      return `
        <div class="analysis-card">
          <div class="analysis-card-header">
            <span class="analysis-card-icon">${cat.icon}</span>
            <span class="analysis-card-name">${cat.name_ja}</span>
            <span class="analysis-card-count">${data.count}件</span>
          </div>
          <div class="analysis-card-desc">${cat.description || cat.name_en}</div>
          <div class="analysis-card-projects">
            ${data.projects.map(name => `<span class="mini-tag">${name}</span>`).join('')}
          </div>
        </div>
      `;
    }).join('');
  }

  // ── Success Factor Analysis ───────────────
  function renderSuccessSection() {
    renderSuccessBarChart(allProjects);
    renderSuccessRadarChart(allProjects);
    renderSuccessCards();
  }

  function renderSuccessCards() {
    const container = document.getElementById('success-cards');
    if (!container) return;

    const catData = {};
    Object.keys(SUCCESS_FACTOR_CATEGORIES).forEach(k => {
      catData[k] = { count: 0, projects: [] };
    });

    allProjects.forEach(p => {
      (p.success_factors || []).forEach(s => {
        if (catData[s.category]) {
          catData[s.category].count++;
          catData[s.category].projects.push(p.name);
        }
      });
    });

    const sorted = Object.entries(catData).sort((a, b) => b[1].count - a[1].count);

    container.innerHTML = sorted.map(([key, data]) => {
      const cat = SUCCESS_FACTOR_CATEGORIES[key];
      return `
        <div class="analysis-card">
          <div class="analysis-card-header">
            <span class="analysis-card-icon">${cat.icon}</span>
            <span class="analysis-card-name">${cat.name_ja}</span>
            <span class="analysis-card-count">${data.count}件</span>
          </div>
          <div class="analysis-card-desc">${cat.description || cat.name_en}</div>
          <div class="analysis-card-projects">
            ${data.projects.map(name => `<span class="mini-tag">${name}</span>`).join('')}
          </div>
        </div>
      `;
    }).join('');
  }

  // ── Comparison Tool ───────────────────────
  function toggleCompare(projectId) {
    const idx = compareList.indexOf(projectId);
    if (idx > -1) {
      compareList.splice(idx, 1);
    } else if (compareList.length < 4) {
      compareList.push(projectId);
    } else {
      alert('比較は最大4件までです');
      return;
    }

    renderProjectsGrid(); // Update compare buttons
    renderCompareSlots();
    renderComparisonContent();
  }

  function renderCompareSlots() {
    for (let i = 0; i < 4; i++) {
      const slot = document.getElementById(`compare-slot-${i}`);
      if (!slot) continue;

      if (compareList[i]) {
        const p = allProjects.find(proj => proj.id === compareList[i]);
        slot.className = 'compare-slot filled';
        slot.innerHTML = `${p?.flag || ''} ${p?.name || ''} <span class="remove-compare" data-idx="${i}">✕</span>`;
      } else {
        slot.className = 'compare-slot';
        slot.innerHTML = '+ プロジェクト選択';
      }
    }

    // Event listeners for remove buttons
    document.querySelectorAll('.remove-compare').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.dataset.idx);
        compareList.splice(idx, 1);
        renderProjectsGrid();
        renderCompareSlots();
        renderComparisonContent();
      });
    });

    // Event listeners for empty slots
    document.querySelectorAll('.compare-slot:not(.filled)').forEach(slot => {
      slot.addEventListener('click', () => openCompareModal());
    });
  }

  function renderComparisonContent() {
    const container = document.getElementById('comparison-content');
    if (!container) return;

    const selected = compareList.map(id => allProjects.find(p => p.id === id)).filter(Boolean);

    if (selected.length < 2) {
      container.innerHTML = `
        <div class="empty-compare">
          <p style="font-size: 2rem; margin-bottom: 12px;">📊</p>
          <p>プロジェクトDBから「比較に追加」を押すか、上のスロットをクリックして2件以上選択してください</p>
        </div>`;
      document.getElementById('comparison-radar-container').style.display = 'none';
      return;
    }

    // Build comparison table
    const rows = [
      { label: '実施機関', fn: p => p.implementer },
      { label: '対象国', fn: p => (p.country_ja || p.country || []).join(', ') },
      { label: '地域', fn: p => p.region },
      { label: '実施期間', fn: p => `${p.start_year}〜${p.end_year || '現在'}` },
      { label: 'アプローチ', fn: p => (p.approach_ja || p.approach || []).join(', ') },
      { label: '対象作物', fn: p => (p.target_crops || []).join(', ') },
      { label: '所得変化率', fn: p => p.outcomes?.income_change_pct ? `+${p.outcomes.income_change_pct}%` : '—' },
      { label: '受益者数', fn: p => p.outcomes?.beneficiaries_total ? p.outcomes.beneficiaries_total.toLocaleString() + '人' : '—' },
      { label: '気候変動関連度', fn: p => p.climate_relevance === 'high' ? '🔴 高' : p.climate_relevance === 'medium' ? '🟡 中' : '🟢 低' },
      { label: 'ボトルネック', fn: p => (p.bottlenecks || []).map(b => BOTTLENECK_CATEGORIES[b.category]?.icon + ' ' + BOTTLENECK_CATEGORIES[b.category]?.name_ja).join('<br>') },
      { label: '成功要因', fn: p => (p.success_factors || []).map(s => SUCCESS_FACTOR_CATEGORIES[s.category]?.icon + ' ' + SUCCESS_FACTOR_CATEGORIES[s.category]?.name_ja).join('<br>') },
      { label: 'AI信頼度', fn: p => p.ai_confidence ? `${p.ai_confidence}%` : '—' }
    ];

    container.innerHTML = `
      <div class="comparison-table-wrapper">
        <table class="comparison-table">
          <thead>
            <tr>
              <th>項目</th>
              ${selected.map(p => `<th>${p.flag || ''} ${p.name}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            ${rows.map(row => `
              <tr>
                <td class="row-label">${row.label}</td>
                ${selected.map(p => `<td>${row.fn(p)}</td>`).join('')}
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;

    renderComparisonRadar(selected);
  }

  // ── Compare Modal ─────────────────────────
  function openCompareModal() {
    const overlay = document.getElementById('compare-modal-overlay');
    const listEl = document.getElementById('compare-project-list');
    const searchEl = document.getElementById('compare-search');

    function renderList(filter = '') {
      const available = allProjects.filter(p => {
        if (compareList.includes(p.id)) return false;
        if (filter) {
          const searchable = `${p.name} ${p.name_ja} ${p.implementer}`.toLowerCase();
          return searchable.includes(filter.toLowerCase());
        }
        return true;
      });

      listEl.innerHTML = available.map(p => `
        <div class="project-card" style="margin-bottom:8px;padding:14px;" data-id="${p.id}">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div style="font-weight:700;">${p.flag || ''} ${p.name}</div>
              <div style="font-size:0.8rem;color:var(--text-secondary);">${p.implementer} | ${(p.country_ja || []).join(', ')}</div>
            </div>
            <button class="btn btn-primary btn-add-compare" data-id="${p.id}">追加</button>
          </div>
        </div>
      `).join('');

      listEl.querySelectorAll('.btn-add-compare').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          toggleCompare(btn.dataset.id);
          closeCompareModal();
        });
      });
    }

    renderList();
    searchEl.value = '';
    searchEl.addEventListener('input', () => renderList(searchEl.value));

    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeCompareModal() {
    const overlay = document.getElementById('compare-modal-overlay');
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  // ── Research Section ──────────────────────
  function renderResearchSection() {
    const grid = document.getElementById('research-grid');
    const emptyEl = document.getElementById('research-empty');
    if (!grid) return;

    const items = activeResearchTab === 'papers' ? papersData : newsData;

    if (!items || items.length === 0) {
      grid.innerHTML = '';
      if (emptyEl) emptyEl.style.display = 'block';
      return;
    }

    if (emptyEl) emptyEl.style.display = 'none';

    grid.innerHTML = items.map(item => `
      <div class="research-card">
        <div class="research-card-source">
          ${item.source || 'Unknown'} 
          ${item.ai_confidence ? `<span class="ai-badge">🤖 AI信頼度 ${item.ai_confidence}%</span>` : ''}
        </div>
        <div class="research-card-title">
          <a href="${item.source_url || '#'}" target="_blank" rel="noopener">${item.title || item.summary_ja || 'Untitled'}</a>
        </div>
        <div class="research-card-summary">${item.summary_ja || item.summary_en || ''}</div>
        <div class="research-card-tags">
          ${(item.tags || []).slice(0, 4).map(t => `<span class="project-tag">#${t}</span>`).join('')}
          ${(item.bottlenecks || []).slice(0, 2).map(b => `<span class="tag-bottleneck">${BOTTLENECK_CATEGORIES[b.category]?.icon || '⚠️'} ${BOTTLENECK_CATEGORIES[b.category]?.name_ja || b.category}</span>`).join('')}
        </div>
        <div class="research-card-date">${item.date || ''}</div>
      </div>
    `).join('');
  }

  // ── Scroll Animations ─────────────────────
  function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.fade-in-up').forEach(el => observer.observe(el));
  }

  // ── Navigation ────────────────────────────
  function initNavigation() {
    // Active section highlighting
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-links a');

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          navLinks.forEach(link => link.classList.remove('active'));
          const activeLink = document.querySelector(`.nav-links a[href="#${entry.target.id}"]`);
          if (activeLink) activeLink.classList.add('active');
        }
      });
    }, { threshold: 0.3 });

    sections.forEach(section => observer.observe(section));

    // Hamburger
    const hamburger = document.getElementById('hamburger');
    const navLinksEl = document.getElementById('nav-links');
    if (hamburger && navLinksEl) {
      hamburger.addEventListener('click', () => {
        hamburger.classList.toggle('active');
        navLinksEl.classList.toggle('open');
      });

      navLinksEl.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
          hamburger.classList.remove('active');
          navLinksEl.classList.remove('open');
        });
      });
    }
  }

  // ── Event Listeners ───────────────────────
  function initEventListeners() {
    // Search
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
      let debounceTimer;
      searchInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(applyFilters, 200);
      });
    }

    // Filter toggle
    const filterToggle = document.getElementById('filter-toggle-btn');
    const filterPanel = document.getElementById('filter-panel');
    if (filterToggle && filterPanel) {
      filterToggle.addEventListener('click', () => {
        filterPanel.classList.toggle('open');
        filterToggle.classList.toggle('active');
      });
    }

    // Filter selects
    ['filter-region', 'filter-approach', 'filter-implementer', 'filter-climate', 'filter-status'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('change', applyFilters);
    });

    // Modal close
    document.getElementById('modal-close')?.addEventListener('click', closeProjectModal);
    document.getElementById('modal-overlay')?.addEventListener('click', (e) => {
      if (e.target === e.currentTarget) closeProjectModal();
    });

    document.getElementById('compare-modal-close')?.addEventListener('click', closeCompareModal);
    document.getElementById('compare-modal-overlay')?.addEventListener('click', (e) => {
      if (e.target === e.currentTarget) closeCompareModal();
    });

    // Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeProjectModal();
        closeCompareModal();
      }
    });

    // Research tabs
    document.querySelectorAll('.research-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.research-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        activeResearchTab = tab.dataset.tab;
        renderResearchSection();
      });
    });
  }

  // ── Bottleneck & Success descriptions for cards ──
  // (Add descriptions to the categories that charts.js defines)
  const BOTTLENECK_DESCS = {
    input_market: '種子・肥料等の品質不確実性、偽装問題、アクセス不足',
    market_access: '物理的インフラ不備、仲買人依存、価格情報の欠如',
    financial_access: '融資不足、担保要件、農業保険の未整備',
    knowledge_gap: '普及サービス不足、情報の非対称性、技術研修の欠如',
    institutional: '土地権の不安定さ、規制障壁、政府の実施能力不足',
    climate_risk: '干ばつ、洪水、塩害、異常気象',
    gender: '女性農家の意思決定権限不足、資源アクセスの不平等',
    post_harvest: '貯蔵・流通インフラの未整備、品質劣化',
    scalability: 'パイロットから広域展開への障壁、質の維持'
  };

  const SUCCESS_DESCS = {
    farmer_ownership: '農家自身が意思決定する仕組み',
    behavioral_change: '心理学的理論（SDT等）の活用',
    public_private: '政府・民間セクターの協働',
    gender_mainstream: '女性参加の制度化',
    phased_scaleup: 'パイロット→実証→展開の段階的拡大',
    ict_use: 'デジタルツールの導入',
    market_linkage: '中間搾取の排除・直接取引',
    institutional_integration: '各国政府の既存システムへの組み込み'
  };

  // Merge descriptions into chart category objects
  Object.keys(BOTTLENECK_DESCS).forEach(k => {
    if (BOTTLENECK_CATEGORIES[k]) BOTTLENECK_CATEGORIES[k].description = BOTTLENECK_DESCS[k];
  });
  Object.keys(SUCCESS_DESCS).forEach(k => {
    if (SUCCESS_FACTOR_CATEGORIES[k]) SUCCESS_FACTOR_CATEGORIES[k].description = SUCCESS_DESCS[k];
  });

  // ── Init ──────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initEventListeners();
    renderCompareSlots();
    initData();
  });

})();
