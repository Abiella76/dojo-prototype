"""Custom HTML/SVG components.

Small pieces (chips, notes) render inline through `st.markdown` so they sit in
the same document as the widgets around them. Bigger self-contained visuals —
the belt hero, the streak heatmap, the achievement grid — render through
`st.iframe`, which gives them a real isolated DOM where hover
states, gradients and animation behave properly.
"""

from __future__ import annotations

import html
from datetime import date, timedelta
from typing import Any, Iterable

import streamlit as st

from ..config import PRIORITY_COLORS, PRIORITY_GLYPHS, SEQUENTIAL
from .theme import css_vars, tokens


def esc(value: Any) -> str:
    """Escape anything user-typed before it goes near an HTML string."""
    return html.escape(str(value), quote=True)


def _frame(body: str, mode: str, height: int, *, extra_css: str = "") -> None:
    """Wrap component markup in a document that inherits the app's tokens."""
    st.iframe(
        f"""<!doctype html><html><head><meta charset="utf-8"><style>
:root {{
{css_vars(mode)}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: transparent; color: var(--text);
  font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased;
}}
@media (prefers-reduced-motion: reduce) {{
  * {{ animation: none !important; transition: none !important; }}
}}
{extra_css}
</style></head><body>{body}</body></html>""",
        height=height,
    )


# ────── inline pieces ──────

def priority_chip(priority: str) -> str:
    colour = PRIORITY_COLORS.get(priority, "#888")
    glyph = PRIORITY_GLYPHS.get(priority, "")
    # Glyph + label ride along with the colour, so severity never depends on hue alone.
    return (f'<span class="chip chip-prio" style="background:{colour}">'
            f'<span aria-hidden="true">{glyph}</span>{esc(priority)}</span>')


def task_meta(task: dict, *, today: date | None = None, sub_done: int = 0, sub_total: int = 0) -> str:
    today = today or date.today()
    parts = [priority_chip(task.get("priority", "Medium"))]

    due = task.get("due_date")
    if due:
        try:
            due_on = date.fromisoformat(due)
            delta = (due_on - today).days
            if delta < 0:
                label, cls = f"{abs(delta)}d overdue", "chip chip-due chip-overdue"
            elif delta == 0:
                label, cls = "due today", "chip chip-due chip-overdue"
            elif delta == 1:
                label, cls = "due tomorrow", "chip chip-due"
            else:
                label, cls = f"due {due_on.strftime('%b %-d')}", "chip chip-due"
            parts.append(f'<span class="{cls}">{esc(label)}</span>')
        except ValueError:
            pass

    for tag in task.get("tags") or []:
        parts.append(f'<span class="chip chip-tag">#{esc(tag)}</span>')

    if task.get("carried_from"):
        parts.append(f'<span class="chip chip-carried">carried from {esc(task["carried_from"])}</span>')

    if sub_total:
        parts.append(f'<span class="sub-progress">{sub_done}/{sub_total} steps</span>')

    return f'<div class="task-meta">{"".join(parts)}</div>'


def task_header(task: dict, **kwargs) -> None:
    """Priority anchor + meta chips + title, as one markdown block."""
    anchor = f'<span class="prio-{esc(task.get("priority", "Medium")).lower()}"></span>'
    done_cls = " card-done" if task.get("completed") else ""
    st.markdown(
        f'<div class="task-head{done_cls}">{anchor}{task_meta(task, **kwargs)}'
        f'<p class="task-title">{esc(task["text"])}</p></div>',
        unsafe_allow_html=True,
    )


def note_block(text: str) -> None:
    st.markdown(f'<div class="note-body">{esc(text)}</div>', unsafe_allow_html=True)


# ────── hero: belt, XP, streak ──────

def hero(stats: dict[str, Any], name: str, day: dict[str, int], mode: str) -> None:
    t = tokens(mode)
    progress = stats["progress"]
    radius, circumference = 46, 2 * 3.14159 * 46
    offset = circumference * (1 - progress)
    belt_colour = stats["belt_color"]
    next_label = (f'{stats["next_belt_at"] - stats["xp"]:,} XP to next belt'
                  if stats["next_belt_at"] else "Highest rank held")
    score = day["score"]

    body = f"""
<div class="hero">
  <div class="ring-wrap" role="img"
       aria-label="{esc(stats['belt'])} belt, level {stats['level']}, {progress:.0%} to next belt">
    <svg viewBox="0 0 110 110" width="110" height="110">
      <circle cx="55" cy="55" r="{radius}" fill="none" stroke="var(--surface-3)" stroke-width="8"/>
      <circle cx="55" cy="55" r="{radius}" fill="none" stroke="{belt_colour}" stroke-width="8"
              stroke-linecap="round" stroke-dasharray="{circumference:.1f}"
              stroke-dashoffset="{circumference:.1f}"
              transform="rotate(-90 55 55)">
        <animate attributeName="stroke-dashoffset" from="{circumference:.1f}" to="{offset:.1f}"
                 dur="0.9s" fill="freeze" calcMode="spline"
                 keySplines="0.22 0.61 0.36 1" keyTimes="0;1"/>
      </circle>
      <text x="55" y="51" text-anchor="middle" class="ring-lv">LV {stats['level']}</text>
      <text x="55" y="70" text-anchor="middle" class="ring-belt">{esc(stats['belt'])}</text>
    </svg>
  </div>
  <div class="hero-main">
    <p class="hero-kicker">{esc(name)}'s dojo</p>
    <p class="hero-xp"><b>{stats['xp']:,}</b> XP</p>
    <div class="bar" aria-hidden="true"><i style="--w:{progress * 100:.1f}%;background:{belt_colour}"></i></div>
    <p class="hero-sub">{esc(next_label)}</p>
  </div>
  <div class="hero-stats">
    <div class="stat"><b>{stats['streak']}</b><span>day streak</span></div>
    <div class="stat"><b>{score}%</b><span>today</span></div>
    <div class="stat"><b>{day['done']}/{day['total']}</b><span>tasks</span></div>
  </div>
</div>
"""
    css = f"""
.hero {{
  display: flex; align-items: center; gap: 26px; flex-wrap: wrap;
  padding: 20px 24px; border-radius: 16px;
  background: linear-gradient(135deg, var(--surface-2) 0%, var(--surface-3) 100%);
  border: 1px solid var(--border); box-shadow: {t['shadow']};
}}
.ring-lv {{ fill: var(--text); font-size: 15px; font-weight: 700; letter-spacing: .02em; }}
.ring-belt {{ fill: var(--text-2); font-size: 10.5px; font-weight: 600; letter-spacing: .09em;
              text-transform: uppercase; }}
.hero-main {{ flex: 1 1 220px; min-width: 200px; }}
.hero-kicker {{ margin: 0 0 2px; font-size: .72rem; font-weight: 650; letter-spacing: .1em;
                text-transform: uppercase; color: var(--text-3); }}
.hero-xp {{ margin: 0 0 10px; font-size: 1.05rem; color: var(--text-2); }}
.hero-xp b {{ font-size: 2rem; color: var(--text); font-variant-numeric: tabular-nums;
              letter-spacing: -.02em; margin-right: 4px; }}
.bar {{ height: 7px; border-radius: 99px; background: var(--surface); overflow: hidden;
        border: 1px solid var(--border); }}
.bar i {{ display: block; height: 100%; width: 0; border-radius: 99px;
          animation: grow .9s cubic-bezier(.22,.61,.36,1) forwards; }}
@keyframes grow {{ to {{ width: var(--w); }} }}
.hero-sub {{ margin: 7px 0 0; font-size: .78rem; color: var(--text-3); }}
.hero-stats {{ display: flex; gap: 10px; }}
.stat {{ min-width: 82px; padding: 11px 13px; border-radius: 12px; background: var(--surface);
         border: 1px solid var(--border); text-align: center; }}
.stat b {{ display: block; font-size: 1.4rem; font-weight: 650; letter-spacing: -.02em;
           font-variant-numeric: tabular-nums; }}
.stat span {{ font-size: .68rem; color: var(--text-3); text-transform: uppercase;
              letter-spacing: .07em; }}
"""
    _frame(body, mode, height=178, extra_css=css)


# ────── streak heatmap ──────

def heatmap(day_xp: dict[str, int], mode: str, *, weeks: int = 52,
            today: date | None = None) -> None:
    """GitHub-style calendar of daily XP.

    Sequential encoding: one hue, light to dark. The lightest step means "near
    zero", so an empty day recedes into the surface rather than competing. The
    grid is drawn at a fixed cell size and scrolls horizontally inside its own
    container rather than scaling to fit, which would distort the cells.
    """
    today = today or date.today()
    start = today - timedelta(days=weeks * 7 - 1)
    start -= timedelta(days=(start.weekday() + 1) % 7)  # back to a Sunday

    values = [v for v in day_xp.values() if v > 0]
    peak = max(values) if values else 1
    cuts = [peak * f for f in (0.0, 0.2, 0.4, 0.6, 0.8)]

    def step(xp: int) -> str:
        if xp <= 0:
            return "var(--surface-3)"
        for i in range(len(cuts) - 1, -1, -1):
            if xp > cuts[i]:
                return SEQUENTIAL[min(i + 1, len(SEQUENTIAL) - 1)]
        return SEQUENTIAL[0]

    cell, gap, top = 13, 3, 16
    pitch = cell + gap
    cells, months = [], []
    cursor, col, last_month = start, 0, None

    while cursor <= today:
        for row in range(7):
            if cursor > today:
                break
            if row == 0 and cursor.month != last_month:
                # Skip a label that would collide with the previous one — the
                # first column is usually a stub of the month before.
                if not months or col * pitch - months[-1][0] >= 3 * pitch:
                    months.append((col * pitch, cursor.strftime("%b")))
                last_month = cursor.month
            xp = day_xp.get(cursor.isoformat(), 0)
            tip = f"{cursor.strftime('%a %b %-d, %Y')} — {xp} XP" if xp else \
                  f"{cursor.strftime('%a %b %-d, %Y')} — nothing finished"
            cells.append(
                f'<rect x="{col * pitch}" y="{top + row * pitch}" '
                f'width="{cell}" height="{cell}" rx="3" fill="{step(xp)}" '
                f'stroke="var(--surface)" stroke-width="1" data-tip="{esc(tip)}"/>'
            )
            cursor += timedelta(days=1)
        col += 1

    width = max(col * pitch, 1)
    height = top + 7 * pitch
    month_labels = "".join(
        f'<text x="{x}" y="10" class="hm-mon">{label}</text>' for x, label in months
    )
    legend = "".join(
        f'<span class="sw" style="background:{c}"></span>'
        for c in ["var(--surface-3)", *SEQUENTIAL[1:]]
    )

    body = f"""
<div class="hm-wrap">
  <div class="hm-scroll">
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img"
         aria-label="Daily XP for the last {weeks} weeks">
      {month_labels}{''.join(cells)}
    </svg>
  </div>
  <div class="hm-legend"><span>Less</span>{legend}<span>More</span></div>
  <div id="tip" role="tooltip"></div>
</div>
"""
    css = """
.hm-wrap { position: relative; }
.hm-scroll { overflow-x: auto; overflow-y: hidden; padding-bottom: 2px; }
.hm-scroll::-webkit-scrollbar { height: 6px; }
.hm-scroll::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
.hm-mon { fill: var(--text-3); font-size: 10px; font-weight: 600; letter-spacing: .04em; }
rect[data-tip] { transition: opacity .12s ease; cursor: default; }
rect[data-tip]:hover { opacity: .7; stroke: var(--text-2); }
.hm-legend { display: flex; align-items: center; gap: 4px; justify-content: flex-end;
             margin-top: 8px; font-size: .68rem; color: var(--text-3); }
.sw { width: 11px; height: 11px; border-radius: 3px; display: inline-block;
      border: 1px solid var(--border); }
#tip { position: fixed; pointer-events: none; opacity: 0; transform: translate(-50%, -125%);
       background: var(--surface-2); color: var(--text); border: 1px solid var(--border);
       border-radius: 8px; padding: 5px 9px; font-size: .72rem; white-space: nowrap;
       box-shadow: 0 4px 14px rgba(0,0,0,.3); transition: opacity .1s ease; z-index: 9; }
"""
    body += """
<script>
const tip = document.getElementById('tip');
for (const r of document.querySelectorAll('rect[data-tip]')) {
  r.addEventListener('mouseenter', e => {
    const b = e.target.getBoundingClientRect();
    tip.textContent = e.target.dataset.tip;
    tip.style.left = (b.left + b.width / 2) + 'px';
    tip.style.top = b.top + 'px';
    tip.style.opacity = 1;
  });
  r.addEventListener('mouseleave', () => { tip.style.opacity = 0; });
}
</script>
"""
    _frame(body, mode, height=height + 46, extra_css=css)


# ────── achievements ──────

def achievement_grid(items: Iterable[dict[str, Any]], mode: str) -> None:
    items = list(items)
    cards = "".join(
        f'<div class="ach{"" if item["earned"] else " locked"}">'
        f'<b>{esc(item["label"])}</b><span>{esc(item["description"])}</span>'
        f'<i>{"Earned" if item["earned"] else "Locked"}</i></div>'
        for item in items
    )
    css = """
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(168px, 1fr)); gap: 10px; }
.ach { padding: 12px 13px; border-radius: 12px; background: var(--surface-2);
       border: 1px solid var(--border); border-left: 3px solid var(--accent); }
.ach.locked { opacity: .45; border-left-color: var(--border); }
.ach b { display: block; font-size: .86rem; margin-bottom: 3px; }
.ach span { display: block; font-size: .72rem; color: var(--text-3); line-height: 1.35; }
.ach i { display: block; margin-top: 7px; font-style: normal; font-size: .64rem;
         letter-spacing: .08em; text-transform: uppercase; color: var(--text-3); }
.ach:not(.locked) i { color: var(--accent); }
"""
    _frame(f'<div class="grid">{cards}</div>', mode,
           height=int(((len(items) + 3) // 4) * 112 + 12), extra_css=css)
