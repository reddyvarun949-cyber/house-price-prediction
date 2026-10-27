import { useEffect, useState } from "react";
import { getOptions, predictPrice } from "./api.js";

// Starting values for the form (a typical 2-bedroom flat).
const EMPTY_FORM = {
  area_sqft: "1200",
  bedrooms: "2",
  bathrooms: "2",
  age_years: "5",
  distance_to_metro_km: "1.5",
  floor: "3",
  locality: "",
  parking: "Yes",
  furnishing: "Semi-Furnished",
};

const NUMBER_FIELDS = [
  { name: "area_sqft", label: "Area (sq ft)", step: "1" },
  { name: "bedrooms", label: "Bedrooms", step: "1" },
  { name: "bathrooms", label: "Bathrooms", step: "1" },
  { name: "age_years", label: "Age of building (years)", step: "1" },
  { name: "distance_to_metro_km", label: "Distance to metro (km)", step: "0.1" },
  { name: "floor", label: "Floor (0 = ground)", step: "1" },
];

function App() {
  const [options, setOptions] = useState(null);   // allowed values from the API
  const [form, setForm] = useState(EMPTY_FORM);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [loading, setLoading] = useState(false);

  // Load the dropdown values once when the page opens.
  useEffect(() => {
    getOptions()
      .then((data) => {
        setOptions(data);
        setForm((f) => ({ ...f, locality: data.categories.locality[0] }));
      })
      .catch((err) => setError(err.message));
  }, []);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm({ ...form, [name]: value });
    setFieldErrors({ ...fieldErrors, [name]: undefined }); // clear the message for this field
  }

  // Simple checks in the browser; the API checks everything again.
  function checkForm() {
    const problems = {};
    for (const field of NUMBER_FIELDS) {
      if (form[field.name] === "") problems[field.name] = "Required";
      else if (Number.isNaN(Number(form[field.name]))) problems[field.name] = "Must be a number";
    }
    return problems;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setResult(null);
    setError("");
    const problems = checkForm();
    if (Object.keys(problems).length > 0) {
      setFieldErrors(problems);
      return;
    }
    setLoading(true);
    try {
      const data = await predictPrice(form);
      setResult(data);
    } catch (err) {
      setError(err.message);
      setFieldErrors(err.fields || {});
    } finally {
      setLoading(false);
    }
  }

  if (!options && !error) {
    return <main className="page"><p className="muted">Loading form…</p></main>;
  }

  return (
    <main className="page">
      <header>
        <h1>House Price Estimator</h1>
        <p className="muted">Enter the details of a house to estimate its price in lakh rupees.</p>
      </header>

      {error && <div className="alert">{error}</div>}

      {options && (
        <form onSubmit={handleSubmit} className="card" noValidate>
          <div className="grid">
            <label>
              Locality
              <select name="locality" value={form.locality} onChange={handleChange}>
                {options.categories.locality.map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </label>

            {NUMBER_FIELDS.map((field) => {
              const [min, max] = options.numeric_ranges[field.name];
              return (
                <label key={field.name}>
                  {field.label}
                  <input
                    type="number"
                    name={field.name}
                    value={form[field.name]}
                    min={min}
                    max={max}
                    step={field.step}
                    onChange={handleChange}
                    className={fieldErrors[field.name] ? "invalid" : ""}
                  />
                  <span className="hint">
                    {fieldErrors[field.name] || `Allowed: ${min} – ${max}`}
                  </span>
                </label>
              );
            })}

            <label>
              Parking
              <select name="parking" value={form.parking} onChange={handleChange}>
                {options.categories.parking.map((p) => <option key={p}>{p}</option>)}
              </select>
            </label>

            <label>
              Furnishing
              <select name="furnishing" value={form.furnishing} onChange={handleChange}>
                {options.categories.furnishing.map((f) => <option key={f}>{f}</option>)}
              </select>
            </label>
          </div>

          <button type="submit" disabled={loading}>
            {loading ? "Estimating…" : "Estimate price"}
          </button>
        </form>
      )}

      {result && (
        <section className="card result">
          <p className="muted">Estimated price</p>
          <p className="price">₹ {result.predicted_price_lakhs.toFixed(1)} lakhs</p>
          <p>
            Likely range: ₹ {result.likely_range_lakhs[0].toFixed(1)} – {result.likely_range_lakhs[1].toFixed(1)} lakhs
          </p>
          <p className="muted small">{result.note} Model: {result.model}.</p>
        </section>
      )}
    </main>
  );
}

export default App;
