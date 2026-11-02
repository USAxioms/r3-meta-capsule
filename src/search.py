"""Two searches under an identical oracle-call budget.

BUDGET METRIC: one oracle call = one evaluation of the objective pair
(f1, f2). Constraint checking is analytic and free for BOTH methods, which is
the standard convention and favours neither.

  r3_search       Proj-based. Repairs every candidate into C before spending
                  an oracle call, so no call is ever spent on an infeasible
                  point. Accepts only strict decrease of mu, which is the
                  well-founded measure, so termination is by Theorem (term).

  baseline_search Penalty hill-climb: the conventional comparator. Evaluates
                  candidates whether or not they are feasible and adds a
                  penalty. This is a WEAK-BUT-STANDARD baseline; it is not a
                  state-of-the-art constrained optimiser, and the contribution
                  claim is scoped to it accordingly.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import domain as D                                     # noqa: E402
from prng import SplitMix64                            # noqa: E402

PENALTY = 10 ** 6
DELTAS = (-8, -4, -1, 1, 4, 8)


class Oracle(object):
    def __init__(self, budget):
        self.budget = budget
        self.calls = 0

    def value(self, x):
        if self.calls >= self.budget:
            raise StopIteration
        self.calls += 1
        return D.scalarize(x)


def _neighbour(rng, x):
    y = list(x)
    i = rng.randint(0, D.NVAR - 1)
    y[i] += DELTAS[rng.randint(0, len(DELTAS) - 1)]
    return tuple(y)


def r3_search(seed, budget, p=None, rejection_log=None):
    rng = SplitMix64(seed)
    orc = Oracle(budget)
    x = D.project(D.ANCHOR, p)
    best = orc.value(x)
    archive = [x]
    rejected = 0
    try:
        while True:
            cand = _neighbour(rng, x)
            if D.violations(cand, p):
                rejected += 1
            proj = D.project(cand, p, rejection_log)     # Proj : D -> C
            v = orc.value(proj)
            if v < best:                                  # strict mu decrease
                best, x = v, proj
                archive = [a for a in archive if not D.dominates(proj, a)]
                if not any(D.dominates(a, proj) for a in archive):
                    archive.append(proj)
    except StopIteration:
        pass
    return {"best": best, "x": x, "calls": orc.calls,
            "rejected_candidates": rejected, "archive": archive}


def baseline_search(seed, budget, p=None):
    rng = SplitMix64(seed)
    orc = Oracle(budget)
    x = D.ANCHOR
    infeasible_calls = 0

    def penalised(y):
        raw = orc.value(y)
        nv = len(D.violations(y, p))
        return raw + PENALTY * nv, nv

    best, nv = penalised(x)
    try:
        while True:
            cand = _neighbour(rng, x)
            cand = tuple(min(D.HI, max(D.LO, c)) for c in cand)
            v, nv = penalised(cand)                       # call spent regardless
            if nv:
                infeasible_calls += 1
            if v < best:
                best, x = v, cand
    except StopIteration:
        pass
    feas = D.feasible(x, p)
    return {"best": best if feas else None, "x": x, "calls": orc.calls,
            "feasible": feas, "infeasible_calls": infeasible_calls,
            "reported": best}


def r3_pareto_search(seed, budget, p=None, rejection_log=None):
    """Archive-driven variant used ONLY to discharge Obligation 3.

    The scalarised search descends a single weighted measure, so it cannot
    reach regions that improve one objective at the cost of the weighted sum
    even when they strictly dominate the reference. That is a property of the
    scalarisation, not evidence that no dominating design exists, and reading
    it as the latter is how a search defect gets reported as a finding.

    This procedure keeps a non-dominated archive and accepts any candidate the
    archive does not dominate. It makes NO fixed-point claim: there is no
    well-founded measure here, and none is asserted.
    """
    rng = SplitMix64(seed)
    orc = Oracle(budget)
    x = D.project(D.ANCHOR, p)
    orc.value(x)
    archive = [x]
    try:
        while True:
            base = archive[rng.randint(0, len(archive) - 1)]
            cand = D.project(_neighbour(rng, base), p, rejection_log)
            orc.value(cand)
            if any(D.dominates(a, cand) for a in archive) or cand in archive:
                continue
            archive = [a for a in archive if not D.dominates(cand, a)]
            archive.append(cand)
    except StopIteration:
        pass
    archive.sort(key=lambda a: (D.f1(a), D.f2(a)))
    return {"archive": archive, "calls": orc.calls}
