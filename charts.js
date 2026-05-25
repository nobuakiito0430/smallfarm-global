/* ============================================
   SmallFarm Global — Charts Module
   Chart.js configurations and rendering
   ============================================ */

// Chart.js global defaults for dark theme
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(148, 163, 184, 0.1)';
Chart.defaults.font.family = "'Inter', 'Noto Sans JP', sans-serif";

// Bottleneck category definitions
const BOTTLENECK_CATEGORIES = {
  input_market: { name_ja: '投入市場の信頼性', name_en: 'Input Market Reliability', icon: '🌱', color: '#ef4444' },
  market_access: { name_ja: '市場アクセス', name_en: 'Market Access', icon: '🛒', color: '#f59e0b' },
  financial_access: { name_ja: '金融アクセス', name_en: 'Financial Access', icon: '💰', color: '#8b5cf6' },
  knowledge_gap: { name_ja: '技術・知識ギャップ', name_en: 'Knowledge Gap', icon: '📚', color: '#3b82f6' },
  institutional: { name_ja: '制度・政策環境', name_en: 'Institutional Environment', icon: '🏛️', color: '#6366f1' },
  climate_risk: { name_ja: '気候・環境リスク', name_en: 'Climate Risk', icon: '🌡️', color: '#ec4899' },
  gender: { name_ja: 'ジェンダー格差', name_en: 'Gender Gap', icon: '⚖️', color: '#14b8a6' },
  post_harvest: { name_ja: 'ポストハーベストロス', name_en: 'Post-Harvest Loss', icon: '📦', color: '#f97316' },
  scalability: { name_ja: 'スケーラビリティ', name_en: 'Scalability', icon: '📈', color: '#eab308' }
};

const SUCCESS_FACTOR_CATEGORIES = {
  farmer_ownership: { name_ja: '農家のオーナーシップ', name_en: 'Farmer Ownership', icon: '🙋', color: '#10b981' },
  behavioral_change: { name_ja: '行動変容アプローチ', name_en: 'Behavioral Change', icon: '🧠', color: '#06b6d4' },
  public_private: { name_ja: '官民連携', name_en: 'Public-Private Partnership', icon: '🤝', color: '#8b5cf6' },
  gender_mainstream: { name_ja: 'ジェンダー主流化', name_en: 'Gender Mainstreaming', icon: '👩‍🌾', color: '#ec4899' },
  phased_scaleup: { name_ja: '段階的スケールアップ', name_en: 'Phased Scale-up', icon: '🪜', color: '#f59e0b' },
  ict_use: { name_ja: 'ICT活用', name_en: 'ICT Utilization', icon: '📱', color: '#3b82f6' },
  market_linkage: { name_ja: '市場関係者との直接接続', name_en: 'Market Linkage', icon: '🔗', color: '#f97316' },
  institutional_integration: { name_ja: '現地制度への統合', name_en: 'Institutional Integration', icon: '🏗️', color: '#6366f1' }
};

// Store chart instances for cleanup
const chartInstances = {};

function destroyChart(id) {
  if (chartInstances[id]) {
    chartInstances[id].destroy();
    delete chartInstances[id];
  }
}

/* ---------- Bottleneck Bar Chart ---------- */
function renderBottleneckBarChart(projects) {
  destroyChart('bottleneck-bar');
  const canvas = document.getElementById('bottleneck-bar-chart');
  if (!canvas) return;

  // Count bottlenecks
  const counts = {};
  Object.keys(BOTTLENECK_CATEGORIES).forEach(k => counts[k] = 0);
  projects.forEach(p => {
    (p.bottlenecks || []).forEach(b => {
      if (counts[b.category] !== undefined) counts[b.category]++;
    });
  });

  // Sort by frequency
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const labels = sorted.map(([k]) => BOTTLENECK_CATEGORIES[k].name_ja);
  const data = sorted.map(([, v]) => v);
  const colors = sorted.map(([k]) => BOTTLENECK_CATEGORIES[k].color);
  const icons = sorted.map(([k]) => BOTTLENECK_CATEGORIES[k].icon);

  chartInstances['bottleneck-bar'] = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'プロジェクト数',
        data: data,
        backgroundColor: colors.map(c => c + '40'),
        borderColor: colors,
        borderWidth: 2,
        borderRadius: 8,
        borderSkipped: false
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.95)',
          borderColor: 'rgba(148, 163, 184, 0.2)',
          borderWidth: 1,
          cornerRadius: 10,
          padding: 12,
          titleFont: { weight: 700 },
          callbacks: {
            title: (items) => {
              const idx = items[0].dataIndex;
              return icons[idx] + ' ' + items[0].label;
            },
            label: (item) => ` ${item.raw} プロジェクトで該当`
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(148, 163, 184, 0.06)' },
          ticks: { stepSize: 1 }
        },
        y: {
          grid: { display: false },
          ticks: { font: { size: 12, weight: 500 } }
        }
      },
      animation: {
        duration: 1200,
        easing: 'easeOutQuart'
      }
    }
  });
}

/* ---------- Bottleneck Radar Chart (by Region) ---------- */
function renderBottleneckRadarChart(projects) {
  destroyChart('bottleneck-radar');
  const canvas = document.getElementById('bottleneck-radar-chart');
  if (!canvas) return;

  const regions = ['Sub-Saharan Africa', 'South Asia', 'Multiple'];
  const regionColors = ['#10b981', '#3b82f6', '#f59e0b'];
  const categories = Object.keys(BOTTLENECK_CATEGORIES);
  const labels = categories.map(k => BOTTLENECK_CATEGORIES[k].name_ja);

  const datasets = regions.map((region, idx) => {
    const regionProjects = projects.filter(p => p.region === region);
    const data = categories.map(cat => {
      let count = 0;
      regionProjects.forEach(p => {
        (p.bottlenecks || []).forEach(b => {
          if (b.category === cat) count++;
        });
      });
      return count;
    });

    return {
      label: region === 'Multiple' ? '複数地域' : region === 'Sub-Saharan Africa' ? 'サブサハラアフリカ' : '南アジア',
      data: data,
      borderColor: regionColors[idx],
      backgroundColor: regionColors[idx] + '20',
      borderWidth: 2,
      pointBackgroundColor: regionColors[idx],
      pointBorderColor: '#0a0f1a',
      pointBorderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6
    };
  });

  chartInstances['bottleneck-radar'] = new Chart(canvas, {
    type: 'radar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 16, usePointStyle: true, pointStyle: 'circle' }
        },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.95)',
          borderColor: 'rgba(148, 163, 184, 0.2)',
          borderWidth: 1,
          cornerRadius: 10,
          padding: 12
        }
      },
      scales: {
        r: {
          angleLines: { color: 'rgba(148, 163, 184, 0.1)' },
          grid: { color: 'rgba(148, 163, 184, 0.1)' },
          pointLabels: { font: { size: 10, weight: 500 } },
          ticks: {
            stepSize: 1,
            display: false
          },
          beginAtZero: true
        }
      },
      animation: { duration: 1500, easing: 'easeOutQuart' }
    }
  });
}

/* ---------- Bottleneck Heatmap ---------- */
function renderBottleneckHeatmap(projects) {
  destroyChart('bottleneck-heatmap');
  const canvas = document.getElementById('bottleneck-heatmap');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const regions = ['Sub-Saharan Africa', 'South Asia', 'Multiple'];
  const regionLabels = ['サブサハラアフリカ', '南アジア', '複数地域'];
  const categories = Object.keys(BOTTLENECK_CATEGORIES);
  const catLabels = categories.map(k => BOTTLENECK_CATEGORIES[k].name_ja);

  // Build matrix
  const matrix = [];
  let maxVal = 0;
  regions.forEach(region => {
    const row = [];
    const regionProjects = projects.filter(p => p.region === region);
    categories.forEach(cat => {
      let count = 0;
      regionProjects.forEach(p => {
        (p.bottlenecks || []).forEach(b => {
          if (b.category === cat) count++;
        });
      });
      row.push(count);
      if (count > maxVal) maxVal = count;
    });
    matrix.push(row);
  });

  // Draw heatmap manually on canvas
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = 400 * dpr;
  canvas.style.width = rect.width + 'px';
  canvas.style.height = '400px';
  ctx.scale(dpr, dpr);

  const width = rect.width;
  const height = 400;
  const marginLeft = 140;
  const marginTop = 50;
  const marginRight = 30;
  const marginBottom = 30;
  const cellWidth = (width - marginLeft - marginRight) / categories.length;
  const cellHeight = (height - marginTop - marginBottom) / regions.length;

  ctx.clearRect(0, 0, width, height);

  // Column labels
  ctx.save();
  ctx.font = '11px Inter, sans-serif';
  ctx.fillStyle = '#94a3b8';
  ctx.textAlign = 'center';
  categories.forEach((cat, i) => {
    const x = marginLeft + i * cellWidth + cellWidth / 2;
    ctx.save();
    ctx.translate(x, marginTop - 8);
    ctx.rotate(-0.4);
    ctx.fillText(BOTTLENECK_CATEGORIES[cat].icon + ' ' + BOTTLENECK_CATEGORIES[cat].name_ja, 0, 0);
    ctx.restore();
  });
  ctx.restore();

  // Row labels + cells
  regions.forEach((region, ri) => {
    const y = marginTop + ri * cellHeight;

    // Row label
    ctx.font = '12px Inter, sans-serif';
    ctx.fillStyle = '#f1f5f9';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText(regionLabels[ri], marginLeft - 12, y + cellHeight / 2);

    // Cells
    categories.forEach((cat, ci) => {
      const x = marginLeft + ci * cellWidth;
      const val = matrix[ri][ci];
      const intensity = maxVal > 0 ? val / maxVal : 0;

      // Cell background
      const r = Math.round(245 * intensity + 15 * (1 - intensity));
      const g = Math.round(158 * intensity * 0.3 + 23 * (1 - intensity));
      const b = Math.round(11 * intensity * 0.3 + 42 * (1 - intensity));
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${0.15 + intensity * 0.7})`;

      const pad = 3;
      const radius = 8;
      const cx = x + pad;
      const cy = y + pad;
      const cw = cellWidth - pad * 2;
      const ch = cellHeight - pad * 2;

      ctx.beginPath();
      ctx.moveTo(cx + radius, cy);
      ctx.lineTo(cx + cw - radius, cy);
      ctx.quadraticCurveTo(cx + cw, cy, cx + cw, cy + radius);
      ctx.lineTo(cx + cw, cy + ch - radius);
      ctx.quadraticCurveTo(cx + cw, cy + ch, cx + cw - radius, cy + ch);
      ctx.lineTo(cx + radius, cy + ch);
      ctx.quadraticCurveTo(cx, cy + ch, cx, cy + ch - radius);
      ctx.lineTo(cx, cy + radius);
      ctx.quadraticCurveTo(cx, cy, cx + radius, cy);
      ctx.closePath();
      ctx.fill();

      // Value text
      if (val > 0) {
        ctx.font = 'bold 16px Inter, sans-serif';
        ctx.fillStyle = intensity > 0.5 ? '#ffffff' : '#94a3b8';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(val, x + cellWidth / 2, y + cellHeight / 2);
      }
    });
  });
}

/* ---------- Success Factor Bar Chart ---------- */
function renderSuccessBarChart(projects) {
  destroyChart('success-bar');
  const canvas = document.getElementById('success-bar-chart');
  if (!canvas) return;

  const counts = {};
  Object.keys(SUCCESS_FACTOR_CATEGORIES).forEach(k => counts[k] = 0);
  projects.forEach(p => {
    (p.success_factors || []).forEach(s => {
      if (counts[s.category] !== undefined) counts[s.category]++;
    });
  });

  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const labels = sorted.map(([k]) => SUCCESS_FACTOR_CATEGORIES[k].name_ja);
  const data = sorted.map(([, v]) => v);
  const colors = sorted.map(([k]) => SUCCESS_FACTOR_CATEGORIES[k].color);
  const icons = sorted.map(([k]) => SUCCESS_FACTOR_CATEGORIES[k].icon);

  chartInstances['success-bar'] = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'プロジェクト数',
        data,
        backgroundColor: colors.map(c => c + '40'),
        borderColor: colors,
        borderWidth: 2,
        borderRadius: 8,
        borderSkipped: false
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.95)',
          borderColor: 'rgba(148, 163, 184, 0.2)',
          borderWidth: 1,
          cornerRadius: 10,
          padding: 12,
          callbacks: {
            title: (items) => {
              const idx = items[0].dataIndex;
              return icons[idx] + ' ' + items[0].label;
            },
            label: (item) => ` ${item.raw} プロジェクトで該当`
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(148, 163, 184, 0.06)' },
          ticks: { stepSize: 1 }
        },
        y: {
          grid: { display: false },
          ticks: { font: { size: 12, weight: 500 } }
        }
      },
      animation: { duration: 1200, easing: 'easeOutQuart' }
    }
  });
}

/* ---------- Success Factor Radar Chart ---------- */
function renderSuccessRadarChart(projects) {
  destroyChart('success-radar');
  const canvas = document.getElementById('success-radar-chart');
  if (!canvas) return;

  const approaches = ['market-oriented', 'value-chain', 'digital', 'climate-smart'];
  const approachLabels = ['市場志向型', 'バリューチェーン', 'デジタル', '気候スマート'];
  const approachColors = ['#10b981', '#3b82f6', '#f59e0b', '#ec4899'];
  const categories = Object.keys(SUCCESS_FACTOR_CATEGORIES);
  const labels = categories.map(k => SUCCESS_FACTOR_CATEGORIES[k].name_ja);

  const datasets = approaches.map((approach, idx) => {
    const approachProjects = projects.filter(p => (p.approach || []).includes(approach));
    const data = categories.map(cat => {
      let count = 0;
      approachProjects.forEach(p => {
        (p.success_factors || []).forEach(s => {
          if (s.category === cat) count++;
        });
      });
      return count;
    });

    return {
      label: approachLabels[idx],
      data,
      borderColor: approachColors[idx],
      backgroundColor: approachColors[idx] + '15',
      borderWidth: 2,
      pointBackgroundColor: approachColors[idx],
      pointBorderColor: '#0a0f1a',
      pointBorderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6
    };
  });

  chartInstances['success-radar'] = new Chart(canvas, {
    type: 'radar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 16, usePointStyle: true, pointStyle: 'circle' }
        },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.95)',
          borderColor: 'rgba(148, 163, 184, 0.2)',
          borderWidth: 1,
          cornerRadius: 10,
          padding: 12
        }
      },
      scales: {
        r: {
          angleLines: { color: 'rgba(148, 163, 184, 0.1)' },
          grid: { color: 'rgba(148, 163, 184, 0.1)' },
          pointLabels: { font: { size: 10, weight: 500 } },
          ticks: { stepSize: 1, display: false },
          beginAtZero: true
        }
      },
      animation: { duration: 1500, easing: 'easeOutQuart' }
    }
  });
}

/* ---------- Comparison Radar Chart ---------- */
function renderComparisonRadar(selectedProjects) {
  destroyChart('comparison-radar');
  const canvas = document.getElementById('comparison-radar-chart');
  if (!canvas) return;

  if (selectedProjects.length < 2) {
    document.getElementById('comparison-radar-container').style.display = 'none';
    return;
  }

  document.getElementById('comparison-radar-container').style.display = 'block';

  const metrics = [
    { key: 'income', label: '所得向上率' },
    { key: 'participants', label: '参加者規模' },
    { key: 'bottlenecks', label: 'ボトルネック数' },
    { key: 'success', label: '成功要因数' },
    { key: 'climate', label: '気候変動対応' },
    { key: 'approaches', label: 'アプローチ多様性' }
  ];

  const colors = ['#10b981', '#3b82f6', '#f59e0b', '#ec4899'];

  // Normalize values for radar
  const maxIncome = Math.max(...selectedProjects.map(p => p.outcomes?.income_change_pct || 0), 1);
  const maxParticipants = Math.max(...selectedProjects.map(p => p.outcomes?.participants || 0), 1);

  const datasets = selectedProjects.map((project, idx) => {
    const income = (project.outcomes?.income_change_pct || 0) / maxIncome * 10;
    const participants = Math.log10(Math.max(project.outcomes?.participants || 1, 1)) / Math.log10(maxParticipants) * 10;
    const bottleneckCount = (project.bottlenecks || []).length;
    const successCount = (project.success_factors || []).length;
    const climateMap = { high: 10, medium: 6, low: 3, none: 0 };
    const climate = climateMap[project.climate_relevance] || 0;
    const approaches = (project.approach || []).length * 3;

    return {
      label: project.name,
      data: [income, participants, bottleneckCount, successCount, climate, approaches],
      borderColor: colors[idx % colors.length],
      backgroundColor: colors[idx % colors.length] + '15',
      borderWidth: 2,
      pointBackgroundColor: colors[idx % colors.length],
      pointBorderColor: '#0a0f1a',
      pointBorderWidth: 2,
      pointRadius: 5,
      pointHoverRadius: 7
    };
  });

  chartInstances['comparison-radar'] = new Chart(canvas, {
    type: 'radar',
    data: {
      labels: metrics.map(m => m.label),
      datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 16, usePointStyle: true, pointStyle: 'circle', font: { size: 13 } }
        },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.95)',
          borderColor: 'rgba(148, 163, 184, 0.2)',
          borderWidth: 1,
          cornerRadius: 10,
          padding: 12
        }
      },
      scales: {
        r: {
          angleLines: { color: 'rgba(148, 163, 184, 0.1)' },
          grid: { color: 'rgba(148, 163, 184, 0.1)' },
          pointLabels: { font: { size: 12, weight: 600 } },
          ticks: { display: false },
          beginAtZero: true
        }
      },
      animation: { duration: 1200, easing: 'easeOutQuart' }
    }
  });
}

/* ---------- Resize Handler for Heatmap ---------- */
let heatmapResizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(heatmapResizeTimer);
  heatmapResizeTimer = setTimeout(() => {
    if (window._heatmapProjects) {
      renderBottleneckHeatmap(window._heatmapProjects);
    }
  }, 300);
});
