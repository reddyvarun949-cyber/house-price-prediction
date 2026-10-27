"""Flask API for the House Price Prediction project.

Run from the project root:
    python backend/app.py
The API starts on http://localhost:5000

Endpoints
    GET  /api/health    -> is the API up and is the model loaded?
    GET  /api/options   -> allowed values and ranges (the frontend uses these to build the form)
    POST /api/predict   -> JSON with house details -> predicted price in lakhs

The model is trained in notebook/House_Price_Prediction.ipynb and loaded ONCE when the server starts.
We never retrain on a request.
"""
import json
import math
import os

import joblib
import pandas as pd
from flask import Flask, jsonify, request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "house_price_model.joblib")
INFO_PATH = os.path.join(BASE_DIR, "models", "model_info.json")

# Which website may call this API from a browser (the Vite dev server by default).
ALLOWED_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")

app = Flask(__name__)

# ---- load the model once at start-up ----
if not os.path.exists(MODEL_PATH) or not os.path.exists(INFO_PATH):
    raise SystemExit("Model files not found. Run notebook/House_Price_Prediction.ipynb first to create models/.")
model = joblib.load(MODEL_PATH)
with open(INFO_PATH) as f:
    info = json.load(f)

NUMERIC = info["numeric_features"]
CATEGORICAL = info["categorical_features"]
INTEGER_FIELDS = {"bedrooms", "bathrooms", "floor"}


@app.after_request
def add_cors_headers(response):
    """Allow the React app (a different port = a different 'origin') to call this API."""
    response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def validate(payload):
    """Return (clean_row, errors). errors is a dict: field -> message a person can understand."""
    errors, row = {}, {}
    if not isinstance(payload, dict):
        return None, {"body": "Send a JSON object with the house details."}

    for field in NUMERIC:
        low, high = info["numeric_ranges"][field]
        value = payload.get(field)
        if value is None or value == "":
            errors[field] = "This field is required."
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            errors[field] = "Must be a number."
            continue
        if math.isnan(number) or math.isinf(number):
            errors[field] = "Must be a real number."
        elif field in INTEGER_FIELDS and not number.is_integer():
            errors[field] = "Must be a whole number."
        elif not (low <= number <= high):
            errors[field] = f"Must be between {low:g} and {high:g} (the range the model was trained on)."
        else:
            row[field] = number

    for field in CATEGORICAL:
        allowed = info["categories"][field]
        value = payload.get(field)
        if value is None or str(value).strip() == "":
            errors[field] = "This field is required."
        elif str(value).strip() not in allowed:
            errors[field] = f"Unknown value '{value}'. Choose one of: {', '.join(allowed)}."
        else:
            row[field] = str(value).strip()

    if not errors and row["bathrooms"] > row["bedrooms"] + 2:
        errors["bathrooms"] = "Bathrooms look too high for the number of bedrooms. Please check the value."
    return row, errors


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "model": info["model_name"]})


@app.get("/api/options")
def options():
    return jsonify({
        "categories": info["categories"],
        "numeric_ranges": info["numeric_ranges"],
        "model": info["model_name"],
        "test_mae_lakhs": info["test_metrics"]["MAE"],
    })


@app.route("/api/predict", methods=["POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":           # browser "preflight" check before a POST
        return ("", 204)
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Request body must be JSON (Content-Type: application/json)."}), 400

    row, errors = validate(payload)
    if errors:
        return jsonify({"error": "Some inputs are invalid.", "fields": errors}), 422

    features = pd.DataFrame([row], columns=NUMERIC + CATEGORICAL)
    price = float(model.predict(features)[0])
    mae = info["test_metrics"]["MAE"]
    return jsonify({
        "predicted_price_lakhs": round(price, 2),
        "likely_range_lakhs": [round(max(price - mae, 0), 2), round(price + mae, 2)],
        "model": info["model_name"],
        "note": f"On unseen test houses this model was off by {mae:.1f} lakhs on average.",
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
