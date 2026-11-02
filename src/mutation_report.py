"""Aggregate the sharded mutation runs into one score.

Reported three ways on purpose:

  raw        killed / all mutants
  equivalent survivors proved extensionally equal to the original, listed with
             their proofs in spec/mutation_equivalents.json
  effective  killed / (mutants - proven equivalents)

The effective rate is only meaningful because the equivalence file contains
proofs rather than judgements. If an entry there is ever weakened to an
opinion, the effective rate becomes self-serving and should be ignored in
favour of the raw one.
"""
import argparse, glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from projection import render                      # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    shards = sorted(glob.glob(os.path.join(ROOT, "logs", "mut_s*.json")))
    if not shards:
        sys.stderr.write("no shard files; run src/mutation.py --shards N --shard i\n")
        sys.exit(1)

    total = killed = 0
    survivors = []
    for f in shards:
        d = json.load(open(f))
        total += d["mutants"]
        killed += d["killed"]
        survivors += d["survivors"]

    proven = [s for s in survivors if s.get("judgement") == "equivalent"]
    other = [s for s in survivors if s.get("judgement") != "equivalent"]
    out = {
        "exhaustive": True,
        "shards": len(shards),
        "mutants": total,
        "killed": killed,
        "raw_kill_rate_percent": 100 * killed // total,
        "proven_equivalent_survivors": len(proven),
        "unexplained_survivors": len(other),
        "effective_kill_rate_percent":
            100 * killed // (total - len(proven)) if total > len(proven) else None,
        "survivors": sorted(survivors, key=lambda r: (r["file"], r["at_line_col"])),
        "note": ("An unexplained survivor is a defect the suite cannot see. "
                 "Equivalence claims live in spec/mutation_equivalents.json "
                 "and are proofs, not judgements."),
    }
    with open(a.out, "w") as fh:
        fh.write(render(out) + "\n")
    sys.stdout.write(render({k: out[k] for k in
                             ("mutants", "killed", "raw_kill_rate_percent",
                              "proven_equivalent_survivors",
                              "unexplained_survivors",
                              "effective_kill_rate_percent")}) + "\n")
    for s in other:
        sys.stdout.write("UNEXPLAINED %s@%s %s\n"
                         % (s["file"], s["at_line_col"], s["mutation"]))


if __name__ == "__main__":
    main()
