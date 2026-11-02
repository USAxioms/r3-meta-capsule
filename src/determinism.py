"""Determinism contract D1-D6 under WAD-18.

D1 is now vacuous by construction: there is no floating point left to pin.
In its place D6 is enforced STATICALLY, by parsing every source file in src/
and rejecting the constructs through which a float could re-enter:

    * a float literal
    * a call to float()
    * the true-division operator '/'   (// and the WAD helpers are fine)
    * any math.* function other than isqrt
    * importing random, statistics, decimal or fractions

A contract that is only asserted in prose is a contract nobody keeps.
"""
import argparse, ast, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOWED_MATH = {"isqrt"}
BANNED_IMPORTS = {"random", "statistics", "decimal", "fractions", "numpy"}


def audit_source(path):
    with open(path) as fh:
        tree = ast.parse(fh.read(), filename=path)
    bad = []
    rel = os.path.basename(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            bad.append("%s:%d float literal %r" % (rel, node.lineno, node.value))
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            bad.append("%s:%d true division '/'" % (rel, node.lineno))
        elif isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Div):
            bad.append("%s:%d true division '/='" % (rel, node.lineno))
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id == "float":
                bad.append("%s:%d call to float()" % (rel, node.lineno))
            if (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                    and f.value.id == "math" and f.attr not in ALLOWED_MATH):
                bad.append("%s:%d math.%s (only %s permitted)"
                           % (rel, node.lineno, f.attr, sorted(ALLOWED_MATH)))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names = ([a.name.split(".")[0] for a in node.names]
                     if isinstance(node, ast.Import)
                     else [(node.module or "").split(".")[0]])
            for n in names:
                if n in BANNED_IMPORTS:
                    bad.append("%s:%d imports %s" % (rel, node.lineno, n))
    return bad


def audit_tree(src_dir=HERE):
    bad = []
    for name in sorted(os.listdir(src_dir)):
        if name.endswith(".py"):
            bad.extend(audit_source(os.path.join(src_dir, name)))
    return bad


def assert_contract(manifest_path):
    with open(manifest_path) as fh:
        man = json.load(fh)
    c = man["determinism_contract"]
    failures = []

    # D6 no floating point, enforced by parsing the source
    failures.extend("D6: " + b for b in audit_tree())
    if c.get("ieee754_used") is not False:
        failures.append("D6: manifest does not declare ieee754_used = false")
    if c.get("decimal_digits") != 18:
        failures.append("D6: manifest does not declare 18 decimal digits")

    # D2 reduction order / threads
    if c["threads"] != 1:
        failures.append("D2: threads must be pinned to 1")
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        if os.environ.get(var) != "1":
            failures.append("D2: %s is not 1" % var)

    # D3 iteration order
    if os.environ.get("PYTHONHASHSEED") != "0":
        failures.append("D3: PYTHONHASHSEED is not 0")

    # D4 randomness
    if c["prng"]["algorithm"] != "splitmix64" or c["prng"]["seed"] is None:
        failures.append("D4: declared PRNG is not the seeded splitmix64")

    # D5 environment
    if os.environ.get("TZ") != "UTC":
        failures.append("D5: TZ is not UTC")
    if os.environ.get("LC_ALL") != "C":
        failures.append("D5: LC_ALL is not C")
    return failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assert-contract", dest="manifest", required=True)
    a = ap.parse_args()
    fails = assert_contract(a.manifest)
    if fails:
        for f in fails:
            sys.stderr.write("DETERMINISM FAIL  " + f + "\n")
        sys.exit(2)
    sys.stdout.write("determinism contract D2-D6 (WAD-18): OK, "
                     "no floating point in src/\n")


if __name__ == "__main__":
    main()
