import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = "/api";
function generateAssessmentId() {
  const timestamp = Date.now().toString(36).toUpperCase();
  const random = Math.random()
    .toString(36)
    .slice(2, 6)
    .toUpperCase();

  return `ASM-${timestamp}-${random}`;
}

const emptyAssessment = {
  assessment_id: "",
  patient_ref: "demo-001",
  education: 16,
  mmse: 27,
  adas: "",
  faq: "",
  sex: "2",
  moca: ""
};

function formatFeatureName(feature) {
  const names = {
    "num__education": "Education",
    "num__mmse": "MMSE",
    "num__adas": "ADAS",
    "num__faq": "FAQ",
    "cat__sex_1.0": "Sex: Male",
    "cat__sex_2.0": "Sex: Female",
    "num__missingindicator_education": "Education missingness",
    "num__missingindicator_mmse": "MMSE missingness",
    "num__missingindicator_adas": "ADAS missingness",
    "num__missingindicator_faq": "FAQ missingness"
  };

  return names[feature] || feature;
}

function toNumberOrNull(value) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }

  const number = Number(value);

  return Number.isFinite(number) ? number : null;
}

function buildAssessment(form) {
  return {
    assessment_id:
      form.assessment_id || generateAssessmentId(),

    patient_ref:
      form.patient_ref || "anonymous",

    education:
      toNumberOrNull(form.education),

    mmse:
      toNumberOrNull(form.mmse),

    adas:
      toNumberOrNull(form.adas),

    faq:
      toNumberOrNull(form.faq),

    sex:
      toNumberOrNull(form.sex),

    moca:
      toNumberOrNull(form.moca)
  };
}

function priorityClass(priority) {
  return String(priority || "LOW").toLowerCase();
}

function App() {
  const [page, setPage] = useState("dashboard");
  const [form, setForm] = useState(emptyAssessment);
  const [info, setInfo] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [uncertainty, setUncertainty] = useState(null);
  const [quality, setQuality] = useState(null);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [uncertaintyLoading, setUncertaintyLoading] = useState(false);

  const [cohort, setCohort] = useState([]);
  const [capacity, setCapacity] = useState("");
  const [ranking, setRanking] = useState(null);
  const [rankingLoading, setRankingLoading] = useState(false);
  const [populationRisk, setPopulationRisk] = useState(null);
const loadPatients = async () => {
  try {
    const response = await fetch(`${API}/patients`);

    if (!response.ok) {
      throw new Error("Could not load saved patients.");
    }

    const data = await response.json();

    setCohort(
      data.patients.map((patient) => ({
        ...patient,
        selected_for_capacity: false,
      }))
    );
  } catch (err) {
    setError(err.message || "Could not load saved patients.");
  }
};

  useEffect(() => {
    fetch(`${API}/model-info`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(
            `Model information request failed: ${response.status}`
          );
        }

        return response.json();
      })
      .then((data) => setInfo(data))
      .catch((err) => {
        setError(err.message || "Could not connect to backend.");
      });
  }, []);
  useEffect(() => {
    loadPatients();
  }, []);
  useEffect(() => {
    fetch(`${API}/population/risk-distribution`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(
            `Population risk request failed: ${response.status}`
          );
        }

        return response.json();
      })
      .then((data) => setPopulationRisk(data))
      .catch((err) => {
        console.error(
          "Could not load population risk distribution:",
          err
        );
      });
  }, []);

  const goToAssessment = () => {
    setPage("assessment");
  };

  const goToDashboard = () => {
    setPage("dashboard");
  };

  const update = (key, value) => {
    setForm((previous) => ({
      ...previous,
      [key]: value
    }));
  };

  const predict = async (event) => {
    event.preventDefault();

    setError("");
    setPrediction(null);
    setExplanation(null);
    setUncertainty(null);
    setQuality(null);
    setLoading(true);

  try {
      const assessment = buildAssessment(form);
      setForm((previous) => ({
          ...previous,
          assessment_id: assessment.assessment_id
      }));

      const response = await fetch(`${API}/assessment`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(assessment)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Assessment failed."
        );
      }

      setPrediction(data.prediction);
      setExplanation(data.explanation);
      setQuality(data.data_quality);

      await loadUncertainty(assessment);
    } catch (err) {
      setError(
        err.message || "Could not connect to the backend."
      );
    } finally {
      setLoading(false);
    }
  };

  const loadUncertainty = async (assessment) => {
    setUncertaintyLoading(true);

    try {
      const response = await fetch(`${API}/uncertainty`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(assessment)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Uncertainty analysis failed."
        );
      }

      setUncertainty(data);
    } catch (err) {
      setUncertainty({
        available: false,
        reason:
          err.message ||
          "Uncertainty information is unavailable."
      });
    } finally {
      setUncertaintyLoading(false);
    }
  };


  const removePatient = (index) => {
    setCohort((previous) =>
      previous.filter((_, itemIndex) => itemIndex !== index)
    );
  };

  const clearCohort = () => {
    setCohort([]);
    setRanking(null);
  };

  const rankCohort = async () => {
    if (cohort.length === 0) {
      setError("Add at least one patient to the cohort first.");
      return;
    }

    setError("");
    setRankingLoading(true);

    try {
      const capacityNumber =
        capacity === ""
          ? null
          : Number(capacity);

      const response = await fetch(`${API}/rank`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          patients: cohort,
          capacity: capacityNumber
        })
      });

      const data = await response.json();
      await loadPatients();

      if (!response.ok) {
        throw new Error(
          data.detail || "Cohort ranking failed."
        );
      }

      setRanking(data);
    } catch (err) {
      setError(
        err.message || "Could not rank the cohort."
      );
    } finally {
      setRankingLoading(false);
    }
  };

  return (
  <div className="app">

    {page === "dashboard" && (
      <section className="card dashboard-card">

        <div className="eyebrow">
          CLINICAL DECISION-SUPPORT RESEARCH PROTOTYPE
        </div>

        <h1>
          AI-Driven Alzheimer's
          <br />
          Diagnostic Prioritization
        </h1>

        <p className="hero-description">
          Research dashboard for calibrated risk estimation,
          patient prioritization, and resource-allocation
          simulation in clinician-led diagnostic workflows.
        </p>

        <div className="dashboard-stats">

          <div className="stat-card">
            <span>RESEARCH COHORT</span>
            <strong>1,677</strong>
            <small>Stage-1 participants</small>
          </div>

          <div className="stat-card">
            <span>TARGET CASES</span>
            <strong>128</strong>
            <small>24-month retrospective target</small>
          </div>

          <div className="stat-card">
            <span>TARGET RATE</span>
            <strong>7.63%</strong>
            <small>Retrospective cohort rate</small>
          </div>
          <div className="stat-card">
            <span>STAGE-1 COMPLETE</span>
            <strong>98.93%</strong>
            <small>Complete core-input records</small>
          </div>

        </div>

        <div className="dashboard-actions">

          <button
            type="button"
            className="primary-button"
            onClick={goToAssessment}
          >
            Start New Assessment
          </button>

        </div>


        <div className="research-notice">
          <strong>Research prototype:</strong>{" "}
          This dashboard supports retrospective research
          prioritization. It does not provide a medical
          diagnosis or treatment recommendation.
        </div>

      </section>
    )}
    {page === "assessment" && (
        <>

      <header className="hero">
        <div className="hero-inner">
          <div>
            <div className="eyebrow">
              CLINICAL DECISION-SUPPORT RESEARCH PROTOTYPE
            </div>

            <h1>
              AI-Driven Prioritization
            </h1>

            <p className="hero-subtitle">
              Early Alzheimer's diagnostic pathway
            </p>

            <p className="hero-description">
              Calibrated Stage-1 risk estimation and
              research prioritization support for
              clinician-led diagnostic workflows.
            </p>
          </div>

          <div className="hero-badge">
            <span>STAGE 1</span>
            <small>Pre-MRI prioritization</small>
          </div>
        </div>
      </header>

      <main>

        {error && (
          <section className="alert error">
            <strong>Request error:</strong> {error}
          </section>
        )}

        <section className="card">

          <div className="section-heading">
            <div>
              <span className="section-number">01</span>
              <h2>Patient Assessment</h2>
            </div>

            <span className="stage-tag">
              PRE-MRI
            </span>
          </div>

          <p className="section-description">
            Enter available Stage-1 screening information.
            The model estimates retrospective research risk
            to support prioritization for further diagnostic
            evaluation.
          </p>

          <form
            onSubmit={predict}
            className="assessment-grid"
          >
            <label>
              Assessment ID
              <span className="input-help">
                Generated automatically
              </span>

              <input
              type="text"
              value={
                form.assessment_id ||
                "Generated after assessment"
            }
            readOnly
          />
        </label>

            <label>
              Patient Reference
              <input
                type="text"
                value={form.patient_ref}
                onChange={(e) =>
                  update("patient_ref", e.target.value)
                }
                placeholder="e.g. patient-001"
              />
            </label>

            <label>
              Education
              <span className="input-help">
                Years, 0–20
              </span>
              <input
                type="number"
                min="0"
                max="20"
                step="1"
                value={form.education}
                onChange={(e) =>
                  update("education", e.target.value)
                }
                placeholder="0–20"
              />
            </label>

            <label>
              MMSE
              <span className="input-help">
                Score, 0–30
              </span>
              <input
                type="number"
                min="0"
                max="30"
                step="1"
                value={form.mmse}
                onChange={(e) =>
                  update("mmse", e.target.value)
                }
                placeholder="0–30"
              />
            </label>

            <label>
              ADAS-11
              <span className="input-help">
                Score, 0–70
              </span>
              <input
                type="number"
                min="0"
                max="70"
                step="any"
                value={form.adas}
                onChange={(e) =>
                  update("adas", e.target.value)
                }
                placeholder="Optional"
              />
            </label>

            <label>
              FAQ
              <span className="input-help">
                Score, 0–30
              </span>
              <input
                type="number"
                min="0"
                max="30"
                step="1"
                value={form.faq}
                onChange={(e) =>
                  update("faq", e.target.value)
                }
                placeholder="Optional"
              />
            </label>

            <label>
              Sex
              <span className="input-help">
                ADNI coding
              </span>
              <select
                value={form.sex}
                onChange={(e) =>
                  update("sex", e.target.value)
                }
              >
                <option value="1">Male</option>
                <option value="2">Female</option>
              </select>
            </label>

            <label>
              MoCA
              <span className="input-help">
                Contextual only, not Stage-1 model input
              </span>
              <input
                type="number"
                min="0"
                max="30"
                step="1"
                value={form.moca}
                onChange={(e) =>
                  update("moca", e.target.value)
                }
                placeholder="Optional"
              />
            </label>

            <div className="form-actions">

              <button
                type="submit"
                className="primary-button"
                disabled={loading}
              >
                {loading
                  ? "Calculating..."
                  : "Calculate Research Risk"}
              </button>

              <div className="queue-status">
                ✓ Assessment saved to prioritization queue
              </div>
              {capacity && cohort.length > 0 && (
  <div className="capacity-summary">
    Selected for simulated capacity:{" "}
    <strong>
      {Math.min(Number(capacity), cohort.length)}
    </strong>{" "}
    of <strong>{cohort.length}</strong> patients
  </div>
)}

            </div>

          </form>

          <div className="model-input-note">
            <strong>Stage-1 model inputs:</strong>{" "}
            Education, MMSE, ADAS, FAQ and Sex.
            MoCA is displayed for contextual information
            because it is not used by the Stage-1 model.
          </div>

        </section>

        {prediction && (
          <section className="card result-card">

            <div className="section-heading">
              <div>
                <span className="section-number">02</span>
                <h2>Prioritization Result</h2>
              </div>

              <span className="stage-tag">
                {prediction.stage}
              </span>
            </div>

            <div className="result-grid">

              <div className="risk-panel">

                <span className="metric-label">
                  CALIBRATED RESEARCH RISK
                </span>

                <div className="risk-value">
                  {(prediction.risk_score * 100).toFixed(1)}%
                </div>

                <div
                  className={`priority-badge ${priorityClass(
                    prediction.priority
                  )}`}
                >
                  {prediction.priority} PRIORITY
                </div>

                <p className="metric-note">
                  This is a model-estimated risk score,
                  not a diagnosis or clinical probability
                  of Alzheimer's disease.
                </p>

              </div>

              <div className="quality-panel">

                <span className="metric-label">
                  DATA QUALITY
                </span>

                <div
                  className={`quality-badge ${
                    quality
                      ? quality.level.toLowerCase()
                      : ""
                  }`}
                >
                  {quality?.level || "UNKNOWN"}
                </div>

                {quality && (
                  <>
                    <p>
                      <strong>
                        {quality.available}
                      </strong>{" "}
                      of{" "}
                      <strong>
                        {quality.total}
                      </strong>{" "}
                      core model inputs available
                    </p>

                    <div className="progress-track">
                      <div
                        className="progress-bar"
                        style={{
                          width: `${quality.completeness * 100}%`
                        }}
                      />
                    </div>

                    {quality.warnings?.length > 0 && (
                      <div className="warning-list">
                        {quality.warnings.map(
                          (warning, index) => (
                            <p key={index}>
                              {warning}
                            </p>
                          )
                        )}
                      </div>
                    )}
                  </>
                )}

              </div>

            </div>

            <div className="result-meta">

              <div>
                <span>Model</span>
                <strong>
                  {prediction.model_version}
                </strong>
              </div>

              <div>
                <span>Workflow</span>
                <strong>
                  Clinician-led diagnostic evaluation
                </strong>
              </div>

            </div>

            <div className="research-notice">
              <strong>Interpretation:</strong>{" "}
              The priority category is a research/resource
              prioritization output. It is not a clinical
              cutoff and should not be used by itself to
              determine diagnosis, treatment, or eligibility
              for care.
            </div>

          </section>
        )}

        {explanation && (
          <section className="card">

            <div className="section-heading">
              <div>
                <span className="section-number">03</span>
                <h2>Model Explainability</h2>
              </div>
            </div>

            <p className="section-description">
              These contributions describe how the input
              variables influence the logistic-regression
              model score. They are not causal effects or
              independent clinical effects.
            </p>

            <div className="table-wrapper">

              <table>
                <thead>
                  <tr>
                    <th>Feature</th>
                    <th>Direction</th>
                    <th>Contribution</th>
                  </tr>
                </thead>

                <tbody>
                  {explanation.contributions
                    ?.slice(0, 10)
                    .map((item, index) => (
                      <tr key={index}>
                        <td>
                          <strong>
                            {formatFeatureName(
                              item.raw_feature ||
                              item.feature
                            )}
                          </strong>
                        </td>

                        <td>
                          <span
                            className={
                              item.contribution > 0
                                ? "direction-up"
                                : item.contribution < 0
                                ? "direction-down"
                                : "direction-neutral"
                            }
                          >
                            {item.direction}
                          </span>
                        </td>

                        <td>
                          {Number(
                            item.contribution
                          ).toFixed(4)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>

            </div>

            <div className="explanation-note">
              {explanation.interpretation}
            </div>

          </section>
        )}

        {prediction && (
          <section className="card">

            <div className="section-heading">
              <div>
                <span className="section-number">04</span>
                <h2>Uncertainty Analysis</h2>
              </div>
            </div>

            {uncertaintyLoading && (
              <p>
                Loading retrospective uncertainty analysis...
              </p>
            )}

            {!uncertaintyLoading && uncertainty && (
              <>
                <div className="uncertainty-grid">

                  <div className="uncertainty-box">
                    <span>
                      Production calibrated risk
                    </span>

                    <strong>
                      {(
                        uncertainty.production_calibrated_risk *
                        100
                      ).toFixed(2)}
                      %
                    </strong>

                    <small>
                      Used for the displayed prioritization
                      result.
                    </small>
                  </div>

                  {uncertainty.available ? (
                    <div className="uncertainty-box">
                      <span>
                        Bootstrap raw model probability
                      </span>

                      <strong>
                        {(
                          uncertainty
                            .bootstrap_raw_probability_mean *
                          100
                        ).toFixed(2)}
                        %
                      </strong>

                      <small>
                        Mean across 500 uncalibrated retrospective model refits.
                      </small>
                    </div>
                  ) : null}

                </div>

                {uncertainty.available ? (
                  <div className="interval-panel">

                    <h3>
                      Bootstrap raw-probability interval
                    </h3>

                    <div className="interval-value">
                      {(
                        uncertainty
                          .bootstrap_raw_probability_lower_95 *
                        100
                      ).toFixed(2)}
                      % –{" "}
                      {(
                        uncertainty
                          .bootstrap_raw_probability_upper_95 *
                        100
                      ).toFixed(2)}
                      %
                    </div>

                    <p>
                      This empirical interval describes
                      uncertainty in raw model estimates
                      across the retrospective bootstrap
                      refits. It is <strong>not</strong> a
                      clinical confidence interval.
                    </p>

                  </div>
                ) : (
                  <div className="research-notice">
                    <strong>
                      Patient-specific bootstrap interval
                      unavailable.
                    </strong>

                    <p>
                      {uncertainty.reason}
                    </p>

                    <p>
                      The production calibrated risk remains
                      available separately.
                    </p>
                  </div>
                )}
              </>
            )}

          </section>
        )}

        <section className="card">

          <div className="section-heading">
            <div>
              <span className="section-number">05</span>
              <h2>Prioritization Queue</h2>
            </div>

            <span className="stage-tag">
              RESEARCH
            </span>
          </div>

          <p className="section-description">
            Review saved patient assessments and create a ranked research prioritization queue.
          </p>

          {cohort.length === 0 ? (
            <div className="empty-state">
             No patients are currently in the prioritization queue.
              New assessments are automatically added after submission.
            </div>
          ) : (
            <div className="cohort-list">

              {cohort.map((patient, index) => (
                <div
                  className="cohort-row"
                  key={`${patient.patient_ref}-${index}`}
                >

                  <div>
                    <strong>
                      {patient.assessment_id}
                    </strong>
                    <span>
                      Patient: {patient.patient_ref}
                    </span>


                    <span>
                      MMSE: {patient.mmse ?? "—"} ·{" "}
                      ADAS: {patient.adas ?? "—"} ·{" "}
                      FAQ: {patient.faq ?? "—"}
                    </span>
                  </div>

                  <button
                    type="button"
                    className="remove-button"
                    onClick={() =>
                      removePatient(index)
                    }
                  >
                    Remove
                  </button>

                </div>
              ))}

            </div>
          )}

          <div className="ranking-controls">

            <label>
              Simulated capacity
              <span className="input-help">
                Optional number of patients/resources
              </span>

              <input
                type="number"
                min="1"
                max={Math.max(cohort.length, 1)}
                value={capacity}
                onChange={(e) =>
                  setCapacity(e.target.value)
                }
                placeholder="e.g. 3"
              />
              <div className="capacity-hint">
                Enter the number of simulated diagnostic-resource slots available.
              </div>
            </label>

            <button
              type="button"
              className="primary-button"
              disabled={
                rankingLoading ||
                cohort.length === 0
              }
              onClick={rankCohort}
            >
              {rankingLoading
                ? "Ranking..."
                : "Rank Cohort"}
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={clearCohort}
            >
              Clear Cohort
            </button>

          </div>

          {ranking && (
            <div className="ranking-results">

              <div className="ranking-summary">

                <div>
                  <span>Total patients</span>
                  <strong>
                    {ranking.total_patients}
                  </strong>
                </div>
            

                <div>
                  <span>Selected capacity</span>
                  <strong>
                    {ranking.selected_count}
                  </strong>
                </div>

                <div>
                  <span>Mean risk</span>
                  <strong>
                    {(ranking.cohort_summary.mean_risk * 100).toFixed(1)}%
                  </strong>
                </div>

              </div>

              <div className="table-wrapper">

                <table>
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Assessment</th>
                      <th>Patient</th>
                      <th>Risk</th>
                      <th>Priority</th>
                      <th>Data</th>
                      <th>Capacity</th>
                    </tr>
                  </thead>

                  <tbody>
                    {ranking.patients.map(
                      (patient) => (
                        <tr key={`${patient.patient_ref}-${patient.rank}`}>

                          <td>
                            <strong>
                              #{patient.rank}
                            </strong>
                          </td>
                          <td>
                            {patient.assessment_id}
                          </td>

                          <td>
                            {patient.patient_ref}
                          </td>

                          <td>
                            {(patient.risk_score * 100).toFixed(2)}%
                          </td>

                          <td>
                            <span
                              className={`table-priority ${priorityClass(
                                patient.priority
                              )}`}
                            >
                              {patient.priority}
                            </span>
                          </td>

                          <td>
                            {patient.data_quality.level}
                          </td>

                          <td>
                            {patient.selected_for_capacity
                              ? "SELECTED"
                              : "—"}
                          </td>

                        </tr>
                      )
                    )}
                  </tbody>
                </table>

              </div>

              <div className="research-notice">
                <strong>
                  Research resource-allocation simulation:
                </strong>{" "}
                the ranking and capacity selection are
                retrospective workflow-support outputs.
                They do not autonomously determine who
                receives clinical care or diagnostic testing.
              </div>

            </div>
          )}

        </section>

        {info && (
          <section className="card">

            <div className="section-heading">
              <div>
                <span className="section-number">06</span>
                <h2>Model Information</h2>
              </div>
            </div>

            <div className="model-grid">

              <div>
                <span>Model stage</span>
                <strong>
                  {info.stage}
                </strong>
              </div>

              <div>
                <span>Selected model</span>
                <strong>
                  {info.selected_model}
                </strong>
              </div>

              <div>
                <span>Model version</span>
                <strong>
                  {info.model_version}
                </strong>
              </div>

            </div>

            <h3>Stage-1 Features</h3>

            <div className="feature-tags">
              {info.features?.map(
                (feature) => (
                  <span key={feature}>
                    {formatFeatureName(feature)}
                  </span>
                )
              )}
            </div>

            <div className="threshold-grid">

              <div>
                <span>
                  High-priority research threshold
                </span>

                <strong>
                  {(
                    info.priority_thresholds.high_threshold *
                    100
                  ).toFixed(2)}
                  %
                </strong>
              </div>

              <div>
                <span>
                  Medium-priority research threshold
                </span>

                <strong>
                  {(
                    info.priority_thresholds.medium_threshold *
                    100
                  ).toFixed(2)}
                  %
                </strong>
              </div>

            </div>

            <div className="research-notice">
              <strong>Important:</strong>{" "}
              These thresholds are research/resource-oriented
              and are not validated clinical cutoffs.
            </div>

          </section>
        )}

        <section className="card final-notice">

          <h2>
            Research Prototype Notice
          </h2>

          <p>
            This system is a clinical decision-support
            research prototype derived from retrospective
            ADNI data. It estimates progression-related
            research risk and supports prioritization
            research.
          </p>

          <p>
            It does not provide a medical diagnosis, does
            not recommend treatment, and should not replace
            clinician judgment, local protocols, or
            established diagnostic evaluation.
          </p>

        </section>

      </main>

      <footer>
        AI-Driven Prioritization for Early Alzheimer's
        Diagnostic Pathways · Research Prototype
      </footer>
      </>
    )}

    </div>
  );
}

createRoot(
  document.getElementById("root")
).render(
  <App />
);





