"""A real domain instance: constrained bi-objective integer design.

Integer arithmetic throughout. Dynamic range is bounded and known a priori
(each variable is 6 bits), which is exactly the regime in which M5 licenses
fixed-point / integer representation. No floats appear anywhere in the
objective or constraint path, so the search is bit-exact by construction
rather than by contract.

The feasible set is deliberately NON-CONVEX (g2) and DISCONNECTED (g3), so the
metric existence route is unavailable and the termination route must be used.
This is the case the paper warns about, instantiated rather than described.
"""
NVAR = 6
LO, HI = 0, 63

# constraint parameters, perturbed by the sensitivity analysis
P_SUM_MAX = 200
P_PROD_MIN = 300
P_GAP_MIN = 10

ANCHOR = (20, 20, 30, 10, 10, 10)     # witness that C is non-empty (PO0)
MAX_SHED_PASSES = 512                 # bounded: each pass removes >= 1 unit
MAX_G2_PASSES = 2 * HI + 2            # bounded: each pass raises one coord by 1


def violations(x, p=None):
    """Hard-constraint violations, as sorted codes. Pure integer arithmetic."""
    smax, pmin, gmin = p or (P_SUM_MAX, P_PROD_MIN, P_GAP_MIN)
    v = []
    if any(xi < LO or xi > HI for xi in x):
        v.append("G0_BOUNDS")
    if sum(x) > smax:
        v.append("G1_SUM")
    if x[0] * x[1] < pmin:
        v.append("G2_PRODUCT")          # non-convex
    if abs(x[2] - x[3]) < gmin:
        v.append("G3_GAP")              # disconnected
    if (x[4] % 2) != (x[5] % 2):
        v.append("G4_PARITY")
    return sorted(v)


def feasible(x, p=None):
    return not violations(x, p)


def f1(x):
    """'mass': rewards small variables."""
    return sum(xi * xi for xi in x)


def f2(x):
    """'throughput shortfall': rewards large variables. Conflicts with f1."""
    return 4 * (NVAR * HI - sum(x))


def scalarize(x):
    """Integer scalarisation used as the well-founded measure mu.
    Non-negative and bounded below, so strict decrease implies termination."""
    return f1(x) + 20 * f2(x)


def dominates(a, b):
    """Pareto dominance on (f1, f2), minimisation."""
    fa, fb = (f1(a), f2(a)), (f1(b), f2(b))
    return all(p <= q for p, q in zip(fa, fb)) and any(p < q for p, q in zip(fa, fb))


def eps_dominates(a, b, eps=(0, 0)):
    """PO3. No objective worse by more than eps_j, at least one better."""
    fa, fb = (f1(a), f2(a)), (f1(b), f2(b))
    no_worse = all(p <= q + e for p, q, e in zip(fa, fb, eps))
    better = any(p < q - e for p, q, e in zip(fa, fb, eps))
    return no_worse and better


def project(x, p=None, rejection_log=None):
    """Proj : D -> C. Deterministic repair, then a declared feasible fallback.

    Totality is guaranteed: if the repair sequence does not reach C within its
    bounded number of passes, ANCHOR is returned. Nothing is ever rejected
    into a dead end, and every repair is logged.
    """
    smax, pmin, gmin = p or (P_SUM_MAX, P_PROD_MIN, P_GAP_MIN)
    before = tuple(x)
    y = [min(HI, max(LO, int(xi))) for xi in x]

    for _ in range(8):                               # bounded repair passes
        if not violations(y, p):
            break
        # G2: raise the smaller of x0,x1 until the product clears pmin.
        # min(HI, ...) makes escaping the upper bound structurally impossible,
        # rather than prevented by a comparison that has to be got right.
        for _g2_pass in range(MAX_G2_PASSES):
            if y[0] * y[1] >= pmin:
                break                         # the min() clamp below makes a
                                              # separate at-the-cap exit dead
            i = 0 if y[0] <= y[1] else 1      # y[i] < HI here: the
            y[i] = min(HI, y[i] + 1)          # guard above broke otherwise
        # G3: push x2 and x3 apart, away from their midpoint. need is clamped
        # at zero rather than guarded by a comparison, so the already-wide-
        # enough case is a no-op by construction instead of by a branch.
        need = max(0, gmin - abs(y[2] - y[3]))
        up, dn = (2, 3) if y[2] >= y[3] else (3, 2)
        give = min(need, HI - y[up])
        y[up] += give
        y[dn] = max(LO, y[dn] - (need - give))
        # G4: parity
        if (y[4] % 2) != (y[5] % 2):
            y[5] = y[5] - 1 if y[5] > LO else y[5] + 1
        # G1: shed from the largest coordinate that is not load-bearing
        for _shed_pass in range(MAX_SHED_PASSES):
            if sum(y) <= smax:
                break
            order = sorted(range(NVAR), key=lambda i: (-y[i], i))
            for i in order:
                trial = list(y)
                trial[i] -= 2 if i in (4, 5) else 1      # keep G4 intact
                if trial[i] < LO:
                    continue
                if i in (0, 1) and trial[0] * trial[1] < pmin:
                    continue
                if i in (2, 3) and abs(trial[2] - trial[3]) < gmin:
                    continue
                y = trial
                break
            else:
                break

    out = tuple(y)
    if violations(out, p):
        # PO0 made operational: the fallback is only a fallback if it is
        # actually in C for THESE parameters. Silently returning an
        # infeasible anchor would break totality while appearing to repair it.
        if violations(ANCHOR, p):
            raise ValueError(
                "feasible set may be empty for parameters %r: the declared "
                "anchor %r violates %r" % (p, ANCHOR, violations(ANCHOR, p)))
        out = ANCHOR
    if out != before and rejection_log is not None:
        rejection_log.write('{"candidate": %s, "violated": %s, "repaired_to": %s}\n'
                            % (list(before), violations(before, p), list(out)))
    return out
