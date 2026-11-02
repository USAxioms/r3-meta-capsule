"""Proj: validation as projection onto the feasible set, not as rejection.

A rejection filter leaves Phi partial and the iteration can stall with no
successor state. Projection restores totality at the cost of one new
obligation: C must be non-empty and Proj single-valued under a declared
tie-break. The tie-break here is lexicographic over sorted attribute keys.

Rejected candidates are NOT discarded. They are logged by SHA3-256 digest
plus violation codes, so the ledger stays bounded in size.
"""
import hashlib, json

SCHEMA_KEYS = ("id", "attributes", "notes")


def canon(obj):
    """THE canonical serialisation. Every hash and every log line in the
    capsule goes through this one function, so key ordering is established in
    exactly one place and is covered by exactly one test."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def render(obj):
    """THE console/file pretty renderer. One definition, one test, so key
    ordering is not re-decided in five modules."""
    return json.dumps(obj, sort_keys=True, indent=2)


def digest(obj):
    return hashlib.sha3_256(canon(obj).encode("utf-8")).hexdigest()


def schema_violations(state):
    """Structural feasibility: what makes a candidate a well-formed state at all."""
    bad = []
    if not isinstance(state, dict):
        return ["SCHEMA_NOT_OBJECT"]
    for k in sorted(state.keys()):
        if k not in SCHEMA_KEYS:
            bad.append("SCHEMA_UNKNOWN_KEY:%s" % k)
    attrs = state.get("attributes")
    if not isinstance(attrs, dict):
        bad.append("SCHEMA_ATTRIBUTES_NOT_OBJECT")
    else:
        for k in sorted(attrs.keys()):
            if not isinstance(attrs[k], bool):
                bad.append("SCHEMA_NON_BOOLEAN_ATTRIBUTE:%s" % k)
    return bad


def nearest_feasible(state):
    """Declared tie-break: drop unknown keys, coerce non-boolean attributes to
    False (the conservative direction: an attribute is not satisfied unless it
    is explicitly and validly satisfied)."""
    out = {k: state[k] for k in sorted(state) if k in SCHEMA_KEYS}
    attrs = out.get("attributes")
    if not isinstance(attrs, dict):
        out["attributes"] = {}
    else:
        out["attributes"] = {k: (attrs[k] is True) for k in sorted(attrs)}
    out.setdefault("id", "unnamed")
    out.setdefault("notes", [])
    return out


def project(candidate, rejection_log=None):
    bad = schema_violations(candidate)
    if not bad:
        return candidate, []
    if rejection_log is not None:
        rejection_log.write(canon(
            {"candidate_sha3": digest(candidate), "violated": sorted(bad)}) + "\n")
    return nearest_feasible(candidate), sorted(bad)
