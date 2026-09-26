# ADR: J7L Human-Review Remediation V2

**Date:** 2026-09-26  
**Status:** Proposed for implementation  
**Scope:** Recover the J7L audited/adjudicated development successor after V1 human-review contamination

## Context

The J7L audited/adjudicated development successor V1 was intended to preserve the
28 already-frozen human assessments and obtain blinded human assessments for the
remaining 20 frozen development cases.

During S2, the first eight successor submissions (`j7l-dev-003` through
`j7l-dev-010`) were not independently authored human judgments. An AI assistant
selected the criterion scores, failure-label sets, evidence notes, verdict
implications, and rationale, and those values were pasted into the human
submission path. The operator had inspected the reviewer-safe JSON, but the
judgment itself did not originate independently from the designated human
reviewer.

`j7l-dev-011` was also exposed to an AI-proposed judgment, but it was not
submitted. V1 therefore stopped at:

- preserved original human assessments: 28;
- V1 successor submissions: 8;
- V1 total recorded human assessments: 36;
- V1 pending successor assessments: 12;
- next V1 case: `j7l-dev-011`;
- provider requests: 0;
- Jev requests: 0.

The contamination does not invalidate the frozen 48-case scientific subject, the
48/48 V3 GLM execution, the original 28-case human freeze, or the failed V3
human/reference audit. It invalidates V1's claim that its submitted successor
judgments are independent human assessments.

The project requires evidence-preserving recovery. Existing append-only records
must not be deleted, overwritten, rescored, silently relabeled, averaged, or
laundered into a valid lineage.

## Decision

Create a separate local evidence lineage:

`auragateway-j7l-human-review-remediation-v2`

V1 remains preserved and permanently non-advancing for human-authority purposes.

V2 will:

1. bind the exact V1 contamination state before new human review;
2. preserve the original 28 frozen human assessments byte-for-byte;
3. require one distinct human reviewer for all 20 cases outside the original
   28-case human audit;
4. require the V2 reviewer to attest that they have not seen AI-proposed or V1
   judgments for these cases;
5. derive all 20 work items from the same frozen primary reviewer-safe export and
   the same J7K human semantic projection;
6. exclude V1 assessment content, V3 model judgments, predecessor comparison
   content, Jev output, authoring targets, and family metadata from the reviewer
   work items;
7. persist the 20 V2 assessments append-only and in frozen case order;
8. freeze the resulting clean 48-human development inventory before any full-48
   human-versus-V3 comparison.

## Why all 20 are repeated

Only eight V1 assessments were submitted, and `j7l-dev-011` was exposed without
submission. A narrower repair could attempt to repeat only exposed or submitted
cases. That would create a mixed reviewer/provenance story across the 20-case
tail and require case-by-case arguments about exposure.

V2 instead gives the entire 20-case tail one clean reviewer identity and one
protocol. This is simpler to audit and lowers future interpretation cost.

## Reviewer boundary

The V2 reviewer must be a different person from the V1 assessment actor and must
not have seen:

- this conversation's AI-proposed scores or rationales;
- V1 successor submissions or assessments;
- V3 model-reference judgments;
- predecessor human/model comparison outputs;
- Jev outputs;
- authoring targets.

The software can enforce identity-hash inequality and record explicit
attestations. It cannot prove a person's mental independence. Operator procedure
remains part of the evidence boundary.

The AI assistant may explain mechanics and validate a human-authored submission
after the reviewer has made their own judgment. It may not propose the score,
labels, verdict, evidence note, or rationale before that human decision.

## Evidence custody

Preserve unchanged:

```text
.local/auragateway/j7l-audited-adjudicated-development-reference-v1/
```

Create:

```text
.local/auragateway/j7l-human-review-remediation-v2/
    v1_contamination_freeze.json
    reviewer_identity.json
    work-items/
    submissions/
    assessments/
    full_human_inventory_freeze.json
```

The V1 contamination freeze records hashes only for the eight submitted V1
assessments. It does not copy their judgment content into V2 reviewer work
items.

## State transitions

### R2.1 — Observe V1 contamination

Expected state:

```text
V1 successor completed = 8
V1 total human = 36
V1 pending = 12
V1 next case = j7l-dev-011
```

If this state differs, stop and re-observe before binding V2.

### R2.2 — Initialize V2

Requires:

- a reviewer SHA-256 distinct from the V1 actor hash;
- explicit distinct-human attestation;
- explicit no-prior-judgment-exposure attestation.

Initialization writes the V1 contamination freeze and reviewer identity
append-only.

### R2.3 — Prepare 20 blinded work items

Materialize the exact ordered 20-case remainder:

```text
j7l-dev-003..012
j7l-dev-015..024
```

No provider request. No Jev request. No model-reference read.

### R2.4 — Complete 20 human assessments

The fresh reviewer scores each case independently. Submission is sequential and
append-only.

### R2.5 — Freeze full human inventory

Only after all 20 V2 assessments exist:

```text
28 original frozen humans
+
20 V2 fresh humans
=
48 clean development human assessments
```

The resulting freeze binds:

- the predecessor 28-case human-freeze SHA;
- the V2 reviewer identity hash;
- the exact ordered 20 V2 assessment SHA-256 values.

Only after this freeze may the project implement and execute the full-48
human-versus-V3 comparison.

## Non-claims

V2 does not establish that:

- any human judgment is universally correct;
- GLM-5.2 is qualified;
- the final 48 cases will have zero material disagreements;
- coverage will pass;
- Jev is qualified;
- J7M has been reached;
- final A/B/C quality non-inferiority is established;
- AuraGateway is production ready.

V2 only restores a defensible human-evidence boundary for the 20-case
development tail.
