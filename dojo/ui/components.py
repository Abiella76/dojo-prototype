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

from ..config import PRIORITY_COLORS, TIER_LABELS, TIER_RANKS, sequential
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

def tier_chip(priority: str) -> str:
    """Difficulty badge. The rank letter and label ride along with the colour,
    so the tier never depends on hue alone."""
    colour = PRIORITY_COLORS.get(priority, "#888")
    label = TIER_LABELS.get(priority, priority)
    rank = TIER_RANKS.get(priority, "?")
    return (f'<span class="chip chip-tier" style="background:{colour}" '
            f'title="{esc(priority)} priority">'
            f'<span class="chip-rank">{esc(rank)}</span>{esc(label)}</span>')


priority_chip = tier_chip  # older name, same badge


def quest_meta(task: dict, *, today: date | None = None, sub_done: int = 0, sub_total: int = 0) -> str:
    today = today or date.today()
    parts = [tier_chip(task.get("priority", "Medium"))]

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
        parts.append(f'<span class="objectives">{sub_done}/{sub_total} objectives</span>')

    return f'<div class="quest-meta">{"".join(parts)}</div>'


def quest_header(task: dict, **kwargs) -> None:
    """Tier anchor + meta chips + title, as one markdown block."""
    anchor = f'<span class="tier-{esc(task.get("priority", "Medium")).lower()}"></span>'
    done_cls = " card-done" if task.get("completed") else ""
    st.markdown(
        f'<div class="quest-head{done_cls}">{anchor}{quest_meta(task, **kwargs)}'
        f'<p class="quest-title">{esc(task["text"])}</p></div>',
        unsafe_allow_html=True,
    )


def note_block(text: str) -> None:
    st.markdown(f'<div class="note-body">{esc(text)}</div>', unsafe_allow_html=True)


# ────── HUD: rank, XP bar, streak ──────

def hero(stats: dict[str, Any], name: str, day: dict[str, int], mode: str,
         gain: int | None = None, gain_note: str = "") -> None:
    """The game HUD: rank crest, animated XP bar, streak flame, run readouts.

    `gain` erupts a "+N XP" burst out of the XP bar. It is drawn inside this
    component's own document on purpose: an iframe always paints above the
    parent's positioned content, so a floating number in the parent page would
    be hidden behind this panel no matter its z-index.
    """
    t = tokens(mode)
    progress = stats["progress"]
    belt_colour = stats["belt_color"]
    next_label = (f'{stats["next_belt_at"] - stats["xp"]:,} XP TO NEXT RANK'
                  if stats["next_belt_at"] else "MAX RANK HELD")
    streak = stats["streak"]
    # The flame grows and burns faster the longer the run — a glanceable
    # reward for consistency rather than another number to read.
    heat = min(streak / 14, 1.0)
    flame_size = 1 + heat * 0.5
    flame_speed = 2.2 - heat * 1.1
    flame_colour = "#ff8a1f" if streak >= 3 else "var(--text-3)"

    burst = (
        f'<div class="burst">+{gain} XP'
        f'{f"<small>{esc(gain_note)}</small>" if gain_note else ""}</div>'
        if gain else ""
    )

    body = f"""
<div class="hud">
  <div class="crest" role="img"
       aria-label="{esc(stats['belt'])} belt, level {stats['level']}, {progress:.0%} to next rank">
    <svg viewBox="0 0 96 106" width="92" height="102">
      <defs>
        <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="{belt_colour}" stop-opacity=".55"/>
          <stop offset="100%" stop-color="{belt_colour}" stop-opacity=".05"/>
        </linearGradient>
      </defs>
      <path d="M48 2 92 27v52L48 104 4 79V27z" fill="url(#cg)"
            stroke="{belt_colour}" stroke-width="2"/>
      <path d="M48 11 84 32v42L48 95 12 74V32z" fill="none"
            stroke="{belt_colour}" stroke-width="1" opacity=".35"/>
      <text x="48" y="50" text-anchor="middle" class="crest-lv">{stats['level']}</text>
      <text x="48" y="66" text-anchor="middle" class="crest-lb">LEVEL</text>
      <text x="48" y="84" text-anchor="middle" class="crest-belt">{esc(stats['belt']).upper()}</text>
    </svg>
  </div>

  <div class="hud-main">
    <p class="hud-kicker">{esc(name)} &middot; RANK {stats['level']}</p>
    <p class="hud-xp"><b>{stats['xp']:,}</b><span>XP</span></p>
    <div class="xpbar" aria-hidden="true">
      <i style="--w:{progress * 100:.1f}%"></i>
      <u></u>
    </div>
    <p class="hud-sub">{esc(next_label)}</p>
  </div>

  {burst}
  <div class="hud-stats">
    <div class="stat streak">
      <span class="flame" style="--fs:{flame_size:.2f};--fd:{flame_speed:.2f}s;--fc:{flame_colour}">
        &#9650;</span>
      <b>{streak}</b><span>DAY RUN</span>
    </div>
    <div class="stat"><b>{day['score']}%</b><span>CLEARED</span></div>
    <div class="stat"><b>{day['done']}<em>/{day['total']}</em></b><span>QUESTS</span></div>
  </div>
</div>
"""
    css = f"""
.hud {{
  display: flex; align-items: center; gap: 22px; flex-wrap: wrap;
  padding: 16px 20px; border-radius: 14px;
  background:
    linear-gradient(135deg, rgba(34,211,238,.07), transparent 45%),
    linear-gradient(180deg, var(--surface-2), var(--surface));
  border: 1px solid var(--border); box-shadow: {t['shadow']};
  position: relative; overflow: hidden;
}}
.hud::after {{
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background: repeating-linear-gradient(180deg, rgba(255,255,255,.03) 0 1px, transparent 1px 3px);
}}
.crest svg {{ filter: drop-shadow(0 0 12px {belt_colour}55); }}
.crest-lv {{ fill: var(--text); font-family: var(--font-display); font-size: 26px; font-weight: 800; }}
.crest-lb {{ fill: var(--text-3); font-size: 8px; font-weight: 700; letter-spacing: .22em; }}
.crest-belt {{ fill: {belt_colour}; font-size: 9.5px; font-weight: 800; letter-spacing: .13em; }}

.hud-main {{ flex: 1 1 240px; min-width: 210px; }}
.hud-kicker {{
  margin: 0 0 3px; font-size: .68rem; font-weight: 700; letter-spacing: .2em;
  text-transform: uppercase; color: var(--text-3);
}}
.hud-xp {{ margin: 0 0 10px; display: flex; align-items: baseline; gap: 6px; }}
.hud-xp b {{
  font-family: var(--font-display); font-size: 2.05rem; font-weight: 800;
  color: var(--text); letter-spacing: .01em;
  text-shadow: 0 0 18px rgba(34,211,238,.35);
}}
.hud-xp span {{ font-size: .78rem; font-weight: 700; letter-spacing: .18em; color: var(--text-3); }}

.xpbar {{
  position: relative; height: 12px; border-radius: 3px; overflow: hidden;
  background: var(--surface); border: 1px solid var(--border);
}}
.xpbar i {{
  display: block; height: 100%; width: 0; border-radius: 2px;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
  box-shadow: 0 0 14px var(--glow);
  animation: fill 1.1s cubic-bezier(.2,.8,.3,1) forwards;
}}
/* a shimmer sweeping the filled portion, so the bar reads as "live" */
.xpbar u {{
  position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(100deg, transparent 30%, rgba(255,255,255,.5) 50%, transparent 70%);
  transform: translateX(-100%);
  animation: sweep 2.6s 1.1s ease-in-out infinite;
}}
@keyframes fill {{ to {{ width: var(--w); }} }}
@keyframes sweep {{ 60%, 100% {{ transform: translateX(100%); }} }}
.hud-sub {{
  margin: 7px 0 0; font-size: .68rem; color: var(--text-3);
  letter-spacing: .14em; font-weight: 600;
}}

.hud-stats {{ display: flex; gap: 8px; }}
.stat {{
  min-width: 84px; padding: 9px 12px; border-radius: 8px; background: var(--surface);
  border: 1px solid var(--border); text-align: center; position: relative;
}}
.stat b {{
  display: block; font-family: var(--font-display); font-size: 1.3rem; font-weight: 800;
  letter-spacing: .01em;
}}
.stat b em {{ font-style: normal; font-size: .8rem; color: var(--text-3); }}
.stat span {{
  font-size: .6rem; color: var(--text-3); text-transform: uppercase;
  letter-spacing: .14em; font-weight: 700;
}}
.streak {{ border-color: color-mix(in srgb, var(--fc, #ff8a1f) 40%, var(--border)); }}
.flame {{
  position: absolute; top: -7px; left: 50%; transform: translateX(-50%) scale(var(--fs));
  color: var(--fc); font-size: .7rem; line-height: 1;
  filter: drop-shadow(0 0 6px var(--fc));
  animation: flicker var(--fd) ease-in-out infinite;
}}
@keyframes flicker {{
  0%, 100% {{ opacity: .75; transform: translateX(-50%) scale(var(--fs)); }}
  50% {{ opacity: 1; transform: translateX(-50%) scale(calc(var(--fs) * 1.22)); }}
}}

/* reward burst — rises out of the XP bar */
.burst {{
  /* anchored to the empty stretch of bar left of the stat tiles, so it never
     lands on top of the XP total */
  position: absolute; right: 232px; bottom: 40px; z-index: 4; pointer-events: none;
  text-align: right;
  font-family: var(--font-display); font-size: 1.9rem; font-weight: 800;
  color: var(--accent); letter-spacing: .04em; white-space: nowrap;
  text-shadow: 0 0 14px var(--glow), 0 0 40px var(--glow);
  animation: burst 2.1s cubic-bezier(.2,.75,.3,1) forwards;
}}
.burst small {{
  display: block; font-size: .58rem; letter-spacing: .3em;
  color: var(--accent-2); text-shadow: none; margin-top: 2px;
}}
@keyframes burst {{
  0% {{ opacity: 0; transform: translateY(14px) scale(.6); }}
  14% {{ opacity: 1; transform: translateY(0) scale(1.15); }}
  26% {{ transform: translateY(0) scale(1); }}
  100% {{ opacity: 0; transform: translateY(-54px) scale(1); }}
}}
@media (prefers-reduced-motion: reduce) {{ .burst {{ animation: none; opacity: 1; }} }}
"""
    _frame(body, mode, height=168, extra_css=css)


def rank_up_banner(belt: str, level: int, colour: str, mode: str) -> None:
    """Promotion crest, drawn for the rank-up dialog."""
    body = f"""
<div class="promo">
  <svg viewBox="0 0 96 106" width="112" height="124">
    <path d="M48 2 92 27v52L48 104 4 79V27z" fill="{colour}" fill-opacity=".18"
          stroke="{colour}" stroke-width="2"/>
    <text x="48" y="58" text-anchor="middle" class="promo-lv">{level}</text>
    <text x="48" y="76" text-anchor="middle" class="promo-lb">LEVEL</text>
  </svg>
  <b>{esc(belt).upper()} BELT</b>
  <i>rank {level} reached</i>
</div>
"""
    css = f"""
.promo {{ text-align: center; padding: 4px 0 10px; }}
.promo svg {{ filter: drop-shadow(0 0 16px {colour}); animation: pop .7s cubic-bezier(.2,1.6,.4,1) both; }}
.promo-lv {{ fill: var(--text); font-family: var(--font-display); font-size: 30px; font-weight: 800; }}
.promo-lb {{ fill: var(--text-3); font-size: 8px; font-weight: 700; letter-spacing: .24em; }}
.promo b {{
  display: block; margin-top: 6px; font-family: var(--font-display);
  font-size: 1.5rem; font-weight: 800; letter-spacing: .1em; color: {colour};
  text-shadow: 0 0 18px {colour}80;
}}
.promo i {{
  display: block; margin-top: 6px; font-style: normal; font-size: .66rem;
  letter-spacing: .3em; text-transform: uppercase; color: var(--text-3);
}}
@keyframes pop {{ from {{ transform: scale(.3); opacity: 0; }} to {{ transform: scale(1); opacity: 1; }} }}
"""
    _frame(body, mode, height=228, extra_css=css)


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

    ramp = sequential(mode)
    values = [v for v in day_xp.values() if v > 0]
    peak = max(values) if values else 1
    cuts = [peak * f for f in (0.0, 0.2, 0.4, 0.6, 0.8)]

    def step(xp: int) -> str:
        if xp <= 0:
            return "var(--surface-3)"
        for i in range(len(cuts) - 1, -1, -1):
            if xp > cuts[i]:
                return ramp[min(i + 1, len(ramp) - 1)]
        return ramp[0]

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
        for c in ["var(--surface-3)", *ramp[1:]]
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


quest_header_alias = quest_header
task_header = quest_header  # older name
