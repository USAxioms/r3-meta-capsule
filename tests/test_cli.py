"""The command-line surface. These exist because mutation testing showed that
argparse contracts and console rendering were entirely uncovered."""
import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from projection import canon                          # noqa: E402
from certify import monotone_verdict                  # noqa: E402
from projection import render                        # noqa: E402

ENV = dict(os.environ, PYTHONHASHSEED="0", LC_ALL="C", TZ="UTC",
           OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")


def run(script, args):
    return subprocess.run([sys.executable, os.path.join(ROOT, "src", script)] + args,
                          env=ENV, cwd=ROOT, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)


class TestRequiredFlags(unittest.TestCase):
    """Kills the argparse 'required=True' -> False mutants."""

    def test_engine_requires_every_flag(self):
        full = ["--manifest", "manifest.json",
                "--invariants", "spec/meta_invariants.json",
                "--state", "data/reference_state.json",
                "--trace", "/dev/null", "--rejections", "/dev/null",
                "--result", "/dev/null"]
        for drop in ("--manifest", "--state", "--trace", "--rejections"):
            args = []
            skip = False
            for tok in full:
                if tok == drop:
                    skip = True
                    continue
                if skip:
                    skip = False
                    continue
                args.append(tok)
            r = run("r3_engine.py", args)
            self.assertEqual(r.returncode, 2,
                             "argparse did not reject a run without %s" % drop)
            self.assertIn(b"required", r.stderr)

    def test_certify_requires_trace_and_manifest(self):
        for args in (["--manifest", "manifest.json"],
                     ["--trace", "logs/trace.jsonl"]):
            r = run("certify.py", args)
            self.assertEqual(r.returncode, 2)
            self.assertIn(b"required", r.stderr)

    def test_certificate_file_is_canonically_rendered(self):
        """Kills certify's file-writing 'sort_keys=True' mutant."""
        with tempfile.TemporaryDirectory() as t:
            trace = os.path.join(t, "trace.jsonl")
            with open(trace, "w") as fh:
                for k, mu in enumerate([3, 2, 1]):
                    fh.write(canon({"k": k, "mu": mu}) + "\n")
            r = run("certify.py", ["--trace", trace,
                                   "--manifest", "manifest.json"])
            self.assertEqual(r.returncode, 0)
            text = open(os.path.join(t, "certificate.json")).read()
        self.assertEqual(text, render(json.loads(text)) + "\n")


class TestCanonicalRendering(unittest.TestCase):
    """Kills the 'sort_keys=True' -> False mutants: there is now exactly one
    canonical serialiser and one console renderer, and both are covered."""

    def test_canon_is_key_order_independent(self):
        self.assertEqual(canon({"b": 1, "a": 2}), canon({"a": 2, "b": 1}))
        self.assertEqual(canon({"b": 1, "a": 2}), '{"a":2,"b":1}')

    def test_render_sorts_keys(self):
        out = render({"b": 1, "a": 2})
        self.assertLess(out.index('"a"'), out.index('"b"'))

    def test_trace_lines_are_canonical(self):
        with tempfile.TemporaryDirectory() as t:
            trace = os.path.join(t, "trace.jsonl")
            r = run("r3_engine.py",
                    ["--manifest", "manifest.json",
                     "--invariants", "spec/meta_invariants.json",
                     "--state", "data/reference_state.json",
                     "--trace", trace,
                     "--rejections", os.path.join(t, "rej.jsonl"),
                     "--result", os.path.join(t, "res.json")])
            self.assertEqual(r.returncode, 0)
            for line in open(trace):
                if line.strip():
                    self.assertEqual(line.strip(), canon(json.loads(line)))


class TestMonotoneVerdict(unittest.TestCase):
    """Kills certify's 'len(residuals) > 1' mutant."""

    def test_single_residual_is_three_valued_none(self):
        self.assertIsNone(monotone_verdict([5]))
        self.assertIsNone(monotone_verdict([]))

    def test_two_residuals_give_a_verdict(self):
        self.assertTrue(monotone_verdict([5, 3]))
        self.assertFalse(monotone_verdict([3, 5]))
        self.assertFalse(monotone_verdict([3, 3]))


if __name__ == "__main__":
    unittest.main()


class TestRatifyRendering(unittest.TestCase):
    """Kills the ratify 'sort_keys=True' mutants: it uses the shared renderer."""

    def test_ratify_output_is_canonically_rendered(self):
        with tempfile.TemporaryDirectory() as t:
            out = os.path.join(t, "ratification_status.json")
            r = run("ratify.py", ["--out", out])
            self.assertEqual(r.returncode, 0)
            text = open(out).read()
        self.assertEqual(text, render(json.loads(text)) + "\n")
        self.assertEqual(r.stdout.decode(), text)

    def test_engine_result_is_canonically_rendered(self):
        with tempfile.TemporaryDirectory() as t:
            res = os.path.join(t, "res.json")
            r = run("r3_engine.py",
                    ["--manifest", "manifest.json",
                     "--invariants", "spec/meta_invariants.json",
                     "--state", "data/reference_state.json",
                     "--trace", os.path.join(t, "tr.jsonl"),
                     "--rejections", os.path.join(t, "rj.jsonl"),
                     "--result", res])
            self.assertEqual(r.returncode, 0)
            text = open(res).read()
        self.assertEqual(text, render(json.loads(text)) + "\n")
