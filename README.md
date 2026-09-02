# Dojo

A task manager that keeps score. Finish tasks, earn XP, climb the belts.

Built with Streamlit and SQLite. Single user, runs locally, no account needed.

![Dojo board](docs/board.png)

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Data lives in `~/.dojo/dojo.db`. Point `DOJO_DB` somewhere else if you'd rather:

```bash
DOJO_DB=./dojo.db streamlit run app.py
```

## What it does

**Capture.** Type a task the way you'd say it and the fields get filled in:

```
call the dentist tomorrow #health !high
file taxes by 2026-09-15 !critical #admin #money
renew passport in 3 weeks #admin
```

`!critical` `!high` `!medium` `!low` (and `!c` `!h` `!m` `!l`) set priority,
`#tag` adds tags, and dates understand `today`, `tomorrow`, `friday`,
`next monday`, `in 3 days`, `in 2 weeks`, `sept 20` and `2026-09-15`.
This all runs locally with no API key.

**Score.** Completing a task pays out XP:

| Priority | Base XP |
|---|---|
| Critical | 50 |
| High | 30 |
| Medium | 20 |
| Low | 10 |

Plus **+5** for beating a due date and **+25** for clearing a full day's board
(3 or more tasks), and a streak multiplier of **×1.25** at 3 consecutive days,
**×1.5** at 7 or more. Each card shows what it's worth before you click.

Lifetime XP maps to belts — White, Yellow, Orange, Green, Blue, Purple, Brown,
Black, Red, Grandmaster — and there are 12 achievements to collect.

Reopening a task takes its XP back, and the clean-sweep bonus is recomputed
whenever the board changes, so the ledger always matches what's on screen.

**Organise.** Due dates, tags, subtask checklists, notes, and filters by status,
priority, tag or free text. Unfinished work from previous days is moved onto
today automatically, once per day, tagged with where it came from.

**Review.** The Progress tab charts tasks finished per day, cumulative XP,
where your effort goes by priority, and a year-long consistency calendar —
plus a table view of the same numbers.

## AI assist (optional)

Everything above works without it. Set an API key to turn on smarter capture,
subtask suggestions, and a "Plan my day" coach that sequences your board:

```bash
export OPENAI_API_KEY=sk-...
```

or put it in `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "sk-..."
```

`OPENAI_MODEL` overrides the model (default `gpt-4o-mini`). Anything the model
can't be reached for falls back to the local parser — the app never blocks on it.

## Backup

The sidebar downloads a full JSON export and restores one. Backups written by
the older `session_state` version of this app import too.

## Layout

```
app.py                 entry point, sidebar, routing
dojo/config.py         priorities, XP rules, belts, palette
dojo/db.py             SQLite storage, XP ledger, carry-over, import/export
dojo/gamify.py         XP preview, belt progress, achievements
dojo/nlp.py            local natural-language task parser
dojo/ai.py             optional LLM assist, degrades gracefully
dojo/ui/theme.py       design tokens and CSS
dojo/ui/components.py  HTML/SVG components (belt ring, heatmap, chips)
dojo/ui/board.py       the daily board
dojo/ui/stats.py       charts and history
tests/test_dojo.py     unit tests
```

## Tests

```bash
pip install pytest && python -m pytest tests/ -q
```
