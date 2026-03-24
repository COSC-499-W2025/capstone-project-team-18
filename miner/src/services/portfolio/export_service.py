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
  }
}());
"""


def export_portfolio_static(portfolio_id: int, session: Session) -> bytes:
    """
    Build and return a ZIP archive containing a self-contained static web
    portfolio for the given portfolio_id.

    The archive contains:
      index.html, portfolio_data.js, style.css, filter.js

    Raises KeyNotFoundError if the portfolio does not exist.
    """
    portfolio = load_portfolio(session, portfolio_id)
    if portfolio is None:
        raise KeyNotFoundError(f"No portfolio with id {portfolio_id}")

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
        })

    portfolio_data = {
        "portfolio_id": portfolio_id,
        "title": portfolio.title,
        "project_cards": cards_data,
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
