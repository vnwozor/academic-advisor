"""Advisor engine: loads the trained .pkl and turns a student's habits into advice.

Two AI techniques work together here:
  * Machine learning  - the Random Forest models from the Colab notebook project
                        next-semester CGPA and academic standing.
  * What-if reasoning - each habit the student controls is nudged to a realistic
                        target and re-scored by the model; the habits that move the
                        projected CGPA most become the advice.
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = Path(__file__).parent / "model" / "advisor_model.pkl"

# Allowed range for every input: (min, max)
LIMITS = {
    "prev_cgpa": (0.0, 5.0),
    "attendance": (0, 100),
    "study_hours": (0, 40),
    "assignments_done": (0, 100),
    "ca_score": (0, 30),
    "course_units": (12, 30),
    "sleep_hours": (3, 10),
}

# Nigerian 5-point scale, highest band first
CLASSES = [
    (4.50, "First Class"),
    (3.50, "Second Class Upper"),
    (2.40, "Second Class Lower"),
    (1.50, "Third Class"),
    (1.00, "Pass"),
    (0.00, "Fail"),
]


def degree_class(cgpa: float) -> str:
    for floor, name in CLASSES:
        if cgpa >= floor:
            return name
    return "Fail"


# Each lever: how to improve the habit, and how to say it to the student.
def _levers(s):
    return [
        ("attendance", min(100, s["attendance"] + 15),
         "Attend more lectures",
         lambda v: f"Push attendance from {s['attendance']:.0f}% to {v:.0f}%. Missed lectures are where CA questions come from."),
        ("study_hours", min(25, s["study_hours"] + 6),
         "Study a little more each week",
         lambda v: f"Go from {s['study_hours']:g} to {v:g} hours a week. That's under an hour extra per day."),
        ("assignments_done", 100,
         "Submit every assignment",
         lambda v: f"You're submitting {s['assignments_done']:.0f}% of assignments. Each one you skip is free marks left behind."),
        ("ca_score", min(30, s["ca_score"] + 5),
         "Raise your CA score",
         lambda v: f"Aim for {v:.0f}/30 in continuous assessment, up from {s['ca_score']:.0f}. Prepare for tests the way you prepare for exams."),
        ("sleep_hours", 7.5,
         "Sleep closer to 7½ hours",
         lambda v: f"You're on {s['sleep_hours']:g} hours a night. Tired reading doesn't stick."),
        ("course_units", max(15, s["course_units"] - 3),
         "Carry a lighter load",
         lambda v: f"Dropping from {s['course_units']:.0f} to {v:.0f} units lets you give each course proper attention."),
    ]


class Advisor:
    def __init__(self, path=MODEL_PATH):
        bundle = joblib.load(path)
        self.regressor = bundle["regressor"]
        self.classifier = bundle["classifier"]
        self.features = bundle["features"]
        self.metrics = bundle.get("metrics", {})
        self.cohort = bundle.get("cohort", {})

    @staticmethod
    def validate(data: dict) -> dict:
        """Return a clean dict of floats, or raise ValueError naming the bad field."""
        clean = {}
        for name, (lo, hi) in LIMITS.items():
            if name not in data or data[name] in ("", None):
                raise ValueError(f"'{name}' is missing.")
            try:
                value = float(data[name])
            except (TypeError, ValueError):
                raise ValueError(f"'{name}' must be a number.")
            if not lo <= value <= hi:
                raise ValueError(f"'{name}' must be between {lo} and {hi}.")
            clean[name] = value
        return clean

    def _project(self, student: dict) -> float:
        row = pd.DataFrame([student])[self.features]
        return float(min(5.0, max(0.0, self.regressor.predict(row)[0])))

    def advise(self, data: dict) -> dict:
        s = self.validate(data)
        projected = self._project(s)
        standing = str(self.classifier.predict(pd.DataFrame([s])[self.features])[0])

        tips = []
        for field, target, title, explain in _levers(s):
            if target == s[field]:
                continue
            gain = self._project({**s, field: target}) - projected
            if gain >= 0.02:
                tips.append({"field": field, "title": title, "detail": explain(target),
                             "gain": round(gain, 2)})
        tips.sort(key=lambda t: t["gain"], reverse=True)
        tips = tips[:3]

        best = projected
        if tips:
            improved = dict(s)
            for field, target, *_ in _levers(s):
                if any(t["field"] == field for t in tips):
                    improved[field] = target
            best = max(projected, self._project(improved))

        return {
            **self.statistics(s),
            "projected_cgpa": round(projected, 2),
            "degree_class": degree_class(projected),
            "standing": standing,
            "tips": tips,
            "potential_cgpa": round(best, 2),
            "potential_class": degree_class(best),
        }

    def statistics(self, s: dict) -> dict:
        """Numbers behind the projection: likely range, standing probabilities,
        and where each habit sits among the simulated cohort."""
        row = pd.DataFrame([s])[self.features]

        # Each of the forest's trees makes its own guess; their spread is the likely range.
        guesses = np.array([t.predict(row.to_numpy())[0] for t in self.regressor.estimators_])
        low, high = np.clip(np.percentile(guesses, [10, 90]), 0, 5)

        probs = self.classifier.predict_proba(row)[0]
        probability = {str(c): round(float(p), 3) for c, p in zip(self.classifier.classes_, probs)}

        compare = []
        pct_table = self.cohort.get("percentiles", {})
        for f in self.features:
            q = pct_table.get(f)
            if not q:
                continue
            compare.append({
                "field": f,
                "value": s[f],
                "percentile": int(np.clip(np.searchsorted(q, s[f], side="right") - 1, 0, 100)),
                "p25": q[25], "median": q[50], "p75": q[75],
                "min": LIMITS[f][0], "max": LIMITS[f][1],
            })

        importance = sorted(self.cohort.get("importance", {}).items(), key=lambda kv: kv[1], reverse=True)
        return {
            "range": [round(float(low), 2), round(float(high), 2)],
            "probability": probability,
            "compare": compare,
            "importance": [{"field": f, "weight": w} for f, w in importance],
        }


if __name__ == "__main__":
    example = {"prev_cgpa": 3.2, "attendance": 70, "study_hours": 8, "assignments_done": 75,
               "ca_score": 18, "course_units": 24, "sleep_hours": 5.5}
    import json
    print(json.dumps(Advisor().advise(example), indent=2))
