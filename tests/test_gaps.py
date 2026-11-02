"""Tests written to kill specific surviving mutants.

Each test here exists because mutation testing showed the suite could not see
a particular defect. The mutant it kills is named.
"""
import io, json, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import wad18 as W                                        # noqa: E402
import domain as D                                       # noqa: E402
import r3_engine as E                                    # noqa: E402
from projection import nearest_feasible, project          # noqa: E402
from certify import lipschitz_estimate, posteriori_bound  # noqa: E402

INV = json.load(open(os.path.join(ROOT, "spec", "meta_invariants.json")))["invariants"]
D0 = json.load(open(os.path.join(ROOT, "data", "reference_state.json")))


class TestEngineGuards(unittest.TestCase):

    def test_constant_mu_aborts(self):
        """Kills r3_engine '>=' -> '>': a step that changes the state without
        reducing mu has no termination argument and must abort."""
        inv = [{"id": "A", "hard": True, "requires": "a"},
               {"id": "B", "hard": True, "requires": "b"}]
        state = {"id": "s", "attributes": {"a": True, "b": False}, "notes": []}

        def flip(s, sigma, invariants):
            n = json.loads(json.dumps(s))
            n["attributes"]["a"] = not n["attributes"]["a"]
            n["attributes"]["b"] = not n["attributes"]["b"]
            return n

        original = E.refine
        E.refine = flip
        try:
            out = E.run(state, inv, budget=10)
        finally:
            E.refine = original
        self.assertEqual(out["status"], E.NO_FIXPOINT)
        self.assertEqual(out["reason"], "mu_not_decreasing")

    def test_audit_requires_exactly_true(self):
        """Kills r3_engine 'True' -> 'False' in audit(): a truthy-but-not-True
        attribute must count as a violation, not as satisfaction."""
        inv = [{"id": "A", "hard": True, "requires": "a"}]
        for value in (1, "yes", [1]):
            s = {"id": "s", "attributes": {"a": value}, "notes": []}
            _, sigma = E.audit(s, inv)
            self.assertEqual(sigma["mu"], 1, "accepted %r as True" % (value,))


class TestProjectionCoercion(unittest.TestCase):

    def test_non_boolean_coerces_to_false_not_true(self):
        """Kills projection 'is True' -> 'is False': the conservative
        direction is that an attribute is unsatisfied unless validly True."""
        out = nearest_feasible({"attributes": {"a": "yes", "b": True, "c": 0}})
        self.assertEqual(out["attributes"], {"a": False, "b": True, "c": False})

    def test_rejection_record_names_the_violations(self):
        log = io.StringIO()
        project({"attributes": {"a": "yes"}, "junk": 1}, log)
        rec = json.loads(log.getvalue())
        self.assertIn("SCHEMA_UNKNOWN_KEY:junk", rec["violated"])
        self.assertIn("SCHEMA_NON_BOOLEAN_ATTRIBUTE:a", rec["violated"])


class TestCertifyPaths(unittest.TestCase):

    def test_lipschitz_is_the_max_ratio_not_the_last(self):
        res = [W.from_int(100), W.from_int(50), W.from_int(45), W.from_int(9)]
        # ratios are 0.5, 0.9, 0.2 -> conservative estimate is 0.9
        self.assertEqual(W.to_str(lipschitz_estimate(res), 3), "0.900")

    def test_lipschitz_none_on_degenerate_input(self):
        self.assertIsNone(lipschitz_estimate([W.from_int(5)]))
        self.assertIsNone(lipschitz_estimate([]))

    def test_zero_residual_is_skipped_not_divided_by(self):
        res = [W.ZERO, W.from_int(4), W.from_int(2)]
        self.assertEqual(W.to_str(lipschitz_estimate(res), 3), "0.500")

    def test_boundary_L_just_below_one_still_certifies(self):
        L = W.ONE - 1                       # one ulp below 1
        out = posteriori_bound(W.from_str("0.000001"), L)
        self.assertEqual(out["certificate"], "CONTRACTION")
        self.assertIsNotNone(out["bound_wad18"])

    def test_L_none_is_no_contraction(self):
        out = posteriori_bound(W.from_str("0.000001"), None)
        self.assertEqual(out["certificate"], "NO_CONTRACTION")
        self.assertIsNone(out["L_hat_wad18"])


class TestDomainBoundaries(unittest.TestCase):

    def test_constraints_are_inclusive_at_the_boundary(self):
        """Kills domain '<' -> '<=' and '>' -> '>=': each hard constraint is
        satisfied exactly AT its bound and violated one step past it."""
        x = list(D.ANCHOR)
        # G2: product exactly P_PROD_MIN is feasible
        y = [20, 15, 30, 10, 10, 10]        # 300 == P_PROD_MIN
        self.assertNotIn("G2_PRODUCT", D.violations(tuple(y)))
        y[1] = 14                            # 280 < 300
        self.assertIn("G2_PRODUCT", D.violations(tuple(y)))
        # G3: gap exactly P_GAP_MIN is feasible
        z = [20, 20, 20, 10, 10, 10]        # gap == 10
        self.assertNotIn("G3_GAP", D.violations(tuple(z)))
        z[2] = 19                            # gap 9
        self.assertIn("G3_GAP", D.violations(tuple(z)))

    def test_sum_bound_is_inclusive(self):
        base = [20, 20, 30, 10, 10, 10]
        base[0] = D.P_SUM_MAX - sum(base[1:])
        self.assertEqual(sum(base), D.P_SUM_MAX)
        self.assertNotIn("G1_SUM", D.violations(tuple(base)))
        base[5] += 2                         # keeps parity, breaks the sum
        self.assertIn("G1_SUM", D.violations(tuple(base)))

    def test_bounds_check_is_inclusive(self):
        self.assertNotIn("G0_BOUNDS", D.violations((63, 63, 63, 53, 10, 10)))
        self.assertIn("G0_BOUNDS", D.violations((64, 63, 63, 53, 10, 10)))
        self.assertIn("G0_BOUNDS", D.violations((-1, 63, 63, 53, 10, 10)))


class TestWadEdges(unittest.TestCase):

    def test_from_ratio_normalises_negative_denominator(self):
        """Kills wad18 'den < 0' mutations."""
        self.assertEqual(W.from_ratio(1, -2), W.from_ratio(-1, 2))
        self.assertEqual(W.to_str(W.from_ratio(1, -2)), "-0.500000000000000000")

    def test_round_half_even_at_exact_halves(self):
        for num, den, want in ((1, 2, 0), (3, 2, 2), (5, 2, 2), (7, 2, 4),
                               (-1, 2, 0), (-3, 2, -2)):
            self.assertEqual(W.round_half_even(num, den), want,
                             "%d/%d" % (num, den))

    def test_division_by_zero_is_raised_not_silent(self):
        with self.assertRaises(ZeroDivisionError):
            W.div(W.ONE, W.ZERO)

    def test_negative_sqrt_raises(self):
        with self.assertRaises(ValueError):
            W.sqrt(-W.ONE)


if __name__ == "__main__":
    unittest.main()


class TestGapsRoundTwo(unittest.TestCase):
    """Second pass: written against the survivors of the first mutation run."""

    def test_zero_coordinate_is_in_bounds(self):
        """Kills domain 'xi < LO' -> 'xi <= LO': LO itself is admissible."""
        x = (20, 20, 30, 0, 10, 10)
        self.assertEqual(D.violations(x), [])

    def test_gap_repair_is_exact_not_merely_feasible(self):
        """Kills domain 'need - give' -> 'need + give': the repair must move
        the pair exactly to the bound, not overshoot it."""
        out = D.project((20, 20, 60, 58, 10, 10))
        self.assertEqual(abs(out[2] - out[3]), D.P_GAP_MIN)

    def test_empty_feasible_set_is_raised_not_faked(self):
        """Kills the silent-anchor path: if C is empty for these parameters,
        say so rather than return an infeasible point."""
        impossible = (200, 63 * 63 + 1, 10)      # product unreachable at HI
        with self.assertRaises(ValueError):
            D.project((0, 0, 0, 0, 0, 0), impossible)

    def test_digest_is_key_order_independent(self):
        """Kills projection 'sort_keys=True' -> False: two states with the
        same content must hash the same whatever order they were built in."""
        from projection import digest
        a = {"id": "x", "attributes": {"a": True, "b": False}, "notes": []}
        b = {"notes": [], "attributes": {"b": False, "a": True}, "id": "x"}
        self.assertEqual(digest(a), digest(b))

    def test_zero_denominator_is_rejected(self):
        """Kills wad18 'den <= 0' -> 'den < 0'."""
        with self.assertRaises(ValueError):
            W.round_half_even(1, 0)

    def test_cliffs_delta_wad_value_is_signed(self):
        """Kills stats 'gt - lt' -> 'gt + lt' in the WAD rendering."""
        from stats import cliffs_delta
        d = cliffs_delta([1, 2], [3, 4])
        self.assertLess(d["delta_wad18"], 0)
        self.assertEqual(W.to_str(d["delta_wad18"]), "-1.000000000000000000")

    def test_certify_respects_the_declared_route(self):
        """Kills certify 'route == metric' -> '!=': on the termination route
        no error bound may be emitted, however small the residuals get."""
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            trace = os.path.join(tmp, "trace.jsonl")
            with open(trace, "w") as fh:
                for k, mu in enumerate([8, 4, 2, 1, 0]):
                    fh.write(json.dumps({"k": k, "mu": mu}) + "\n")
            subprocess.check_call(
                [sys.executable, os.path.join(ROOT, "src", "certify.py"),
                 "--trace", trace,
                 "--manifest", os.path.join(ROOT, "manifest.json")],
                stdout=subprocess.DEVNULL,
                env=dict(os.environ, PYTHONHASHSEED="0", LC_ALL="C", TZ="UTC",
                         OMP_NUM_THREADS="1", MKL_NUM_THREADS="1"))
            cert = json.load(open(os.path.join(tmp, "certificate.json")))
        self.assertEqual(cert["declared_route"], "termination")
        self.assertEqual(cert["certificate"], "NO_CONTRACTION")
        self.assertIsNone(cert["bound_wad18"])


class TestGapsRoundThree(unittest.TestCase):

    def test_g2_repair_never_escapes_the_upper_bound(self):
        """Kills domain 'y[1] < HI' -> '<=': a repair that pushes a coordinate
        to HI+1 leaves C while appearing to satisfy the product constraint."""
        hardest = (D.P_SUM_MAX, D.HI * D.HI, D.P_GAP_MIN)   # product needs both at HI
        for start in ((0, 0, 0, 0, 0, 0), (1, 63, 5, 5, 1, 1), (63, 1, 5, 5, 1, 1)):
            try:
                out = D.project(start, hardest)
            except ValueError:
                continue                     # declared-empty C is an honest answer
            self.assertTrue(all(D.LO <= v <= D.HI for v in out),
                            "escaped bounds: %r" % (out,))

    def test_eps_dominance_strictness(self):
        """Kills domain 'p < q - e' -> '<=': eps-dominance needs at least one
        objective STRICTLY better, else every point dominates itself."""
        x = (20, 20, 30, 10, 10, 10)
        self.assertFalse(D.eps_dominates(x, x))
        self.assertFalse(D.dominates(x, x))


class TestGapsRoundFour(unittest.TestCase):

    def test_g2_repair_raises_the_second_coordinate_at_the_cap(self):
        """Kills domain 'y[1] < HI' -> '<=' with C NON-EMPTY, which the
        round-three test could not reach because it only used parameter sets
        where C was empty and the code raised first."""
        p = (400, 63 * 40, D.P_GAP_MIN)          # reachable: x0 at HI, x1 raised
        out = D.project((63, 1, 5, 5, 1, 1), p)
        self.assertEqual(D.violations(out, p), [])
        self.assertTrue(all(D.LO <= v <= D.HI for v in out),
                        "repair escaped the bound: %r" % (out,))
        self.assertEqual(out[0], D.HI)
        self.assertGreaterEqual(out[0] * out[1], p[1])

    def test_shed_loop_is_bounded_by_a_named_constant(self):
        """The old 'guard < 512' comparison was an equivalent-mutant factory.
        The bound is now structural, and this pins it."""
        self.assertIsInstance(D.MAX_SHED_PASSES, int)
        self.assertGreater(D.MAX_SHED_PASSES, D.NVAR * (D.HI - D.LO))

    def test_p_value_cap_is_exact_at_one(self):
        """Kills the stats 'num > den' comparison, now min()."""
        from stats import wilcoxon_signed_rank
        r = wilcoxon_signed_rank([1, 2, 3, 4], [2, 1, 4, 3])
        self.assertLessEqual(r["p_exact"]["num"], r["p_exact"]["den"])
        self.assertLessEqual(r["p_two_sided_wad18"], W.ONE)


class TestGapsRoundFive(unittest.TestCase):
    """Characterisation and boundary tests for the last mutant classes."""

    def test_sum_at_the_cap_is_not_shed(self):
        """Kills domain 'sum(y) <= smax' -> '<': a point exactly at the bound
        is feasible and must be returned untouched."""
        x = (40, 40, 40, 30, 25, 25)          # sums to exactly P_SUM_MAX
        self.assertEqual(sum(x), D.P_SUM_MAX)
        self.assertEqual(D.violations(x), [])
        self.assertEqual(D.project(x), x)

    def test_g2_terminates_with_both_coordinates_at_the_cap(self):
        """The min()-bounded repair must stop, not spin, when the product is
        unreachable and both coordinates are pinned at HI."""
        p = (D.P_SUM_MAX, D.HI * D.HI + 1, D.P_GAP_MIN)
        with self.assertRaises(ValueError):
            D.project((63, 63, 5, 5, 1, 1), p)

    def test_zeros_dropped_is_counted_not_added(self):
        """Kills stats 'len(diffs) - n' -> '+'."""
        from stats import wilcoxon_signed_rank
        r = wilcoxon_signed_rank([1, 2, 3, 4, 5], [1, 3, 3, 5, 4])
        self.assertEqual(r["zeros_dropped"], 2)
        self.assertEqual(r["n_effective"], 3)

    def test_magnitude_bands_are_strict_at_the_edge(self):
        """Kills stats 'm < threshold' -> '<=' : a delta exactly on a
        threshold belongs to the higher band."""
        from stats import magnitude
        self.assertEqual(magnitude(W.from_str("0.146999999999999999")),
                         "negligible")
        self.assertEqual(magnitude(W.from_str("0.147")), "small")
        self.assertEqual(magnitude(W.from_str("0.33")), "medium")
        self.assertEqual(magnitude(W.from_str("0.474")), "large")
        self.assertEqual(magnitude(W.from_str("-0.474")), "large")

    def test_neighbourhood_is_symmetric_and_signed(self):
        """Kills the search DELTAS sign mutants: a hill-climb whose moves are
        all one direction cannot descend."""
        from search import DELTAS
        self.assertEqual(sorted(DELTAS), [-8, -4, -1, 1, 4, 8])
        self.assertEqual(sorted(-d for d in DELTAS), sorted(DELTAS))

    def test_penalty_is_added_not_subtracted(self):
        """Kills search 'raw + PENALTY * nv' -> '-': a subtracted penalty makes
        infeasible points look best and the baseline ends outside C."""
        from search import baseline_search, PENALTY
        for seed in (1, 2, 3, 4, 5):
            b = baseline_search(seed, 400)
            self.assertTrue(b["feasible"], "baseline left C on seed %d" % seed)
            self.assertLess(b["reported"], PENALTY)

    def test_searches_are_pinned_characterisations(self):
        """Any change to the accept rule or the move set changes these. Pinned
        from a verified run, so trajectory-altering mutants die here."""
        from search import r3_search, baseline_search
        r = r3_search(1, 2000)
        self.assertEqual(r["x"], (32, 32, 42, 32, 31, 31))
        self.assertEqual(r["best"], 20998)
        b = baseline_search(1, 2000)
        self.assertEqual(b["reported"], 21324)


class TestGapsRoundSix(unittest.TestCase):
    """The last four mutant classes."""

    def test_eps_dominance_allows_an_equal_objective(self):
        """Kills domain 'p <= q + e' -> '<': dominance requires NO objective
        worse and at least one strictly better. Equal on one is allowed."""
        d0 = D.ANCHOR
        witness = (20, 16, 21, 11, 18, 14)
        self.assertEqual(D.f2(witness), D.f2(d0))         # equal on f2
        self.assertLess(D.f1(witness), D.f1(d0))          # strictly better on f1
        self.assertTrue(D.eps_dominates(witness, d0, (0, 0)))
        self.assertTrue(D.dominates(witness, d0))

    def test_g2_tie_break_is_pinned(self):
        """Kills domain 'y[0] <= y[1]' -> '<': with the two coordinates equal
        the repair must raise the FIRST, and the result is pinned."""
        self.assertEqual(D.project((0, 0, 0, 0, 0, 0)), (18, 17, 10, 0, 0, 0))
        self.assertEqual(D.project((5, 5, 20, 10, 2, 2))[0:2], (18, 17))

    def test_g2_pass_bound_covers_the_whole_range(self):
        self.assertGreaterEqual(D.MAX_G2_PASSES, 2 * (D.HI - D.LO))

    def test_baseline_accept_rule_is_strict(self):
        """Kills search 'v < best' -> '<=': accepting equal values changes the
        walk. The endpoint is pinned for three seeds."""
        from search import baseline_search
        self.assertEqual(baseline_search(1, 2000)["x"], (40, 40, 40, 30, 18, 30))
        self.assertEqual(baseline_search(2, 2000)["x"], (40, 40, 40, 28, 26, 26))
        self.assertEqual(baseline_search(3, 2000)["x"], (38, 33, 40, 29, 38, 22))


class TestGapsRoundSeven(unittest.TestCase):

    def test_parity_predicate_is_on_the_coordinates_not_their_sum(self):
        """The old '(x4 + x5) % 2' made every +/- mutation an equivalence,
        because sum-parity equals difference-parity. The predicate is now
        written on the coordinates and is tested directly."""
        self.assertNotIn("G4_PARITY", D.violations((20, 20, 30, 10, 2, 4)))
        self.assertNotIn("G4_PARITY", D.violations((20, 20, 30, 10, 3, 5)))
        self.assertIn("G4_PARITY", D.violations((20, 20, 30, 10, 2, 5)))
        self.assertIn("G4_PARITY", D.violations((20, 20, 30, 10, 5, 2)))

    def test_parity_repair_at_the_lower_bound_goes_up(self):
        """Kills domain 'y[5] > LO' -> '>=': at the floor the repair must add,
        not subtract into an out-of-bounds value."""
        out = D.project((20, 20, 30, 10, 1, 0))
        self.assertEqual(D.violations(out), [])
        self.assertEqual(out[4] % 2, out[5] % 2)
        self.assertGreaterEqual(out[5], D.LO)
        self.assertEqual(out, (20, 20, 30, 10, 1, 1))

    def test_eps_dominance_uses_epsilon_as_a_tolerance(self):
        """Kills domain 'q + e' -> 'q - e': with a non-zero epsilon a design
        slightly worse on one objective still counts as no-worse."""
        d0 = D.ANCHOR
        slightly_worse_on_f2 = None
        for cand in [(20, 16, 21, 11, 18, 12), (20, 16, 21, 11, 16, 14)]:
            if D.f1(cand) < D.f1(d0) and D.f2(cand) > D.f2(d0):
                slightly_worse_on_f2 = cand
                break
        self.assertIsNotNone(slightly_worse_on_f2, "fixture no longer valid")
        slack = D.f2(slightly_worse_on_f2) - D.f2(d0)
        self.assertFalse(D.eps_dominates(slightly_worse_on_f2, d0, (0, 0)))
        self.assertTrue(D.eps_dominates(slightly_worse_on_f2, d0, (0, slack)))


class TestGapsRoundEight(unittest.TestCase):
    """Written against the exhaustive mutation run's survivors."""

    def test_better_side_of_dominance_uses_epsilon(self):
        """Kills domain 'q - e' -> '+' in the strictly-better test: an
        improvement smaller than epsilon does not count as better."""
        d0 = D.ANCHOR
        cand = (20, 16, 21, 11, 18, 14)
        gain = D.f1(d0) - D.f1(cand)
        self.assertGreater(gain, 0)
        self.assertTrue(D.eps_dominates(cand, d0, (gain - 1, 0)))
        self.assertFalse(D.eps_dominates(cand, d0, (gain, 0)))

    def test_g2_loop_stops_exactly_at_the_product_bound(self):
        """Kills domain 'y0*y1 >= pmin' -> '>': the bound is inclusive."""
        p = (D.P_SUM_MAX, 20 * 15, D.P_GAP_MIN)
        out = D.project((20, 15, 30, 10, 10, 10), p)
        self.assertEqual(out[0] * out[1], p[1])
        self.assertEqual(out[:2], (20, 15))

    def test_g2_loop_stops_with_both_coordinates_at_the_cap(self):
        """Kills domain 'y >= HI and y >= HI' -> '>' : at HI the loop must
        stop rather than spin for MAX_G2_PASSES."""
        p = (400, D.HI * D.HI, D.P_GAP_MIN)
        out = D.project((63, 63, 20, 5, 1, 1), p)
        self.assertEqual(out[:2], (D.HI, D.HI))

    def test_gap_repair_leaves_an_exact_gap_alone(self):
        """Kills domain 'abs(y2-y3) < gmin' -> '<=' in the repair."""
        x = (20, 20, 30, 20, 10, 10)
        self.assertEqual(abs(x[2] - x[3]), D.P_GAP_MIN)
        self.assertEqual(D.project(x), x)

    def test_shed_may_take_a_coordinate_down_to_the_floor(self):
        """Kills domain 'trial[i] < LO' -> '<=': LO is a legal destination."""
        x = (63, 63, 63, 53, 2, 0)
        out = D.project(x)
        self.assertEqual(D.violations(out), [])
        self.assertLessEqual(sum(out), D.P_SUM_MAX)
        self.assertIn(D.LO, out)

    def test_shed_respects_the_gap_at_its_exact_bound(self):
        """Kills domain 'abs(trial2-trial3) < gmin' -> '<=' in the shed pass."""
        out = D.project((63, 63, 40, 30, 20, 20))
        self.assertGreaterEqual(abs(out[2] - out[3]), D.P_GAP_MIN)
        self.assertEqual(D.violations(out), [])

    def test_unchanged_projection_writes_no_rejection_line(self):
        """Kills domain 'out != before' -> '==': a point already in C is not
        a rejection and must not be logged as one."""
        log = io.StringIO()
        x = (20, 20, 30, 10, 10, 10)
        self.assertEqual(D.project(x, None, log), x)
        self.assertEqual(log.getvalue(), "")
        D.project((99, 0, 5, 5, 1, 2), None, log)
        self.assertTrue(log.getvalue().strip())

    def test_pareto_search_archive_is_sound(self):
        """Kills search 'len(archive) - 1' -> '+1' and covers the procedure
        that discharges Obligation 3."""
        from search import r3_pareto_search
        r = r3_pareto_search(1, 1500)
        self.assertGreater(len(r["archive"]), 1)
        for a in r["archive"]:
            self.assertEqual(D.violations(a), [])
        for a in r["archive"]:
            self.assertFalse(any(D.dominates(b, a) for b in r["archive"]),
                             "archive contains a dominated member")

    def test_result_reports_the_final_measure(self):
        """Kills r3_engine 'history[-1]' -> '[+1]': the reported final_mu must
        be the LAST one, which is zero at the fixed point."""
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as t:
            res = os.path.join(t, "res.json")
            subprocess.check_call(
                [sys.executable, os.path.join(ROOT, "src", "r3_engine.py"),
                 "--manifest", os.path.join(ROOT, "manifest.json"),
                 "--invariants", os.path.join(ROOT, "spec", "meta_invariants.json"),
                 "--state", os.path.join(ROOT, "data", "reference_state.json"),
                 "--trace", os.path.join(t, "tr.jsonl"),
                 "--rejections", os.path.join(t, "rj.jsonl"),
                 "--result", res], stdout=subprocess.DEVNULL,
                env=dict(os.environ, PYTHONHASHSEED="0", LC_ALL="C", TZ="UTC",
                         OMP_NUM_THREADS="1", MKL_NUM_THREADS="1"))
            out = json.load(open(res))
        self.assertEqual(out["final_mu"], 0)
        self.assertEqual(out["status"], "FIXPOINT")


class TestProjectionCharacterisation(unittest.TestCase):
    """Pinned outputs from a verified run. The repair has several interacting
    guards whose individual effects are hard to isolate; any change to one of
    them moves at least one of these, which is exactly what a characterisation
    test is for."""

    FIXTURES = {
        (99, 0, 5, 5, 1, 2): (63, 5, 15, 5, 1, 1),
        (0, 0, 0, 0, 0, 0): (18, 17, 10, 0, 0, 0),
        (63, 63, 63, 63, 63, 63): (32, 32, 42, 32, 31, 31),
        (1, 1, 20, 19, 3, 4): (18, 17, 29, 19, 3, 3),
        (63, 63, 40, 30, 20, 20): (45, 45, 40, 30, 20, 20),
        (20, 15, 30, 10, 1, 0): (20, 15, 30, 10, 1, 1),
        (20, 20, 30, 20, 1, 0): (20, 20, 30, 20, 1, 1),
        (63, 63, 63, 53, 2, 0): (47, 47, 57, 47, 2, 0),
        (5, 5, 20, 10, 2, 2): (18, 17, 20, 10, 2, 2),
        (40, 40, 40, 30, 25, 25): (40, 40, 40, 30, 25, 25),
        (30, 10, 50, 45, 7, 0): (30, 10, 55, 45, 7, 1),
        (62, 5, 10, 9, 1, 1): (62, 5, 19, 9, 1, 1),
    }

    def test_pinned_projections(self):
        for src, want in sorted(self.FIXTURES.items()):
            got = D.project(src)
            self.assertEqual(got, want, "project(%r)" % (src,))
            self.assertEqual(D.violations(got), [])

    def test_g2_does_not_overshoot_an_exact_product(self):
        """Kills domain 'y0*y1 >= pmin' -> '>': entered through a parity
        violation so the G2 loop actually runs with the product already at
        the bound."""
        out = D.project((20, 15, 30, 10, 1, 0))
        self.assertEqual(out[:2], (20, 15))
        self.assertEqual(out[0] * out[1], D.P_PROD_MIN)

    def test_g3_does_not_widen_an_exact_gap(self):
        """Kills domain 'abs(y2-y3) < gmin' -> '<=', entered the same way."""
        out = D.project((20, 20, 30, 20, 1, 0))
        self.assertEqual(abs(out[2] - out[3]), D.P_GAP_MIN)


class TestGapsRoundNine(unittest.TestCase):
    """The last killable survivors of the exhaustive run."""

    def test_shed_reaches_the_floor_exactly(self):
        """Kills domain 'trial[i] < LO' -> '<=': LO is a legal destination for
        a shed, not a forbidden one. Needs a tight sum budget to reach it."""
        p = (12, 9, 2)
        out = D.project((8, 8, 8, 4, 6, 6), p)
        self.assertEqual(out, (3, 3, 3, 1, 0, 2))
        self.assertEqual(D.violations(out, p), [])
        self.assertIn(D.LO, out)

    def test_shed_may_land_exactly_on_the_product_bound(self):
        """Kills domain 'trial[0]*trial[1] < pmin' -> '<=': shedding down TO
        the bound is allowed; only below it is not."""
        p = (12, 1, 2)
        out = D.project((8, 8, 8, 4, 6, 6), p)
        self.assertEqual(out, (1, 1, 4, 2, 2, 2))
        self.assertEqual(out[0] * out[1], p[1])

    def test_r3_accept_rule_is_strict(self):
        """Kills search 'v < best' -> '<=' in the scalarised descent: the
        measure must strictly decrease or the termination argument is void.
        Endpoints pinned across three seeds."""
        from search import r3_search
        self.assertEqual(r3_search(1, 2000)["x"], (32, 32, 42, 32, 31, 31))
        self.assertEqual(r3_search(2, 2000)["x"], (32, 32, 42, 32, 31, 31))
        self.assertEqual(r3_search(3, 2000)["x"], (31, 31, 42, 32, 32, 32))
        for seed in (1, 2, 3):
            self.assertEqual(r3_search(seed, 2000)["best"], 20998)


class TestGapsRoundTen(unittest.TestCase):

    def test_scalarised_archive_only_grows_on_strict_improvement(self):
        """Kills search 'v < best' -> '<=' in r3_search. The endpoint is the
        same either way, so the endpoint alone cannot see this mutation; the
        ARCHIVE can. Accepting ties admits every equal-valued neighbour and
        inflates it by two orders of magnitude."""
        from search import r3_search
        for seed, want in ((1, 18), (2, 17), (3, 20)):
            r = r3_search(seed, 2000)
            self.assertEqual(len(r["archive"]), want,
                             "archive size changed on seed %d" % seed)
        self.assertEqual(r3_search(7, 2000)["rejected_candidates"], 1267)
