"""Trains the advisor models and writes model/advisor_model.pkl.

Same code as notebooks/advisor_model.ipynb (which is the version run on Google Colab),
so the model can also be rebuilt locally:  python train_model.py
"""
from pathlib import Path

OUT = Path(__file__).parent / "model" / "advisor_model.pkl"
OUT.parent.mkdir(exist_ok=True)

import numpy as np
import pandas as pd
import sklearn, joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score, classification_report

print("scikit-learn", sklearn.__version__)

rng = np.random.default_rng(303)
N = 3000

df = pd.DataFrame({
    "prev_cgpa":        np.clip(rng.normal(3.1, 0.85, N), 0.5, 5.0).round(2),
    "attendance":       np.clip(rng.normal(78, 15, N), 20, 100).round(0),
    "study_hours":      np.clip(rng.gamma(3.0, 4.0, N), 0, 40).round(1),
    "assignments_done": np.clip(rng.normal(80, 18, N), 0, 100).round(0),
    "ca_score":         np.clip(rng.normal(19, 5, N), 0, 30).round(0),
    "course_units":     rng.integers(15, 27, N),
    "sleep_hours":      np.clip(rng.normal(6.5, 1.3, N), 3, 10).round(1),
})

def true_cgpa(d):
    return (
        0.55 * d.prev_cgpa
        + 0.012 * d.attendance
        + 0.045 * np.minimum(d.study_hours, 25)      # gains flatten after ~25 hrs/week
        + 0.006 * d.assignments_done
        + 0.035 * d.ca_score
        - 0.03 * (d.course_units - 20)
        - 0.09 * np.abs(d.sleep_hours - 7.5)
        - 0.95
    )

df["next_cgpa"] = np.clip(true_cgpa(df) + rng.normal(0, 0.22, N), 0, 5).round(2)

def standing(g):
    if g >= 3.5: return "On track"
    if g >= 2.4: return "Needs attention"
    return "At risk"

df["standing"] = df.next_cgpa.apply(standing)
print(df.head())

print(df.describe().round(2))
print()
print(df.standing.value_counts())

FEATURES = ["prev_cgpa", "attendance", "study_hours", "assignments_done",
            "ca_score", "course_units", "sleep_hours"]

X = df[FEATURES]
X_train, X_test, yr_train, yr_test, yc_train, yc_test = train_test_split(
    X, df.next_cgpa, df.standing, test_size=0.2, random_state=42, stratify=df.standing)

print(len(X_train), "training rows,", len(X_test), "test rows")

regressor = RandomForestRegressor(n_estimators=200, max_depth=12, min_samples_leaf=3,
                                  random_state=42, n_jobs=-1)
regressor.fit(X_train, yr_train)
pred = regressor.predict(X_test)

print("Mean absolute error:", round(mean_absolute_error(yr_test, pred), 3), "grade points")
print("R² score:          ", round(r2_score(yr_test, pred), 3))

classifier = RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_leaf=3,
                                    random_state=42, n_jobs=-1, class_weight="balanced")
classifier.fit(X_train, yc_train)
cpred = classifier.predict(X_test)

print("Accuracy:", round(accuracy_score(yc_test, cpred), 3))
print(classification_report(yc_test, cpred))

importance = pd.Series(regressor.feature_importances_, index=FEATURES).sort_values(ascending=False)
print(importance.round(3))

# Statistics about the student population, used by the web app to compare
# a student's habits with everyone else's.
cohort = {
    "percentiles": {f: np.percentile(X_train[f], np.arange(101)).round(3).tolist() for f in FEATURES},
    "importance": {f: round(float(v), 4) for f, v in zip(FEATURES, regressor.feature_importances_)},
    "standing_share": (df.standing.value_counts(normalize=True).round(4)).to_dict(),
    "size": int(len(df)),
}

bundle = {
    "regressor": regressor,
    "classifier": classifier,
    "features": FEATURES,
    "cohort": cohort,
    "metrics": {
        "mae": round(float(mean_absolute_error(yr_test, pred)), 3),
        "r2": round(float(r2_score(yr_test, pred)), 3),
        "accuracy": round(float(accuracy_score(yc_test, cpred)), 3),
    },
    "sklearn_version": sklearn.__version__,
}
joblib.dump(bundle, OUT, compress=3)
print("Saved advisor_model.pkl", bundle["metrics"])

loaded = joblib.load(OUT)
me = pd.DataFrame([{"prev_cgpa": 3.2, "attendance": 70, "study_hours": 8, "assignments_done": 75,
                    "ca_score": 18, "course_units": 24, "sleep_hours": 5.5}])[loaded["features"]]
print("Projected CGPA:", round(float(loaded["regressor"].predict(me)[0]), 2))
print("Standing:      ", loaded["classifier"].predict(me)[0])
