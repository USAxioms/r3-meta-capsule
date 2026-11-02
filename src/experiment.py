"""Obligation 4 (contribution) and Obligation 3 (epsilon-dominance).

Pre-registered before the run: 30 seeds, identical oracle budget, paired
two-sided Wilcoxon signed-rank, Cliff's delta effect size, bootstrap CI on the
paired difference. The result is reported whichever way it comes out.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import domain as D                                        # noqa: E402
from search import (r3_search, baseline_search,
                    r3_pareto_search)                     # noqa: E402
from stats import (wilcoxon_signed_rank, cliffs_delta, bootstrap_ci,
                   sd)                                    # noqa: E402
import wad18 as W                                         # noqa: E402

SEEDS = list(range(1, 31))
BUDGET = 2000
PARETO_BUDGET = 4000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--rejections", default=None)
    a = ap.parse_args()

    rej = open(a.rejections, "w") if a.rejections else None
    r3v, basev, rows = [], [], []
    total_rejected = 0
    best_x = None
    try:
        for s in SEEDS:
            r = r3_search(s, BUDGET, None, rej)
            b = baseline_search(s, BUDGET)
            r3v.append(r["best"])
            basev.append(b["reported"])
            total_rejected += r["rejected_candidates"]
            if best_x is None or r["best"] < D.scalarize(best_x):
                best_x = r["x"]
            rows.append({"seed": s, "r3": r["best"], "baseline": b["reported"],
                         "baseline_feasible": b["feasible"],
                         "baseline_infeasible_calls": b["infeasible_calls"],
                         "calls_r3": r["calls"], "calls_baseline": b["calls"]})
    finally:
        if rej:
            rej.close()

    assert all(x["calls_r3"] == x["calls_baseline"] == BUDGET for x in rows), \
        "budget parity violated"

    w = wilcoxon_signed_rank(r3v, basev)
    w["p_two_sided_wad18"] = W.to_str(w["p_two_sided_wad18"])
    if w.get("W") is not None:
        w["W"] = W.to_str(w["W"])
    d = cliffs_delta(r3v, basev)
    d["delta_wad18"] = W.to_str(d["delta_wad18"])
    diff = [x - y for x, y in zip(r3v, basev)]
    ci = bootstrap_ci(diff)
    for k in ("mean_wad18", "ci_lo_wad18", "ci_hi_wad18"):
        ci[k] = W.to_str(ci[k])

    d0 = D.ANCHOR
    eps = (0, 0)
    par = r3_pareto_search(1, PARETO_BUDGET)
    witnesses = [a for a in par["archive"] if D.eps_dominates(a, d0, eps)]
    witness = witnesses[0] if witnesses else None
    po3 = {
        "method": ("Obligation 3 is judged against the non-dominated ARCHIVE, "
                   "not against the scalarised optimum. A weighted descent "
                   "cannot reach designs that dominate the reference when the "
                   "weights point elsewhere; treating its failure as evidence "
                   "that no such design exists is a search defect reported as "
                   "a finding."),
        "pareto_budget": PARETO_BUDGET,
        "archive_size": len(par["archive"]),
        "archive_members_dominating_d0": len(witnesses),
        "witness": list(witness) if witness else None,
        "witness_objectives": ({"f1": D.f1(witness), "f2": D.f2(witness)}
                               if witness else None),
        "eps_dominates_d0": witness is not None,
        "strictly_dominates_d0": (D.dominates(witness, d0)
                                  if witness else False),
        "scalarised_optimum_dominates_d0": D.dominates(best_x, d0),
        "scalarised_note": ("the scalarised optimum does NOT dominate d0; it "
                            "trades f1 for f2, which is what its weights ask "
                            "for"),
        "reference_d0": list(d0),
        "d0_objectives": {"f1": D.f1(d0), "f2": D.f2(d0)},
        "best_objectives": {"f1": D.f1(best_x), "f2": D.f2(best_x)},
        "best_x": list(best_x),
        "epsilon": list(eps),
    }

    out = {
        "pre_registered": {"seeds": len(SEEDS), "budget_metric": "oracle_calls",
                           "budget": BUDGET, "test": "wilcoxon-signed-rank-paired",
                           "effect_size": "cliffs-delta", "alternative": "two-sided"},
        "baseline": "penalty hill-climb (weak-but-standard; NOT state of the art)",
        "arithmetic": "WAD-18 exact fixed point; no IEEE-754 anywhere",
        "r3_mean_wad18": W.to_str(W.mean([W.from_int(v) for v in r3v])),
        "baseline_mean_wad18": W.to_str(W.mean([W.from_int(v) for v in basev])),
        "r3_sd_wad18": W.to_str(sd(r3v)["sd_wad18"]),
        "baseline_sd_wad18": W.to_str(sd(basev)["sd_wad18"]),
        "r3_wins": sum(1 for x, y in zip(r3v, basev) if x < y),
        "ties": sum(1 for x, y in zip(r3v, basev) if x == y),
        "baseline_wins": sum(1 for x, y in zip(r3v, basev) if x > y),
        "wilcoxon": w,
        "cliffs_delta": d,
        "paired_difference_ci": ci,
        "rejected_candidates_total": total_rejected,
        "PO3_epsilon_dominance": po3,
        "per_seed": rows,
        "scope_caveat": ("Contribution is established against this baseline on "
                         "this instance only. It is not a claim about R3 versus "
                         "modern constrained optimisers, and no such claim is "
                         "supported by this capsule."),
    }
    with open(a.out, "w") as fh:
        json.dump(out, fh, sort_keys=True, indent=2)
        fh.write("\n")
    print(json.dumps({k: out[k] for k in
                      ("r3_mean_wad18", "baseline_mean_wad18", "r3_wins",
                       "ties", "baseline_wins", "wilcoxon", "cliffs_delta")},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
