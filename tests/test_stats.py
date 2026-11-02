import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import wad18 as W                                           # noqa: E402
from stats import (wilcoxon_signed_rank, cliffs_delta,
                   doubled_ranks, _null_counts,
                   bootstrap_ci)                             # noqa: E402


class TestExactStats(unittest.TestCase):

    def test_null_mass_is_exactly_two_to_the_n(self):
        for ranks in ([2, 4, 6, 8, 10], [2, 2, 6, 8], [2]):
            self.assertEqual(sum(_null_counts(ranks)), 2 ** len(ranks))

    def test_known_exact_p_value(self):
        """n=5, every pair moves the same way: W+ = 0, p = 2/32 = 1/16."""
        r = wilcoxon_signed_rank([1, 2, 3, 4, 5], [2, 3, 4, 5, 6])
        self.assertEqual(r["p_exact"], {"num": 1, "den": 16})
        self.assertEqual(W.to_str(r["p_two_sided_wad18"], 6), "0.062500")

    def test_p_is_one_when_no_differences(self):
        r = wilcoxon_signed_rank([1, 2, 3], [1, 2, 3])
        self.assertEqual(r["p_exact"], {"num": 1, "den": 1})

    def test_ties_give_integer_doubled_ranks(self):
        dr = doubled_ranks([5, 5, 9])
        self.assertEqual(dr, [3, 3, 6])                  # mid-ranks 1.5,1.5,3
        self.assertTrue(all(isinstance(x, int) for x in dr))

    def test_cliffs_delta_bounds(self):
        self.assertEqual(cliffs_delta([1, 2], [3, 4])["delta_exact"],
                         {"num": -4, "den": 4})
        self.assertEqual(cliffs_delta([3, 4], [1, 2])["delta_exact"],
                         {"num": 4, "den": 4})

    def test_everything_returned_is_integer_valued(self):
        r = wilcoxon_signed_rank([1, 5, 3], [2, 2, 9])
        self.assertIsInstance(r["p_two_sided_wad18"], int)
        d = cliffs_delta([1, 5, 3], [2, 2, 9])
        self.assertIsInstance(d["delta_wad18"], int)


if __name__ == "__main__":
    unittest.main()


class TestStatsSurvivors(unittest.TestCase):

    def test_null_support_is_the_total_rank_mass(self):
        """Kills stats 'len(counts) - 1' -> '+1'."""
        r = wilcoxon_signed_rank([1, 2, 3, 4, 5], [2, 3, 4, 5, 6])
        self.assertEqual(r["null_support"], sum(doubled_ranks([1, 1, 1, 1, 1])))

    def test_cliffs_delta_with_ties(self):
        """Kills stats 'x < y' -> '<=' in the lt count: ties must count for
        neither side."""
        d = cliffs_delta([1, 2, 3], [2, 3, 4])
        # pairs: gt = 3 (2>1? no...) computed exactly, ties excluded both ways
        gt = sum(1 for x in [1, 2, 3] for y in [2, 3, 4] if x > y)
        lt = sum(1 for x in [1, 2, 3] for y in [2, 3, 4] if x < y)
        self.assertEqual(d["delta_exact"], {"num": gt - lt, "den": 9})
        self.assertEqual(d["delta_exact"], {"num": -5, "den": 9})

    def test_bootstrap_rejects_a_bad_alpha(self):
        """The percentile indices are asserted, not clamped."""
        with self.assertRaises(ValueError):
            bootstrap_ci([1, 2, 3], iters=10, alpha_num=200, alpha_den=100)


class TestBootstrapIndices(unittest.TestCase):

    def test_default_alpha_gives_a_usable_interval(self):
        """Kills stats '2*alpha_den - alpha_num' -> '+' in the index and in
        the reported level."""
        ci = bootstrap_ci([10, 12, 14, 16, 18], iters=20)
        self.assertLessEqual(ci["ci_lo_wad18"], ci["mean_wad18"])
        self.assertLessEqual(ci["mean_wad18"], ci["ci_hi_wad18"])
        self.assertEqual(ci["level"], {"num": 195, "den": 200})

    def test_zero_alpha_is_rejected(self):
        """Kills stats 'hi_i < iters' -> '<=': an index equal to the sample
        size would read past the end."""
        with self.assertRaises(ValueError):
            bootstrap_ci([1, 2, 3], iters=20, alpha_num=0, alpha_den=100)


class TestBootstrapDegenerate(unittest.TestCase):

    def test_single_resample_is_rejected(self):
        """Kills stats 'lo_i < hi_i' -> '<=': a degenerate interval where the
        two percentile indices coincide is not a confidence interval."""
        with self.assertRaises(ValueError):
            bootstrap_ci([1, 2, 3], iters=1)
