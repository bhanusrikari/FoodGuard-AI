# FoodGuard AI — Annotation Guide

> Operationalizes `DATASET_SPEC.md` sections 1-3 into a step-by-step procedure
> an annotator follows for every image. If this guide and `DATASET_SPEC.md`
> ever disagree, `DATASET_SPEC.md` is authoritative — report the discrepancy
> instead of picking one silently.

---

## The Decision Order (apply every time, in this exact sequence)

```
1. Growth structure visible?
   (fuzzy / powdery / filamentous texture, raised colonies, discrete
    colored spots with irregular or ring patterning — white, green,
    black, grey, blue-green)
        │
        ├─ YES ──────────────────────────────► mold_like_growth
        │                                      decision_rule_step:
        │                                      "1_growth_structure_visible"
        │  (even if other spoilage signs are also present in the same
        │   image — mold is the higher-priority signal)
        │
        └─ NO
            │
            2. Discoloration / texture change / liquefaction /
               wilting / sliminess present, but no growth structure?
                    │
                    ├─ YES ────────────────► spoilage_indicator
                    │                        decision_rule_step:
                    │                        "2_deterioration_no_growth"
                    │
                    └─ NO
                        │
                        3. Looks like a normal, unremarkable instance
                           of this food?
                                │
                                ├─ YES ────► normal
                                │            decision_rule_step:
                                │            "3_normal_appearance"
                                │
                                └─ NO / CAN'T TELL ──► review_queue
                                                       decision_rule_step:
                                                       "4_cannot_tell"
                                                       split: "excluded"
```

Record the `decision_rule_step` you used — it is a required manifest field
and the validator cross-checks it against `label` (a mismatch is an error).

---

## Step 1 — Recognizing mold-like growth

**Look for:** fuzzy or powdery surface texture, filamentous strands, raised
3-D colonies, discrete spots (white/green/black/grey/blue-green) with
irregular edges or concentric rings.

**Common mistake to avoid:** natural surface bloom that is *normal* for the
product — e.g. the white bloom on some cheese rinds or grapes, or cocoa
bloom on chocolate. If it lacks an actual growth structure (no fuzz, no
raised colony, no spreading pattern), it is not mold — go to step 2/3, don't
default to `mold_like_growth` just because it's an unfamiliar surface marking.

**If mold-like growth is present alongside other spoilage** (discoloration,
sliminess, etc. in the same image): label `mold_like_growth` anyway — it's
the more specific and higher-priority signal.

## Step 2 — Recognizing spoilage without growth

**Look for:** browning/graying/dulling, wilting or shriveling, sliminess or
unexpected wetness, softening or liquefaction, off-color flat/smooth patches,
unusual translucency, freezer burn, expired packaged food with no visible
growth.

**Common mistake to avoid:** don't "round up" ambiguous discoloration to
`mold_like_growth` just because the food looks unappetizing — if there's no
growth structure, it's `spoilage_indicator`, even if severe.

## Step 3 — Recognizing normal

**Look for:** typical color/texture for the food type. Minor cosmetic
variation that's normal for fresh food (slight banana-peel bruising, normal
bread-crust browning, standard retail packaging) is still `normal`.

**Common mistake to avoid:** don't stretch `normal` to cover something you're
not sure about just to avoid the review queue — see step 4.

## Step 4 — When you cannot tell

Route to `review_queue` (`split: "excluded"`) whenever:
- the image is blurry, too small, too dark, or too far away to apply steps 1-3 confidently
- it's genuinely ambiguous whether a surface marking is growth or normal bloom
- the food/context is occluded or unclear

**This is not a failure** — it is the correct, honest outcome for images that
don't meet the bar for a confident label. Never force a `review_queue`
candidate into one of the three classes to "make quota." A second annotator
will look at it (see below); if still unresolved, it stays excluded
permanently.

---

## Double Annotation (mandatory for these cases)

Per `DATASET_SPEC.md` §8, **always** double-annotate:
- every `mold_like_growth` image, regardless of source
- every `team_capture` or `pilot_consented` image, regardless of label

The second annotator labels independently, **without seeing the first
annotator's label first**. Then:

| First vs. second | Outcome |
|---|---|
| Agree | Label locked, `agreement_status: "agree"` |
| Disagree | A third person (or a scheduled two-person discussion) adjudicates. Record the reasoning in `annotation_notes`. `agreement_status: "resolved"` |
| Still unresolved after adjudication | Force to `review_queue` / `split: "excluded"`, `agreement_status: "unresolved"` — do not pick a side arbitrarily |

Both original labels and the resolution reasoning are kept in the record —
never silently overwritten.

---

## Quick Reference Card

| If you see... | Label |
|---|---|
| Fuzzy/powdery/filamentous growth, colored spots with irregular/ring pattern | `mold_like_growth` |
| Browning, wilting, sliming, liquefying — no growth structure | `spoilage_indicator` |
| Looks like a normal example of this food | `normal` |
| Can't confidently apply the above three | `review_queue` (→ `excluded`) |
| Natural bloom/rind marking with no growth structure | `normal` (not mold) |
| Mold *and* other spoilage in the same image | `mold_like_growth` (mold wins) |
