"""Stats and history.

Chart choices follow the project's viz rules: one measure per axis (never a
second y-scale), a single categorical hue for single-series charts (so no
legend is needed — the title names the series), the reserved status palette for
priority, and a one-hue sequential ramp for the calendar heatmap. Every chart
ships a hover tooltip and a table view.
"""

from __future__ import annotations

from datetime import date, timedelta

import altair as alt
import pandas as pd
import streamlit as st

from .. import db, gamify
from ..config import PRIORITIES, PRIORITY_COLORS, SERIES, TIER_LABELS
from . import components as c
from .theme import tokens

RANGES = {"30 days": 30, "90 days": 90, "12 months": 365}


def _chart_config(chart: alt.Chart, mode: str) -> alt.Chart:
    """Recessive grid and axes; text in ink tokens, never a series colour."""
    t = tokens(mode)
    return (
        chart.configure_view(strokeWidth=0, fill="transparent")
        .configure_axis(
            grid=True, gridColor=t["border"], gridOpacity=0.55, gridWidth=1,
            domain=False, tickColor=t["border"], tickSize=4,
            labelColor=t["text_2"], titleColor=t["text_3"],
            labelFontSize=11, titleFontSize=11, titleFontWeight=600,
        )
        .configure_legend(labelColor=t["text_2"], titleColor=t["text_3"])
        .properties(background="transparent")
    )


def _daily_frame(days: int, today: date) -> pd.DataFrame:
    """One row per calendar day in the window, zero-filled."""
    start = today - timedelta(days=days - 1)
    index = pd.date_range(start, today, freq="D")
    frame = pd.DataFrame({"day": index.strftime("%Y-%m-%d"), "date": index})

    completions = pd.DataFrame(db.completions_by_day(start.isoformat()))
    xp = pd.DataFrame(db.xp_by_day(start.isoformat()))
    for source, columns in ((completions, ["total", "done"]), (xp, ["xp"])):
        if source.empty:
            for col in columns:
                frame[col] = 0
        else:
            frame = frame.merge(source, on="day", how="left")
    return frame.fillna({"total": 0, "done": 0, "xp": 0}).astype(
        {"total": int, "done": int, "xp": int}
    )


def render(mode: str, today: date | None = None) -> None:
    today = today or date.today()
    stats = gamify.lifetime_stats()
    series = SERIES[mode][0]

    label = st.segmented_control("Range", list(RANGES), default="90 days",
                                 key="stats_range") or "90 days"
    days = RANGES[label]
    frame = _daily_frame(days, today)

    # ── headline numbers: a stat row, not a chart ──
    row = st.columns(4)
    row[0].metric("Quests cleared", f"{int(frame['done'].sum()):,}", help=f"In the last {label}")
    row[1].metric("XP earned", f"{int(frame['xp'].sum()):,}")
    rate = frame["done"].sum() / frame["total"].sum() * 100 if frame["total"].sum() else 0
    row[2].metric("Completion rate", f"{rate:.0f}%")
    row[3].metric("Best day", f"{int(frame['done'].max())} quests")

    st.divider()

    # ── tasks finished per day ──
    st.markdown("#### Quests cleared per day")
    bars = (
        alt.Chart(frame)
        .mark_bar(size=max(3, min(16, int(560 / max(len(frame), 1)))),
                  cornerRadiusEnd=4, color=series)
        .encode(
            x=alt.X("date:T", title=None, axis=alt.Axis(format="%b %-d", labelAngle=0)),
            y=alt.Y("done:Q", title="quests", axis=alt.Axis(tickMinStep=1)),
            tooltip=[
                alt.Tooltip("date:T", title="Day", format="%a %b %-d, %Y"),
                alt.Tooltip("done:Q", title="Cleared"),
                alt.Tooltip("total:Q", title="Logged"),
            ],
        )
        .properties(height=190)
    )
    st.altair_chart(_chart_config(bars, mode), width="stretch")

    # ── XP over time ──
    st.markdown("#### XP earned")
    frame = frame.assign(cumulative=frame["xp"].cumsum())
    line = (
        alt.Chart(frame)
        .mark_line(strokeWidth=2, color=series, interpolate="monotone")
        .encode(
            x=alt.X("date:T", title=None, axis=alt.Axis(format="%b %-d", labelAngle=0)),
            y=alt.Y("cumulative:Q", title="cumulative XP"),
            tooltip=[
                alt.Tooltip("date:T", title="Day", format="%a %b %-d, %Y"),
                alt.Tooltip("xp:Q", title="XP that day"),
                alt.Tooltip("cumulative:Q", title="Running total"),
            ],
        )
        .properties(height=180)
    )
    st.altair_chart(_chart_config(line, mode), width="stretch")

    # ── priority mix ──
    st.markdown("#### Where the effort goes")
    breakdown = pd.DataFrame(db.priority_breakdown((today - timedelta(days=days - 1)).isoformat()))
    if breakdown.empty:
        st.caption("No quests in this window yet.")
    else:
        breakdown["open"] = breakdown["total"] - breakdown["done"]
        breakdown = breakdown[breakdown["priority"].isin(PRIORITIES)]
        breakdown["tier"] = breakdown["priority"].map(TIER_LABELS)
        tier_order = [TIER_LABELS[p] for p in PRIORITIES]
        # Priority is ordinal severity: the axis labels each row, so colour is
        # reinforcement rather than the only channel carrying meaning.
        mix = (
            alt.Chart(breakdown)
            .mark_bar(cornerRadiusEnd=4, height=22)
            .encode(
                y=alt.Y("tier:N", sort=tier_order, title=None),
                x=alt.X("done:Q", title="cleared", axis=alt.Axis(tickMinStep=1)),
                color=alt.Color(
                    "tier:N", sort=tier_order, legend=None,
                    scale=alt.Scale(domain=tier_order,
                                    range=[PRIORITY_COLORS[p] for p in PRIORITIES]),
                ),
                tooltip=[
                    alt.Tooltip("tier:N", title="Tier"),
                    alt.Tooltip("done:Q", title="Cleared"),
                    alt.Tooltip("open:Q", title="Still active"),
                    alt.Tooltip("total:Q", title="Total"),
                ],
            )
            .properties(height=alt.Step(30))
        )
        st.altair_chart(_chart_config(mix, mode), width="stretch")

    # ── streak calendar ──
    st.markdown("#### Consistency")
    st.caption(f"Daily XP over the last 52 weeks · current streak {stats['streak']} days")
    c.heatmap({r["day"]: r["xp"] for r in db.xp_by_day((today - timedelta(days=380)).isoformat())},
              mode, today=today)

    # ── achievements ──
    st.markdown("#### Achievements")
    earned = [a for a in gamify.achievements(stats) if a["earned"]]
    st.caption(f"{len(earned)} of {len(gamify.ACHIEVEMENTS)} earned")
    c.achievement_grid(gamify.achievements(stats), mode)

    # ── table view (the accessibility fallback for every chart above) ──
    with st.expander("View the data as a table"):
        table = frame[["day", "total", "done", "xp", "cumulative"]].rename(
            columns={"day": "Date", "total": "On the board", "done": "Finished",
                     "xp": "XP", "cumulative": "Cumulative XP"}
        )
        st.dataframe(table.iloc[::-1], width="stretch", hide_index=True)
