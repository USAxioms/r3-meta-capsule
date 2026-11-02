"""Certification in WAD-18. Refuses to certify what it cannot certify.

The source stopping rule ||Phi(d_k)-d_k|| <= eps bounds the RESIDUAL, not the
distance to any fixed point. With L < 1 the a-posteriori bound is

    ||d_k - d*||  <=  eps * L / (1 - L)

computed here as exact fixed-point arithmetic, so the reported bound is not
itself subject to rounding error of unknown sign.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wad18 as W                                     # noqa: E402
from projection import render                         # noqa: E402


def lipschitz_estimate(residuals_wad):
    """Conservative (max) ratio of successive residuals, in WAD-18."""
    tail = residuals_wad[-10:]
    ratios = [W.div(b, a) for a, b in zip(tail, tail[1:]) if a > 0]
    if not ratios:
        return None
    return max(ratios)


def posteriori_bound(epsilon_wad, L_wad):
    if L_wad is None or L_wad >= W.ONE:
        return {"certificate": "NO_CONTRACTION",
                "L_hat_wad18": None if L_wad is None else W.to_str(L_wad),
                "bound_wad18": None,
                "note": "residual does not bound distance to any fixed point"}
    bound = W.div(W.mul(epsilon_wad, L_wad), W.ONE - L_wad)
    return {"certificate": "CONTRACTION", "L_hat_wad18": W.to_str(L_wad),
            "bound_wad18": W.to_str(bound), "bound_raw": bound}


def monotone_verdict(residuals):
    """Three-valued on purpose. A single residual cannot evidence a trend, and
    saying 'true' there would be a claim the data does not support."""
    if len(residuals) < 2:
        return None
    return all(b < a for a, b in zip(residuals, residuals[1:]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", required=True)
    ap.add_argument("--manifest", required=True)
    a = ap.parse_args()

    with open(a.manifest) as fh:
        man = json.load(fh)
    route = man["operator"]["declared_route"]
    eps = W.from_str(man["convergence"]["epsilon_wad18"])

    residuals = []
    with open(a.trace) as fh:
        for line in fh:
            if line.strip():
                residuals.append(W.from_int(json.loads(line)["mu"]))

    if route == "metric":
        out = posteriori_bound(eps, lipschitz_estimate(residuals))
    else:
        out = {"certificate": "NO_CONTRACTION", "L_hat_wad18": None,
               "bound_wad18": None,
               "note": ("declared route is '%s'; mu is a well-founded measure, "
                        "not a metric residual, so no error bound is emitted"
                        % route)}

    out["declared_route"] = route
    out["epsilon_wad18"] = W.to_str(eps)
    out["arithmetic"] = "WAD-18 exact fixed point; no IEEE-754 anywhere"
    out["mu_strictly_decreasing"] = monotone_verdict(residuals)
    out.pop("bound_raw", None)
    path = os.path.join(os.path.dirname(a.trace), "certificate.json")
    with open(path, "w") as fh:
        fh.write(render(out) + "\n")
    sys.stdout.write(render(out) + "\n")


if __name__ == "__main__":
    main()
