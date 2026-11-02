import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import wad18 as W   # noqa: E402


class TestWad18(unittest.TestCase):

    def test_round_half_even(self):
        self.assertEqual(W.round_half_even(5, 2), 2)      # 2.5 -> 2
        self.assertEqual(W.round_half_even(7, 2), 4)      # 3.5 -> 4
        self.assertEqual(W.round_half_even(-5, 2), -2)    # -2.5 -> -2
        self.assertEqual(W.round_half_even(1, 3), 0)

    def test_roundtrip(self):
        for s in ("0.000000000000000001", "-3.250000000000000000",
                  "123456.789000000000000000"):
            self.assertEqual(W.to_str(W.from_str(s)), s)

    def test_rejects_over_precision(self):
        with self.assertRaises(ValueError):
            W.from_str("1.0000000000000000001")

    def test_sqrt_two(self):
        # sqrt(2) = 1.41421356237309504880...; floor at 18 places
        self.assertEqual(W.to_str(W.sqrt(W.from_int(2))),
                         "1.414213562373095048")

    def test_sqrt_residual_exposed(self):
        root, residual = W.sqrt_exact(W.from_int(2))
        self.assertGreaterEqual(residual, 0)
        self.assertLess(W.mul(root, root), W.from_int(2) + 1)

    def test_ring_laws(self):
        a, b, c = W.from_str("1.5"), W.from_str("-2.25"), W.from_str("0.125")
        self.assertEqual(W.mul(a, b), W.mul(b, a))
        self.assertEqual(a + (b + c), (a + b) + c)
        # these three are exactly representable, so distributivity is exact
        self.assertEqual(W.mul(a, b + c), W.mul(a, b) + W.mul(a, c))

    def test_div_inverse_within_one_ulp(self):
        a, b = W.from_str("1.0"), W.from_str("3.0")
        q = W.div(a, b)
        self.assertLessEqual(abs(W.mul(q, b) - a), 1)

    def test_no_float_leaks(self):
        vals = [W.from_int(3), W.div(W.from_int(1), W.from_int(7)),
                W.sqrt(W.from_int(5)), W.mean([W.from_int(1), W.from_int(2)]),
                W.variance([W.from_int(1), W.from_int(3)])]
        for v in vals:
            self.assertIsInstance(v, int)
            self.assertNotIsInstance(v, float)
        W.assert_wad(*vals)
        with self.assertRaises(TypeError):
            W.assert_wad(1.0)


if __name__ == "__main__":
    unittest.main()


class TestWad18Signs(unittest.TestCase):
    """Written against surviving mutants in the arithmetic core."""

    def test_multiplication_carries_the_sign(self):
        self.assertEqual(W.to_str(W.mul(W.from_str("2"), W.from_str("-3"))),
                         "-6.000000000000000000")
        self.assertEqual(W.to_str(W.mul(W.from_str("-2"), W.from_str("-3"))),
                         "6.000000000000000000")

    def test_division_carries_the_sign(self):
        self.assertEqual(W.to_str(W.div(W.from_str("6"), W.from_str("-3"))),
                         "-2.000000000000000000")

    def test_zero_renders_without_a_minus(self):
        self.assertEqual(W.to_str(W.ZERO), "0.000000000000000000")
        self.assertEqual(W.to_str(W.mul(W.ZERO, W.from_str("-5"))),
                         "0.000000000000000000")

    def test_sqrt_residual_is_a_subtraction(self):
        a = W.from_int(2)
        root, residual = W.sqrt_exact(a)
        self.assertEqual(residual, a - W.mul(root, root))
        self.assertGreater(residual, 0)

    def test_variance_centres_by_subtracting_the_mean(self):
        v = W.variance([W.from_int(1), W.from_int(3)])
        self.assertEqual(W.to_str(v), "1.000000000000000000")

    def test_empty_string_parses_as_zero(self):
        self.assertEqual(W.from_str(""), W.ZERO)
        self.assertEqual(W.from_str("  "), W.ZERO)

    def test_non_numeric_is_rejected(self):
        for bad in ("abc", "1.2.3", "1,5"):
            with self.assertRaises(ValueError):
                W.from_str(bad)


class TestWad18Edges2(unittest.TestCase):

    def test_sqrt_of_zero_is_zero(self):
        """Kills wad18 'a < 0' -> '<=' in sqrt: zero is a legal argument."""
        self.assertEqual(W.sqrt(W.ZERO), W.ZERO)
        root, residual = W.sqrt_exact(W.ZERO)
        self.assertEqual((root, residual), (W.ZERO, W.ZERO))

    def test_assert_wad_returns_true(self):
        """Kills wad18 'return True' -> False in assert_wad."""
        self.assertIs(W.assert_wad(W.ONE, W.ZERO), True)
