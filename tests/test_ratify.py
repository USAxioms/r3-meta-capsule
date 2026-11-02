import json, os, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import ratify                                        # noqa: E402

INV = os.path.join(ROOT, "spec", "meta_invariants.json")


def _rat(tmp, **over):
    body = {"attestor": "A. Reviewer <a@example.org>",
            "attested_sha3": ratify.file_sha3(INV),
            "attested_utc": "2026-10-31T00:00:00Z",
            "statement": "M1-M8 are a reasonable standard for this artefact.",
            "independent": True}
    body.update(over)
    path = os.path.join(tmp, "ratification.json")
    with open(path, "w") as fh:
        json.dump(body, fh)
    return path


class TestRatify(unittest.TestCase):

    def test_unratified_by_default(self):
        res = ratify.check()
        self.assertFalse(res["ratified"])
        self.assertEqual(res["status"], "BLOCKED_ON_EXTERNAL_ATTESTATION")
        self.assertTrue(res["certificate_is_vacuous_per_proposition_4"])

    def test_valid_attestation_passes(self):
        with tempfile.TemporaryDirectory() as t:
            res = ratify.check(INV, _rat(t))
        self.assertTrue(res["ratified"])
        self.assertEqual(res["status"], "RATIFIED")
        self.assertFalse(res["certificate_is_vacuous_per_proposition_4"])

    def test_edit_after_attestation_revokes_it(self):
        """The whole mechanism: you cannot ratify a set and then change it."""
        with tempfile.TemporaryDirectory() as t:
            rat = _rat(t)
            edited = os.path.join(t, "meta_invariants.json")
            doc = json.load(open(INV))
            doc["invariants"] = doc["invariants"][:-1]     # quietly drop M8
            with open(edited, "w") as fh:
                json.dump(doc, fh)
            res = ratify.check(edited, rat)
        self.assertFalse(res["ratified"])
        self.assertEqual(res["status"], "REVOKED_BY_EDIT")
        self.assertTrue(res["certificate_is_vacuous_per_proposition_4"])

    def test_self_attestation_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            res = ratify.check(INV, _rat(t, independent=False))
        self.assertEqual(res["status"], "NOT_INDEPENDENT")
        self.assertFalse(res["ratified"])
        self.assertTrue(res["certificate_is_vacuous_per_proposition_4"])

    def test_malformed_attestation_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = _rat(t)
            body = json.load(open(p))
            del body["statement"]
            json.dump(body, open(p, "w"))
            res = ratify.check(INV, p)
        self.assertEqual(res["status"], "MALFORMED_ATTESTATION")
        self.assertFalse(res["ratified"])
        self.assertTrue(res["certificate_is_vacuous_per_proposition_4"])


if __name__ == "__main__":
    unittest.main()
