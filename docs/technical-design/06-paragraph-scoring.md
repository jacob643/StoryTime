# Paragraph Scoring Proposals

**Date**: 2026-06-20  
**Status**: Draft for discussion  
**Context**: After implementing split-level rolling (3.6.10), the per-split scoring (`min()` of split tiers) feels too punishing, especially on long paragraphs. This doc catalogues alternative approaches.

---

## Current system (baseline)

- Text is split into ~50-char chunks, each chunk typed by the user gets a per-split CPM.
- Rolling window (max 20 splits) stores historical per-split speeds.
- Rolling stats: mean and stddev of per-split speeds (with σ ≥ 10 floor).
- Tier thresholds are z-score boundaries: |z| < 0.5 → tier 2 (neutral), 0.5–1.5 → tier 1/3, >1.5 → tier 0/4.

---

## Proposal A — Paragraph-average (original, pre-3.6.10)

Compute paragraph-level CPM = mean(split_speeds). Score that single CPM against rolling stats.

```
paragraph_cpm = mean(split_speeds)
z = (paragraph_cpm - rolling_avg) / rolling_stddev
```

**Pros**: Simple, length-independent, no explosion of chance events.  
**Cons**: Masks within-paragraph variation — a user who types 300, 50, 300 gets the same score as 217, 217, 217 (both avg = 217). Doesn't reward consistency.

---

## Proposal B — Min-of-splits (current 3.6.10)

Score each split individually, take the minimum tier.

```
tiers = [compute_outcome_tier(s, avg, stddev) for s in split_speeds]
outcome = min(tiers)
```

**Pros**: Strongly rewards consistency; one slow split matters. Intuitive.  
**Cons**: Punishes longer paragraphs combinatorially — each extra split adds another chance to hit a low tier. A 2-split paragraph needs one "bad" split to fail; a 6-split paragraph can be dragged down by a single slow segment. Feels unfair in practice.

---

## Proposal C — σ / √N rescaling (user's suggestion)

Keep paragraph-average CPM, but adjust the effective stddev based on paragraph length. Since N observed splits are a sample, the standard error of the mean is σ_split / √N.

```
paragraph_cpm = mean(split_speeds)
effective_stddev = rolling_stddev / sqrt(N)
z = (paragraph_cpm - rolling_avg) / effective_stddev
```

**Intuition**: If we only had 1 split, the mean is just that split and its uncertainty is the full rolling σ. With 10 splits, the average is much more precisely known, so the same deviation from the mean represents a more significant departure. Longer paragraphs automatically become "harder" (the z-score grows for the same absolute deviation).

**Example**: User types at rolling_avg = 300, σ = 40.
  - 2 splits at 250 CPM each → mean = 250, effective_σ = 40/√2 ≈ 28.3, z = -1.77 → tier 0.
  - 6 splits at 250 CPM each → mean = 250, effective_σ = 40/√6 ≈ 16.3, z = -3.06 → still tier 0.
  - 2 splits at 280, 320 → mean = 300, effective_σ = 28.3, z = 0 → tier 2.
  - 6 splits at 290 avg → effective_σ = 16.3, z = -0.61 → tier 1.

**Pros**: Mathematically principled (standard error of the mean). Length naturally modulates difficulty. Single-split case degrades gracefully (√1 = 1).  
**Cons**: Assumes splits are i.i.d. — may not hold if user fatigue causes drift. Doesn't penalize within-paragraph variance (same averaging criticism as A).

---

## Proposal D — Split-level z-score then aggregate (min-of-z)

Compute a z-score for each split, then aggregate z-scores before mapping to a tier.

```
z_scores = [(s - rolling_avg) / rolling_stddev for s in split_speeds]
agg_z = min(z_scores)          # worst split wins
# or
agg_z = mean(z_scores)         # average z
# or
agg_z = median(z_scores)       # robust to outliers
outcome = tier_from_z(agg_z)
```

**min-of-z**: Equivalent to Proposal B.  
**mean-of-z**: Equivalent to Proposal A (mean of z = z of mean, linear).  
**median-of-z**: Robust to outliers, doesn't penalize length. A single bad split doesn't ruin the paragraph unless it's truly extreme.

**Pros of median**: Simple, interpretable, length-independent.  
**Cons of median**: Still doesn't directly model the confidence gained from more samples.

---

## Proposal E — Proportion-based (count of delinquent splits)

Set thresholds on the fraction of splits below a given z-score.

```
bad = sum(1 for s in split_speeds if (s - rolling_avg) / rolling_stddev < -0.5)
frac = bad / N
if frac == 0:        tier = neutral or above   (all splits within range)
elif frac < 0.33:    tier = -1  (mild negative)
elif frac < 0.66:    tier = -2  (moderate negative)
else:                tier = -3  (strong negative)
```

Symmetrically for fast splits and positive tiers.

**Pros**: Tolerant of occasional stutters. Models "did the user mostly keep up?" rather than "was the user ever slow?".  
**Cons**: Arbitrary thresholds. Adds complexity. Still favours longer paragraphs (more samples → more stable fraction).

---

## Proposal F — Hierarchical Bayes / empirical shrinkage

Model each paragraph's true speed as a sample from a prior centred on rolling stats, with likelihood per split. The posterior mean is a weighted average of the prior and the data, where weight depends on N (more splits = more weight on data). This is equivalent to Proposal C under a normal-normal conjugate model.

```
prior_precision = 1 / rolling_stddev^2
data_precision = N / observed_stddev^2     # if we estimate per-paragraph variance
posterior_mean = (prior_precision * rolling_avg + data_precision * sample_mean) / (prior_precision + data_precision)
```

**Pros**: Fully Bayesian, principled uncertainty quantification.  
**Cons**: Overkill for a typing game. Requires estimating per-paragraph variance from ~2–10 data points (unreliable). Hard to explain.

---

## Comparison table

| Proposal | Length-adjusted | Rewards consistency | Simple to implement | Intuitive for players |
|---|---|---|---|---|
| A — Paragraph-average | No | No | Yes | Yes |
| B — Min-of-splits | ❌ (penalises length) | Yes | Yes | Yes |
| C — σ/√N | ✔ (principled) | No (averages splits) | Yes | Moderate |
| D — Median z | No | Moderate | Yes | Yes |
| E — Proportion | Moderate | Moderate | Moderate | Moderate |
| F — Hierarchical | ✔ | Moderate | No | No |

---

## Recommendation

**Proposal C (σ/√N rescaling)** appears to be the strongest candidate:
- It's mathematically sound (standard error of the mean).
- It naturally accounts for paragraph length without arbitrary penalties.
- It builds directly on the existing rolling-stats infrastructure (no new data structures).
- The only code change is in `_compute_first_paragraph_tier` and `_compute_subsequent_tier` inside `backend/routes/generate.py`.

Implementation sketch:

```python
def _compute_subsequent_tier(split_speeds, rolling, params):
    avg, stddev = compute_speed_stats(rolling, params.min_stddev_cpm)
    n = len(split_speeds)
    effective_stddev = stddev / math.sqrt(n)
    paragraph_cpm = sum(split_speeds) / n
    return compute_outcome_tier(paragraph_cpm, avg=avg, stddev=effective_stddev, params=params)
```

The first-paragraph case would follow the same pattern: baseline provides avg + σ, evaluated splits are averaged and scored against `σ / √N_evaluated`.

**Edge case — single-split first paragraph (n=1):** When there's only one split (the most common case for a 40-word first paragraph), the split-half approach has nothing to reserve for evaluation. The outcome is forced to tier 2 (neutral). The single split's CPM is appended to the rolling list so that the second paragraph has a baseline to score against.

For a hybrid that also rewards consistency, consider combining C with a small penalty for within-paragraph variance:

```python
consistency_penalty = stddev(split_speeds) / (stddev * 2)  # fraction of expected spread
adjusted_z = z - consistency_penalty
```

But start with pure C — it's clean and correct.
