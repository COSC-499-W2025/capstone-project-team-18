"""
Static web portfolio export service.

Produces a downloadable ZIP archive containing a self-contained single-page
web portfolio:
  - index.html        — page structure and inline rendering of Part A sections
  - portfolio_data.js — embedded JSON snapshot of all portfolio parts + figures data
  - style.css         — visual styles
  - filter.js         — client-side gallery search/filter/sort logic
  - figures.js        — contribution map and skill timeline visualizations

The static bundle requires no server — it is the "public mode" deliverable.
Images are base64-encoded inline so the ZIP is fully self-contained.
"""

import base64
import io
import json
import urllib.request
import zipfile
from datetime import date, datetime
from typing import Any, Optional

from sqlmodel import Session

from src.database.api.CRUD.portfolio import load_portfolio, get_project_cards_for_portfolio
from src.database import get_project_report_models_by_names, get_most_recent_user_config
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
    <p class="portfolio-updated">Last updated: {last_updated}</p>
  </header>

  <nav id="section-nav">{nav_html}</nav>

  <!-- Part A: Narrative sections -->
  <section id="narrative">
{sections_html}
  </section>

  <!-- Figures: contribution map + skill timeline -->
  <section id="figures">
    <h2>Figures</h2>
    <div id="contribution-map"></div>
    <div id="skill-timeline"></div>
  </section>

  <!-- Part B + C: Project gallery -->
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
  <script src="figures.js"></script>
</body>
</html>
"""

_CSS = """\
/* ===== Reset & Base ===== */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f0f0f0;
  color: #111111;
  line-height: 1.6;
}

header {
  padding: 2rem;
  border-bottom: 1px solid #e0e0e0;
  background: #ffffff;
}

header h1 {
  font-size: 2rem;
  color: #111111;
}

header .portfolio-updated {
  font-size: 0.8rem;
  color: #666;
  margin-top: 0.25rem;
}

/* ===== Section navigation ===== */
#section-nav {
  max-width: 1100px;
  margin: 1rem auto 0;
  padding: 0 1.5rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.nav-links a {
  font-size: 0.8rem;
  color: #6f7cff;
  text-decoration: none;
  padding: 5px 14px;
  border-radius: 999px;
  border: 1px solid rgba(111, 124, 255, 0.3);
  background: rgba(111, 124, 255, 0.06);
  transition: all 0.15s;
}

.nav-links a:hover {
  background: rgba(111, 124, 255, 0.18);
  border-color: rgba(111, 124, 255, 0.55);
}

/* ===== Part A: Narrative sections ===== */
#narrative {
  max-width: 1100px;
  margin: 2rem auto;
  padding: 0 1.5rem;
}

.narrative-section {
  margin-bottom: 2rem;
}

.narrative-section h2 {
  font-size: 1.25rem;
  color: #444444;
  margin-bottom: 0.5rem;
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 0.25rem;
}

.narrative-section h2 a.section-anchor {
  color: inherit;
  text-decoration: none;
}

.narrative-section h2 a.section-anchor:hover {
  text-decoration: underline;
}

.block-text {
  font-size: 0.95rem;
  color: #333333;
  margin-bottom: 0.75rem;
  line-height: 1.7;
}

.block-list {
  font-size: 0.95rem;
  color: #333333;
  margin-bottom: 0.75rem;
  padding-left: 1.5rem;
  line-height: 1.8;
}

.block-list li {
  margin-bottom: 0.2rem;
}

/* ===== Figures section ===== */
#figures {
  max-width: 1100px;
  margin: 2rem auto;
  padding: 0 1.5rem;
}

#figures h2 {
  font-size: 1.5rem;
  color: #111111;
  margin-bottom: 1rem;
}

.figure-card {
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.figure-empty {
  color: #777777;
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
  color: #111111;
}

.figure-controls {
  display: flex;
  gap: 0.4rem;
  align-items: center;
}

.figure-btn {
  background: transparent;
  border: 1px solid #002145;
  color: #002145;
  padding: 0.3rem 0.55rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.75rem;
}

.figure-btn.active {
  background: #002145;
  color: #ffffff;
}

.figure-btn:disabled {
  border-color: #d0d0d0;
  color: #aaaaaa;
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
  border-color: #002145;
}

.contrib-cell.active {
  border-color: #002145;
}

.contrib-hover-info {
  margin-top: 0.75rem;
  border-left: 3px solid #002145;
  background: #f5f5f5;
  color: #111111;
  font-size: 0.78rem;
  border-radius: 6px;
  padding: 0.5rem 0.6rem;
}

.contrib-legend {
  margin-top: 0.8rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #777777;
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

.skill-view-toggle {
  display: flex;
  gap: 0;
}
.skill-toggle-btn {
  padding: 4px 12px;
  font-size: 0.75rem;
  border: 1px solid #d0d0d0;
  background: transparent;
  color: #666666;
  cursor: pointer;
  font-weight: 400;
}
.skill-toggle-btn:first-child { border-radius: 6px 0 0 6px; }
.skill-toggle-btn:last-child  { border-radius: 0 6px 6px 0; border-left: none; }
.skill-toggle-btn.active {
  background: #002145;
  color: #ffffff;
  font-weight: 600;
}

.skill-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-bottom: 14px;
}
.skill-legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.75rem;
  color: #444444;
}
.skill-legend-swatch {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}

.skill-stacked-wrap {
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  background: #ffffff;
  padding: 10px 4px 4px;
  position: relative;
}
.skill-stacked-svg {
  display: block;
  width: 100%;
  height: 380px;
}
.skill-tooltip {
  position: absolute;
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 8px 12px;
  pointer-events: none;
  z-index: 20;
  width: 170px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  display: none;
}
.skill-tooltip-label {
  font-size: 0.69rem;
  color: #777777;
  margin-bottom: 6px;
  padding-bottom: 5px;
  border-bottom: 1px solid #e0e0e0;
  white-space: nowrap;
}
.skill-tooltip-row {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 3px;
}
.skill-tooltip-swatch {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  flex-shrink: 0;
}
.skill-tooltip-name {
  font-size: 0.69rem;
  color: #555555;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.skill-tooltip-count {
  font-size: 0.69rem;
  color: #111111;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

.skill-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

.skill-card {
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  padding: 0.8rem;
  background: #ffffff;
}

.skill-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: #111111;
  margin-bottom: 0.35rem;
}

.skill-total {
  font-size: 0.72rem;
  color: #777777;
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
  color: #111111;
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
  background: #ffffff;
  border: 1px solid #d0d0d0;
  color: #111111;
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
}

#gallery-filters label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  color: #666666;
}

#search-input { min-width: 220px; }

#clear-filters {
  background: #e0e0e0;
  border: none;
  color: #111111;
  padding: 0.4rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
}
#clear-filters:hover { background: #d0d0d0; }

/* Cards grid */
#cards-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(700px, 1fr));
  gap: 1.25rem;
}

/* Base card */
.project-card {
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  padding: 1.25rem;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}

/* Part B: showcase cards use gold border */
.project-card.showcase {
  border-color: #ca8a04;
  box-shadow: 0 0 12px rgba(202, 138, 4, 0.25);
}

.project-card.showcase .card-name {
  color: #92400e;
}

/* Card internals */
.card-image {
  width: 100%;
  height: auto;
  max-height: 200px;
  object-fit: contain;
  border-radius: 6px;
  margin-bottom: 0.75rem;
}

.card-name {
  font-size: 1rem;
  font-weight: 600;
  color: #111111;
  margin-bottom: 0.4rem;
  word-break: break-word;
}

.card-dates {
  font-size: 0.75rem;
  color: #777777;
  margin-bottom: 0.5rem;
}

.card-summary {
  font-size: 0.85rem;
  color: #555555;
  margin-bottom: 0.75rem;
  word-break: break-word;
}

.card-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 0.4rem;
}

.badge {
  background: #f0f0f0;
  border-radius: 999px;
  padding: 0.15rem 0.6rem;
  font-size: 0.7rem;
  color: #333333;
  border: 1px solid #e0e0e0;
  word-break: break-all;
}

.badge.theme  { background: #ccfbf1; color: #0f766e; border: 1px solid #5eead4; }
.badge.tone   { background: #f3f4f6; color: #6b7280; border: 1px solid #d1d5db; }
.badge.tag    { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
.badge.skill  { background: #dbeafe; color: #0055B7; border: 1px solid #93c5fd; }
.badge.framework { background: #ede9fe; color: #6d28d9; border: 1px solid #c4b5fd; }

.card-meta {
  font-size: 0.75rem;
  color: #777777;
  margin-top: 0.5rem;
}

/* ===== Card details section ===== */
.card-details {
  margin-top: 0.85rem;
  padding-top: 0.85rem;
  border-top: 1px solid #e8e8e8;
}

.card-stats {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 0.5rem;
  margin-bottom: 0.85rem;
  padding: 0.65rem 0.75rem;
  background: #f5f5f5;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

.stat-box {}

.stat-label {
  font-size: 0.62rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.2rem;
}

.stat-value {
  font-size: 0.9rem;
  font-weight: 600;
  color: #111111;
}

.card-section-title {
  font-size: 0.7rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0.75rem 0 0.45rem;
}

/* Language breakdown */
.lang-stacked {
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  margin-bottom: 0.5rem;
}

.lang-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.1rem;
}

.lang-legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.72rem;
  color: #555;
}

.lang-legend-item span + span { color: #888; margin-left: 2px; }

/* Activity breakdown */
.activity-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.3rem;
}

.activity-label {
  font-size: 0.72rem;
  color: #555;
  min-width: 64px;
}

.activity-track {
  flex: 1;
  height: 4px;
  background: #e8e8e8;
  border-radius: 2px;
  overflow: hidden;
}

.activity-fill {
  height: 100%;
  border-radius: 2px;
}

.activity-pct {
  font-size: 0.7rem;
  color: #666;
  min-width: 30px;
  text-align: right;
}

/* Your Contribution */
.contrib-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}

.contrib-label {
  font-size: 0.72rem;
  color: #555;
  min-width: 110px;
}

.contrib-bar-track {
  flex: 1;
  height: 5px;
  background: #e8e8e8;
  border-radius: 3px;
  overflow: hidden;
}

.contrib-bar-fill-commit {
  height: 100%;
  border-radius: 3px;
  background: #6f7cff;
}

.contrib-bar-fill-loc {
  height: 100%;
  border-radius: 3px;
  background: #8ad6a2;
}

.contrib-pct {
  font-size: 0.7rem;
  color: #888;
  min-width: 32px;
  text-align: right;
}

/* GitHub link button */
.github-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 0.75rem;
  font-size: 0.8rem;
  color: #6f7cff;
  text-decoration: none;
  padding: 5px 12px;
  border: 1px solid rgba(111, 124, 255, 0.3);
  border-radius: 999px;
  background: rgba(111, 124, 255, 0.06);
  transition: all 0.15s;
}

.github-link:hover {
  background: rgba(111, 124, 255, 0.18);
  border-color: rgba(111, 124, 255, 0.55);
}

.hidden { display: none !important; }
"""


_FILTER_JS = """\
(function () {
  'use strict';

  var container = document.getElementById('cards-container');

  var MONTHS = ['Jan','Feb','Mar','Apr','May','Jun',
                'Jul','Aug','Sep','Oct','Nov','Dec'];

  function formatDate(iso) {
    if (!iso) return '?';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso.slice(0, 10);
    return MONTHS[d.getUTCMonth()] + ' ' + d.getUTCFullYear();
  }

  var LANG_COLORS = ['#6f7cff','#E63946','#A89B6B','#8ad6a2','#7A9BA8','#e08060','#8B6B7A','#5B8C85','#7fc0db'];

  var COMMIT_COLORS = {
    'feat':'#6f7cff','feature':'#6f7cff',
    'fix':'#E63946','bugfix':'#E63946',
    'docs':'#8ad6a2','doc':'#8ad6a2',
    'refactor':'#7fc0db','chore':'#7fc0db',
    'test':'#A89B6B',
    'perf':'#e08060','performance':'#e08060',
    'config':'#8B6B7A','unknown':'#555'
  };

  var COMMIT_NAMES = {
    'feat':'Feat','feature':'Feat',
    'fix':'Fix','bugfix':'Fix',
    'docs':'Docs','doc':'Docs',
    'refactor':'Refactor','chore':'Chore',
    'test':'Test','perf':'Perf','performance':'Perf',
    'config':'Config','unknown':'Other'
  };

  function computeDuration(start, end) {
    if (!start) return null;
    var s = new Date(start);
    var e = end ? new Date(end) : new Date();
    if (isNaN(s.getTime())) return null;
    var months = (e.getFullYear() - s.getFullYear()) * 12 + (e.getMonth() - s.getMonth());
    if (months < 1) return '< 1 month';
    if (months === 1) return '1 month';
    if (months < 12) return months + ' months';
    var yrs = Math.round(months / 12 * 10) / 10;
    return yrs + (yrs === 1 ? ' year' : ' years');
  }

  function displayLang(key) {
    return key.replace(/^CodingLanguage\\./i, '');
  }

  // ---- Render all cards on load ----
  function renderCards(cards) {
    container.innerHTML = '';
    cards.forEach(function (card) {
      container.appendChild(buildCardEl(card));
    });
  }

  function getImageSrc(b64) {
    if (b64.startsWith('/9j/')) return 'data:image/jpeg;base64,' + b64;
    if (b64.startsWith('iVBOR')) return 'data:image/png;base64,' + b64;
    if (b64.startsWith('R0lG')) return 'data:image/gif;base64,' + b64;
    if (b64.startsWith('UklG')) return 'data:image/webp;base64,' + b64;
    return 'data:image/jpeg;base64,' + b64;
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
      html += '<img class="card-image" src="' + getImageSrc(card.image_data) + '" alt="' + esc(card.project_name) + '" />';
    }

    // Name
    html += '<div class="card-name">' + esc(card.title_override || card.project_name) + '</div>';

    // Dates
    if (card.start_date || card.end_date) {
      html += '<div class="card-dates">' +
        formatDate(card.start_date) +
        ' \u2014 ' +
        (card.end_date ? formatDate(card.end_date) : 'present') +
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

    // ---- Details section (stats, language, activity, contribution) ----
    html += '<div class="card-details">';

    // Stats strip
    html += '<div class="card-stats">';
    var dur = computeDuration(card.start_date, card.end_date);
    if (dur) html += '<div class="stat-box"><div class="stat-label">Duration</div><div class="stat-value">' + esc(dur) + '</div></div>';
    if (card.total_lines != null) html += '<div class="stat-box"><div class="stat-label">Lines of Code</div><div class="stat-value">' + Number(card.total_lines).toLocaleString() + '</div></div>';
    if (card.contributors != null) html += '<div class="stat-box"><div class="stat-label">Contributors</div><div class="stat-value">' + esc(String(card.contributors)) + '</div></div>';
    if (card.work_pattern) html += '<div class="stat-box"><div class="stat-label">Work Pattern</div><div class="stat-value">' + esc(card.work_pattern) + '</div></div>';
    html += '</div>';

    // Language Breakdown
    if (card.languages && Object.keys(card.languages).length) {
      var langKeys = Object.keys(card.languages).sort(function(a,b){return card.languages[b]-card.languages[a];}).slice(0,6);
      var langTotal = langKeys.reduce(function(s,k){return s+card.languages[k];},0);
      if (langTotal > 0) {
        html += '<div class="card-section-title">Language Breakdown</div>';
        html += '<div class="lang-stacked">';
        langKeys.forEach(function(k,i){
          var pct=(card.languages[k]/langTotal*100).toFixed(1);
          var c=LANG_COLORS[i%LANG_COLORS.length];
          html+='<div style="width:'+pct+'%;background:'+c+';height:100%;" title="'+esc(displayLang(k))+' '+pct+'%"></div>';
        });
        html += '</div><div class="lang-legend">';
        langKeys.forEach(function(k,i){
          var pct=(card.languages[k]/langTotal*100).toFixed(1);
          var c=LANG_COLORS[i%LANG_COLORS.length];
          html+='<div class="lang-legend-item"><div style="width:8px;height:8px;border-radius:2px;background:'+c+';flex-shrink:0;"></div><span>'+esc(displayLang(k))+'</span><span>'+pct+'%</span></div>';
        });
        html += '</div>';
      }
    }

    // Activity Breakdown
    if (card.commit_type_distribution && Object.keys(card.commit_type_distribution).length) {
      var ctEntries = Object.keys(card.commit_type_distribution)
        .map(function(k){return{key:k,val:card.commit_type_distribution[k]};})
        .sort(function(a,b){return b.val-a.val;})
        .slice(0,6);
      if (ctEntries.length) {
        html += '<div class="card-section-title">Activity Breakdown</div>';
        ctEntries.forEach(function(e){
          var lk=e.key.toLowerCase();
          var name=COMMIT_NAMES[lk]||e.key;
          var c=COMMIT_COLORS[lk]||'#6f7cff';
          var pct=Math.round(e.val);
          html+='<div class="activity-row"><span class="activity-label">'+esc(name)+'</span>'+
            '<div class="activity-track"><div class="activity-fill" style="width:'+Math.min(100,pct)+'%;background:'+c+';"></div></div>'+
            '<span class="activity-pct">'+pct+'%</span></div>';
        });
      }
    }

    html += '</div>'; // end .card-details

    // Meta: role + group project
    var meta = [];
    if (card.collaboration_role) meta.push(card.collaboration_role);
    if (card.is_group_project) meta.push('Group project');
    if (meta.length) {
      html += '<div class="card-meta">' + meta.map(esc).join(' \u00b7 ') + '</div>';
    }

    // GitHub link (only present if repo is public)
    if (card.repo_url) {
      html += '<a class="github-link" href="' + esc(card.repo_url) + '" target="_blank" rel="noopener noreferrer">' +
        '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" style="flex-shrink:0">' +
        '<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38' +
        ' 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52' +
        '-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2' +
        '-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82' +
        '.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12' +
        '.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01' +
        ' 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>' +
        '</svg>' +
        'View on GitHub</a>';
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
  }
}());
"""


_FIGURES_JS = """\
(function () {
  'use strict';

  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  if (typeof PORTFOLIO_DATA === 'undefined') return;

  var contrib  = PORTFOLIO_DATA.contribution || {};
  var personal = contrib.personal_timeline  || {};
  var totalTL  = contrib.total_timeline     || {};
  var skillAct = PORTFOLIO_DATA.skill_activity || {};

  var hasContrib = Object.keys(personal).length > 0 || Object.keys(totalTL).length > 0;
  var hasSkill   = Object.keys(skillAct).length > 0;

  if (!hasContrib && !hasSkill) {
    var fig = document.getElementById('figures');
    if (fig) fig.style.display = 'none';
    return;
  }

  if (hasContrib) {
    var cmEl = document.getElementById('contribution-map');
    if (cmEl) buildContributionMap(cmEl, personal, totalTL);
  }
  if (hasSkill) {
    var stEl = document.getElementById('skill-timeline');
    if (stEl) buildSkillTimeline(stEl, skillAct);
  }

  // ==========================================================
  // ContributionMap
  // ==========================================================
  function buildContributionMap(el, personal, total) {
    var ACCENT = '#002145';
    var ML = ['January','February','March','April','May','June',
              'July','August','September','October','November','December'];

    // Collect available years from data
    var yrs = {};
    [].concat(Object.keys(personal), Object.keys(total)).forEach(function (d) {
      if (/^\\d{4}-\\d{2}-\\d{2}$/.test(d)) yrs[d.slice(0, 4)] = true;
    });
    var sortedYears = Object.keys(yrs).sort();
    if (!sortedYears.length) return;

    var yIdx = sortedYears.length - 1;
    var mode = 'personal';

    // Build DOM skeleton
    el.className = 'figure-card';

    var hdr = el.appendChild(document.createElement('div'));
    hdr.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px;';

    var hTitle = hdr.appendChild(document.createElement('h3'));
    hTitle.textContent = 'Contribution Map';
    hTitle.style.cssText = 'margin:0;font-size:18px;font-weight:600;';

    var btnRow = hdr.appendChild(document.createElement('div'));
    btnRow.style.cssText = 'display:flex;gap:8px;';

    function mkBtn(label, active) {
      var b = document.createElement('button');
      b.textContent = label;
      b.style.cssText = 'padding:6px 10px;border-radius:7px;font-size:12px;font-weight:500;cursor:pointer;border:1px solid ' + ACCENT + ';transition:all 0.2s;';
      b.style.background = active ? ACCENT : 'transparent';
      b.style.color      = active ? '#fff' : ACCENT;
      return b;
    }
    var btnP = btnRow.appendChild(mkBtn('Personal', true));
    var btnR = btnRow.appendChild(mkBtn('Ratio View', false));

    var desc = el.appendChild(document.createElement('p'));
    desc.style.cssText = 'margin:0 0 12px;font-size:12px;color:#888;';

    var grid = el.appendChild(document.createElement('div'));
    grid.style.cssText = 'display:flex;gap:3px;overflow-x:auto;padding-bottom:8px;min-height:90px;';

    // Footer: legend + year nav
    var foot = el.appendChild(document.createElement('div'));
    foot.style.cssText = 'margin-top:16px;padding-top:12px;border-top:1px solid #e0e0e0;display:flex;align-items:center;justify-content:space-between;font-size:11px;color:#888;flex-wrap:wrap;gap:8px;';

    var leg = foot.appendChild(document.createElement('div'));
    leg.style.cssText = 'display:flex;align-items:center;gap:8px;';
    leg.innerHTML = '<span>Less</span>' +
      [0, 0.25, 0.5, 0.75, 1].map(function (op) {
        var bg = op === 0 ? '#e8e8e8' : 'rgba(0,33,69,' + op + ')';
        return '<div style="width:10px;height:10px;border-radius:2px;background:' + bg + ';display:inline-block;margin:0 1px;"></div>';
      }).join('') +
      '<span>More</span>';

    var ynav = foot.appendChild(document.createElement('div'));
    ynav.style.cssText = 'display:flex;align-items:center;gap:6px;';

    var prevBtn = ynav.appendChild(document.createElement('button'));
    prevBtn.innerHTML = '\\u2190';
    var yearLbl = ynav.appendChild(document.createElement('span'));
    yearLbl.style.cssText = 'min-width:50px;text-align:center;font-size:11px;font-weight:600;color:' + ACCENT + ';';
    var nextBtn = ynav.appendChild(document.createElement('button'));
    nextBtn.innerHTML = '\\u2192';
    [prevBtn, nextBtn].forEach(function (b) {
      b.style.cssText = 'padding:4px 8px;background:transparent;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;';
    });

    var tooltip = document.body.appendChild(document.createElement('div'));
    tooltip.style.cssText = 'position:fixed;pointer-events:none;display:none;background:#ffffff;border:1px solid #e0e0e0;border-radius:8px;padding:8px 12px;font-size:12px;color:' + ACCENT + ';z-index:1000;box-shadow:0 4px 16px rgba(0,0,0,0.12);white-space:nowrap;';

    function draw() {
      var yr = sortedYears[yIdx];
      yearLbl.textContent = yr;

      var canPrev = yIdx > 0, canNext = yIdx < sortedYears.length - 1;
      prevBtn.disabled = !canPrev;
      nextBtn.disabled = !canNext;
      prevBtn.style.border = '1px solid ' + (canPrev ? ACCENT : '#444');
      prevBtn.style.color  = canPrev ? ACCENT : '#555';
      nextBtn.style.border = '1px solid ' + (canNext ? ACCENT : '#444');
      nextBtn.style.color  = canNext ? ACCENT : '#555';

      desc.textContent = mode === 'personal'
        ? 'Contribution activity as a function of commits'
        : 'Your activity as a percentage of total team contributions';

      // Generate dates for this year
      var dates = [];
      var cur = new Date(Date.UTC(+yr, 0, 1));
      var end = new Date(Date.UTC(+yr, 11, 31));
      while (cur <= end) {
        dates.push(cur.toISOString().slice(0, 10));
        cur.setUTCDate(cur.getUTCDate() + 1);
      }

      // Normalisation values
      var maxP = 1;
      dates.forEach(function (d) { if ((personal[d] || 0) > maxP) maxP = personal[d]; });
      var maxR = 0.1;
      if (mode === 'ratio') {
        dates.forEach(function (d) {
          var u = personal[d] || 0, t = total[d] || 0;
          if (t > 0 && u > 0) { var r = u / t; if (r > maxR) maxR = r; }
        });
      }

      // Group into Sunday-start weeks
      var weeks = [], wk = [];
      dates.forEach(function (d) {
        if (new Date(d + 'T12:00:00Z').getUTCDay() === 0 && wk.length) { weeks.push(wk); wk = []; }
        wk.push(d);
      });
      if (wk.length) weeks.push(wk);

      grid.innerHTML = '';
      weeks.forEach(function (week) {
        var col = document.createElement('div');
        col.style.cssText = 'display:flex;flex-direction:column;gap:3px;flex-shrink:0;';
        week.forEach(function (d) {
          var u = personal[d] || 0, t = total[d] || 0;
          var opacity = 0;
          if (mode === 'personal') {
            opacity = u > 0 ? Math.max(0.1, u / maxP) : 0;
          } else {
            if (u > 0 && t > 0) opacity = Math.max(0.1, (u / t) / maxR);
          }
          var bg = opacity === 0 ? '#e8e8e8' : 'rgba(0,33,69,' + opacity.toFixed(3) + ')';
          var sq = document.createElement('div');
          sq.style.cssText = 'width:11px;height:11px;border-radius:2px;background:' + bg + ';flex-shrink:0;cursor:default;';
          if (u > 0) {
            var dateObj = new Date(d + 'T12:00:00Z');
            var lbl = ML[dateObj.getUTCMonth()] + ' ' + dateObj.getUTCDate() + ', ' + dateObj.getUTCFullYear() +
              ': ' + u + ' commit' + (u !== 1 ? 's' : '');
            if (mode === 'ratio' && t > 0) lbl += ' (' + Math.round(u / t * 100) + '% of team)';
            (function (lbl) {
              sq.addEventListener('mouseenter', function (e) { tooltip.textContent = lbl; tooltip.style.display = 'block'; tooltip.style.left = (e.clientX + 14) + 'px'; tooltip.style.top = (e.clientY + 14) + 'px'; });
              sq.addEventListener('mousemove', function (e) { tooltip.style.left = (e.clientX + 14) + 'px'; tooltip.style.top = (e.clientY + 14) + 'px'; });
              sq.addEventListener('mouseleave', function () { tooltip.style.display = 'none'; });
            }(lbl));
          }
          col.appendChild(sq);
        });
        grid.appendChild(col);
      });
    }

    btnP.addEventListener('click', function () {
      mode = 'personal';
      btnP.style.background = ACCENT; btnP.style.color = '#fff';
      btnR.style.background = 'transparent'; btnR.style.color = ACCENT;
      draw();
    });
    btnR.addEventListener('click', function () {
      mode = 'ratio';
      btnR.style.background = ACCENT; btnR.style.color = '#fff';
      btnP.style.background = 'transparent'; btnP.style.color = ACCENT;
      draw();
    });
    prevBtn.addEventListener('click', function () { if (yIdx > 0) { yIdx--; draw(); } });
    nextBtn.addEventListener('click', function () { if (yIdx < sortedYears.length - 1) { yIdx++; draw(); } });

    draw();
  }

  // ==========================================================
  // SkillTimelineGraph
  // ==========================================================
  function buildSkillTimeline(el, skillAct) {
    var COLORS = ['#0055B7','#0891b2','#d97706','#65a30d','#be185d',
                  '#0f766e','#ea580c','#4f46e5','#b45309','#7c3aed'];
    var MS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

    // 1. Aggregate into monthly counts
    var monthly = {}, totals = {}, minD = null, maxD = null;
    Object.keys(skillAct).forEach(function (skill) {
      var byDate = skillAct[skill] || {};
      Object.keys(byDate).forEach(function (ds) {
        var cnt = +(byDate[ds]) || 0;
        if (cnt <= 0) return;
        var d = new Date(ds);
        if (isNaN(d.getTime())) return;
        if (!minD || d < minD) minD = new Date(d);
        if (!maxD || d > maxD) maxD = new Date(d);
        var mk = ds.slice(0, 7);
        if (!monthly[skill]) monthly[skill] = {};
        monthly[skill][mk] = (monthly[skill][mk] || 0) + cnt;
        totals[skill] = (totals[skill] || 0) + cnt;
      });
    });

    var skills = Object.keys(totals).sort(function (a, b) { return totals[b] - totals[a]; });
    if (!skills.length || !minD || !maxD) return;

    // 2. Month buckets
    var buckets = [];
    var cur = new Date(minD.getFullYear(), minD.getMonth(), 1);
    var endM = new Date(maxD.getFullYear(), maxD.getMonth(), 1);
    while (cur <= endM) {
      var yr4 = cur.getFullYear(), mo = cur.getMonth();
      var mk = yr4 + '-' + String(mo + 1).padStart(2, '0');
      buckets.push({
        key:   mk,
        short: MS[mo] + " '" + String(yr4).slice(2),
        full:  MS[mo] + ' ' + yr4
      });
      cur.setMonth(mo + 1);
    }

    // 3. Cumulative series
    var cumul = {}, gMax = 1;
    skills.forEach(function (s) {
      var run = 0;
      cumul[s] = buckets.map(function (b) { run += (monthly[s] && monthly[s][b.key]) || 0; return run; });
      var last = cumul[s][buckets.length - 1] || 0;
      if (last > gMax) gMax = last;
    });

    var mode = 'stacked';

    // Build wrapper DOM
    el.className = 'figure-card';

    var hdr = el.appendChild(document.createElement('div'));
    hdr.style.cssText = 'display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;gap:12px;flex-wrap:wrap;';

    var hTitle = hdr.appendChild(document.createElement('h3'));
    hTitle.textContent = 'Most Utilized Skills';
    hTitle.style.cssText = 'margin:0;font-size:18px;font-weight:600;';

    var tgl = hdr.appendChild(document.createElement('div'));
    var btnS = tgl.appendChild(document.createElement('button'));
    btnS.textContent = 'Stacked';
    btnS.style.cssText = 'padding:4px 12px;font-size:12px;border-radius:6px 0 0 6px;border:1px solid #d0d0d0;background:#002145;color:#ffffff;cursor:pointer;font-weight:600;';
    var btnI = tgl.appendChild(document.createElement('button'));
    btnI.textContent = 'Individual';
    btnI.style.cssText = 'padding:4px 12px;font-size:12px;border-radius:0 6px 6px 0;border:1px solid #d0d0d0;border-left:none;background:transparent;color:#666;cursor:pointer;';

    var subDesc = el.appendChild(document.createElement('p'));
    subDesc.textContent = 'Cumulative running total of skill occurrences across all projects.';
    subDesc.style.cssText = 'margin:0 0 12px;font-size:12px;color:#999;';

    var chartArea = el.appendChild(document.createElement('div'));

    // ---- Shared helpers ----
    function ticks(len) {
      if (len <= 1) return [0];
      if (len <= 6) { var r = []; for (var i = 0; i < len; i++) r.push(i); return r; }
      var step = (len - 1) / 5, s = {};
      s[0] = s[len - 1] = true;
      for (var t = 1; t < 5; t++) s[Math.round(step * t)] = true;
      return Object.keys(s).map(Number).sort(function (a, b) { return a - b; });
    }

    // ---- Stacked view ----
    function renderStacked() {
      var vis = skills.filter(function (s) { return (totals[s] || 0) >= 10; });
      if (!vis.length) {
        chartArea.innerHTML = '<p style="color:#999;padding:20px;text-align:center;">Not enough data (\u226510 occurrences required per skill).</p>';
        return;
      }
      var n = buckets.length;
      var W = 760, H = 380, L = 8, R = 8, T = 12, B = 30;
      var CW = W - L - R, CH = H - T - B;

      var gmI = Math.max.apply(null, vis.map(function (s) { return cumul[s][n - 1] || 0; }).concat([1]));
      function ln(v) { return Math.log(1 + v) / Math.log(1 + gmI); }

      // Log-stacked series
      var ls = [];
      vis.forEach(function (s, k) {
        var logS = (cumul[s] || []).map(ln);
        ls.push(k === 0 ? logS.slice() : logS.map(function (v, i) { return v + (ls[k - 1][i] || 0); }));
      });
      var tH = Math.max(1, (ls[ls.length - 1] || [])[n - 1] || 1);

      function xA(i) { return (L + (i / Math.max(1, n - 1)) * CW).toFixed(2); }
      function yA(v) { return (T + (1 - v / tH) * CH).toFixed(2); }

      // Legend
      var legHtml = '<div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:14px;">';
      vis.forEach(function (s, k) {
        var c = COLORS[k % COLORS.length];
        legHtml += '<div style="display:flex;align-items:center;gap:5px;">' +
          '<div style="width:10px;height:10px;border-radius:2px;background:' + c + ';flex-shrink:0;"></div>' +
          '<span style="font-size:12px;color:#333;">' + esc(s) + '</span>' +
          '<span style="font-size:11px;color:#888;">(' + (totals[s] || 0) + ')</span></div>';
      });
      legHtml += '</div>';

      var svg = ['<svg width="100%" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" style="display:block;">'];
      [0.25, 0.5, 0.75, 1].forEach(function (r) {
        var y = (T + CH * (1 - r)).toFixed(2);
        svg.push('<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y + '" y2="' + y + '" stroke="#e8e8e8" stroke-width="1"/>');
      });
      vis.forEach(function (s, k) {
        var top = ls[k] || [], bot = k === 0 ? new Array(n).fill(0) : (ls[k - 1] || []);
        var c = COLORS[k % COLORS.length];
        var tp = top.map(function (v, i) { return (i ? 'L' : 'M') + ' ' + xA(i) + ' ' + yA(v); }).join(' ');
        var bp = bot.slice().reverse().map(function (v, ri) { return 'L ' + xA(n - 1 - ri) + ' ' + yA(v); }).join(' ');
        svg.push('<path d="' + tp + ' ' + bp + ' Z" fill="' + c + '" fill-opacity="0.75"/>');
        svg.push('<path d="' + tp + '" fill="none" stroke="' + c + '" stroke-width="1.2" stroke-opacity="0.9"/>');
      });
      ticks(n).forEach(function (i) {
        svg.push('<text x="' + xA(i) + '" y="' + (H - 6) + '" text-anchor="middle" fill="#7f7f7f" font-size="9">' + esc((buckets[i] || {}).short || '') + '</text>');
      });
      svg.push('</svg>');

      chartArea.innerHTML = legHtml + '<div style="border-radius:8px;border:1px solid #e0e0e0;background:#ffffff;padding:10px 4px 4px;">' + svg.join('') + '</div>';

      // ---- Hover tooltip for stacked chart ----
      var svgEl = chartArea.querySelector('svg');
      var wrapper = chartArea.querySelector('div');
      if (svgEl && wrapper) {
        wrapper.style.position = 'relative';
        var tip = wrapper.appendChild(document.createElement('div'));
        tip.style.cssText = 'position:absolute;pointer-events:none;display:none;background:#ffffff;border:1px solid #e0e0e0;border-radius:8px;padding:10px 14px;font-size:12px;color:#333;z-index:10;min-width:160px;box-shadow:0 4px 16px rgba(0,0,0,0.12);';
        svgEl.style.cursor = 'crosshair';
        svgEl.addEventListener('mousemove', function(e) {
          var svgRect = svgEl.getBoundingClientRect();
          var mx = (e.clientX - svgRect.left) / svgRect.width * W;
          var idx = Math.round((mx - L) / CW * Math.max(1, n - 1));
          idx = Math.max(0, Math.min(n - 1, idx));
          var b = buckets[idx];
          if (!b) { tip.style.display = 'none'; return; }
          var tHtml = '<div style="font-weight:600;margin-bottom:7px;color:#111111;border-bottom:1px solid #e0e0e0;padding-bottom:6px;">' + esc(b.full) + '</div>';
          vis.forEach(function(s, k) {
            var c = COLORS[k % COLORS.length], cnt = cumul[s][idx] || 0;
            tHtml += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">' +
              '<div style="width:8px;height:8px;border-radius:2px;background:' + c + ';flex-shrink:0;"></div>' +
              '<span style="flex:1;">' + esc(s) + '</span>' +
              '<span style="color:#777;min-width:30px;text-align:right;">' + cnt + '</span>' +
              '</div>';
          });
          tip.innerHTML = tHtml;
          var wrapRect = wrapper.getBoundingClientRect();
          var tx = e.clientX - wrapRect.left + 14;
          var ty = e.clientY - wrapRect.top - 20;
          if (tx + 200 > wrapRect.width) tx -= 220;
          if (ty < 0) ty = 4;
          tip.style.left = tx + 'px'; tip.style.top = ty + 'px'; tip.style.display = 'block';
        });
        svgEl.addEventListener('mouseleave', function() { tip.style.display = 'none'; });
      }
    }

    // ---- Individual (small multiples) view ----
    function renderIndividual() {
      var vis = skills.slice(0, 5).filter(function (s) { return (totals[s] || 0) > 0; });
      if (!vis.length) { chartArea.innerHTML = '<p style="color:#999;padding:20px;text-align:center;">No skill data.</p>'; return; }
      var W = 400, H = 140, LP = 10, RP = 10, TP = 12, BP = 22;
      var CW2 = W - LP - RP, CH2 = H - TP - BP;
      var n = buckets.length;
      function logS(v) { return gMax <= 1 ? v / gMax : Math.log(1 + v) / Math.log(1 + gMax); }
      function xF(i) { return (LP + (i / Math.max(1, n - 1)) * CW2).toFixed(2); }
      function yF(v) { return (TP + (1 - logS(v)) * CH2).toFixed(2); }
      var html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(400px,1fr));gap:24px;padding-top:8px;">';
      vis.forEach(function (s, idx) {
        var c = COLORS[idx % COLORS.length], ser = cumul[s] || [], tot = totals[s] || 0;
        var lp = ser.map(function (v, i) { return (i ? 'L' : 'M') + ' ' + xF(i) + ' ' + yF(v); }).join(' ');
        var btm = (TP + CH2).toFixed(2);
        var ap = lp + ' L ' + xF(n - 1) + ' ' + btm + ' L ' + xF(0) + ' ' + btm + ' Z';
        var svg = ['<svg width="100%" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" style="display:block;">'];
        [0.25, 0.5, 0.75, 1].forEach(function (r) {
          var y = (TP + CH2 * (1 - r)).toFixed(2);
          svg.push('<line x1="' + LP + '" x2="' + (W - RP) + '" y1="' + y + '" y2="' + y + '" stroke="#e8e8e8" stroke-width="1"/>');
        });
        if (lp) {
          svg.push('<path d="' + ap + '" fill="' + c + '" fill-opacity="0.2"/>');
          svg.push('<path d="' + lp + '" fill="none" stroke="' + c + '" stroke-width="2"/>');
        }
        ser.forEach(function (v, i) {
          var lbl = ((buckets[i] || {}).full || '') + ': ' + v + ' occurrence' + (v !== 1 ? 's' : '') + ' cumulative';
          svg.push('<circle cx="' + xF(i) + '" cy="' + yF(v) + '" r="2.4" fill="' + c + '" stroke="#121212" stroke-width="0.6"><title>' + esc(lbl) + '</title></circle>');
        });
        ticks(n).forEach(function (i) {
          svg.push('<text x="' + xF(i) + '" y="' + (H - 6) + '" text-anchor="middle" fill="#7f7f7f" font-size="9">' + esc((buckets[i] || {}).short || '') + '</text>');
        });
        svg.push('</svg>');
        html += '<div style="border:1px solid #e0e0e0;border-radius:10px;background:#ffffff;padding:18px;border-top:3px solid ' + c + ';">' +
          '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">' +
          '<div style="color:#111111;font-size:13px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + esc(s) + '">' + esc(s) + '</div>' +
          '<div style="color:#777777;font-size:11px;">' + tot + ' occurrence' + (tot !== 1 ? 's' : '') + '</div></div>' +
          svg.join('') + '</div>';
      });
      html += '</div>';
      chartArea.innerHTML = html;
    }

    btnS.addEventListener('click', function () {
      mode = 'stacked';
      btnS.style.background = '#002145'; btnS.style.color = '#ffffff'; btnS.style.fontWeight = '600';
      btnI.style.background = 'transparent'; btnI.style.color = '#666'; btnI.style.fontWeight = '';
      renderStacked();
    });
    btnI.addEventListener('click', function () {
      mode = 'individual';
      btnI.style.background = '#002145'; btnI.style.color = '#ffffff'; btnI.style.fontWeight = '600';
      btnS.style.background = 'transparent'; btnS.style.color = '#666'; btnS.style.fontWeight = '';
      renderIndividual();
    });

    renderStacked();
  }

}());
"""


def _get_github_repo_url(username: str, repo_name: str, token: Optional[str] = None) -> Optional[str]:
    """
    Returns the GitHub HTML URL if the repo exists and is public, else None.
    Uses the OAuth token when available for a higher API rate limit.
    """
    api_url = f"https://api.github.com/repos/{username}/{repo_name}"
    req = urllib.request.Request(api_url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not data.get("private", True):
                return data.get("html_url") or f"https://github.com/{username}/{repo_name}"
    except Exception:
        pass
    return None


def _render_section_html(section) -> str:
    """
    Render a PortfolioSection as HTML, producing proper semantic elements:
    - TextBlock → <p class="block-text">
    - TextListBlock → <ul class="block-list"><li>...</li></ul>
    - Unknown types → escaped plain text in a <p>
    """
    parts = []
    for tag in section.block_order:
        block = section.blocks_by_tag.get(tag)
        if block is None or block.current_content is None:
            continue
        content = block.current_content
        ctype = content.content_type.value if hasattr(content, "content_type") else ""
        if ctype == "TextList":
            items_html = "".join(
                f"<li>{_esc(item)}</li>" for item in content.items
            )
            parts.append(f'      <ul class="block-list">{items_html}</ul>')
        elif ctype == "Text":
            text = content.text
            if text:
                parts.append(f'      <p class="block-text">{_esc(text)}</p>')
        else:
            rendered = content.render()
            if rendered:
                parts.append(f'      <p class="block-text">{_esc(rendered)}</p>')
    return "\n".join(parts)


def export_portfolio_static(portfolio_id: int, session: Session) -> bytes:
    """
    Build and return a ZIP archive containing a static web portfolio for the
    given `portfolio_id`.

    The archive contains:
    - `index.html`
    - `portfolio_data.js`
    - `style.css`
    - `filter.js`
    - `figures.js`

    Raises `KeyNotFoundError` if the portfolio does not exist.
    """
    portfolio = load_portfolio(session, portfolio_id)
    if portfolio is None:
        raise KeyNotFoundError(f"No portfolio with ID {portfolio_id}")

    # --- Build Part A HTML (sections) ---
    sections_html_parts = []
    for section in portfolio.sections:
        rendered_blocks_html = _render_section_html(section)
        sections_html_parts.append(
            f'    <div class="narrative-section" id="section-{_esc(section.id)}">\n'
            f'      <h2><a class="section-anchor" href="#section-{_esc(section.id)}">'
            f'{_esc(section.title)}</a></h2>\n'
            f'{rendered_blocks_html}\n'
            f'    </div>'
        )
    sections_html = "\n".join(sections_html_parts)

    # --- Build section navigation links ---
    nav_links_html = "".join(
        f'<a href="#section-{_esc(s.id)}">{_esc(s.title)}</a>'
        for s in portfolio.sections
    ) + '<a href="#figures">Figures</a><a href="#gallery">Projects</a>'
    nav_html = f'<div class="nav-links">{nav_links_html}</div>'

    # --- Format last updated date ---
    last_updated = portfolio.metadata.last_updated_at.strftime("%-d %b %Y")

    # --- Build Part C card data ---
    card_models = get_project_cards_for_portfolio(session, portfolio_id)
    cards_data = []
    for c in card_models:
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
            # Populated later from ProjectReportModel / GitHub API
            "total_lines": None,
            "contributors": None,
            "commit_share": None,
            "loc_share": None,
            "repo_url": None,
        })

    # --- Aggregate figures data from project reports ---
    # COMMIT_ACTIVITY_TIMELINE / TOTAL_COMMIT_ACTIVITY_TIMELINE: {date: count}
    # PROJECT_SKILL_ACTIVITY: {skill: [date, ...]}
    project_names = [c.project_name for c in card_models]
    personal_timeline: dict = {}
    total_timeline: dict = {}
    skill_activity: dict = {}  # {skill: {date: count}}

    try:
        report_models = get_project_report_models_by_names(session, project_names)
        report_by_name = {rm.project_name: rm for rm in (report_models or []) if rm is not None}
        for i, pname in enumerate(project_names):
            rm = report_by_name.get(pname)
            if rm is None:
                continue
            stat = rm.statistic or {}

            # Per-project card stats
            cards_data[i]["total_lines"] = stat.get("TOTAL_PROJECT_LINES")
            cards_data[i]["contributors"] = stat.get("TOTAL_AUTHORS")
            cards_data[i]["commit_share"] = stat.get("USER_COMMIT_PERCENTAGE")
            cards_data[i]["loc_share"] = stat.get("TOTAL_CONTRIBUTION_PERCENTAGE")

            for d, cnt in (stat.get("COMMIT_ACTIVITY_TIMELINE") or {}).items():
                personal_timeline[d] = personal_timeline.get(d, 0) + int(cnt)

            for d, cnt in (stat.get("TOTAL_COMMIT_ACTIVITY_TIMELINE") or {}).items():
                total_timeline[d] = total_timeline.get(d, 0) + int(cnt)

            for skill, dates in (stat.get("PROJECT_SKILL_ACTIVITY") or {}).items():
                if not isinstance(dates, list):
                    continue
                if skill not in skill_activity:
                    skill_activity[skill] = {}
                for d in dates:
                    if isinstance(d, str):
                        skill_activity[skill][d] = skill_activity[skill].get(d, 0) + 1
    except Exception:
        pass  # Figures data is non-critical; silently omit if unavailable

    # --- Populate GitHub repo URLs for public repos ---
    try:
        user_config = get_most_recent_user_config(session)
        github_username = (user_config.github or "").strip()
        github_token = user_config.access_token
        if github_username:
            for card_data in cards_data:
                card_data["repo_url"] = _get_github_repo_url(
                    github_username, card_data["project_name"], github_token
                )
    except Exception:
        pass  # GitHub links are non-critical

    portfolio_data = {
        "portfolio_id": portfolio_id,
        "title": portfolio.title,
        "last_updated_at": portfolio.metadata.last_updated_at.isoformat(),
        "project_cards": cards_data,
        "contribution": {
            "personal_timeline": personal_timeline,
            "total_timeline": total_timeline,
        },
        "skill_activity": skill_activity,
    }
    portfolio_data_js = "var PORTFOLIO_DATA = " + json.dumps(
        portfolio_data, default=_json_default, indent=2
    ) + ";\n"

    # --- Build index.html ---
    index_html = _HTML_TEMPLATE.format(
        title=_esc(portfolio.title),
        sections_html=sections_html,
        nav_html=nav_html,
        last_updated=_esc(last_updated),
    )

    # --- Assemble ZIP ---
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", index_html)
        zf.writestr("portfolio_data.js", portfolio_data_js)
        zf.writestr("style.css", _CSS)
        zf.writestr("filter.js", _FILTER_JS)
        zf.writestr("figures.js", _FIGURES_JS)

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
