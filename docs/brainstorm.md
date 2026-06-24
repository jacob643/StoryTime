# Brainstorm — Ideas That May Never Get Built

Random ideas worth capturing but not committed to any milestone. No promises.

## Random Story Ending

On each paragraph submission, there's a configurable chance (default 20%) that the generated paragraph is the final one — the story ends. The ending tone matches the outcome tier of the last typed paragraph:

- **Tier 4 (very positive)**: a triumphant, uplifting ending
- **Tier 3 (positive)**: a satisfying, hopeful ending
- **Tier 2 (neutral)**: a balanced, open-ended conclusion
- **Tier 1 (negative)**: a somber, discouraging ending
- **Tier 0 (very negative)**: a tragic, bleak ending

The chance of ending is customizable per-game. After the ending paragraph, the game shows a "story over" state instead of fetching another paragraph. The player can then restart with a new prompt.

## Continue a Written Story

Instead of starting from scratch, let the player pick a previously written story (from `writtenStories/`) and resume it. The session is reconstructed — history, rolling split speeds, last outcome tier — so the LLM continues the narrative as if the game never stopped. Useful for long stories or returning to a story after a break.

## Max Tokens Safety Cap

Smaller models can loop infinitely during generation. Add `max_tokens` (default 300) to `GameSettings` → `options.num_predict` in Ollama, mirroring the existing `max_tokens: 500` in the OpenAI-compatible provider. The Ollama API returns `"done_reason": "length"` when truncated, which we could optionally surface.

- **Option A**: hardcode `num_predict: 300` in `ollama.py` — minimal change.
- **Option B**: add `max_tokens` to settings (consistent with temperature/top_k/top_p pattern) — more user control.
