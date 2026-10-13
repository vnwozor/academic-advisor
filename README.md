# Semester Advisor

A personal academic advisor for CSC 303. Tell it how your semester is going and it projects your next CGPA on the 5.0 scale, gives your academic standing, and shows the three habits that would raise your CGPA the most.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/vnwozor/academic-advisor/blob/main/notebooks/advisor_model.ipynb)


## How it works

| Part | What it is |
|---|---|
| `notebooks/advisor_model.ipynb` | Built and trained on **Google Colab**. Generates 3,000 student records, trains a Random Forest **regressor** (projected CGPA) and **classifier** (standing), evaluates them, saves `advisor_model.pkl`. |
| `train_model.py` | The notebook's code as a plain script, to rebuild the `.pkl` locally: `python train_model.py`. |
| `model/advisor_model.pkl` | Both trained models, plus the feature order and test scores. |
| `advisor.py` | Loads the `.pkl`. Validates input, predicts, then runs **what-if analysis**: each habit is nudged to a realistic target and re-scored, so advice is ranked by how much CGPA it actually buys. |
| `app.py` | **Flask** web app. `GET /` serves the page, `POST /api/advise` returns advice as JSON, `GET /api/health` checks the model. |
| `templates/`, `static/` | The web interface. Sliders update the advice live. A statistics section shows the likely CGPA range, how confident the model is, how your habits compare with the other 3,000 students, and which inputs matter most. |
| `tests/test_app.py` | 14 unit tests for the model, the advice logic and the API. |
| `.vscode/` | Python-optimised VS Code settings, recommended extensions and a one-click run config. |

**AI techniques:** supervised machine learning (Random Forest regression + classification) combined with model-based what-if reasoning to generate ranked recommendations. The likely range comes from the spread of the forest's 200 individual tree predictions (10th–90th percentile), and the standing confidence from the classifier's class probabilities.

**Software engineering practices:** version control with Git/GitHub, separate modules for model, logic and web layer, input validation, unit tests, pinned dependencies and a reproducible notebook.

### Model results (test set, 600 students)

```
Mean absolute error: 0.218 grade points
R² score:            0.83
Standing accuracy:   0.812
```

Inputs: CGPA so far, units this semester, lecture attendance, weekly study hours, assignments submitted, average CA score (out of 30), hours of sleep.

Degree classes follow the Nigerian 5-point scale: First Class 4.50+, Second Class Upper 3.50–4.49, Second Class Lower 2.40–3.49, Third Class 1.50–2.39, Pass 1.00–1.49.

---

## Setup, step by step

### 1. Check Git is installed

```bash
git --version
```
```
git version 2.43.0
```

### 2. GitHub: create the repo

Sign in at github.com → **New repository** → name it `academic-advisor` → Public → **Create**.
(If you installed GitHub Desktop or the `gh` CLI, `gh repo create academic-advisor --public` does the same.)

### 3. Push this project

```bash
cd academic-advisor
git init
git add .
git commit -m "Academic advisor: Colab model, Flask app, tests"
git branch -M main
git remote add origin https://github.com/vnwozor/academic-advisor.git
git push -u origin main
```

### 4. Train the model on Google Colab

Click the **Open in Colab** badge above (or Colab → File → Open notebook → GitHub → `vnwozor/academic-advisor`), then **Runtime → Run all**. The last cell downloads `advisor_model.pkl`; put it in `model/`, replacing the old one, and commit it:

```bash
git add model/advisor_model.pkl
git commit -m "Model trained on Colab"
git push
```

### 5. Open in VS Code and set up Python

```bash
code .
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

VS Code will offer to install the recommended extensions (Python, Pylance, Black, Jupyter, GitLens). Accept.

### 6. Run the tests

```bash
python -m unittest -v
```
```
...
Ran 14 tests in 3.7s

OK
```

### 7. Run the web app

```bash
python app.py
```
```
 * Running on http://127.0.0.1:5000
```

Open http://127.0.0.1:5000 and move the sliders. Or press **F5** in VS Code ("Run advisor web app").

### Testing the API directly

```bash
curl -X POST http://127.0.0.1:5000/api/advise -H "Content-Type: application/json" \
  -d '{"prev_cgpa":3.2,"attendance":70,"study_hours":8,"assignments_done":75,"ca_score":18,"course_units":24,"sleep_hours":5.5}'
```
```json
{
  "projected_cgpa": 2.89,
  "degree_class": "Second Class Lower",
  "standing": "Needs attention",
  "tips": [
    {"title": "Study a little more each week", "gain": 0.29, "...": "..."},
    {"title": "Raise your CA score", "gain": 0.18, "...": "..."},
    {"title": "Submit every assignment", "gain": 0.13, "...": "..."}
  ],
  "potential_cgpa": 3.39,
  "potential_class": "Second Class Lower"
}
```

## Limitations

The training data is simulated, because no public dataset of Nigerian students' study habits exists. The model learns the relationships built into that simulation, so treat projections as a guide. Swapping in real (anonymised) records from a department would only require replacing the dataset cell in the notebook.
