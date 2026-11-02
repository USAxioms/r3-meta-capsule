"""Compute the obligation score over the IN-SCOPE denominator.

The denominator is the set of obligations this environment can support. An
obligation that cannot be attempted here is excluded and named with its
reason; it is neither counted as discharged nor counted as a failure, because
both would be false.

Two things are kept strictly apart:

  the SCORE          what the artefact achieved against what it could attempt
  the CERTIFICATE    whether that score was measured against a ratified
                     standard

A perfect score with an unratified standard is a real result and a vacuous
certificate at the same time. Reporting one without the other is the failure
mode this whole capsule exists to catch, so score.py always prints both.
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from projection import render                       # noqa: E402
import ratify                                       # noqa: E402

DISCHARGED = ("discharged", "discharged_negative")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    man = json.load(open(os.path.join(ROOT, "manifest.json")))
    scope, obs = man["scope"], man["obligations"]

    scored, missing = [], []
    for name in scope["scored"]:
        status = obs.get(name, {}).get("status", "ABSENT")
        (scored if status in DISCHARGED else missing).append(
            {"obligation": name, "status": status})

    rat = ratify.check()
    out = {
        "denominator": "in-scope obligations only",
        "scored_total": len(scope["scored"]),
        "scored_discharged": len(scored),
        "score": "%d/%d" % (len(scored), len(scope["scored"])),
        "perfect_within_scope": not missing,
        "outstanding": missing,
        "excluded_from_denominator": [
            {"obligation": k, "reason": v["reason"], "kind": v["kind"]}
            for k, v in sorted(scope["excluded"].items())],
        "certificate": {
            "ratified": rat["ratified"],
            "status": rat["status"],
            "vacuous_per_proposition_4":
                rat["certificate_is_vacuous_per_proposition_4"],
            "note": ("The score below is measured against an invariant set "
                     "that has not been ratified by an independent party. The "
                     "score is real; the certificate that it was the RIGHT "
                     "standard is not. These are separate claims and neither "
                     "substitutes for the other."),
        },
    }
    with open(a.out, "w") as fh:
        fh.write(render(out) + "\n")

    sys.stdout.write("SCORE  %s in-scope obligations discharged%s\n"
                     % (out["score"], " (perfect within scope)"
                        if out["perfect_within_scope"] else ""))
    for e in out["excluded_from_denominator"]:
        sys.stdout.write("EXCLUDED  %s: %s\n" % (e["obligation"], e["kind"]))
    sys.stdout.write("CERTIFICATE  %s%s\n"
                     % (out["certificate"]["status"],
                        " -- score stands, certificate vacuous"
                        if out["certificate"]["vacuous_per_proposition_4"]
                        else ""))


if __name__ == "__main__":
    main()
