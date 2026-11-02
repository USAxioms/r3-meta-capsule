"""Mutation testing: does the test suite actually catch anything?

A suite that passes proves nothing on its own. This harness injects small,
plausible defects into the source, runs the suite against each mutant, and
reports the kill rate. A surviving mutant is a defect the tests cannot see,
and is named in the report rather than summarised away.

Mutations are textual, deterministic, and applied one at a time.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = ["src/r3_engine.py", "src/projection.py", "src/domain.py",
           "src/wad18.py", "src/stats.py", "src/certify.py",
           "src/search.py", "src/ratify.py"]
OP_RULES = {"<=": "<", ">=": ">", "<": "<=", ">": ">=", "+": "-",
            "-": "+", "==": "!=", "!=": "=="}
NAME_RULES = {"True": "False", "False": "True"}
# PYTHONDONTWRITEBYTECODE is not optional here. Mutants are written in place,
# and CPython validates a cached .pyc by (mtime, size). A mutation that does
# not change the file size, written inside the same mtime tick, was being
# served from a stale .pyc: the mutant never loaded, the suite passed, and the
# mutant was recorded as a SURVIVOR. That is a false survivor -- the harness
# understating its own tests. Caches are also cleared before every run.
ENV = dict(os.environ, PYTHONHASHSEED="0", LC_ALL="C", TZ="UTC",
           OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
           PYTHONDONTWRITEBYTECODE="1")


def _clear_pycache():
    for dirpath, dirnames, _ in os.walk(ROOT):
        for d in list(dirnames):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
                dirnames.remove(d)


def _code_tokens(text):
    """Operator and keyword tokens that are REAL CODE.

    The first version of this harness mutated the first textual match, which
    usually landed inside a module docstring or a comment and produced an
    equivalent mutant: a 'survivor' that proved nothing about the suite. Here
    the file is tokenised and only OP and NAME tokens are considered, so
    strings, docstrings and comments are structurally excluded.
    """
    import io, tokenize
    out = []
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.OP and tok.string in OP_RULES:
            out.append((tok, OP_RULES[tok.string]))
        elif tok.type == tokenize.NAME and tok.string in NAME_RULES:
            out.append((tok, NAME_RULES[tok.string]))
    return out


def _apply(text, tok, new_str):
    lines = text.splitlines(keepends=True)
    row = tok.start[0] - 1
    line = lines[row]
    lines[row] = line[:tok.start[1]] + new_str + line[tok.end[1]:]
    return "".join(lines)


def mutants(limit_per_file=0):
    """limit_per_file = 0 means EXHAUSTIVE: every eligible token in every
    target file. A sampled kill rate moves between runs and is not a score."""
    out = []
    for rel in TARGETS:
        text = open(os.path.join(ROOT, rel)).read()
        toks = _code_tokens(text)
        if not toks:
            continue
        if limit_per_file:
            step = max(1, len(toks) // limit_per_file)
            toks = toks[::step][:limit_per_file]
        for tok, new_str in toks:
            mutated = _apply(text, tok, new_str)
            if mutated == text:
                continue
            try:
                compile(mutated, rel, "exec")
            except SyntaxError:
                continue                       # not a valid mutant, skip
            out.append((rel, tok.string, new_str,
                        "%d:%d" % tok.start, mutated))
    return out


def run_suite(workdir=ROOT):
    try:
        r = subprocess.run([sys.executable, os.path.join(workdir, "tests", "run_all.py")],
                           env=ENV, cwd=workdir, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=120)
        return r.returncode
    except subprocess.TimeoutExpired:
        return 124                      # a hang is a kill: the suite detected it


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0,
                    help="0 = exhaustive (every eligible token)")
    a = ap.parse_args()

    results, killed = [], 0
    muts = mutants(a.limit)
    if a.shards > 1:
        muts = [m for i, m in enumerate(muts) if i % a.shards == a.shard]
    originals = {rel: open(os.path.join(ROOT, rel)).read()
                 for rel in {m[0] for m in muts}}
    try:
        for rel, old, new, idx, text in muts:
            with open(os.path.join(ROOT, rel), "w") as fh:
                fh.write(text)                     # mutate in place
            _clear_pycache()
            rc = run_suite()
            with open(os.path.join(ROOT, rel), "w") as fh:
                fh.write(originals[rel])           # restore immediately
            alive = (rc == 0)
            killed += 0 if alive else 1
            results.append({"file": rel, "mutation": "%r -> %r" % (old, new),
                            "at_line_col": idx,
                            "status": "SURVIVED" if alive else "killed"})
    finally:
        for rel, text in originals.items():        # restore on any exit path
            with open(os.path.join(ROOT, rel), "w") as fh:
                fh.write(text)
    if False:
        alive = False

    eq_path = os.path.join(ROOT, "spec", "mutation_equivalents.json")
    judged = json.load(open(eq_path)) if os.path.exists(eq_path) else {
        "equivalents": {}, "admitted_gaps": {}}
    for r in results:
        key = "%s@%s" % (r["file"], r["at_line_col"])
        if r["status"] != "SURVIVED":
            continue
        if key in judged.get("equivalents", {}):
            r["judgement"] = "equivalent"
            r["reason"] = judged["equivalents"][key]
        elif key in judged.get("admitted_gaps", {}):
            r["judgement"] = "ADMITTED GAP"
            r["reason"] = judged["admitted_gaps"][key]
        else:
            r["judgement"] = "UNEXPLAINED"
            r["reason"] = "not classified; treat as a real gap until it is"
    surv = [r for r in results if r["status"] == "SURVIVED"]
    real = [r for r in surv if r["judgement"] != "equivalent"]
    out = {"mutants": len(muts), "killed": killed,
           "survivors_judged_equivalent": len(surv) - len(real),
           "survivors_real_or_unexplained": len(real),
           "effective_kill_rate_percent_floor":
               (100 * killed) // max(1, len(muts) - (len(surv) - len(real))),
           "survived": len(muts) - killed,
           "kill_rate_percent_floor": (100 * killed) // max(1, len(muts)),
           "survivors": surv,
           "all": results,
           "note": ("A survivor is a defect the suite cannot see. Survivors are "
                    "listed in full; a kill rate alone would hide which checks "
                    "are missing.")}
    with open(a.out, "w") as fh:
        json.dump(out, fh, sort_keys=True, indent=2)
        fh.write("\n")
    print(json.dumps({k: out[k] for k in
                      ("mutants", "killed", "survived",
                       "kill_rate_percent_floor",
                       "survivors_judged_equivalent",
                       "survivors_real_or_unexplained",
                       "effective_kill_rate_percent_floor")},
                     sort_keys=True, indent=2))
    for r in out["survivors"]:
        print("SURVIVED [%s]  %s@%s  %s"
              % (r["judgement"], r["file"], r["at_line_col"], r["mutation"]))


if __name__ == "__main__":
    main()
