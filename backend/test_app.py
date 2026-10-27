"""Automated tests for the API. Run from the project root:

    python -m unittest discover -s backend -p "test_*.py" -v

They use Flask's built-in test client, so no server needs to be running.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app  # noqa: E402

VALID = {
    "area_sqft": 1200, "bedrooms": 2, "bathrooms": 2, "age_years": 5,
    "distance_to_metro_km": 1.5, "floor": 4,
    "locality": "Tech City", "parking": "Yes", "furnishing": "Semi-Furnished",
}


class HousePriceApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["status"], "ok")

    def test_options_lists_localities(self):
        data = self.client.get("/api/options").get_json()
        self.assertIn("Tech City", data["categories"]["locality"])
        self.assertIn("area_sqft", data["numeric_ranges"])

    def test_valid_prediction(self):
        r = self.client.post("/api/predict", json=VALID)
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertGreater(body["predicted_price_lakhs"], 0)
        low, high = body["likely_range_lakhs"]
        self.assertLessEqual(low, body["predicted_price_lakhs"])
        self.assertGreaterEqual(high, body["predicted_price_lakhs"])
        print("\n  sample prediction:", body)

    def test_numbers_sent_as_text_are_accepted(self):
        r = self.client.post("/api/predict", json={**VALID, "area_sqft": "1200"})
        self.assertEqual(r.status_code, 200)

    def test_premium_locality_costs_more(self):
        a = self.client.post("/api/predict", json={**VALID, "locality": "Green Park"}).get_json()
        b = self.client.post("/api/predict", json={**VALID, "locality": "New Colony"}).get_json()
        self.assertGreater(a["predicted_price_lakhs"], b["predicted_price_lakhs"])

    def test_missing_field(self):
        payload = dict(VALID)
        del payload["area_sqft"]
        r = self.client.post("/api/predict", json=payload)
        self.assertEqual(r.status_code, 422)
        self.assertIn("area_sqft", r.get_json()["fields"])

    def test_not_a_number(self):
        r = self.client.post("/api/predict", json={**VALID, "age_years": "old"})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.get_json()["fields"]["age_years"], "Must be a number.")

    def test_out_of_range(self):
        r = self.client.post("/api/predict", json={**VALID, "area_sqft": 50000})
        self.assertEqual(r.status_code, 422)
        self.assertIn("between", r.get_json()["fields"]["area_sqft"])

    def test_whole_number_rule(self):
        r = self.client.post("/api/predict", json={**VALID, "bedrooms": 2.5})
        self.assertEqual(r.status_code, 422)

    def test_unknown_locality(self):
        r = self.client.post("/api/predict", json={**VALID, "locality": "Airport Road"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("Unknown value", r.get_json()["fields"]["locality"])

    def test_body_not_json(self):
        r = self.client.post("/api/predict", data="hello", content_type="text/plain")
        self.assertEqual(r.status_code, 400)

    def test_cors_headers_present(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "http://localhost:5173")
        pre = self.client.options("/api/predict")
        self.assertEqual(pre.status_code, 204)


if __name__ == "__main__":
    unittest.main()
