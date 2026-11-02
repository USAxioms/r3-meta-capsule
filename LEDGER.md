# Cognitive State Ledger

Narrative record. Not machine-generated — see finding L2-01. The
machine-generated trace is `logs/trace.jsonl`.

## Level 1 — object: the source operator R3 = I . V . F . A

| # | State | Op | Transition | Check | Note |
|---|---|---|---|---|---|
| 00 | S0 | — | load source specification | — | object is the method |
| 01 | S0 | A | deconstruct the composition | FAIL M1 | I has no type as a state map; category error |
| 02 | S1 | F | re-type: Phi = V.F.A, R3 = lfp(Phi) | M1 PASS | I demoted to combinator |
| 03 | S1 | V | test Phi for totality | FAIL M2 | rejection filter makes Phi partial |
| 04 | REJ-01 | — | "retry on rejection" | REJECTED | no termination argument |
| 05 | S2 | F | V becomes projection Proj | M2 PASS | new obligation PO-0 (nonemptiness) |
| 06 | S2 | V | test fixed-point existence | FAIL M3 | asserted with no hypotheses |
| 07 | S3 | F | supply lattice / metric / termination routes | M3 PASS | conditionality made explicit |
| 08 | S3 | V | test the stopping rule | FAIL M4 | residual certifies nothing without L |
| 09 | S4 | F | a-posteriori bound eps*L/(1-L); L reported | M4 PASS | L-hat error propagated |
| 10 | S4 | V | test determinism claims | FAIL M5 | fixed-point arithmetic is not determinism |
| 11 | REJ-02 | — | "mandate integer arithmetic" | REJECTED | overflow risk, no gain over pinned IEEE-754 |
| 12 | S5 | F | determinism contract D1-D5 | M5 PASS | — |
| 13 | S5 | V | test self-application for circularity | FAIL M6 | self-generated invariants are vacuous |
| 14 | S6 | F | split out externally frozen M | M6 PASS | yields Proposition 4 |
| 15 | S6 | V | test Obligation 3 | FAIL M7 | strict Pareto generically unattainable |
| 16 | S7 | F | weaken to epsilon-dominance | M7 PASS | obligation now falsifiable |
| 17 | S7 | V | test Obligation 4 | FAIL M8 | budget and comparison undefined |
| 18 | S8 | F | oracle-call budget, n>=30, paired test, effect size | M8 PASS | — |
| 19 | S8 | I | method-tier re-audit | M1-M8 PASS | no new violations |
| 20 | S8 | I | output-tier audit of the prior pharmacology artefact | 2 corrections | eigenvalues belong to the Jacobian; k_e ~ k_deg hypothesis unflagged |
| 21 | S9 | F | corrections logged, not overwritten | — | — |
| 22 | S9 | I | residual over M | 0 | no further admissible refinement |
| 23 | S* | — | halt, emit certificate | — | CONFORMANCE_ONLY (Proposition 4) |

Rejections: 2. Violations repaired: 8.

## Level 2 — object: the Level-1 ledger

| # | Finding | Severity | Status |
|---|---|---|---|
| L2-01 | The ledger is post hoc: a reconstruction presented as a trace | Critical | Replaced by `logs/trace.jsonl` for the capsule run; the Level-1 narrative above remains a reconstruction |
| L2-02 | M1-M8 were not frozen before analysis; the manifest's `frozen_before_execution: true` was false, violating M6 while asserting it | Critical | Flag set to `false` in manifest and spec; result.json reports the certificate as vacuous. Requires an external party to repair |
| L2-03 | mu fell by exactly one per step; real repair sequences interact and mu can rise | High | Capsule enforces strict decrease and aborts with `mu_not_decreasing` otherwise. The toy instance still descends by one |
| L2-04 | Two rejections logged; a real search rejects many more | High | Rejection log is now machine-written, and for this instance is genuinely near-empty. Reported, not padded |
| L2-05 | Budget B=24 declared after termination | Medium | Now pre-declared in manifest.json and enforced before the run |
| L2-06 | Non-uniqueness claimed without testing a single alternate ordering | Medium | Tested over 40 orderings: single fixed point. Claim withdrawn |

## Level 3

Not run. It would audit Level 2 against criteria generated at Level 3 by the
same agent, which Proposition 4 shows is the vacuous case. The fixed point is at
Level 2. Further recursion adds length, not information.

The only operation that adds information here is external validation.

## Level 2 repairs actually executed (v2.0.0)

Not more recursion over the ledger — Proposition 4 closed that at Level 2.
These are the outstanding obligations, discharged or honestly refused.

| # | State | Op | Transition | Check | Note |
|---|---|---|---|---|---|
| 24 | T0 | A | audit v1.0.0 against its own manifest | FAIL | PO4, PO5, PO6 all NOT_DISCHARGED; domain instance is 8 booleans |
| 25 | T1 | F | build a real domain: 6 integers, non-convex g2, disconnected g3 | PASS | metric route now genuinely unavailable, as the paper claims |
| 26 | T1 | V | rejection ledger populated? | PASS | 37,638 logged repairs, against 2 in v1.0.0 (closes L2-04) |
| 27 | T2 | F | baseline + 30 seeds + paired test + effect size | PO4 discharged | p = 1/536870912 exact, Cliff's delta -1.0, 30/30 wins |
| 28 | T2 | V | does the optimum Pareto-dominate d0? | **NO** | PO3 discharged NEGATIVE: it trades f1 for f2. Reported as found |
| 29 | T3 | F | Saltelli Sobol S1/ST, N=256 | PO5 discharged | P_SUM_MAX carries all of it; other two constraints inactive |
| 30 | REJ-03 | — | first Sobol run, uncentred estimator | REJECTED | S1 = 32.3, far outside [0,1]: estimator error, not a result. Centred on the grand mean |
| 31 | T4 | A | USER CONSTRAINT: WAD-18, no floating point | FAIL | floats in stats (erf, sqrt), certify, prng, experiment |
| 32 | T5 | F | wad18.py: int-scaled 10**18, half-even, floor sqrt with residual exposed | PASS | D1 becomes vacuous; D6 replaces it |
| 33 | T5 | V | is the no-float claim enforced or merely stated? | FAIL | prose only |
| 34 | T6 | F | D6: static AST audit of src/, run.sh fails closed | PASS | caught 4 real violations in experiment.py |
| 35 | T6 | V | can the Wilcoxon normal approximation survive WAD-18? | NO | erf is unavailable |
| 36 | T7 | F | exact null distribution by integer DP over subset sums | PASS | and it is *better*: the approximation was wrong by ~1000x |
| 37 | T7 | V | does the test suite catch anything? | FAIL | unmeasured |
| 38 | REJ-04 | — | textual mutation harness | REJECTED | mutated docstrings; 33% kill rate was an artefact |
| 39 | T8 | F | token-level mutator over the AST token stream | PASS | 41% real kill rate |
| 40 | T8 | I | round 2: read every survivor, write a test or classify | 58% | 16 tests added |
| 41 | T9 | V | round 3 survivor: domain.project anchor fallback | **REAL BUG** | returned an infeasible anchor for out-of-range parameters — a totality violation inside the totality repair. Now raises |
| 42 | T9 | I | round 4 | 73% raw / 96% effective | 8 equivalents classified per location, 1 gap admitted |
| 43 | T* | — | halt | — | PO6 still open; only an external party closes it |

Rejections this pass: 2 (uncentred Sobol estimator, textual mutator).
Real defects found by the capsule's own instruments: 3.

**Why it stops here.** The remaining survivors are argparse flags, console
formatting, and an off-by-one in an unreachable loop guard. Writing tests for
those buys nothing a reviewer would value. The one item still worth money —
PO6, and the `externally_frozen` flag — cannot be bought with more iterations
at all. That is the diminishing-returns boundary, and it is a property of the
problem rather than of the budget.

## Level 2, pass three (v3.0.0): the regeneration

Prompted by "we need a perfect score". The honest reading of that is: go back
through the ledger, find where I was wrong, and fix it — not raise a number.

| # | State | Op | Transition | Check | Note |
|---|---|---|---|---|---|
| 44 | U0 | A | re-audit v2 against its own claims | 4 FAIL | PO3 negative, 8 self-judged equivalences, 1 admitted gap, sampled mutation rate |
| 45 | U0 | V | is the PO3 negative actually honest? | **NO** | d0 IS dominated, e.g. by (12,27,6,21,18,18). The scalarised search cannot reach dominators because its weights point elsewhere |
| 46 | REJ-05 | — | "report it as an honest negative" (the v2 position) | **REJECTED** | reporting a weighted descent's failure as evidence that no dominating design exists is the exact error this document is about |
| 47 | U1 | F | archive-driven Pareto search; PO3 judged on the archive | PO3 discharged | 12 witnesses; the scalarised failure still reported, with its cause |
| 48 | U1 | V | are the 8 "equivalent" survivors really equivalent? | PARTLY | several were my own sloppy constructs, not mathematics |
| 49 | U2 | F | delete the constructs instead of judging them | PASS | 5 sort_keys literals → one canon + one render; parity predicate rewritten; G3 repair made branch-free; three dead branches removed |
| 50 | U2 | F | close the admitted gap structurally | PASS | min(HI, ...) makes escaping the bound impossible rather than prevented |
| 51 | U3 | V | is a sampled mutation rate a score? | **NO** | it moves between runs; replaced with exhaustive over all 162 tokens |
| 52 | U3 | V | harness self-check | **REAL BUG** | in-place mutants served from a stale .pyc (mtime+size validation): the mutant never loaded and was recorded as a SURVIVOR. The harness was understating its own tests |
| 53 | U4 | F | PYTHONDONTWRITEBYTECODE + cache clear per mutant | PASS | false survivors eliminated |
| 54 | U4 | I | rounds 5-10: read every survivor, kill or prove equivalent | 96% raw | 0 unexplained; 6 proven equivalences, each with a written proof |
| 55 | U5 | F | PO6 made machine-checkable: ratify.py + RATIFICATION.md | BLOCKED | an attestation binds to the invariant file's hash; any later edit auto-revokes |
| 56 | U* | — | halt | — | PO6 and externally_frozen remain open BY CONSTRUCTION |

Rejections this pass: 1 (the v2 PO3 position).
Real defects found: 2 (the PO3 search defect, the stale-pyc false survivors).

**On "perfect".** Everything measurable from inside is now at its ceiling:
125 tests, 0 unexplained mutants, every obligation discharged except one. The
exception is not a shortfall in effort. Proposition 4 says a self-authored
invariant set certifies nothing, and that is a theorem, not a TODO. A 100%
effective mutation score is not evidence against it — a perfectly tested
program can still be measured against the wrong standard, which is exactly
what the proposition warns about. The last step belongs to someone who did not
write this.

## v3.1.0 — scoping the denominator

| # | State | Op | Transition | Check | Note |
|---|---|---|---|---|---|
| 57 | V0 | A | audit the score itself | FAIL | PO6 was sitting in the obligation list as an open item, so the artefact read as 7/8 when PO6 cannot be attempted in this environment at all |
| 58 | V1 | F | split obligations into scored and excluded-with-reason | PASS | denominator is now what the environment can support; PO6 excluded as environment-limited, named not deleted |
| 59 | V1 | V | can exclusion be abused? | RISK | an exclusion column is a place to hide failures |
| 60 | V2 | F | tests/test_score.py polices the scoping | PASS | every obligation must appear in exactly one column; every exclusion must state a reason; anything `closable_here` is forbidden from being excluded |
| 61 | V2 | V | where does M6 belong? | NEITHER | M6 is a meta-invariant, not an obligation. Putting it in `excluded` would launder it, since it IS closable — by someone else, in minutes |
| 62 | V3 | F | M6 recorded under `open_but_not_an_obligation`; ratify.py remains the authority | PASS | the engine's repaired state attribute is not the real status |
| 63 | V3 | F | score.py prints score and certificate together, always | PASS | reporting one without the other is the failure mode this capsule exists to catch |
| 64 | V* | — | halt | — | 7/7 in-scope, certificate still vacuous, both stated in one line |

**On the shape of this pass.** Excluding PO6 was correct and I had it wrong
before: an obligation that cannot be attempted is not a failure. But an
exclusion column is exactly where a failure would hide, so the same pass that
created it also created the tests that constrain it. The rule that matters is
the one in test_score.py: unattemptable here is grounds for exclusion,
inconvenient is not.

## v3.2.0 — the paper

| # | State | Op | Transition | Check | Note |
|---|---|---|---|---|---|
| 65 | W0 | A | audit paper/paper.tex against the capsule | FAIL | prose had drifted: PO4 and PO5 still marked "Not discharged", v3 mutation figures absent from the obligations text, no scoping section |
| 66 | W1 | F | abstract, obligations, results and scoring sections rewritten | PASS | statuses now match manifest.json |
| 67 | W1 | V | verify every asserted number against its log | PASS | 11 figures checked against po4, po5, mutation, score |
| 68 | W2 | F | tests/test_paper.py pins each figure to its log | PASS | prose is now an artefact under test, not commentary |
| 69 | W2 | V | run the new tests | **FAIL** | two copies of the PO3 paragraph: a previous pass added the corrected text and left the superseded section in place, so the document asserted PO3 twice |
| 70 | W3 | F | superseded section removed, instance paragraph preserved | PASS | 142 tests green |
| 71 | W* | — | halt | — | the paper can no longer drift silently |

**Note on 69.** The duplicate was introduced by me, in the pass that was
supposed to be correcting the paper, and it survived a manual read. It was
found by the test written in the same pass. Every defect worth recording in
this ledger has been found by an instrument rather than by inspection, and
this one makes the pattern hard to dismiss as coincidence.
