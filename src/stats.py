"""Exact nonparametric statistics in WAD-18. No floats, no approximations.

The previous version used a normal approximation to the Wilcoxon null
distribution, which needs erf, which needs a transcendental. Under WAD-18 that
is not available, and the replacement is strictly better statistics: the null
distribution is enumerated EXACTLY by dynamic programming over subset sums of
the signed ranks. The p-value is a rational number with denominator 2**n,
reported both as that exact fraction and as a WAD-18 decimal.

Ranks are carried DOUBLED so that mid-ranks from ties stay integers. No
half-integer ever needs a non-integer representation.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wad18 as W                              # noqa: E402
from prng import SplitMix64                    # noqa: E402


def doubled_ranks(values):
    """Mid-ranks times two, so ties stay integral. Deterministic tie order."""
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    out = [0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        dr = i + j + 2                      # 2 * (i+j+2)/2, exact
        for k in range(i, j + 1):
            out[order[k]] = dr
        i = j + 1
    return out


def _null_counts(ranks2):
    """Exact null distribution of the doubled positive-rank sum.

    counts[s] = number of sign assignments whose positive ranks sum to s.
    Total mass is 2**n. Pure integer DP, no sampling, no approximation.
    """
    total = sum(ranks2)
    counts = [0] * (total + 1)
    counts[0] = 1
    for r in ranks2:
        for s in range(total, r - 1, -1):
            if counts[s - r]:
                counts[s] += counts[s - r]
    return counts


def wilcoxon_signed_rank(a, b):
    """Two-sided exact paired test. a, b are sequences of ints."""
    diffs = [x - y for x, y in zip(a, b)]
    nz = [d for d in diffs if d != 0]
    n = len(nz)
    if n == 0:
        return {"n_effective": 0, "W_doubled": None,
                "p_exact": {"num": 1, "den": 1}, "p_two_sided_wad18": W.ONE,
                "method": "exact-dp", "zeros_dropped": len(diffs)}
    assert all(d != 0 for d in nz), "zero differences must be dropped first"
    r2 = doubled_ranks([abs(d) for d in nz])
    w2 = sum(r for d, r in zip(nz, r2) if d > 0)
    counts = _null_counts(r2)
    den = 1 << n
    le = sum(counts[: w2 + 1])
    ge = sum(counts[w2:])
    tail = min(le, ge)
    num = min(2 * tail, den)          # a p-value cannot exceed 1
    g = _gcd(num, den)
    return {"n_effective": n, "W_doubled": w2, "W": W.from_ratio(w2, 2),
            "p_exact": {"num": num // g, "den": den // g},
            "p_two_sided_wad18": W.from_ratio(num, den),
            "method": "exact-dp", "zeros_dropped": len(diffs) - n,
            "null_support": len(counts) - 1}


def _gcd(x, y):
    while y:
        x, y = y, x % y
    return x


BANDS = (("negligible", "0.147"), ("small", "0.33"), ("medium", "0.474"))


def magnitude(delta_wad):
    """Conventional Cliff's delta bands, strict on the lower edge: a delta
    exactly at a threshold belongs to the HIGHER band. Exposed as its own
    function so the boundary is directly testable."""
    m = abs(delta_wad)
    for name, edge in BANDS:
        if m < W.from_str(edge):
            return name
    return "large"


def cliffs_delta(a, b):
    """Exact effect size: an integer count over an integer count."""
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    den = len(a) * len(b)
    d = W.from_ratio(gt - lt, den)
    size = magnitude(d)
    return {"delta_wad18": d, "delta_exact": {"num": gt - lt, "den": den},
            "magnitude": size}


def bootstrap_ci(values, seed=20261031, iters=2000, alpha_num=5, alpha_den=100):
    """Percentile CI of the mean. Resampling indices come from the declared
    integer PRNG; every mean is a WAD-18 value; no float is constructed."""
    rng = SplitMix64(seed)
    n = len(values)
    wv = [W.from_int(v) for v in values]
    means = []
    for _ in range(iters):
        acc = 0
        for _ in range(n):
            acc += wv[rng.randint(0, n - 1)]
        means.append(W.round_half_even(acc, n))
    means.sort()
    lo_i = (alpha_num * iters) // (2 * alpha_den)
    hi_i = ((2 * alpha_den - alpha_num) * iters) // (2 * alpha_den)
    # alpha_num >= 1 keeps hi_i strictly inside the sample; assert rather than
    # clamp, so a bad alpha is a loud failure and not a silent truncation.
    if not (0 <= lo_i < hi_i < iters):
        raise ValueError("percentile indices out of range: %d, %d" % (lo_i, hi_i))
    return {"mean_wad18": W.mean(wv), "ci_lo_wad18": means[lo_i],
            "ci_hi_wad18": means[hi_i],
            "level": {"num": 2 * alpha_den - alpha_num, "den": 2 * alpha_den},
            "iters": iters, "seed": seed}


def sd(values):
    """Population standard deviation, floor-rounded, residual exposed."""
    wv = [W.from_int(v) for v in values]
    var = W.variance(wv)
    root, residual = W.sqrt_exact(var)
    return {"variance_wad18": var, "sd_wad18": root,
            "sd_floor_residual_wad18": residual}
