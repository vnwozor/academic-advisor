"""Tests for the advisor engine and the Flask web app.

Run:  python -m unittest -v
"""
import unittest

from advisor import Advisor, degree_class
from app import app

GOOD = {"prev_cgpa": 4.6, "attendance": 95, "study_hours": 22, "assignments_done": 100,
        "ca_score": 27, "course_units": 18, "sleep_hours": 7.5}
STRUGGLING = {"prev_cgpa": 1.6, "attendance": 40, "study_hours": 2, "assignments_done": 40,
              "ca_score": 9, "course_units": 26, "sleep_hours": 4.5}
AVERAGE = {"prev_cgpa": 3.2, "attendance": 70, "study_hours": 8, "assignments_done": 75,
           "ca_score": 18, "course_units": 24, "sleep_hours": 5.5}


class DegreeClassTests(unittest.TestCase):
    def test_band_edges(self):
        self.assertEqual(degree_class(4.50), "First Class")
        self.assertEqual(degree_class(4.49), "Second Class Upper")
        self.assertEqual(degree_class(3.50), "Second Class Upper")
        self.assertEqual(degree_class(2.40), "Second Class Lower")
        self.assertEqual(degree_class(1.50), "Third Class")
        self.assertEqual(degree_class(0.50), "Fail")


class AdvisorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.advisor = Advisor()

    def test_model_file_loads_with_expected_features(self):
        self.assertEqual(len(self.advisor.features), 7)

    def test_strong_student_is_on_track(self):
        r = self.advisor.advise(GOOD)
        self.assertEqual(r["standing"], "On track")
        self.assertGreaterEqual(r["projected_cgpa"], 3.5)

    def test_struggling_student_is_at_risk(self):
        r = self.advisor.advise(STRUGGLING)
        self.assertEqual(r["standing"], "At risk")
        self.assertLess(r["projected_cgpa"], 2.4)

    def test_better_habits_never_lower_the_projection(self):
        self.assertGreater(self.advisor.advise(GOOD)["projected_cgpa"],
                           self.advisor.advise(STRUGGLING)["projected_cgpa"])

    def test_tips_are_ranked_and_capped_at_three(self):
        tips = self.advisor.advise(AVERAGE)["tips"]
        self.assertTrue(1 <= len(tips) <= 3)
        gains = [t["gain"] for t in tips]
        self.assertEqual(gains, sorted(gains, reverse=True))

    def test_potential_is_at_least_projected(self):
        r = self.advisor.advise(AVERAGE)
        self.assertGreaterEqual(r["potential_cgpa"], r["projected_cgpa"])

    def test_rejects_out_of_range_input(self):
        with self.assertRaises(ValueError):
            self.advisor.advise({**AVERAGE, "prev_cgpa": 6})

    def test_rejects_missing_input(self):
        bad = dict(AVERAGE)
        del bad["ca_score"]
        with self.assertRaises(ValueError):
            self.advisor.advise(bad)


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_home_page_renders(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Semester", res.data)

    def test_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.get_json()["status"], "ok")

    def test_advise_returns_projection(self):
        res = self.client.post("/api/advise", json=AVERAGE)
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        for key in ("projected_cgpa", "degree_class", "standing", "tips", "potential_cgpa"):
            self.assertIn(key, body)

    def test_advise_accepts_form_posts(self):
        res = self.client.post("/api/advise", data={k: str(v) for k, v in AVERAGE.items()})
        self.assertEqual(res.status_code, 200)

    def test_bad_input_returns_400_with_reason(self):
        res = self.client.post("/api/advise", json={**AVERAGE, "attendance": "lots"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("attendance", res.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
