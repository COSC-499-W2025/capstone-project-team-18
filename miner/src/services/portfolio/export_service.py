"""
Static web portfolio export service.

Produces a downloadable ZIP archive containing a self-contained single-page
web portfolio:
  - index.html     — page structure and inline rendering of Part A sections
  - portfolio_data.js — embedded JSON snapshot of all three portfolio parts
  - style.css      — visual styles (showcase cards glow yellow, etc.)
  - filter.js      — client-side gallery search/filter/sort logic (public mode)

The static bundle requires no server — it is the "public mode" deliverable.
Images are base64-encoded inline so the ZIP is fully self-contained.
"""

import base64
import io
import json
import zipfile
from datetime import date, datetime
from typing import Any

from sqlmodel import Session

from src.database.api.CRUD.portfolio import load_portfolio, get_project_cards_for_portfolio
from src.database.api.CRUD.projects import get_project_report_model_by_name
from src.utils.errors import KeyNotFoundError


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode("utf-8")
    raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header>
    <h1 id="portfolio-title">{title}</h1>
  </header>

  <!-- Part A: Narrative sections -->
  <section id="narrative">
{sections_html}
  </section>

  <!-- Figures: Contribution map + skill timeline -->
  <section id="figures">
    <h2>Figures</h2>
    <div id="contribution-map" class="figure-card"></div>
    <div id="skill-timeline" class="figure-card"></div>
  </section>

  <!-- Part B + C: Project gallery (showcase cards float to top, highlighted) -->
  <section id="gallery">
    <h2>Projects</h2>

    <div id="gallery-filters">
      <input type="text" id="search-input" placeholder="Search by name, tag, skill..." />
      <label>Themes: <input type="text" id="filter-themes" placeholder="e.g. web, ml" /></label>
      <label>Tone: <input type="text" id="filter-tones" placeholder="e.g. professional" /></label>
      <label>Tags: <input type="text" id="filter-tags" placeholder="e.g. python, api" /></label>
      <label>Skills: <input type="text" id="filter-skills" placeholder="e.g. React" /></label>
      <button id="clear-filters">Clear</button>
    </div>

    <div id="cards-container"></div>
  </section>

  <script src="portfolio_data.js"></script>
  <script src="filter.js"></script>
</body>
</html>
"""

_CSS = """\
/* ===== Reset & Base ===== */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #0f0f13;
  color: #e2e2e2;
  line-height: 1.6;
}

header {
  padding: 2rem;
  border-bottom: 1px solid #2a2a3a;
}

header h1 {
  font-size: 2rem;
  color: #ffffff;
}

/* ===== Part A: Narrative sections ===== */
#narrative {
  max-width: 900px;
  margin: 2rem auto;
  padding: 0 1.5rem;
}

.narrative-section {
  margin-bottom: 2rem;
}

.narrative-section h2 {
  font-size: 1.25rem;
  color: #a0aec0;
  margin-bottom: 0.5rem;
  border-bottom: 1px solid #2a2a3a;
  padding-bottom: 0.25rem;
}

.narrative-section .block-content {
  white-space: pre-wrap;
  font-size: 0.95rem;
  color: #cbd5e0;
}

/* ===== Figures ===== */
#figures {
  max-width: 1100px;
  margin: 2rem auto;
  padding: 0 1.5rem;
}

#figures h2 {
  font-size: 1.5rem;
  color: #ffffff;
  margin-bottom: 1rem;
}

.figure-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3a;
  border-radius: 10px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.figure-empty {
  color: #a0aec0;
  font-size: 0.9rem;
}

.figure-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}

.figure-title {
  font-size: 1rem;
  font-weight: 600;
  color: #ffffff;
}

.figure-controls {
  display: flex;
  gap: 0.4rem;
  align-items: center;
}

.figure-btn {
  background: transparent;
  border: 1px solid #e63946;
  color: #e63946;
  padding: 0.3rem 0.55rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.75rem;
}

.figure-btn.active {
  background: #e63946;
  color: #ffffff;
}

.figure-btn:disabled {
  border-color: #40445a;
  color: #6b7280;
  cursor: not-allowed;
}

.contrib-grid {
  display: flex;
  gap: 4px;
  overflow-x: auto;
  padding-bottom: 0.5rem;
}

.contrib-week {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.contrib-cell {
  width: 11px;
  height: 11px;
  border-radius: 2px;
  border: 1px solid transparent;
  transition: transform 0.12s ease, border-color 0.12s ease;
}

.contrib-cell.has-activity {
  cursor: pointer;
}

.contrib-cell.has-activity:hover {
  transform: scale(1.15);
  border-color: #e63946;
}

.contrib-cell.active {
  border-color: #e63946;
}

.contrib-hover-info {
  margin-top: 0.75rem;
  border-left: 3px solid #e63946;
  background: #111826;
  color: #d5d9e4;
  font-size: 0.78rem;
  border-radius: 6px;
  padding: 0.5rem 0.6rem;
}

.contrib-legend {
  margin-top: 0.8rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #a0aec0;
  font-size: 0.75rem;
}

.legend-scale {
  display: flex;
  gap: 3px;
  align-items: center;
}

.legend-cell {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.skill-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

.skill-card {
  border: 1px solid #2a2a3a;
  border-radius: 10px;
  padding: 0.8rem;
  background: #121220;
}

.skill-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 0.35rem;
}

.skill-total {
  font-size: 0.72rem;
  color: #a0aec0;
  margin-bottom: 0.5rem;
}

.skill-chart {
  width: 100%;
  height: 120px;
  display: block;
}

/* ===== Part B + C: Gallery ===== */
#gallery {
  max-width: 1100px;
  margin: 2rem auto;
  padding: 0 1.5rem;
}

#gallery h2 {
  font-size: 1.5rem;
  color: #ffffff;
  margin-bottom: 1rem;
}

/* Filter bar */
#gallery-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  align-items: center;
}

#gallery-filters input[type="text"] {
  background: #1a1a2e;
  border: 1px solid #2a2a3a;
  color: #e2e2e2;
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
}

#gallery-filters label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  color: #a0aec0;
}

#search-input { min-width: 220px; }

#clear-filters {
  background: #2a2a3a;
  border: none;
  color: #e2e2e2;
  padding: 0.4rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
}
#clear-filters:hover { background: #3a3a5a; }

/* Cards grid */
#cards-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.25rem;
}

/* Base card */
.project-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3a;
  border-radius: 10px;
  padding: 1.25rem;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}

/* Part B: showcase cards glow yellow */
.project-card.showcase {
  border-color: #f6c90e;
  box-shadow: 0 0 12px rgba(246, 201, 14, 0.35);
}

.project-card.showcase .card-name {
  color: #f6c90e;
}

/* Card internals */
.card-image {
  width: 100%;
  height: 140px;
  object-fit: cover;
  border-radius: 6px;
  margin-bottom: 0.75rem;
}

.card-name {
  font-size: 1rem;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 0.4rem;
}

.card-dates {
  font-size: 0.75rem;
  color: #718096;
  margin-bottom: 0.5rem;
}

.card-summary {
  font-size: 0.85rem;
  color: #a0aec0;
  margin-bottom: 0.75rem;
}

.card-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 0.4rem;
}

.badge {
  background: #2a2a3a;
  border-radius: 4px;
  padding: 0.15rem 0.5rem;
  font-size: 0.7rem;
  color: #cbd5e0;
}

.badge.theme  { background: #1e3a5f; color: #90cdf4; }
.badge.tone   { background: #2d3748; color: #e2e8f0; }
.badge.tag    { background: #2c4a2c; color: #9ae6b4; }
.badge.skill  { background: #4a1a4a; color: #e9d8fd; }
.badge.framework { background: #3d1a1a; color: #feb2b2; }

.card-meta {
  font-size: 0.75rem;
  color: #718096;
  margin-top: 0.5rem;
}

.hidden { display: none !important; }
"""


_FILTER_JS = """\
(function () {
  'use strict';

  var container = document.getElementById('cards-container');

  function mk(tag, className) {
    var el = document.createElement(tag);
    if (className) el.className = className;
    return el;
  }

  // ---- Render all cards on load ----
  function renderCards(cards) {
    container.innerHTML = '';
    cards.forEach(function (card) {
      container.appendChild(buildCardEl(card));
    });
  }

  function buildCardEl(card) {
    var el = document.createElement('div');
    el.className = 'project-card' + (card.is_showcase ? ' showcase' : '');
    el.dataset.name      = (card.project_name || '').toLowerCase();
    el.dataset.themes    = (card.themes || []).join(',').toLowerCase();
    el.dataset.tones     = (card.tones || '').toLowerCase();
    el.dataset.tags      = (card.tags_override || card.tags || []).join(',').toLowerCase();
    el.dataset.skills    = (card.skills || []).join(',').toLowerCase();
    el.dataset.frameworks = (card.frameworks || []).join(',').toLowerCase();

    var html = '';

    // Image
    if (card.image_data) {
      html += '<img class="card-image" src="data:image/png;base64,' + card.image_data + '" alt="' + esc(card.project_name) + '" />';
    }

    // Name
    html += '<div class="card-name">' + esc(card.title_override || card.project_name) + '</div>';

    // Dates
    if (card.start_date || card.end_date) {
      html += '<div class="card-dates">' +
        (card.start_date ? card.start_date.slice(0, 10) : '?') +
        ' — ' +
        (card.end_date ? card.end_date.slice(0, 10) : 'present') +
        '</div>';
    }

    // Summary
    var summary = card.summary_override || card.summary || '';
    if (summary) {
      html += '<div class="card-summary">' + esc(summary) + '</div>';
    }

    // Themes
    if (card.themes && card.themes.length) {
      html += '<div class="card-badges">' +
        card.themes.map(function(t){ return '<span class="badge theme">' + esc(t) + '</span>'; }).join('') +
        '</div>';
    }

    // Tone
    if (card.tones) {
      html += '<div class="card-badges"><span class="badge tone">' + esc(card.tones) + '</span></div>';
    }

    // Tags
    var tags = card.tags_override || card.tags || [];
    if (tags.length) {
      html += '<div class="card-badges">' +
        tags.map(function(t){ return '<span class="badge tag">' + esc(t) + '</span>'; }).join('') +
        '</div>';
    }

    // Skills
    if (card.skills && card.skills.length) {
      html += '<div class="card-badges">' +
        card.skills.map(function(s){ return '<span class="badge skill">' + esc(s) + '</span>'; }).join('') +
        '</div>';
    }

    // Frameworks
    if (card.frameworks && card.frameworks.length) {
      html += '<div class="card-badges">' +
        card.frameworks.map(function(f){ return '<span class="badge framework">' + esc(f) + '</span>'; }).join('') +
        '</div>';
    }

    // Meta
    var meta = [];
    if (card.collaboration_role) meta.push(card.collaboration_role);
    if (card.work_pattern) meta.push(card.work_pattern);
    if (card.is_group_project) meta.push('Group project');
    if (meta.length) {
      html += '<div class="card-meta">' + meta.map(esc).join(' · ') + '</div>';
    }

    el.innerHTML = html;
    return el;
  }

  function esc(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ---- Filter logic ----
  function applyFilters() {
    var search   = document.getElementById('search-input').value.toLowerCase().trim();
    var fThemes  = document.getElementById('filter-themes').value.toLowerCase().trim();
    var fTones   = document.getElementById('filter-tones').value.toLowerCase().trim();
    var fTags    = document.getElementById('filter-tags').value.toLowerCase().trim();
    var fSkills  = document.getElementById('filter-skills').value.toLowerCase().trim();

    var cards = container.querySelectorAll('.project-card');
    cards.forEach(function (card) {
      var show = true;

      if (search) {
        show = show && (
          card.dataset.name.includes(search) ||
          card.dataset.tags.includes(search) ||
          card.dataset.skills.includes(search) ||
          card.dataset.frameworks.includes(search)
        );
      }

      if (fThemes) {
        var terms = fThemes.split(',').map(function(t){ return t.trim(); }).filter(Boolean);
        show = show && terms.some(function(t){ return card.dataset.themes.includes(t); });
      }

      if (fTones) {
        show = show && card.dataset.tones.includes(fTones);
      }

      if (fTags) {
        var terms = fTags.split(',').map(function(t){ return t.trim(); }).filter(Boolean);
        show = show && terms.some(function(t){ return card.dataset.tags.includes(t); });
      }

      if (fSkills) {
        var terms = fSkills.split(',').map(function(t){ return t.trim(); }).filter(Boolean);
        show = show && terms.some(function(t){ return card.dataset.skills.includes(t); });
      }

      card.classList.toggle('hidden', !show);
    });
  }

  // ---- Wire up events ----
  document.getElementById('search-input').addEventListener('input', applyFilters);
  document.getElementById('filter-themes').addEventListener('input', applyFilters);
  document.getElementById('filter-tones').addEventListener('input', applyFilters);
  document.getElementById('filter-tags').addEventListener('input', applyFilters);
  document.getElementById('filter-skills').addEventListener('input', applyFilters);

  document.getElementById('clear-filters').addEventListener('click', function () {
    document.getElementById('search-input').value = '';
    document.getElementById('filter-themes').value = '';
    document.getElementById('filter-tones').value = '';
    document.getElementById('filter-tags').value = '';
    document.getElementById('filter-skills').value = '';
    applyFilters();
  });

  // ---- Initial render ----
  if (typeof PORTFOLIO_DATA !== 'undefined') {
    renderCards(PORTFOLIO_DATA.project_cards || []);
    renderContributionFigure(PORTFOLIO_DATA.figures || {});
    renderSkillTimelineFigure(PORTFOLIO_DATA.figures || {});
  }

  function renderContributionFigure(figures) {
    var root = document.getElementById('contribution-map');
    if (!root) return;

    var contribution = figures.contribution || {};
    var personal = contribution.personal_timeline || {};
    var total = contribution.total_timeline || {};

    var keys = Object.keys(personal).concat(Object.keys(total));
    if (!keys.length) {
      root.innerHTML = '<div class="figure-empty">No contribution data available.</div>';
      return;
    }

    var yearSet = {};
    keys.forEach(function (d) {
      var y = Number(String(d).slice(0, 4));
      if (!isNaN(y)) yearSet[y] = true;
    });
    var years = Object.keys(yearSet).map(Number).sort(function (a, b) { return a - b; });
    var state = {
      yearIndex: years.length - 1,
      mode: 'personal',
    };

    function maxPersonal() {
      var vals = Object.keys(personal).map(function (k) { return Number(personal[k] || 0); });
      return vals.length ? Math.max.apply(null, vals.concat([1])) : 1;
    }

    function datesForYear(y) {
      var start = new Date(y, 0, 1);
      var end = new Date(y, 11, 31);
      var dates = [];
      var cur = new Date(start);
      while (cur <= end) {
        var mm = String(cur.getMonth() + 1).padStart(2, '0');
        var dd = String(cur.getDate()).padStart(2, '0');
        dates.push(cur.getFullYear() + '-' + mm + '-' + dd);
        cur.setDate(cur.getDate() + 1);
      }
      return dates;
    }

    function opacityFor(date, dateRange, maxP) {
      var p = Number(personal[date] || 0);
      var t = Number(total[date] || 0);
      if (state.mode === 'personal') {
        if (p <= 0) return 0;
        return Math.max(0.1, p / maxP);
      }

      if (p <= 0 || t <= 0) return 0;
      var ratio = p / t;
      var maxRatio = 0.1;
      dateRange.forEach(function (d) {
        var pd = Number(personal[d] || 0);
        var td = Number(total[d] || 0);
        if (td > 0) {
          maxRatio = Math.max(maxRatio, pd / td);
        }
      });
      return Math.max(0.1, ratio / maxRatio);
    }

    function tooltipFor(date) {
      var p = Number(personal[date] || 0);
      var t = Number(total[date] || 0);
      if (p <= 0) return '';
      var parsedDate = new Date(date);
      var displayDate = isNaN(parsedDate.getTime())
        ? date
        : parsedDate.toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric'
          });
      if (state.mode === 'personal') {
        return displayDate + ': ' + p + ' commit' + (p === 1 ? '' : 's');
      }
      var pct = t > 0 ? ((p / t) * 100).toFixed(1) : '0.0';
      return displayDate + ': ' + p + '/' + t + ' commits (' + pct + '% of team activity)';
    }

    function groupedWeeks(dateRange) {
      var weeks = [];
      var current = [];
      dateRange.forEach(function (date) {
        var day = new Date(date).getDay();
        if (day === 0 && current.length) {
          weeks.push(current);
          current = [];
        }
        current.push(date);
      });
      if (current.length) weeks.push(current);
      return weeks;
    }

    var activeCell = null;
    var hoverInfo = null;

    function draw() {
      root.innerHTML = '';
      var year = years[state.yearIndex];
      var dateRange = datesForYear(year);
      var weeks = groupedWeeks(dateRange);
      var maxP = maxPersonal();

      var header = mk('div', 'figure-header');
      var title = mk('div', 'figure-title');
      title.textContent = 'Contribution Map';

      var controls = mk('div', 'figure-controls');

      var personalBtn = mk('button', 'figure-btn' + (state.mode === 'personal' ? ' active' : ''));
      personalBtn.textContent = 'Personal';
      personalBtn.onclick = function () { state.mode = 'personal'; draw(); };

      var ratioBtn = mk('button', 'figure-btn' + (state.mode === 'ratio' ? ' active' : ''));
      ratioBtn.textContent = 'Ratio';
      ratioBtn.onclick = function () { state.mode = 'ratio'; draw(); };

      var prevBtn = mk('button', 'figure-btn');
      prevBtn.textContent = '←';
      prevBtn.disabled = state.yearIndex <= 0;
      prevBtn.onclick = function () { state.yearIndex -= 1; draw(); };

      var yearLabel = mk('span', null);
      yearLabel.style.minWidth = '54px';
      yearLabel.style.textAlign = 'center';
      yearLabel.style.color = '#e63946';
      yearLabel.style.fontSize = '0.78rem';
      yearLabel.style.fontWeight = '600';
      yearLabel.textContent = String(year);

      var nextBtn = mk('button', 'figure-btn');
      nextBtn.textContent = '→';
      nextBtn.disabled = state.yearIndex >= years.length - 1;
      nextBtn.onclick = function () { state.yearIndex += 1; draw(); };

      controls.appendChild(personalBtn);
      controls.appendChild(ratioBtn);
      controls.appendChild(prevBtn);
      controls.appendChild(yearLabel);
      controls.appendChild(nextBtn);

      header.appendChild(title);
      header.appendChild(controls);
      root.appendChild(header);

      var grid = mk('div', 'contrib-grid');
      weeks.forEach(function (week) {
        var weekEl = mk('div', 'contrib-week');
        week.forEach(function (date) {
          var cell = mk('div', 'contrib-cell');
          var opacity = opacityFor(date, dateRange, maxP);
          cell.style.background = opacity === 0 ? '#2a2a3a' : 'rgba(230, 57, 70, ' + opacity + ')';
          var tip = tooltipFor(date);
          if (tip) {
            cell.title = tip;
            cell.classList.add('has-activity');
            cell.onmouseenter = function () {
              if (activeCell) activeCell.classList.remove('active');
              activeCell = cell;
              activeCell.classList.add('active');
              if (hoverInfo) hoverInfo.textContent = tip;
            };
            cell.onmouseleave = function () {
              cell.classList.remove('active');
              if (hoverInfo) {
                hoverInfo.textContent = state.mode === 'personal'
                  ? 'Hover over a highlighted day to see commit details.'
                  : 'Hover over a highlighted day to see your commit ratio details.';
              }
            };
          }
          weekEl.appendChild(cell);
        });
        grid.appendChild(weekEl);
      });
      root.appendChild(grid);

      hoverInfo = mk('div', 'contrib-hover-info');
      hoverInfo.textContent = state.mode === 'personal'
        ? 'Hover over a highlighted day to see commit details.'
        : 'Hover over a highlighted day to see your commit ratio details.';
      root.appendChild(hoverInfo);

      var legend = mk('div', 'contrib-legend');
      var left = mk('span', null);
      left.textContent = state.mode === 'personal'
        ? 'Intensity based on personal commit count'
        : 'Intensity based on personal/team ratio';

      var right = mk('div', 'legend-scale');
      var less = mk('span', null);
      less.textContent = 'Less';
      right.appendChild(less);
      [0, 0.25, 0.5, 0.75, 1].forEach(function (o) {
        var l = mk('span', 'legend-cell');
        l.style.background = o === 0 ? '#2a2a3a' : 'rgba(230, 57, 70, ' + o + ')';
        right.appendChild(l);
      });
      var more = mk('span', null);
      more.textContent = 'More';
      right.appendChild(more);

      legend.appendChild(left);
      legend.appendChild(right);
      root.appendChild(legend);
    }

    draw();
  }

  function renderSkillTimelineFigure(figures) {
    var root = document.getElementById('skill-timeline');
    if (!root) return;

    var data = figures.skill_timeline || {};
    var range = figures.skill_timeline_range || {};
    var skills = Object.keys(data);
    if (!skills.length) {
      root.innerHTML = '<div class="figure-empty">No skill timeline data available.</div>';
      return;
    }

    function parseDateValue(value) {
      if (typeof value !== 'string') return null;
      var parsed = new Date(value);
      return isNaN(parsed.getTime()) ? null : parsed;
    }

    function monthStart(dt) {
      return new Date(dt.getFullYear(), dt.getMonth(), 1);
    }

    function monthKey(dt) {
      var month = String(dt.getMonth() + 1);
      if (month.length < 2) month = '0' + month;
      return dt.getFullYear() + '-' + month;
    }

    function buildTimelineBuckets(startDate, endDate) {
      var buckets = [];
      var start = monthStart(startDate);
      var end = monthStart(endDate);
      if (end < start) {
        return [{
          key: monthKey(start),
          shortLabel: start.toLocaleString(undefined, { month: 'short', year: '2-digit' }),
          fullLabel: start.toLocaleString(undefined, { month: 'short', year: 'numeric' })
        }];
      }

      var cursor = new Date(start);
      while (cursor <= end) {
        buckets.push({
          key: monthKey(cursor),
          shortLabel: cursor.toLocaleString(undefined, { month: 'short', year: '2-digit' }),
          fullLabel: cursor.toLocaleString(undefined, { month: 'short', year: 'numeric' })
        });
        cursor.setMonth(cursor.getMonth() + 1);
      }

      return buckets;
    }

    function buildTickIndexes(length) {
      if (length <= 1) return [0];
      if (length <= 6) {
        var all = [];
        for (var idx = 0; idx < length; idx += 1) all.push(idx);
        return all;
      }

      var desired = 6;
      var step = (length - 1) / (desired - 1);
      var ticks = [0, length - 1];
      for (var i = 1; i < desired - 1; i += 1) {
        var candidate = Math.round(step * i);
        if (ticks.indexOf(candidate) === -1) ticks.push(candidate);
      }
      ticks.sort(function (a, b) { return a - b; });
      return ticks;
    }

    var skillMonthCounts = {};
    var totalBySkill = {};
    var minActivityDate = null;
    var maxActivityDate = null;
    var globalMaxMonthly = 1;

    skills.forEach(function (skill) {
      var byDate = data[skill] || {};
      Object.keys(byDate).forEach(function (dateStr) {
        var count = Number(byDate[dateStr] || 0);
        if (!isFinite(count) || count <= 0) return;
        var dt = parseDateValue(dateStr);
        if (!dt) return;

        if (!minActivityDate || dt < minActivityDate) minActivityDate = dt;
        if (!maxActivityDate || dt > maxActivityDate) maxActivityDate = dt;

        if (!skillMonthCounts[skill]) skillMonthCounts[skill] = {};
        var key = monthKey(dt);
        skillMonthCounts[skill][key] = Number(skillMonthCounts[skill][key] || 0) + count;
        totalBySkill[skill] = Number(totalBySkill[skill] || 0) + count;
      });
    });

    var rangeStart = parseDateValue(range.start_date) || minActivityDate;
    var rangeEnd = parseDateValue(range.end_date) || maxActivityDate;
    if (!rangeStart || !rangeEnd) {
      root.innerHTML = '<div class="figure-empty">No skill timeline data available.</div>';
      return;
    }

    var buckets = buildTimelineBuckets(rangeStart, rangeEnd);
    var monthKeys = buckets.map(function (bucket) { return bucket.key; });
    var skillSeries = {};

    Object.keys(totalBySkill).forEach(function (skill) {
      var runningTotal = 0;
      var series = monthKeys.map(function (key) {
        runningTotal += Number((skillMonthCounts[skill] || {})[key] || 0);
        return runningTotal;
      });
      skillSeries[skill] = series;
      var lastValue = series.length ? series[series.length - 1] : 0;
      if (lastValue > globalMaxMonthly) globalMaxMonthly = lastValue;
    });

    var colors = ['#E63946', '#7A9BA8', '#A89B6B', '#7B8B6F', '#8B6B7A'];
    var tickIndexes = buildTickIndexes(monthKeys.length);

    root.innerHTML = '';

    var header = mk('div', 'figure-header');
    var title = mk('div', 'figure-title');
    title.textContent = 'Most Utilized Skills';
    header.appendChild(title);
    root.appendChild(header);

    var subtitle = mk('div', 'figure-subtitle');
    subtitle.textContent = 'Cumulative running total of skill occurrences across all projects, plotted continuously from the earliest to latest project date.';
    subtitle.style.marginBottom = '10px';
    subtitle.style.fontSize = '0.78rem';
    subtitle.style.color = '#6f6f78';
    root.appendChild(subtitle);

    var topSkills = Object.keys(totalBySkill)
      .map(function (skill) {
        var series = skillSeries[skill] || [];
        var total = Number(totalBySkill[skill] || 0);
        return { skill: skill, timelineTotal: total, series: series };
      })
      .filter(function (entry) { return entry.timelineTotal > 0; })
      .sort(function (a, b) { return b.timelineTotal - a.timelineTotal; })
      .slice(0, 5);

    if (!topSkills.length) {
      var empty = mk('div', 'figure-empty');
      empty.textContent = 'No skill timeline data available.';
      root.appendChild(empty);
      return;
    }

    var grid = mk('div', 'skill-grid');

    topSkills.forEach(function (entry, index) {
      var card = mk('div', 'skill-card');
      var name = mk('div', 'skill-name');
      name.textContent = entry.skill;
      var total = mk('div', 'skill-total');
      total.textContent = entry.timelineTotal + ' occurrence' + (entry.timelineTotal === 1 ? '' : 's');

      var svgNS = 'http://www.w3.org/2000/svg';
      var svg = document.createElementNS(svgNS, 'svg');
      svg.setAttribute('viewBox', '0 0 360 120');
      svg.setAttribute('class', 'skill-chart');
      svg.setAttribute('role', 'img');
      svg.setAttribute('aria-label', entry.skill + ' cumulative activity');

      var left = 18;
      var top = 10;
      var width = 326;
      var height = 82;

      [0.25, 0.5, 0.75, 1].forEach(function (r) {
        var y = top + height * (1 - r);
        var line = document.createElementNS(svgNS, 'line');
        line.setAttribute('x1', String(left));
        line.setAttribute('x2', String(left + width));
        line.setAttribute('y1', String(y));
        line.setAttribute('y2', String(y));
        line.setAttribute('stroke', '#1f1f2f');
        line.setAttribute('stroke-width', '1');
        svg.appendChild(line);
      });

      var color = colors[index % colors.length];
      var path = '';
      var area = '';
      var denominator = Math.max(1, entry.series.length - 1);
      function logScale(value) {
        return globalMaxMonthly <= 1 ? value / globalMaxMonthly : Math.log(1 + value) / Math.log(1 + globalMaxMonthly);
      }
      entry.series.forEach(function (value, monthIndex) {
        var x = left + (monthIndex / denominator) * width;
        var y = top + (1 - logScale(value)) * height;
        path += (monthIndex === 0 ? 'M ' : ' L ') + x + ' ' + y;
      });
      area = path + ' L ' + (left + width) + ' ' + (top + height) + ' L ' + left + ' ' + (top + height) + ' Z';

      var areaPath = document.createElementNS(svgNS, 'path');
      areaPath.setAttribute('d', area);
      areaPath.setAttribute('fill', color);
      areaPath.setAttribute('fill-opacity', '0.2');
      svg.appendChild(areaPath);

      var linePath = document.createElementNS(svgNS, 'path');
      linePath.setAttribute('d', path);
      linePath.setAttribute('fill', 'none');
      linePath.setAttribute('stroke', color);
      linePath.setAttribute('stroke-width', '2');
      svg.appendChild(linePath);

      entry.series.forEach(function (value, monthIndex) {
        var x = left + (monthIndex / denominator) * width;
        var y = top + (1 - logScale(value)) * height;
        var dot = document.createElementNS(svgNS, 'circle');
        dot.setAttribute('cx', String(x));
        dot.setAttribute('cy', String(y));
        dot.setAttribute('r', '2.4');
        dot.setAttribute('fill', color);
        dot.setAttribute('stroke', '#0f0f13');
        dot.setAttribute('stroke-width', '1');
        dot.setAttribute('opacity', value > 0 ? '1' : '0.5');
        dot.appendChild(document.createElementNS(svgNS, 'title')).textContent = (buckets[monthIndex] ? buckets[monthIndex].fullLabel : '') + ': ' + value + ' cumulative';
        svg.appendChild(dot);
      });

      tickIndexes.forEach(function (monthIndex) {
        var x = left + (monthIndex / denominator) * width;
        var label = document.createElementNS(svgNS, 'text');
        label.setAttribute('x', String(x));
        label.setAttribute('y', '112');
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('fill', '#7f7f7f');
        label.setAttribute('font-size', '8.5');
        label.textContent = buckets[monthIndex] ? buckets[monthIndex].shortLabel : '';
        svg.appendChild(label);
      });

      card.appendChild(name);
      card.appendChild(total);
      card.appendChild(svg);
      grid.appendChild(card);
    });

    root.appendChild(grid);
  }
}());
"""


def export_portfolio_static(portfolio_id: int, session: Session) -> bytes:
    """
    Build and return a ZIP archive containing a static web portfolio for the
    given `portfolio_id`.

    The archive contains:
    - `index.html`
    - `portfolio_data.js`
    - `style.css`
    - `filter.js`

    Raises `KeyNotFoundError` if the portfolio does not exist.
    """
    portfolio = load_portfolio(session, portfolio_id)
    if portfolio is None:
        raise KeyNotFoundError(f"No portfolio with ID {portfolio_id}")

    # --- Build Part A HTML (sections) ---
    sections_html_parts = []
    for section in portfolio.sections:
        rendered = section.render()
        sections_html_parts.append(
            f'    <div class="narrative-section">\n'
            f'      <h2>{_esc(section.title)}</h2>\n'
            f'      <div class="block-content">{_esc(rendered)}</div>\n'
            f'    </div>'
        )
    sections_html = "\n".join(sections_html_parts)

    # --- Build Part C card data ---
    # Fetch cards ordered: showcase first, then alphabetically
    card_models = get_project_cards_for_portfolio(session, portfolio_id)
    cards_data = []
    personal_timeline: dict[str, int] = {}
    total_timeline: dict[str, int] = {}
    skill_timeline: dict[str, dict[str, int]] = {}
    earliest_project_start: date | None = None
    latest_project_end: date | None = None

    def _parse_stat_date(value: Any) -> date | None:
      if isinstance(value, date):
        return value
      if not isinstance(value, str):
        return None
      try:
        return date.fromisoformat(value[:10])
      except ValueError:
        return None

    for c in card_models:
        project = get_project_report_model_by_name(session, c.project_name)
        statistic = project.statistic if project and isinstance(
            project.statistic, dict) else {}

        stat_start = _parse_stat_date(statistic.get("PROJECT_START_DATE"))
        if stat_start and (earliest_project_start is None or stat_start < earliest_project_start):
          earliest_project_start = stat_start
        stat_end = _parse_stat_date(statistic.get("PROJECT_END_DATE"))
        if stat_end and (latest_project_end is None or stat_end > latest_project_end):
          latest_project_end = stat_end

        # Aggregate contribution timelines across all included projects.
        personal = statistic.get("COMMIT_ACTIVITY_TIMELINE", {})
        total = statistic.get("TOTAL_COMMIT_ACTIVITY_TIMELINE", {})
        for key, value in personal.items() if isinstance(personal, dict) else []:
            try:
                count = int(value)
            except (TypeError, ValueError):
                continue
            personal_timeline[str(key)] = personal_timeline.get(
                str(key), 0) + count
        for key, value in total.items() if isinstance(total, dict) else []:
            try:
                count = int(value)
            except (TypeError, ValueError):
                continue
            total_timeline[str(key)] = total_timeline.get(str(key), 0) + count

        # Aggregate per-skill activity as {skill: {YYYY-MM-DD: count}}.
        skill_activity = statistic.get("PROJECT_SKILL_ACTIVITY", {})
        if isinstance(skill_activity, dict):
            for skill, dates in skill_activity.items():
                if not isinstance(dates, list):
                    continue
                if skill not in skill_timeline:
                    skill_timeline[skill] = {}
                for date_value in dates:
                    if not isinstance(date_value, str):
                        continue
                    skill_timeline[skill][date_value] = skill_timeline[skill].get(
                        date_value, 0) + 1

        cards_data.append({
            "project_name": c.project_name,
            "title_override": c.title_override,
            "summary": c.summary,
            "summary_override": c.summary_override,
            "themes": c.themes or [],
            "tones": c.tones or "",
            "tags": c.tags or [],
            "tags_override": c.tags_override,
            "skills": c.skills or [],
            "frameworks": c.frameworks or [],
            "languages": c.languages or {},
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "is_group_project": c.is_group_project,
            "collaboration_role": c.collaboration_role or "",
            "work_pattern": c.work_pattern or "",
            "commit_type_distribution": c.commit_type_distribution or {},
            "activity_metrics": c.activity_metrics or {},
            "is_showcase": c.is_showcase,
            "image_data": c.image_data,
        })

    portfolio_data = {
        "portfolio_id": portfolio_id,
        "title": portfolio.title,
        "project_cards": cards_data,
        "figures": {
            "contribution": {
                "personal_timeline": personal_timeline,
                "total_timeline": total_timeline,
            },
            "skill_timeline": skill_timeline,
          "skill_timeline_range": {
            "start_date": earliest_project_start.isoformat() if earliest_project_start else None,
            "end_date": latest_project_end.isoformat() if latest_project_end else None,
          },
        },
    }
    portfolio_data_js = "var PORTFOLIO_DATA = " + json.dumps(
        portfolio_data, default=_json_default, indent=2
    ) + ";\n"

    # --- Build index.html ---
    index_html = _HTML_TEMPLATE.format(
        title=_esc(portfolio.title),
        sections_html=sections_html,
    )

    # --- Assemble ZIP ---
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", index_html)
        zf.writestr("portfolio_data.js", portfolio_data_js)
        zf.writestr("style.css", _CSS)
        zf.writestr("filter.js", _FILTER_JS)

    return buf.getvalue()


def _esc(text: str) -> str:
    """Minimal HTML escaping for template interpolation."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
