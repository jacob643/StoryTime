# Agent guidance

Instructions and quick reference for AI agents working on this codebase.

## Instructions

- After each task, mark it `[x]` in `PLAN.md` and update affected docs in `docs/`.
- When a milestone is fully completed, move it to `previous-milestones.md`.
- When adding/renaming/moving files or key functions, update this file.
- Always add or update corresponding tests (pytest for backend, Playwright for frontend). Keep existing tests passing.
- Commit after each single task — never batch multiple tasks into one commit.
- Status key in `PLAN.md`: `[ ]` pending, `[x]` completed, `[~]` in progress.

## Routes (backend/routes/)
| File | Endpoints | Key functions |
|---|---|---|
| `generate.py` | `POST /api/generate` | `_compute_first_paragraph_tier:40`, `_compute_subsequent_tier:55` |
| `generate.py` | `GET /api/health` | N/A |
| `models.py` | `GET /api/models` | N/A |
| `restart.py` | `POST /api/restart` | N/A |
| `settings.py` | `GET/POST /api/settings`, `POST /api/settings/reset`, `GET /api/settings/boundaries` | `_clamp_thresholds:55`, `_settings_to_response:63` |
| `simulate.py` | `POST /api/simulate` | N/A |

## Backend core
| File | Key contents |
|---|---|
| `game_logic.py` | `ScoringParams:27`, `split_text:37`, `compute_speed_stats:58`, `compute_outcome_tier:69`, `compute_tier_boundaries:104`, `get_outcome_label:123`. Constants: `FIXED_THRESHOLDS`, `DEFAULT_AVG_CPM`, `DEFAULT_MIN_STDDEV_CPM`, `TARGET_SPLIT_SIZE`, `MIN_SPLIT_SIZE`, `OUTCOME_LABELS` |
| `settings_manager.py` | `GameSettings:24` (all config fields), `load_settings:68`, `save_settings:82`, `get_settings:104`, `update_settings:111`, `reset_settings:122`. Migrations: `_migrate_fixed_thresholds:57`, `_migrate_outcome_directions:53` |
| `session.py` | `ParagraphRecord:16`, `GameSession:26` (has `rolling_splits`), `SessionStore:37` |
| `prompt_engine.py` | `build_prompt:78`, `build_first_paragraph_prompt:116`, `sanitize_text:140`, `validate_llm_response:160`, `parse_llm_response:171` |
| `main.py` | `main:54` — CLI args via argparse, uvicorn launch, frozen detection |
| `logger.py` | `set_verbose:17` bumps to DEBUG |
| `config.py` | `Settings:4` — pydantic BaseSettings for env vars |
| `_version.py` | `__version__ = "0.1.0"` |

## Providers (backend/providers/)
| File | Key contents |
|---|---|
| `__init__.py` | `LLMProvider:4` (ABC: `generate`, `is_available`, `list_models`) |
| `ollama.py` | `OllamaProvider:9` — passes `options.temperature/top_k/top_p` |
| `openai_compatible.py` | `OpenAICompatibleProvider:7` — passes `temperature`, `top_p` only |
| `mock.py` | `MockProvider:42` — dev/testing, reads tier from prompt |
| `registry.py` | `ProviderRegistry:14` — discovery, activation, delegation, retry |

## Frontend (frontend/)
| File | Key functions / elements |
|---|---|
| `index.html` | `#settingsPanel`, `#settingsSections` (toggles), `#textDisplay`, `#inputBox`, `#message`, `#retryButton`, `#historyEntries`, `#tierChart`, `#fixedThresholdsContainer`, `#initialPrompt`, `#lastParagraph` |
| `script.js` | `checkStartupHealth:9`, `reset:227`, `fetchNextParagraph:364`, `showError:413`, `calculateAndSend:437`, `loadSettings:565`, `collectSettings:621`, `buildFixedThresholdInputs:521`, `refreshDefaultButtons:63`, `cpmToDisplay:92`, `displayToCpm:96`, `getActiveSpeedType:88`, `computeSplits:104`, `computeSplitSpeeds:140`, `updateTierChart:297`, `sendPrompt:952` |
| `style.css` | `.default-btn`, `.settings-group`, `.ft-boundary`, tier colors: `.tier-0` through `.tier-4`, `.message`, `.retry-button` |

## Scripts (scripts/)
| File | Purpose |
|---|---|
| `build.py` | PyInstaller build, version from `_version.py`, `--clean`, `--skip-smoke` |
| `smoke_test.py` | Launches binary, polls `/api/health` up to 30s |
| `run.sh` / `run.bat` | Production launcher: binary first, python fallback |
| `build.sh` / `build.bat` | Wrappers for `build.py` |

## Testing (backend/tests/)
| File | Tests for |
|---|---|
| `test_game_logic.py` | `compute_speed_stats`, `compute_outcome_tier` (fixed + adaptive), `compute_tier_boundaries`, `split_text` |
| `test_settings.py` | `GameSettings` load/save/update/reset, migrations, caching |
| `test_session.py` | Session creation, append, rolling window (max 50) |
| `test_routes_generate.py` | First paragraph creation, subsequent submission, 503s, fallbacks |
| `test_routes_simulate.py` | Dev sim endpoint |
| `test_routes_settings.py` | (implied by test_settings) |
| `test_frontend_smoke.py` | Playwright end-to-end: create session, type paragraph, check retry |

## Key conventions
- **Scoring**: adaptive mode ("split") uses z-score with `σ/√N`. n=1 first paragraph forced tier 2.
- **Settings defaults**: mirrored in JS `SETTINGS_DEFAULTS` and `DEFAULT_FIXED_THRESHOLDS_CPM`. Backend is SSOT.
- **CPM vs WPM**: backend always stores CPM. `cpmToDisplay`/`displayToCpm` in JS. `5*WPM = CPM`.
- **Testing**: `pytest` for backend, `Playwright` for frontend smoke tests.
- **Version**: single source in `backend/_version.py`. `pyproject.toml` synced manually.
