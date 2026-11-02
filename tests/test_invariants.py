import io, json, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import r3_engine as E          # noqa: E402
from projection import project, schema_violations, digest   # noqa: E402

INV = json.load(open(os.path.join(ROOT, "spec", "meta_invariants.json")))["invariants"]
D0 = json.load(open(os.path.join(ROOT, "data", "reference_state.json")))


class TestInvariants(unittest.TestCase):

    def test_feasible_set_nonempty(self):
        """PO0. Proj must land somewhere."""
        s, bad = project({"garbage": 1, "attributes": {"x": "yes"}})
        self.assertEqual(schema_violations(s), [])

    def test_phi_is_total(self):
        """M2. Phi returns a successor for every state, including malformed ones."""
        for state in (D0, {}, {"attributes": {"phi_total": "maybe"}},
                      {"attributes": {}, "junk": None}):
            nxt, sigma, rej = E.phi(state, INV)
            self.assertEqual(schema_violations(nxt), [])
            self.assertIsInstance(sigma["mu"], int)

    def test_mu_strictly_decreases(self):
        out = E.run(D0, INV, budget=24)
        mus = [h["mu"] for h in out["history"]]
        self.assertEqual(mus[0], 8)
        for a, b in zip(mus, mus[1:]):
            self.assertLess(b, a)

    def test_reaches_fixpoint_with_zero_violations(self):
        out = E.run(D0, INV, budget=24)
        self.assertEqual(out["status"], E.FIXPOINT)
        self.assertEqual(out["mu"], 0)
        self.assertEqual(out["certificate"], "CONFORMANCE_ONLY")

    def test_rejections_are_logged_not_suppressed(self):
        """M2/PO2. A projection repair must leave a record."""
        log = io.StringIO()
        E.phi({"attributes": {"phi_total": "maybe"}, "junk": 1}, INV, log)
        lines = [l for l in log.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        rec = json.loads(lines[0])
        self.assertIn("candidate_sha3", rec)
        self.assertTrue(rec["violated"])

    def test_certificate_is_declared_vacuous(self):
        """M6. The capsule must not claim external freezing it does not have."""
        doc = json.load(open(os.path.join(ROOT, "spec", "meta_invariants.json")))
        man = json.load(open(os.path.join(ROOT, "manifest.json")))
        self.assertFalse(doc["externally_frozen"])
        self.assertFalse(man["frozen_before_execution"])


if __name__ == "__main__":
    unittest.main()
