"""Dojo — a quest log that keeps score.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import streamlit as st

from dojo import ai, config, db, gamify, sfx
from dojo.ui import board, stats as stats_view
from dojo.ui.theme import inject

st.set_page_config(
    page_title="Dojo", page_icon="🥋", layout="wide",
    initial_sidebar_state="expanded",
)

try:
    db.connect()
except db.StorageError as exc:
    # A bad DATABASE_URL should explain itself, not dump a traceback at whoever
    # opens the app. The message deliberately carries no credentials.
    st.error(f"**Database connection failed.** {exc}")
    st.markdown(
        """
Check the `DATABASE_URL` secret under **⋮ → Settings → Secrets**:

* It must be one line of TOML, quotes included:
  `DATABASE_URL = "postgresql://user:pass@host/dbname?sslmode=require"`
* Copy the URI from Neon's **Connection Details** — not the `psql ...` command,
  and not a Prisma or JDBC variant.
* Keep `?sslmode=require` on the end.
* A password containing `@ : / ?` or `#` must be percent-encoded.

Remove the secret entirely to fall back to local SQLite storage.
"""
    )
    st.stop()


def api_key() -> str | None:
    """Prefer Streamlit secrets, fall back to the environment."""
    try:
        secret = st.secrets.get("OPENAI_API_KEY")  # type: ignore[union-attr]
    except Exception:
        secret = None
    return ai.api_key(secret)


# ────── theme ──────
# Follow whichever theme Streamlit is actually rendering (Settings → Appearance),
# so the custom markup and the iframed components match its own widgets.
mode = getattr(getattr(st.context, "theme", None), "type", None) or "dark"
inject(mode)

# ────── onboarding ──────
user_name = db.get_setting("user_name")
if not user_name:
    _, middle, _ = st.columns([1, 2, 1])
    with middle:
        st.markdown("# 🥋 DOJO")
        st.markdown("#### A quest log that keeps score.")
        st.caption(
            "Clear quests, earn XP, climb the belts. Everything is stored locally "
            "in SQLite, so your run survives a refresh."
        )
        with st.form("welcome"):
            name = st.text_input("What should we call you?", placeholder="Alex")
            if st.form_submit_button("Enter the dojo", type="primary") and name.strip():
                db.set_setting("user_name", name.strip())
                st.rerun()
    st.stop()

# ────── carry-over (once per day, always into today) ──────
today = date.today()
if not st.session_state.get("carried"):
    moved = db.carry_over(today)
    st.session_state["carried"] = True
    if moved:
        st.toast(f"Carried {moved} unfinished quest{'s' if moved != 1 else ''} into today")

if "day" not in st.session_state:
    st.session_state["day"] = today
selected: date = st.session_state["day"]
day_str = selected.isoformat()

lifetime = gamify.lifetime_stats()
summary = db.day_summary(day_str)
streak = lifetime["streak"]

# ────── reward feedback ──────
# Queued by the board on the previous run and consumed once here, so the
# animations play on a freshly rendered page rather than being cut off by the
# rerun that recorded them.
from dojo.ui import components as c  # noqa: E402

xp_gain = st.session_state.pop("xp_gain", None)
xp_note = st.session_state.pop("xp_note", "")
promotion = st.session_state.pop("belt_up", None)
sound_on = db.get_setting("sound", "on") == "on"


def _play(data: bytes, key: str) -> None:
    """Fire a one-shot sound. The player itself is hidden by CSS.

    Autoplay is allowed here because clearing a quest is a click, and browsers
    permit autoplay once the page has been interacted with. On a browser that
    still blocks it the audio simply doesn't play — nothing breaks.
    """
    with st.container(key=f"sfx-{key}"):
        st.audio(data, format="audio/wav", autoplay=True)


@st.dialog("RANK UP")
def _rank_up_dialog(belt: str, level: int) -> None:
    c.rank_up_banner(belt, level, config.belt_for_xp(lifetime["xp"])[2], mode)
    st.caption(gamify.rank_message(lifetime))

# ────── sidebar ──────
with st.sidebar:
    st.markdown(f"### 🥋 {user_name}")
    st.caption(gamify.rank_message(lifetime))

    st.metric("Rank", f"{lifetime['belt']} · LV {lifetime['level']}")
    st.metric("Total XP", f"{lifetime['xp']:,}")
    st.metric("Run", f"{streak} day{'s' if streak != 1 else ''}")
    st.progress(lifetime["progress"], text=f"{lifetime['progress']:.0%} to next rank")

    st.divider()
    st.caption("**Rewards**")
    st.caption(
        " · ".join(f"{config.TIER_LABELS[p]} {config.BASE_XP[p]}" for p in config.PRIORITIES)
        + f"  \n+{config.EARLY_BONUS} beating a due date  \n"
        f"+{config.SWEEP_BONUS} clearing the log ({config.SWEEP_MIN_TASKS}+ quests)  \n"
        "×1.25 at a 3-day run, ×1.5 at 7+"
    )

    st.divider()
    st.caption("**Backup**")
    st.download_button(
        "Download backup",
        data=json.dumps(db.export_state(), indent=2),
        file_name=f"dojo_backup_{today}.json",
        mime="application/json",
        width="stretch",
    )
    uploaded = st.file_uploader("Restore from backup", type="json",
                                label_visibility="collapsed")
    if uploaded is not None and st.button("Restore", width="stretch"):
        try:
            count = db.import_state(json.load(uploaded))
        except (json.JSONDecodeError, UnicodeDecodeError):
            st.error("That file isn't valid JSON.")
        except (KeyError, TypeError, ValueError) as exc:
            st.error(f"Couldn't read that backup: {exc}")
        else:
            st.success(f"Restored {count} quests.")
            st.session_state.pop("carried", None)
            st.rerun()

    st.divider()
    st.caption(f"AI assist: **{'on' if ai.available(api_key()) else 'off'}**")
    if not ai.available(api_key()):
        st.caption("Set `OPENAI_API_KEY` to enable planning and smart capture.")
    if st.toggle("Sound effects", value=sound_on, key="sound_toggle") != sound_on:
        db.set_setting("sound", "off" if sound_on else "on")
        st.rerun()

    st.divider()
    st.caption(f"Theme: **{mode}** — follows your system; override under ⋮ → Settings.")

    # Which store is live matters: on Streamlit Cloud a SQLite file is wiped
    # whenever the app sleeps, so say plainly which one is in use.
    if db.backend() == "postgres":
        st.caption("Storage: **Postgres** — your history persists.")
    else:
        st.caption(f"Storage: **SQLite** at `{config.DB_PATH}`")
        st.caption(
            ":orange[Hosted on Streamlit Cloud this file is wiped when the app "
            "sleeps.] Set `DATABASE_URL` to a Postgres/Neon database to keep history."
        )
    st.caption(f"v{config.APP_VERSION}")

# ────── header ──────
board_tab, stats_tab = st.tabs(["Quest Log", "Record"])

with board_tab:
    c.hero(lifetime, user_name, summary, mode)
    if xp_gain is not None:
        c.reward_burst(xp_gain, xp_note)
    if promotion:
        _rank_up_dialog(*promotion)
    # Rank-up trumps the per-quest chime when both land on the same click.
    if sound_on and (promotion or xp_gain is not None):
        _play(sfx.rank_up_sound() if promotion else sfx.clear_sound(),
              "rank" if promotion else "clear")
    st.write("")

    nav = st.columns([1, 1, 1.6, 5])
    with nav[0]:
        if st.button("←", width="stretch", help="Previous day"):
            st.session_state["day"] = selected - timedelta(days=1)
            st.rerun()
    with nav[1]:
        if st.button("→", width="stretch", help="Next day"):
            st.session_state["day"] = selected + timedelta(days=1)
            st.rerun()
    with nav[2]:
        if st.button("Today", width="stretch"):
            st.session_state["day"] = today
            st.rerun()
    with nav[3]:
        picked = st.date_input("Day", value=selected, format="YYYY-MM-DD",
                               label_visibility="collapsed")
        if picked != selected:
            st.session_state["day"] = picked
            st.rerun()

    heading = "Today" if selected == today else selected.strftime("%A")
    st.markdown(f"### {heading} · {selected.strftime('%B %-d, %Y')}")

    if selected != today:
        st.caption("Viewing another day — new quests are added to this date.")

    board.quick_add(day_str, api_key())
    st.write("")

    all_tasks = db.list_tasks(day_str)
    if not all_tasks:
        st.info("No quests logged for this day. Accept your first one above.")
    else:
        visible = board.filter_bar(all_tasks)
        st.write("")

        left, right = st.columns([2.4, 1])
        with left:
            if not visible:
                st.caption("No quests match these filters.")
            for task in sorted(visible, key=lambda t: (t["completed"], t["sort_order"])):
                board.task_card(task, streak, api_key(), today)
        with right:
            board.coach_panel(
                [t for t in all_tasks if not t["completed"]],
                {"streak": streak, **summary},
                api_key(),
            )

with stats_tab:
    stats_view.render(mode, today)
