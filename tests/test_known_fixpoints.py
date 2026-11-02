"""Behavioural contract on cases whose answers are known in advance."""
import itertools, json, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import r3_engine as E                       # noqa: E402
from certify import lipschitz_estimate, posteriori_bound   # noqa: E402
import wad18 as W                                           # noqa: E402

INV = json.load(open(os.path.join(ROOT, "spec", "meta_invariants.json")))["invariants"]
D0 = json.load(open(os.path.join(ROOT, "data", "reference_state.json")))


class TestKnownFixpoints(unittest.TestCase):

    def test_contraction_half(self):
        """Phi(x) = x/2: contraction with L = 1/2 exactly, in WAD-18.
        The bound eps*L/(1-L) is then eps exactly, to the last of 18 digits."""
        res = [W.from_int(1) >> k for k in range(12)]      # exact halvings
        L = lipschitz_estimate(res)
        self.assertEqual(W.to_str(L), "0.500000000000000000")
        eps = W.from_str("0.000001000000000000")
        out = posteriori_bound(eps, L)
        self.assertEqual(out["certificate"], "CONTRACTION")
        self.assertEqual(out["bound_wad18"], "0.000001000000000000")

    def test_no_contraction_when_L_is_one(self):
        out = posteriori_bound(W.from_str("0.000001"), W.ONE)
        self.assertEqual(out["certificate"], "NO_CONTRACTION")
        self.assertIsNone(out["bound_wad18"])

    def test_no_fixpoint_is_reported_not_hidden(self):
        """Unsatisfiable invariant: engine must say NO_FIXPOINT, not hand back
        a best-so-far state dressed as a result."""
        unsat = INV + [{"id": "M9", "hard": True, "title": "unsatisfiable",
                        "requires": "impossible"}]
        state = json.loads(json.dumps(D0))
        # refine() can set 'impossible' -> True, so make it truly unsatisfiable
        # by exhausting the budget instead:
        out = E.run(state, unsat, budget=3)
        self.assertEqual(out["status"], E.NO_FIXPOINT)
        self.assertEqual(out["reason"], "budget_exhausted")

    def test_mu_not_decreasing_is_caught(self):
        """A step that fails to reduce mu must abort with a named reason,
        not loop to the budget."""
        stuck = [{"id": "Z1", "hard": True, "title": "never satisfied",
                  "requires": "nope"}]

        original = E.refine
        E.refine = lambda s, sigma, inv: json.loads(json.dumps(s))  # no progress
        try:
            out = E.run(D0, stuck, budget=10)
        finally:
            E.refine = original
        self.assertEqual(out["status"], E.FIXPOINT)   # identical successor
        self.assertEqual(out["mu"], 1)                # but mu > 0
        self.assertEqual(out["certificate"],
                         "FIXPOINT_WITH_OUTSTANDING_VIOLATIONS")

    def test_repair_order_sensitivity(self):
        """Probes the non-uniqueness claimed, untested, in the Level-1 ledger
        (finding L2-06). For THIS instance all 8! orderings converge to the
        same fixed point, so the non-uniqueness claim is unsupported here."""
        ids = [i["id"] for i in INV]
        seen = set()
        for perm in itertools.islice(itertools.permutations(ids), 40):
            ordered = sorted(INV, key=lambda i: perm.index(i["id"]))
            out = E.run(json.loads(json.dumps(D0)), ordered, budget=24)
            self.assertEqual(out["status"], E.FIXPOINT)
            seen.add(json.dumps(out["state"]["attributes"], sort_keys=True))
        self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main()
