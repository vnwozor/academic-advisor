"""Flask web app that serves the academic advisor.

Run:  python app.py   then open http://127.0.0.1:5000
"""
from flask import Flask, jsonify, render_template, request

from advisor import LIMITS, Advisor

app = Flask(__name__)
advisor = Advisor()


@app.get("/")
def home():
    return render_template("index.html", metrics=advisor.metrics,
                           cohort_size=f"{advisor.cohort.get('size', 3000):,}")


@app.post("/api/advise")
def advise():
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict()
    try:
        return jsonify(advisor.advise(data))
    except ValueError as err:
        return jsonify({"error": str(err)}), 400


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "model": advisor.metrics, "inputs": list(LIMITS)})


if __name__ == "__main__":
    app.run(debug=True)
