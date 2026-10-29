# Custom Prompt Templates

Status: planned (Milestone 5.7)

## Goal

Let the player replace the two prompt wrappers used for LLM generation:

- **Opening template** — wraps the player's premise to generate the first paragraph.
- **Continuation template** — wraps the premise, story history, and scored direction for every later paragraph.

The defaults reproduce today's behavior. Custom templates make it possible to generate a noir mystery, a poem, a news report, a screenplay scene, or any other structure instead of the default interactive story framing.

## Template Contract

All placeholders are optional. Templates are plain text; only known tokens are substituted. Any other token is left untouched in the final prompt.

| Placeholder | Opening template | Continuation template |
|---|---|---|
| `{premise}` | Player's initial prompt | Player's initial prompt |
| `{max_words}` | `paragraph_word_count` setting | `paragraph_word_count` setting |
| `{tier}` | `2` | Scored tier `0`–`4` |
| `{direction}` | Random tier-2 phrasing | Random phrasing for the scored tier |
| `{history}` | Empty string | Formatted previous paragraphs, or empty string |

Unknown tokens such as `{style}`, `{foo}`, or `{max_word}` are preserved verbatim. No save-time validation rejects them.

A blank or whitespace-only template falls back to its built-in default so an empty prompt is never sent to the LLM.

### Defaults

Opening:

```text
Write the first paragraph of a story about: {premise}

The paragraph should be exactly {max_words} words long. Write only the paragraph, nothing else.
```

Continuation:

```text
You are writing an interactive story. The premise is: {premise}

{history}Continue the story with {direction}. The paragraph should be exactly {max_words} words long, nothing else.
```

`{history}` expands to:

```text
So far the story has unfolded as follows:
- First paragraph.
- Second paragraph.

```

or to an empty string when there is no history. The default rendering therefore matches the current prompt output exactly.

## Rendering

Add to `backend/prompt_engine.py`:

- `DEFAULT_INITIAL_PROMPT_TEMPLATE`
- `DEFAULT_CONTINUATION_PROMPT_TEMPLATE`
- `KNOWN_PROMPT_PLACEHOLDERS`
- `render_prompt_template(template, values)` — plain string replacement for each known placeholder, leaving every other character and token untouched.
- Optional `template` argument on `build_first_paragraph_prompt()` and `build_prompt()`.

Do not use `str.format()` / `format_map()`, because that would remove or reinterpret unknown braces. Use explicit replacement of the five known tokens.

## Settings

Add two fields to `GameSettings` in `backend/settings_manager.py`:

```python
initial_prompt_template: str = DEFAULT_INITIAL_PROMPT_TEMPLATE
continuation_prompt_template: str = DEFAULT_CONTINUATION_PROMPT_TEMPLATE
```

- Defaults come from `prompt_engine.py` (single source of truth).
- Existing config files without these keys load the defaults automatically.
- A non-string or blank stored value normalizes to the default on load.
- Add both fields to `SettingsResponse` and `SettingsPatch`, limited to 8000 characters.

## Preview Endpoint

Add `POST /api/settings/preview` so the UI can show exactly what the LLM will receive without duplicating rendering logic in JavaScript.

Request:

```json
{
  "kind": "initial",
  "template": "Write ...",
  "max_words": 40
}
```

`kind` is `initial` or `continuation`.

Response:

```json
{ "preview": "Write the first paragraph of a story about: ..." }
```

Sample values:

- Premise: `a lighthouse keeper who finds a message in a bottle`
- History: two short sample paragraphs
- Direction: `a small discovery proves useful`
- Tier: `2` for the opening template, `3` for the continuation template
- Max words: the requested value

The endpoint must call the same `render_prompt_template()` used by the generation routes.

## Generation Routes

- `routes/generate.py` first call: `gs.initial_prompt_template`
- `routes/generate.py` subsequent call: `gs.continuation_prompt_template`
- `routes/restart.py`: `gs.initial_prompt_template`
- `routes/simulate.py` both branches: `gs.continuation_prompt_template`

## Frontend

Add a **Story Prompt Templates** settings section between Word Count and Tier Prompts.

- `#optInitialPromptTemplate` — textarea for the opening template.
- `#optContinuationPromptTemplate` — textarea for the continuation template.
- Placeholder legend for each textarea.
- Per-template **Restore default** button.
- Inline scrollable monospace preview under each textarea (`#initialPromptPreview`, `#continuationPromptPreview`), captioned as using sample premise, history, and tier.

Behavior:

- Add mirrored default strings and both fields to `SETTINGS_DEFAULTS`, with a comment that `backend/prompt_engine.py` is the SSOT.
- Populate both textareas in `loadSettings()`, falling back to defaults when the API omits them.
- Include both fields in `collectSettings()`.
- Preview calls `POST /api/settings/preview` with a ~200 ms debounce while typing.
- Refresh previews when the word-count input changes.
- Show literal unknown placeholders in the preview, confirming they will reach the LLM unchanged.
- Client-side validation only checks non-string/over-length; unknown placeholders are allowed.
- Surface the API's `detail` field when a settings save fails.

## Testing

Backend:

- Default templates produce the same prompts as before.
- Custom templates substitute all five placeholders.
- Unknown placeholders survive rendering.
- Blank templates fall back to defaults.
- Settings defaults, save/load roundtrip, and legacy config migration.
- Preview endpoint returns the same output as the builder for equivalent sample values.
- `generate`, `restart`, and `simulate` pass the stored templates to the provider.

Frontend:

- Textareas load and save both templates.
- Restore-default buttons repopulate the built-in text.
- Preview updates when template text or word count changes.
- Unknown placeholders remain visible in the preview.

## Documentation And Changelog

- Update the prompt assembly section in `docs/technical-design/03-backend-design.md`.
- Update the settings panel section in `docs/technical-design/02-frontend-design.md`.
- Add both fields and the preview endpoint to `docs/development-process/runbook.md`.
- Add a `CHANGELOG.md` entry under `[Unreleased]`.

## Out Of Scope

- Per-session or per-story templates (settings remain global).
- Named template presets.
- Changes to the tier phrasing editor.
- A separate `{style}` setting; custom style is written directly into the templates.
