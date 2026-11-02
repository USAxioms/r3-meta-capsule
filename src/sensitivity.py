"""Obligation 5 (robustness): variance-based sensitivity in WAD-18.

Saltelli estimators for first-order (S_i) and total-effect (ST_i) Sobol
indices, computed entirely in exact fixed point. Perturbed quantities are the
three CONSTRAINT PARAMETERS, not the design variables: the question is whether
the fixed point is stable under uncertainty in the problem specification.

Ranges are tied to a declared +/-10 percent on each parameter, not chosen for
convenience.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wad18 as W                                  # noqa: E402
import domain as D                                 # noqa: E402
from prng import SplitMix64                        # noqa: E402
from search import r3_search                       # noqa: E402

PARAMS = [("P_SUM_MAX", 180, 220), ("P_PROD_MIN", 270, 330), ("P_GAP_MIN", 9, 11)]
N = 512
BOOT = 400
BUDGET = 400
SEED = 20261031


def sample(rng):
    return tuple(rng.randint(lo, hi) for _, lo, hi in PARAMS)


def evaluate(p):
    """Model output: the fixed point reached under parameter set p."""
    return r3_search(SEED, BUDGET, p)["best"]


def sobol():
    rng = SplitMix64(SEED)
    A = [sample(rng) for _ in range(N)]
    B = [sample(rng) for _ in range(N)]
    fA = [W.from_int(evaluate(a)) for a in A]
    fB = [W.from_int(evaluate(b)) for b in B]
    # Centre on the grand mean before forming the Saltelli products. With raw
    # outputs of order 2e4 the estimator is dominated by the mean and returns
    # indices far outside [0,1]; that is an estimator error, not a result.
    gm = W.mean(fA + fB)
    var = W.variance(fA + fB)
    fA = [v - gm for v in fA]
    fB = [v - gm for v in fB]

    rows = []
    for i, (name, _, _) in enumerate(PARAMS):
        AB = [A[j][:i] + (B[j][i],) + A[j][i + 1:] for j in range(N)]
        fAB = [W.from_int(evaluate(x)) - gm for x in AB]
        s_num = W.round_half_even(
            sum(W.mul(fB[j], fAB[j] - fA[j]) for j in range(N)), N)
        st_num = W.round_half_even(
            sum(W.mul(fA[j] - fAB[j], fA[j] - fAB[j]) for j in range(N)), 2 * N)
        # Bootstrap over the N paired samples, using the declared PRNG, so
        # that an index slightly outside [0,1] can be read as estimator noise
        # or not read as noise, instead of being asserted either way.
        brng = SplitMix64(SEED + i + 1)
        s_boot, t_boot = [], []
        for _ in range(BOOT):
            idx = [brng.randint(0, N - 1) for _ in range(N)]
            s_boot.append(W.div(W.round_half_even(
                sum(W.mul(fB[j], fAB[j] - fA[j]) for j in idx), N), var))
            t_boot.append(W.div(W.round_half_even(
                sum(W.mul(fA[j] - fAB[j], fA[j] - fAB[j]) for j in idx),
                2 * N), var))
        s_boot.sort(); t_boot.sort()
        lo, hi = BOOT // 40, BOOT - 1 - BOOT // 40      # central 95 percent
        rows.append({
            "parameter": name,
            "S1_wad18": W.to_str(W.div(s_num, var)) if var else None,
            "ST_wad18": W.to_str(W.div(st_num, var)) if var else None,
            "S1_ci95_wad18": [W.to_str(s_boot[lo]), W.to_str(s_boot[hi])],
            "ST_ci95_wad18": [W.to_str(t_boot[lo]), W.to_str(t_boot[hi])],
            "S1_ci_contains_one": s_boot[lo] <= W.ONE <= s_boot[hi],
            "S1_ci_contains_zero": s_boot[lo] <= W.ZERO <= s_boot[hi],
        })
    return var, fA, fB, rows, gm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    var, fA, fB, rows, gm = sobol()
    allf = [v + gm for v in fA + fB]
    out = {
        "method": "Saltelli first-order and total-effect Sobol indices",
        "arithmetic": "WAD-18 exact fixed point; no IEEE-754 anywhere",
        "base_samples_N": N, "model_runs": N * (len(PARAMS) + 2),
        "oracle_budget_per_run": BUDGET, "seed": SEED,
        "perturbed": [{"parameter": n, "lo": lo, "hi": hi,
                       "nominal": getattr(D, n)} for n, lo, hi in PARAMS],
        "output_variance_wad18": W.to_str(var),
        "output_min": min(allf) // W.SCALE, "output_max": max(allf) // W.SCALE,
        "indices": rows,
        "bootstrap_resamples": BOOT,
        "estimator_note": ("Saltelli estimators are unbiased only "
                           "asymptotically. An index slightly above 1, or "
                           "slightly negative, is finite-sample noise at this N "
                           "and is reported as computed rather than clipped "
                           "into [0,1]."),
        "interpretation": ("S1 near zero with a near-zero output variance means "
                           "the fixed point does not move under the declared "
                           "parameter uncertainty. Indices are undefined, and "
                           "reported as null, when the variance is exactly zero."),
    }
    with open(a.out, "w") as fh:
        json.dump(out, fh, sort_keys=True, indent=2)
        fh.write("\n")
    print(json.dumps({k: out[k] for k in
                      ("output_variance_wad18", "output_min", "output_max",
                       "indices")}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
