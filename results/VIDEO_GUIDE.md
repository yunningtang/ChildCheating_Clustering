# Video verification guide

What to look for, when, and which IDs to prioritize. For the team member doing the video review.

The full ID list is in `tables/video_verification_list.csv`. This document only covers the **10 tier-3 false-negative candidates** (highest analytical value) plus 1 cheater control for comparison.

---

## How to use this doc

For each cluster:
1. Find the IDs and their absolute timestamps below.
2. Open the corresponding video and jump to the time range.
3. Watch with the what-to-look-for cue in mind.
4. Note whether the behavior matches the cluster signature.

The slope-derived signals are subtle (often 1 to 2 seconds of micro-movement). You may need to slow playback to 0.5x to see them clearly.

---

## Priority order

1. **Cluster 1 (T4_pre 2 s, p = 0.004)**: strongest finding. Start here.
2. **Cluster 2 (T2_post 2 s, p = 0.017)**: easiest to verify by eye (smile signal).
3. Cluster 3 (T3_post 5 s, p = 0.100): weak signal, lower priority.
4. Cluster 4 (T2_pre 10 s, p = 0.091): single ID, weakest.

---

## Cluster 1: T4_pre first 2 seconds (p = 0.004)

| ID | label | absolute video time |
|---|---|---|
| **76** | non-cheater (tier 3, verify) | **186.03 to 188.03 s** |
| **313** | non-cheater (tier 3, verify) | **75.77 to 77.77 s** |
| **408** | non-cheater (tier 3, verify) | **110.17 to 112.17 s** |
| 403 | cheater (tier 1, **cheater control to compare against**) | 79.66 to 81.66 s |

**Phase context:** the first 2 seconds of Trial 4. The experimenter is still in the room. The child has had no chance to cheat yet.

**What to look for: leftward gaze drift**

The cluster defining signal is a coordinated horizontal eye movement:
- right eye shifts from looking out (toward the right) toward looking in (toward the nose)
- left eye shifts from looking in toward looking out (toward the left)

In plain terms: **both eyes move left over the 2-second window**. Could be glancing toward the experimenter, the door, the answer materials, or off-camera, depending on room layout.

Secondary signals:
- right outer brow drops slightly (mild relaxation or frown)
- right blink rate decreases (eyes opening / staying open)
- inner brow rises slightly (questioning / thinking expression)

**Questions to answer per ID:**
1. Do 76 / 313 / 408 (the three non-cheaters) show the same kind of leftward gaze shift as 403 (the cheater control)?
2. If yes: are they looking at something specific (experimenter, door, object), or is it an aimless scan?
3. Across the rest of the session, is there any chance these three actually cheated and the original coding missed it?

---

## Cluster 2: T2_post first 2 seconds (p = 0.017)

| ID | label | absolute video time |
|---|---|---|
| **212** | non-cheater (tier 3, verify) | **78.15 to 80.15 s** |
| **275** | non-cheater (tier 3, verify) | **68.47 to 70.47 s** |

**Phase context:** the first 2 seconds after the experimenter checks the answer in Trial 2.

**What to look for: smile onset (large signal)**

This cluster is dominated by a strong mouth signal:
- mouth corners lift (`mouthSmileLeft` + `mouthSmileRight` slope around +0.30, much larger than other clusters)
- upper lip rises (`mouthUpperUp`)
- lower lip drops (`mouthLowerDown`)

In plain terms: **a clear smile or laugh, possibly showing teeth**. This matches the JECP paper strongest finding (cheaters smile more after answer-checking), so this cluster is essentially the blendshape-level confirmation of a known effect.

**Questions to answer per ID:**
- Do 212 and 275 show the kind of got-the-answer smile typical of cheaters?
- If yes, they may be miscoded non-cheaters. This is the easiest cluster to verify by eye.

---

## Cluster 3: T3_post first 5 seconds (p = 0.100)

| ID | label | absolute video time |
|---|---|---|
| **93** | non-cheater (tier 3) | **68.59 to 73.59 s** |
| **190** | non-cheater (tier 3) | **56.94 to 61.94 s** |
| **377** | non-cheater (tier 3) | **84.82 to 89.82 s** |
| **405** | non-cheater (tier 3) | **68.32 to 73.32 s** |

**Phase context:** the first 5 seconds after the experimenter checks the answer in Trial 3.

**What to look for: open-mouth reaction**

Similar to T2_post but over a longer window:
- lower lip drops (`mouthLowerDown` rising), mouth opening
- mouth corners lift (smile)
- upper lip rises

In plain terms: **an open-mouth smile or laugh**, possibly speaking to the experimenter. Because the window is 5 seconds, this may be a sustained reaction rather than a momentary expression.

**Questions to answer per ID:**
- Do these four children show a noticeably energetic / vocal / animated reaction after Trial 3 answer-check?

**Caveat:** p = 0.100 is the weakest of the four clusters. Do not over-interpret.

---

## Cluster 4: T2_pre first 10 seconds (p = 0.091)

| ID | label | absolute video time |
|---|---|---|
| **39** | non-cheater (tier 3) | **63.28 to 73.28 s** |

**Phase context:** the first 10 seconds of Trial 2.

**What to look for: rightward gaze + slight frown**

Opposite direction from Cluster 1:
- looking-left signals decrease (`eyeLookInRight`, `eyeLookOutLeft` going down)
- inner brow drops (`browInnerUp` going down)
- right brow ridge lowers slightly (`browDownRight` going up)

In plain terms: gaze sweeps from left to right while the brows lower slightly (concentration / focus on something to the right).

**Caveat:** n = 6 cluster, single ID, least reliable finding. Verify only if there is time.

---

## Reminder on signal strength

These p-values are **uncorrected** for the 117 clusterings run. Under strict multiple-comparison correction, only Cluster 1 (T4_pre) clearly survives. Treat the other three as supplementary.

A yes-this-child-does-look-like-a-cheater verdict on **76, 313, or 408** (Cluster 1) carries the most analytical weight.

---

## What to write down per ID

A simple notebook format works:

```
ID 76, time 186.03 to 188.03 s
- Leftward gaze drift visible? [Y / N / unclear]
- Looking at any specific target? [describe]
- Other observable behavior? [free text]
- Subjective verdict (looks more like cheater or non-cheater)? [C / NC / unclear]
```

A single sheet with all 10 IDs in this format is enough, no formal scoring system needed at this stage.
