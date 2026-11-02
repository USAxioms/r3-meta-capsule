"""Fill manifest.json with SHA3-256 digests of every capsule file.

Run AFTER execution so that produced logs are hashed too. The manifest's own
hash is necessarily excluded (a file cannot contain its own digest).
"""
import hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {"manifest.json"}


def sha3(path):
    h = hashlib.sha3_256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    entries = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames.sort()
        if "__pycache__" in dirpath:
            continue
        for name in sorted(filenames):
            rel = os.path.relpath(os.path.join(dirpath, name), ROOT)
            if rel in SKIP or rel.endswith(".pyc"):
                continue
            entries.append({"path": rel, "sha3_256": sha3(os.path.join(ROOT, rel)),
                            "produced": rel.startswith("logs/")})
    man_path = os.path.join(ROOT, "manifest.json")
    with open(man_path) as fh:
        man = json.load(fh)
    man["artifacts"] = entries
    man["meta_invariants_sha3"] = sha3(
        os.path.join(ROOT, "spec", "meta_invariants.json"))
    with open(man_path, "w") as fh:
        json.dump(man, fh, sort_keys=True, indent=2)
        fh.write("\n")
    print("hashed %d artifacts" % len(entries))


if __name__ == "__main__":
    sys.exit(main())
