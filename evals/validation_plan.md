# Validation Plan — Reimagined GiftWise (Creator-Embed Wedge)

Three load-bearing assumptions to test before committing months of build.
Each is cheap (1–2 weekends or less) and answers something we genuinely
do not know yet. If any one comes back negative, the larger plan changes.

| # | Question | How we answer | Cost | Status |
|---|----------|---------------|------|--------|
| 1 | Will any creator say yes to embedding GiftWise? | Cold-DM 8–12 targets with a custom-themed demo | 2 weekends | template below |
| 2 | Does conversational input outperform handle paste? | A/B on giftwise.fit, ~200 sessions per arm | 1 weekend build + 2–3 weeks data | design below |
| 3 | Is portrait-shaped curation meaningfully better than current? | `python run_curation_ab.py` against existing 5 fixtures | ~$0.50, 30 min | **prototype shipped** — run to get numbers |

**Recommended order:** #3 first. It is the cheapest, runs today, and gates
the value prop in #1. If we cannot show curation lift, the embed pitch
is "another AI gift finder" — commoditized — and #1 needs different
positioning (or a different wedge entirely).

---

## Experiment #3 — Curation-quality blind taste test

**Status:** prototype shipped in this commit. Files:

- `evals/portrait_ideator.py` — single-call portrait-shaped curator
  (portrait → through-lines → composition with explicit slots → restraint).
  No inventory dependency; tests the *prompt architecture*, not retrieval.
- `evals/judge_v2.py` — adds five new judge dimensions:
  `synthesis`, `composition_shape`, `surprise_in_retrospect`,
  `restraint`, `portrait_coherence`. The last is the headline metric.
- `run_curation_ab.py` — runs current pipeline (control) and portrait
  curator (treatment) on each fixture in `evals/fixtures.py`, judges
  both with v1 + v2 dimensions, prints a side-by-side scorecard with
  per-dimension deltas and an aggregate lift number.

### How to run

```
# all 5 fixtures, both arms (~$0.50)
python run_curation_ab.py

# one fixture, both arms — quickest sanity check
python run_curation_ab.py --fixture passionate_fly_fisher

# Sonnet on both sides (cheaper, isolates prompt architecture from model)
python run_curation_ab.py --portrait-model claude-sonnet-4-6
```

### Decision rule

After running all 5 fixtures with Opus on the treatment side:

- **Treatment beats control on `portrait_coherence` by ≥1.0 points avg
  AND beats on `surprise_in_retrospect` by ≥0.5** → architectural bet
  is real. Proceed to phase 2 (partner config) of the rebuild.
- **Treatment lifts on synthesis dims but ties or loses on v1 dims
  (specificity, evidence_grounding)** → portrait shape works but the
  prompt is over-rotating to taste at the cost of grounding. Iterate
  on the prompt before deciding.
- **No meaningful lift, or treatment loses on ownership_avoidance /
  diversity** → the bet is wrong as currently shaped. Two interpretations:
  (a) the architecture is fine but Opus alone cannot bridge the gap
  without inventory grounding, or (b) "portrait-shaped" is a pretty
  idea that does not produce better picks. We re-plan #2 (agent shape)
  before building further.

### What this experiment does NOT test

- Retrieval quality (no inventory, gifts are concept-only).
- Latency.
- Cost at scale.
- Whether real users *prefer* the output (no human eval yet — judge
  is Claude). Add a human rater pass before committing if the model
  scores are ambiguous.

### Follow-ups if the bet pays off

1. Add a human-rated round: 3–5 people, blind, pick which list "feels
   like a person curated it." Confirm Claude judge agrees with humans.
2. Layer real inventory: extend `portrait_ideator` to take a candidate
   pool and select from it, not invent products. This is the actual
   v2 agent shape.
3. Wire `portrait_ideator` into a `/v2` route on the app behind a
   feature flag. Compare engagement with current pipeline on real
   traffic.

---

## Experiment #1 — Will creators embed?

The riskiest assumption in the whole plan. Without a "yes" from at
least one creator, the embed wedge is theoretical.

### Target list (8–12 creators)

Pick from these archetypes, prioritizing the ones we already follow or
have any prior touch with:

- **Gift-guide newsletters** — small/mid-size Substacks that publish
  seasonal guides. They already do gift curation manually; an AI tool
  is leverage, not threat. Examples to research: *Magasin*, *The Strategist*-adjacent
  independents, *Blackbird Spyplane*-shaped publications.
- **Niche hobby creators** — fly-fishing, pottery, cooking, running.
  Their audience asks them gift questions every December.
- **Parenting / kids newsletters** — high-intent gifting audience,
  often have existing affiliate relationships with kid brands.
- **Wedding / engagement creators** — gifting baked into the content.

Avoid for V0:
- Mega creators (>500K followers). They will not respond and the support
  burden if they did is too high for part-time.
- Pure entertainment creators with no gifting angle. Bad fit.

### Cold-DM template

```
Subject: AI gift-finder for your audience — built it for you to try

Hi [name],

I run GiftWise.fit — an AI gift recommender. Last year you wrote about
[specific gift recommendation / guide / piece]. I built something I
think your audience would use a lot, and I'd like you to try it for free.

Two-minute version: I can spin up a private version of GiftWise themed
for [their publication name], using your affiliate links instead of
mine. Your readers get an AI gift-finder they can't get anywhere else,
you keep the affiliate revenue, and I get to learn from real usage.

I built a demo on the kind of person your audience writes for —
[paste link to a curated demo result for a giftee profile that matches
their audience]. The interesting thing isn't the AI part; it's the
curation. It tries not to be on-the-nose.

If this is interesting, I'd send you a 60-second video walk-through
of the embed and we can decide in one call. If not, no follow-up.

— [Chad]
giftwise.fit
```

### What to send

For each target, prepare:

1. **One curated demo result** for a synthetic person who matches
   their audience. Use giftwise.fit, save the result page URL.
2. **A one-screenshot mockup** of what their themed embed would look
   like (their logo + colors on the input page). Sketch in Figma; this
   is a 30-minute job per creator.
3. **A 60-second loom** showing: (a) the audience-member's experience
   on the embed, (b) the affiliate-link flow that funnels to *their*
   account, (c) the analytics dashboard they would see.

### Outreach scoring

| Outcome | Count target | Interpretation |
|---|---|---|
| No reply | most | fine; baseline cold rate |
| Reply, not interested | some | useful — note the reason |
| Reply, want to learn more | ≥2 of 12 | wedge is real; book calls |
| Yes, let's try it | ≥1 of 12 | ship phase 5 (embed delivery) |

If 0 of 12 want to learn more after a 2-week followup, the wedge
needs a reframe before more investment.

### What we learn even if no one says yes

- *Why* they declined. "Already have something" → missing context
  on the market. "Not enough audience" → wrong target shape. "Don't
  trust an unknown service" → trust/track-record problem we solve
  with paid pilots, not cold pitches.

---

## Experiment #2 — Does conversational input win?

Validates the input thesis before committing to the agent rebuild.

### Hypothesis

A 4–6 turn conversational intake produces:
- higher completion rate than handle-paste (more visitors finish)
- equal or better recommendation quality (judge scores on output)
- broader applicability (works for giftees without active social)

### Build (1 weekend)

- New route `/start-chat` parallel to existing handle paste.
- Reuse `gift_ideator` on the back end — only the intake changes.
- 5 questions, free-text, with optional skip. Final prompt: "Got
  their Instagram or TikTok? I can pull more if so." Handle is
  optional add-on, not required.
- A/B selector: 50% of giftwise.fit homepage CTA goes to chat,
  50% to handle paste. Track via cookie or query param.

### Metrics

| Metric | How measured | Decision |
|---|---|---|
| Completion rate | sessions reaching `/results` ÷ sessions starting intake | chat must be ≥ handle |
| Time to first result | server-side timestamps | chat should not be >30% slower |
| Output quality | sample 20 sessions per arm, run through `judge.py` v1 | chat output ≥ handle output on v1 dims |
| User-reported satisfaction | optional thumbs at result page | chat must not be worse |

### Power / volume

At ~15 sessions/day (current rate), 50/50 split = ~7.5/arm/day.
Two weeks gives ~100 sessions per arm — enough to detect a 15%
completion-rate delta with reasonable confidence. If we want a
finer signal, run 3 weeks.

### Decision rule

- **Chat completion ≥ handle, output quality ≥ handle** → chat
  becomes the primary CTA, handle becomes "advanced / power user"
  affordance. Wire chat into the agent rebuild.
- **Chat completion higher, quality lower** → chat is the right
  shape but the prompt needs more signal extraction. Iterate.
- **Chat completion lower** → handle paste is doing more work than
  we credited. Investigate why (mobile typing friction? Question
  ordering?) before declaring the input thesis dead.

### What this experiment does NOT test

- The full reimagined agent shape — we are deliberately holding the
  curator constant to isolate the input variable.
- Embed performance — that is gated by experiment #1.

---

## Sequencing

```
Week 1:
  - Run experiment #3 (today, ~30 min). Read scorecard. Decide.
  - Start drafting experiment #1 demo links + screenshots.

Week 2:
  - If #3 passed: send first 4 cold DMs (experiment #1).
  - In parallel: build experiment #2 chat intake behind feature flag.

Weeks 3-4:
  - Collect #1 replies, do calls.
  - Run #2 A/B for 2-3 weeks.
  - Decide on the agent rebuild based on combined signal.
```

If `#3` fails: stop, re-plan the curation architecture before any
outreach. The pitch in `#1` depends on differentiation we have not
yet proven.
