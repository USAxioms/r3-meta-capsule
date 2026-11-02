import json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

MAN = json.load(open(os.path.join(ROOT, "manifest.json")))


class TestScope(unittest.TestCase):

    def test_every_obligation_is_classified_exactly_once(self):
        """No obligation may be silently dropped from both columns."""
        scope = MAN["scope"]
        obs = set(MAN["obligations"])
        scored = set(scope["scored"])
        excluded = set(scope["excluded"])
        self.assertEqual(scored & excluded, set(), "an obligation is in both columns")
        self.assertEqual(scored | excluded, obs,
                         "obligations missing from the scope block: %s"
                         % sorted(obs - (scored | excluded)))

    def test_every_exclusion_states_a_reason(self):
        for name, info in MAN["scope"]["excluded"].items():
            self.assertTrue(info.get("reason"), "%s excluded with no reason" % name)
            self.assertIn(info.get("kind"), ("environment-limited",))
            self.assertFalse(info.get("counts_against_score"))

    def test_scored_obligations_are_all_discharged(self):
        for name in MAN["scope"]["scored"]:
            self.assertIn(MAN["obligations"][name]["status"],
                          ("discharged", "discharged_negative"), name)

    def test_exclusion_is_not_available_to_a_closable_item(self):
        """An obligation may be excluded only if it cannot be attempted HERE.
        Anything closable in this environment must stay in the denominator."""
        for name, info in MAN["scope"]["excluded"].items():
            self.assertFalse(info.get("closable_here", False),
                             "%s is closable here and must be scored" % name)

    def test_m6_is_not_quietly_counted_as_discharged(self):
        """M6 is not an obligation and is not in either column; the capsule
        must still carry it as open, with the certificate marked vacuous."""
        import ratify
        self.assertIn("M6_external_ratification",
                      MAN["scope"]["open_but_not_an_obligation"])
        res = ratify.check()
        self.assertFalse(res["ratified"])
        self.assertTrue(res["certificate_is_vacuous_per_proposition_4"])


class TestScoreReport(unittest.TestCase):

    def test_report_separates_score_from_certificate(self):
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as t:
            out = os.path.join(t, "score.json")
            subprocess.check_call(
                [sys.executable, os.path.join(ROOT, "src", "score.py"),
                 "--out", out], stdout=subprocess.DEVNULL,
                env=dict(os.environ, PYTHONHASHSEED="0", LC_ALL="C", TZ="UTC",
                         OMP_NUM_THREADS="1", MKL_NUM_THREADS="1"))
            rep = json.load(open(out))
        self.assertEqual(rep["score"], "7/7")
        self.assertTrue(rep["perfect_within_scope"])
        self.assertEqual(rep["outstanding"], [])
        self.assertTrue(rep["certificate"]["vacuous_per_proposition_4"])
        self.assertEqual(len(rep["excluded_from_denominator"]), 1)


if __name__ == "__main__":
    unittest.main()
