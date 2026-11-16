# Load a Written Story and Continue It

**Status:** Proposed
**Related docs:** [Backend Design](03-backend-design.md), [Frontend Design](02-frontend-design.md), [Paragraph Scoring](06-paragraph-scoring.md)

## 1. Goal

Let a player reopen a story they started earlier (e.g. yesterday), see everything already written, and continue with the next paragraph.

Example: yesterday I started `a bar of soap`. Today I open Story Time, pick that story, see its paragraphs, and the game knows the last paragraph in the file is the one I haven't written yet.

## 2. Core idea

The `.txt` file in `writtenStories/` becomes the single source of truth. No JSON sidecar, no legacy parser, no migration.

- A paragraph is **written by the player** once its `Date`/`Speed` lines exist underneath it.
- The **last paragraph in the file with no `Date`/`Speed` lines underneath it is the current, unwritten paragraph**.
- Therefore loading a story needs no guessing: the last block is either the paragraph to type (`has_current`) or the last one was completed and a new paragraph must be generated.
- A generated paragraph is appended immediately, before the player types it. Closing the app can no longer lose the story or the paragraph you were about to type.

## 3. File format

One story per file, same directory and filename scheme as today:

```
writtenStories/<premise-slug>_<8 hex chars>.txt
```

Exact format:

```
Premise: a bar of soap

The bar of soap had seen better days, its edges worn smooth by years of service.
Date: 2026-10-29 12:46:10
Speed: 312.4 CPM | Tier: 1 (negative)

It slipped from the counter and tumbled into the drain, where a new life began.
```

Rules:

- Line 1 is `Premise: <verbatim premise>`, then one blank line. The premise is stored in full (current code truncates it to a 50-char slug, which is not enough to resume).
- Each paragraph occupies **exactly one line**. `parse_llm_response` already collapses newlines; the writer also enforces `text.replace("\n", " ").strip()`.
- Metadata goes **underneath** the paragraph, one line each:
  - `Date: YYYY-MM-DD HH:MM:SS` (completion time, local or UTC — pick one and stay consistent)
  - `Speed: <cpm> CPM | Tier: <0-4> (<label>)`
- A blank line follows the metadata and separates paragraphs.
- **No splits, no paragraph numbers, no `--- Paragraph N ---` markers.**
- A paragraph is complete if and only if it has at least one metadata line. A trailing paragraph with none is `current`.
- New stories only. Old-format files are left untouched and are not listed (see §9).

Example with a completed first paragraph and an unwritten second:

```
Premise: a bar of soap

The bar of soap had seen better days.
Date: 2026-10-29 12:46:10
Speed: 312.4 CPM | Tier: 1 (negative)

It slipped from the counter and tumbled into the drain.
```

## 4. Parsing rules

`backend/story_file.py` (new module):

```python
@dataclass
class StoryParagraph:
    text: str
    speed_cpm: float | None = None
    outcome_tier: int | None = None
    completed_at: datetime | None = None

@dataclass
class Story:
    story_id: str
    premise: str
    path: Path
    paragraphs: list[StoryParagraph]      # completed only
    current: str | None = None            # last uncompleted paragraph
```

Algorithm:

1. Read lines, drop `\r`, ignore blank lines.
2. The first non-empty line must match `^Premise: (.+)$`; otherwise this is not a v2 story → skip it.
3. Walk the remaining lines:
   - `^Date: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$` or `^Speed: [\d.]+ CPM \| Tier: [0-4] ` → attach to the previous paragraph and mark it complete.
   - Any other line → start a new paragraph.
4. After the walk, if the final paragraph has no metadata and is the last paragraph → it is `current` and is removed from `paragraphs`.
5. A non-final paragraph with no metadata is malformed; log a warning and treat it as completed with defaults (`speed_cpm=0`, `tier=2`) so the rest of the story stays readable.
6. Strict metadata regexes mean a paragraph that happens to start with `Date:` or `Speed:` in prose is not misparsed.

Enforce during writes: paragraph text is one line, stripped, non-empty, and never starts with a metadata-looking line. If it does, prefix/escape it deterministically (e.g. prepend a space) so round-tripping cannot corrupt the file.

## 5. Writing rules

The file is **append-only**. We never rewrite or delete an existing story file. Writes go through one `Story` object per live session, guarded by a per-story `threading.Lock`.

### 5.1 Story creation

On `POST /api/restart` and on the first `POST /api/generate` (no `session_id`):

1. Generate the opening paragraph via the LLM.
2. Create `writtenStories/<slug>_<id8>.txt` with:
   ```
   Premise: <premise>

   <opening paragraph>
   ```
3. Register the file with the live session (`session.story_id`, `session.story`).

The opening paragraph exists in the file **before** the player types anything, so an abandoned story is still resumable.

### 5.2 When a paragraph is fetched (the player has typed it)

Today the backend records the typed paragraph when the frontend triggers the next fetch (at the fetch-trigger percentage). New order in `POST /api/generate`:

1. Compute tier/splits/boundaries as today from the request.
2. Call the LLM for the next paragraph.
3. **Only after the LLM succeeds**, in one append pass:
   - Append `Date: ...` and `Speed: ...` underneath the current paragraph.
   - Append a blank line and the new paragraph text underneath.
4. Update the in-memory session (move current → history, set new current).
5. Return the new paragraph.

If the LLM fails, the file is untouched: the current paragraph still has no metadata and remains resumable, and a retry cannot create duplicate metadata.

If the process crashes between the metadata append and the new paragraph append, the file ends with a completed paragraph and no current. Loading then generates a fresh next paragraph via the continue endpoint — no data is lost.

### 5.3 `POST /api/stories/{id}/continue`

- If `story.current` exists → return it unchanged (no LLM call, deterministic resume).
- Otherwise build the continuation prompt from `Premise` + all completed paragraph texts, direction tier = last completed paragraph's tier (default 2), and append the generated paragraph as the new current.
- Response: `{ "response": "...", "outcome_tier": 1, "tier_boundaries": [...] }`.
- This is separate from `/api/generate`, whose contract is "the player just typed; record it and produce the next one".

## 6. API

### `GET /api/stories`

Returns summaries, newest first (`limit`, `offset`, optional `q`):

```json
{
  "stories": [
    {
      "story_id": "a_bar_of_soap_e2dfb6f5",
      "premise": "a bar of soap",
      "paragraph_count": 4,
      "has_current": true,
      "updated_at": "2026-10-29T12:49:31Z",
      "last_speed_cpm": 312.4,
      "last_outcome_tier": 1
    }
  ],
  "total": 1
}
```

`updated_at` = file mtime. Cache summaries by `(path, mtime, size)` so listing a large folder does not re-parse unchanged files.

### `GET /api/stories/{story_id}`

Full story:

```json
{
  "story_id": "...",
  "premise": "...",
  "paragraphs": [
    {"text": "...", "speed_cpm": 312.4, "outcome_tier": 1, "completed_at": "2026-10-29T12:46:10Z"}
  ],
  "current": "It slipped from the counter and tumbled into the drain.",
  "tier_boundaries": [300.0, 350.0, 400.0, 450.0]
}
```

### `DELETE /api/stories/{story_id}`

Permanently deletes the story `.txt` file and detaches any live session from it. Returns `{"ok": true}`; 404 for unknown/invalid IDs. The picker's **✕** button calls this after a confirmation prompt and then refreshes the list.

### `POST /api/stories/{story_id}/resume`

Creates a live `GameSession` from the file. **No LLM call.**

```json
{
  "session_id": "uuid",
  "story_id": "...",
  "premise": "...",
  "paragraphs": [...],
  "current": "..." | null,
  "tier_boundaries": [300.0, 350.0, 400.0, 450.0]
}
```

- `session.initial_prompt = story.premise`, `session.history = story.paragraphs`, `session.story_id = story_id`.
- Rolling window is seeded from `~/.storytime/performance.json` exactly like a new session. Splits are no longer stored in the story file; the global performance file already contains them.
- Keep one live session per `story_id`; a second resume returns the existing session so two tabs cannot append duplicate paragraphs.
- 404 for unknown/invalid IDs.

## 7. Scoring on resume

- The global rolling window is reused, unmodified. Do not replay anything from the story file (there are no splits there anymore).
- Boundaries are computed from the current settings, so a settings change since yesterday is reflected immediately.
- If the global window is empty, the first fetched paragraph is scored with the existing first-paragraph rules.
- The first paragraph generated after resume uses the last completed paragraph's tier for tone continuity; it is not recorded and does not affect scoring.
- A story with zero completed paragraphs behaves as a first paragraph (tier 2).

## 8. Frontend

### 8.1 Entry points

- Add a **Recent stories** button next to "Start a new story" in `#initialPromptContainer`.
- Opens a `<dialog id="storyPicker">` listing premise, relative date ("Yesterday"), completed count, and last tier.
- Each row has an **✕** delete button on the right. It confirms, calls `DELETE /api/stories/{id}`, clears the active game if that story was open, and refreshes the list.
- Empty state: "No saved stories yet. Start one above."
- If `localStorage['storytime-last-story']` points at an existing story, show a one-click banner: **Continue "a bar of soap"**.

### 8.2 `loadStory(storyId)`

1. `reset()`.
2. `POST /api/stories/{id}/resume`.
3. Render completed paragraphs into `#completedText` using the existing `<span class="completed-p">` structure, and fill `completedParagraphs[]`.
4. Fill `historyData` (oldest → newest) from the parsed paragraphs and render via `buildHistoryItem`; newest stays on top. Time taken was never persisted, so restored entries show speed and tier only (suppress the `Time:` field when unknown).
5. Set `sessionId`, `initialPromptInput.value = premise`, and the tier chart from `tier_boundaries`.
6. If `current` is present, use it. Otherwise call `POST /api/stories/{id}/continue` with a "Loading next paragraph..." message.
7. Set `textContent`, `inputBox.disabled = false`, `initSplits(textContent)`, `updateTextDisplay()`, focus the input.
8. Persist `storytime-last-story = storyId`; show `Continuing: <premise>`.
9. On failure, `showError` with a retry that re-runs `loadStory(storyId)`.

`updateTextDisplay()` already renders `#completedText` ahead of the active paragraph, so restoring only needs to populate that container before setting `textContent`.

### 8.3 Starting a new story

`sendPrompt()` keeps calling `reset()`; additionally clears `storytime-last-story`, closes the picker, and stores the `story_id` returned by `/api/restart`.

## 9. Old files

Per decision: **no legacy support.**

- New stories are written in the v2 format above.
- Listing/resume only recognizes files whose first non-empty line is `Premise: ...`.
- At implementation time the old-format `.txt` files in `writtenStories/` were purged so the folder contains only the current format. The app itself never deletes or rewrites unrecognized files.
- Because filenames include a fresh 8-hex suffix, new stories never collide with any future files.

## 10. Edge cases

| Case | Behavior |
|---|---|
| Story file has one paragraph with no metadata | Resume shows it as `current`; no generation. |
| Story file ends with metadata | No current; `/continue` generates and appends one. |
| LLM offline on resume | Resume succeeds from the file; only `/continue` fails with 503 + retry. |
| LLM failure during `/api/generate` | File untouched; current paragraph stays unwritten; retry is safe. |
| Crash after metadata write, before new paragraph write | File ends completed; resume generates a fresh next paragraph. |
| Two tabs resume the same story | Same `session_id`; appends serialized by the per-story lock. Simultaneous typing in both tabs is unsupported. |
| Invalid `story_id` or path traversal | 404; ID validated (`^[a-z0-9][a-z0-9_-]{0,120}$`) and resolved path must be inside `writtenStories/`. |
| Paragraph text starts with `Date:`/`Speed:` | Escaped by the writer; strict metadata regexes prevent misparse. |
| Premise contains emoji/non-ASCII | Stored verbatim in the `Premise:` header; filename slug falls back to `untitled`. |
| Story file deleted while session is live | Appends recreate the file with the header and in-memory history, or fail with a clear 500; play continues in memory. |
| Very long story | List endpoint reads each file but caches by mtime/size; detail loads only the chosen story. |

## 11. Implementation tasks

Each task is one commit with tests.

### T1 — `backend/story_file.py`
- `Story`, `StoryParagraph`, parser, `create_story`, `append_paragraph`, `complete_current`, `load_story`, `list_stories`, `stories_dir()`/`story_path()`, per-story locks, `story_id` validation.
- Enforce one-line paragraphs and metadata escaping.
- Tests: exact round-trip of the example format, current detection, completed detection, malformed non-final block, invalid header, metadata-looking text, traversal, atomic append order, summary sorting/caching.

### T2 — Wire persistence into generation
- Create the file (header + opening paragraph) in `/api/restart` and the first `/api/generate`.
- Attach `Story` to `GameSession`; add `story_id`.
- In `/api/generate` with a session: after a successful LLM call, complete the current paragraph and append the next; no write on LLM failure.
- Remove the old `_persist_paragraph` block format and the `Splits:` line.
- Update `test_session.py` persistence tests to the new format; add idempotent-retry and failure tests.

### T3 — Story endpoints
- `GET /api/stories`, `GET /api/stories/{id}`, `POST /api/stories/{id}/resume`, `POST /api/stories/{id}/continue`.
- One-session-per-story registry; resume rebuilds history and premise; continue returns existing current or generates and appends.
- Tests: list/detail/resume/continue, 404/503, no duplicate current generation, 0-paragraph story, story whose last block is unwritten.

### T4 — Story picker and resume UI
- Recent stories button + `<dialog>`, relative dates, tier badges, empty/loading/error states.
- `loadStory()` per §8.2; recent-story banner; clear state on new story.
- Playwright: start → complete a paragraph → reload → resume → restored text/history/chart/current → type → file gains metadata + next paragraph; empty state; LLM-down continue.

### T5 — Docs and cleanup
- Update `docs/technical-design/02-frontend-design.md`, `03-backend-design.md` (routes + story file format), this doc, and `CHANGELOG.md`.
- Add the milestone/tasks to `PLAN.md`.

## 12. Out of scope

- Migrating, listing, or rewriting old-format files.
- Editing/deleting/renaming stories in the UI.
- Persisting partially typed input (a refresh still restarts the current paragraph from the beginning).
- Per-paragraph duration in restored history (not stored in the format).
- Per-story scoring history separate from the global rolling window.
- Multi-device sync or story sharing.

## 13. Resolved decisions

1. **Abandoned stories:** shown in the picker, sorted by `updated_at`, with a "not played yet" label when there are zero completed paragraphs.
2. **Timestamp timezone:** local time, matching the old format's human-readable behavior. `Date:` is display-only; scoring never reads it.
3. **Stale current paragraph:** kept on resume for deterministic behavior. Regenerating it is out of scope.
4. **Metadata order:** `Date:` first, then `Speed: ... | Tier: ...`, directly underneath the paragraph.
5. **Purge:** legacy files were deleted rather than archived; no migration code exists.
