import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import domain as D                                   # noqa: E402
from prng import SplitMix64                          # noqa: E402
from search import r3_search, baseline_search        # noqa: E402


class TestDomain(unittest.TestCase):

    def test_feasible_set_nonempty(self):
        """PO0: C has a declared witness."""
        self.assertTrue(D.feasible(D.ANCHOR))

    def test_projection_is_total_on_fuzzed_input(self):
        """M2 under adversarial input: 2000 deterministic random states,
        including out-of-bounds ones, must all land in C."""
        rng = SplitMix64(7)
        for _ in range(2000):
            x = tuple(rng.randint(-50, 120) for _ in range(D.NVAR))
            y = D.project(x)
            self.assertEqual(D.violations(y), [], "escaped C from %r" % (x,))

    def test_projection_is_idempotent_on_C(self):
        rng = SplitMix64(11)
        for _ in range(300):
            x = D.project(tuple(rng.randint(0, 63) for _ in range(D.NVAR)))
            self.assertEqual(D.project(x), x)

    def test_feasible_set_is_disconnected(self):
        """G3 forbids |x2-x3| < 10, so C is not connected and the metric
        existence route is genuinely unavailable here."""
        a = (20, 20, 30, 10, 10, 10)
        b = (20, 20, 10, 30, 10, 10)
        self.assertTrue(D.feasible(a) and D.feasible(b))
        mid = tuple((p + q) // 2 for p, q in zip(a, b))
        self.assertIn("G3_GAP", D.violations(mid))

    def test_objectives_conflict(self):
        """A bi-objective claim needs two objectives that actually disagree."""
        small, large = (18, 17, 10, 0, 0, 0), (32, 32, 42, 32, 31, 31)
        self.assertLess(D.f1(small), D.f1(large))
        self.assertGreater(D.f2(small), D.f2(large))

    def test_no_floats_in_objective_path(self):
        x = D.project((5, 5, 5, 5, 5, 5))
        for v in (D.f1(x), D.f2(x), D.scalarize(x)):
            self.assertIsInstance(v, int)
            self.assertNotIsInstance(v, float)

    def test_r3_never_evaluates_an_infeasible_point(self):
        r = r3_search(3, 300)
        self.assertTrue(D.feasible(r["x"]))
        self.assertGreater(r["rejected_candidates"], 0)

    def test_budget_parity(self):
        r, b = r3_search(5, 500), baseline_search(5, 500)
        self.assertEqual(r["calls"], b["calls"])
        self.assertEqual(r["calls"], 500)

    def test_search_is_reproducible(self):
        self.assertEqual(r3_search(9, 400)["x"], r3_search(9, 400)["x"])


if __name__ == "__main__":
    unittest.main()
