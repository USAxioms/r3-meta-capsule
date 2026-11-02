"""The paper is an artefact of the capsule and is tested like one.

Prose drifts from code silently. This happened: a pass updated the obligation
results and left the previous pass's contradictory paragraph in place, so the
document asserted both that Obligation 3 was discharged and that it was
discharged negatively. These tests pin every number the paper claims to the
log file that produced it, and fail on the stale phrasings that have actually
occurred rather than on hypothetical ones.
"""
import json, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = open(os.path.join(ROOT, "paper", "paper.tex")).read()


def log(name):
    return json.load(open(os.path.join(ROOT, "logs", name)))


class TestPaperNumbers(unittest.TestCase):
    """Every figure asserted in the prose must match the run that produced it."""

    def test_exact_p_value(self):
        p = log("po4_contribution.json")["wilcoxon"]["p_exact"]
        self.assertIn("%d/%d" % (p["num"], p["den"]), TEX)

    def test_seeds_and_budget(self):
        pre = log("po4_contribution.json")["pre_registered"]
        self.assertEqual(pre["seeds"], 30)
        self.assertEqual(pre["budget"], 2000)
        self.assertIn("30\nseeds", TEX.replace(" seeds", "\nseeds"))
        self.assertIn("2000 oracle calls", TEX)

    def test_po3_witness_and_count(self):
        w = log("po4_contribution.json")["PO3_epsilon_dominance"]
        self.assertEqual(w["witness"], [20, 16, 21, 11, 18, 14])
        self.assertTrue(w["strictly_dominates_d0"])
        self.assertIn("$(20,16,21,11,18,14)$", TEX)
        self.assertEqual(w["archive_members_dominating_d0"], 12)
        self.assertIn("twelve such designs", TEX)

    def test_sobol_headline(self):
        po5 = log("po5_robustness.json")
        self.assertEqual(po5["base_samples_N"], 512)
        self.assertIn("N=512", TEX)
        s1 = po5["indices"][0]["S1_wad18"]
        self.assertTrue(s1.startswith("0.990"))
        self.assertIn("S_1 = 0.990", TEX)

    def test_mutation_figures(self):
        m = log("mutation.json")
        self.assertEqual((m["mutants"], m["killed"]), (162, 156))
        self.assertEqual(m["raw_kill_rate_percent"], 96)
        self.assertEqual(m["proven_equivalent_survivors"], 6)
        self.assertEqual(m["unexplained_survivors"], 0)
        self.assertIn("162 mutants, 156 killed", TEX)
        self.assertIn("96 percent", TEX)

    def test_score_and_certificate_both_appear(self):
        sc = log("score.json")
        self.assertEqual(sc["score"], "7/7")
        self.assertIn(r"\frac{7}{7}", TEX)
        self.assertTrue(sc["certificate"]["vacuous_per_proposition_4"])
        self.assertIn("blocked\\_on\\_external\\_attestation", TEX.lower())


class TestPaperHasNoStalePhrasing(unittest.TestCase):
    """Each of these was a real defect in a shipped draft."""

    STALE = ("Not discharged",
             r"discharged \emph{negatively}",
             "34 mutants",
             "8 survivors classified as equivalent",
             "one gap admitted")

    def test_no_superseded_claims(self):
        for phrase in self.STALE:
            self.assertNotIn(phrase, TEX, "stale claim in the paper: %r" % phrase)

    def test_po3_is_not_claimed_both_ways(self):
        self.assertEqual(TEX.count("Obligation~3 is discharged"), 1)

    def test_every_listing_target_exists(self):
        for rel in re.findall(r"\\lstinputlisting\[[^\]]*\]\{\.\./([^}]+)\}", TEX):
            self.assertTrue(os.path.exists(os.path.join(ROOT, rel)),
                            "paper includes a file that is not in the capsule: %s" % rel)

    def test_environments_balance(self):
        from collections import Counter
        b = Counter(re.findall(r"\\begin\{(\w+\*?)\}", TEX))
        e = Counter(re.findall(r"\\end\{(\w+\*?)\}", TEX))
        self.assertEqual(b, e, "unbalanced LaTeX environments")

    def test_braces_balance(self):
        self.assertEqual(TEX.count("{"), TEX.count("}"))


if __name__ == "__main__":
    unittest.main()
