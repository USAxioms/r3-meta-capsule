"""External ratification check for M6 and Obligation 6.

Proposition 4 says self-certification against a self-authored invariant set is
vacuous. No code can repair that: the repair is an act by somebody who did not
write the code. What code CAN do is make the act machine-checkable, so that
'externally frozen' stops being a claim in prose and becomes a verifiable
state with exactly one way to reach it.

A ratification is a file spec/ratification.json containing:

    attestor            who is attesting, and how they can be contacted
    attested_sha3       SHA3-256 of spec/meta_invariants.json AS REVIEWED
    attested_utc        when
    statement           what they are attesting to, in their own words
    independent         true only if the attestor did not author the capsule

The check passes only when the file exists, the hash matches the invariant
file on disk RIGHT NOW, and independent is true. Any later edit to the
invariant set breaks the hash and revokes the ratification automatically,
which is the point: you cannot ratify a set and then change it.
"""
import argparse, hashlib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from projection import render                          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = os.path.join(ROOT, "spec", "meta_invariants.json")
RAT = os.path.join(ROOT, "spec", "ratification.json")
REQUIRED = ("attestor", "attested_sha3", "attested_utc", "statement",
            "independent")


def file_sha3(path):
    h = hashlib.sha3_256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check(inv_path=INV, rat_path=RAT):
    current = file_sha3(inv_path)
    if not os.path.exists(rat_path):
        return {"ratified": False, "status": "BLOCKED_ON_EXTERNAL_ATTESTATION",
                "current_invariant_sha3": current,
                "reason": "no spec/ratification.json; see spec/RATIFICATION.md",
                "certificate_is_vacuous_per_proposition_4": True}
    with open(rat_path) as fh:
        rat = json.load(fh)
    missing = [k for k in REQUIRED if k not in rat]
    if missing:
        return {"ratified": False, "status": "MALFORMED_ATTESTATION",
                "current_invariant_sha3": current,
                "reason": "missing fields: %s" % sorted(missing),
                "certificate_is_vacuous_per_proposition_4": True}
    if rat["attested_sha3"] != current:
        return {"ratified": False, "status": "REVOKED_BY_EDIT",
                "current_invariant_sha3": current,
                "attested_sha3": rat["attested_sha3"],
                "reason": ("the invariant set has changed since it was "
                           "attested; the attestation does not cover it"),
                "certificate_is_vacuous_per_proposition_4": True}
    if rat["independent"] is not True:
        return {"ratified": False, "status": "NOT_INDEPENDENT",
                "current_invariant_sha3": current,
                "reason": "attestor did not declare independence",
                "certificate_is_vacuous_per_proposition_4": True}
    return {"ratified": True, "status": "RATIFIED",
            "current_invariant_sha3": current,
            "attestor": rat["attestor"], "attested_utc": rat["attested_utc"],
            "certificate_is_vacuous_per_proposition_4": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = check()
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(render(res) + "\n")
    sys.stdout.write(render(res) + "\n")


if __name__ == "__main__":
    main()
