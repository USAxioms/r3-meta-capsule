"""R3 = lfp(Phi), Phi = Proj . F . A.

Termination is by a well-founded measure, never by assumption.
Absence of a fixed point is a RESULT (NO_FIXPOINT), never a silent best-so-far.
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from projection import project, digest, canon, render   # noqa: E402

NO_FIXPOINT = "NO_FIXPOINT"
FIXPOINT = "FIXPOINT"


def audit(state, invariants):
    """A : D -> D x Sigma. Sigma carries the outstanding violations and mu."""
    attrs = state.get("attributes", {})
    viol = [inv["id"] for inv in invariants
            if attrs.get(inv["requires"]) is not True]
    return state, {"violations": sorted(viol), "mu": len(viol)}


def refine(state, sigma, invariants):
    """F : D x Sigma -> D. One admissible repair per step, applied in sorted
    violation order so the trajectory is deterministic (D3)."""
    if not sigma["violations"]:
        return state
    target = sigma["violations"][0]
    inv = next(i for i in invariants if i["id"] == target)
    nxt = json.loads(json.dumps(state))          # deep copy, no aliasing
    nxt["attributes"][inv["requires"]] = True
    nxt.setdefault("notes", []).append("repaired:" + target)
    return nxt


def phi(state, invariants, rejection_log=None):
    # Phi : C -> C. A state arriving from outside C is projected into it first;
    # without this, refine() can fault on a malformed state and Phi is partial,
    # which is exactly the M2 violation this capsule exists to repair.
    state, _entry = project(state, rejection_log)
    s, sigma = audit(state, invariants)
    candidate = refine(s, sigma, invariants)
    projected, rejected = project(candidate, rejection_log)
    return projected, sigma, rejected


def run(state, invariants, budget, trace=None, rejection_log=None):
    history = []
    prev_mu = None
    for k in range(budget):
        nxt, sigma, rejected = phi(state, invariants, rejection_log)
        rec = {"k": k, "mu": sigma["mu"], "violations": sigma["violations"],
               "state_sha3": digest(state), "next_sha3": digest(nxt),
               "projection_repairs": rejected}
        if trace is not None:
            trace.write(canon(rec) + "\n")
        history.append(rec)

        if rec["state_sha3"] == rec["next_sha3"]:
            # A fixed point with outstanding violations is still a fixed point,
            # but it certifies nothing. Never conflate the two.
            cert = ("CONFORMANCE_ONLY" if sigma["mu"] == 0
                    else "FIXPOINT_WITH_OUTSTANDING_VIOLATIONS")
            return {"status": FIXPOINT, "k": k, "mu": sigma["mu"],
                    "certificate": cert, "state": nxt, "history": history}

        # well-founded measure must strictly decrease, else no termination proof
        if prev_mu is not None and sigma["mu"] >= prev_mu:
            return {"status": NO_FIXPOINT, "reason": "mu_not_decreasing",
                    "k": k, "state": nxt, "history": history}
        prev_mu = sigma["mu"]
        state = nxt

    return {"status": NO_FIXPOINT, "reason": "budget_exhausted",
            "state": state, "history": history}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--state", required=True)
    p.add_argument("--invariants", default=None)
    p.add_argument("--trace", required=True)
    p.add_argument("--rejections", required=True)
    p.add_argument("--result", default=None)
    a = p.parse_args()

    with open(a.manifest) as fh:
        man = json.load(fh)
    inv_path = a.invariants or os.path.join(
        os.path.dirname(a.manifest), "spec", "meta_invariants.json")
    with open(inv_path) as fh:
        inv_doc = json.load(fh)
    with open(a.state) as fh:
        state = json.load(fh)

    budget = man["operator"]["budget_transitions"]
    with open(a.trace, "w") as tr, open(a.rejections, "w") as rj:
        out = run(state, inv_doc["invariants"], budget, tr, rj)

    result = {
        "status": out["status"],
        "steps": len(out["history"]),
        "final_mu": out["history"][-1]["mu"] if out["history"] else None,
        "reason": out.get("reason"),
        "certificate": out.get("certificate", "NONE"),
        "meta_invariants_externally_frozen": inv_doc["externally_frozen"],
        "certificate_is_vacuous_per_proposition_4":
            not inv_doc["externally_frozen"],
        "final_state_sha3": digest(out["state"]),
    }
    path = a.result or os.path.join(os.path.dirname(a.trace), "result.json")
    with open(path, "w") as fh:
        fh.write(render(result) + "\n")
    sys.stdout.write(render(result) + "\n")


if __name__ == "__main__":
    main()
