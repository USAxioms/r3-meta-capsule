"""D1-D5: two runs from the frozen manifest must be byte-identical."""
import hashlib, json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = dict(os.environ, PYTHONHASHSEED="0", LC_ALL="C", TZ="UTC",
           OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
FORBIDDEN = ("hostname", os.uname().nodename, str(os.getpid()))


def run_once(outdir):
    trace = os.path.join(outdir, "trace.jsonl")
    rej = os.path.join(outdir, "rejections.jsonl")
    res = os.path.join(outdir, "result.json")
    subprocess.check_call(
        [sys.executable, os.path.join(ROOT, "src", "r3_engine.py"),
         "--manifest", os.path.join(ROOT, "manifest.json"),
         "--invariants", os.path.join(ROOT, "spec", "meta_invariants.json"),
         "--state", os.path.join(ROOT, "data", "reference_state.json"),
         "--trace", trace, "--rejections", rej, "--result", res],
        env=ENV, stdout=subprocess.DEVNULL)
    blob = b""
    for f in (trace, rej, res):
        blob += open(f, "rb").read()
    return hashlib.sha3_256(blob).hexdigest(), blob


class TestDeterminism(unittest.TestCase):

    def test_two_runs_byte_identical(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            h1, _ = run_once(a)
            h2, _ = run_once(b)
        self.assertEqual(h1, h2)

    def test_no_environment_leakage(self):
        """D5. Hex digests are excluded: a pid or hostname can occur inside a
        SHA3 string by coincidence, and flagging that would be a false alarm."""
        with tempfile.TemporaryDirectory() as a:
            _, blob = run_once(a)
        payload = []
        for line in blob.decode().splitlines():
            line = line.strip()
            if not line.startswith("{"):
                payload.append(line)
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                payload.append(line)
                continue
            payload.append(json.dumps(
                {k: v for k, v in rec.items() if not k.endswith("sha3")},
                sort_keys=True))
        text = " ".join(payload)
        for leak in FORBIDDEN:
            self.assertNotIn(leak, text)

    def test_contract_asserted(self):
        sys.path.insert(0, os.path.join(ROOT, "src"))
        import determinism
        old = os.environ.copy()
        os.environ.update({k: ENV[k] for k in
                           ("PYTHONHASHSEED", "LC_ALL", "TZ",
                            "OMP_NUM_THREADS", "MKL_NUM_THREADS")})
        try:
            fails = determinism.assert_contract(os.path.join(ROOT, "manifest.json"))
        finally:
            os.environ.clear(); os.environ.update(old)
        self.assertEqual(fails, [])


if __name__ == "__main__":
    unittest.main()
