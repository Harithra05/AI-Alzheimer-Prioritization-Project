# AI-Driven Prioritization for Early Alzheimer's Diagnostic Pathways

Research/engineering reference implementation for the project workflow:

Patient data -> preprocessing -> model comparison -> calibrated risk score -> priority level -> SHAP explanation -> clinician dashboard

## Important workflow alignment

Your problem statement says the system prioritizes people for further diagnostic evaluation, including MRI/PET, while your original feature list includes MRI-derived eTIV/nWBV/ASF.

Those two statements describe different stages:

- **Stage 1 (pre-MRI):** demographics + cognitive screening; can be used to prioritize the MRI queue.
- **Stage 3 (post-MRI):** add MRI-derived features and re-rank patients for further evaluation.

This project therefore supports both:
1. `stage1`: no MRI-derived inputs.
2. `stage3`: adds MRI-derived inputs.

Do not use MRI-derived features in a model that is claimed to decide who should receive the first MRI.

## Target

The default configuration is a retrospective baseline-status target for a proof of concept. This is not a clinical diagnosis.

For a stronger research study, change the target definition to a prospectively defined outcome such as conversion/progression within a fixed follow-up window. The code contains a placeholder configuration for that extension, but the exact longitudinal endpoint should be agreed with your supervisor/protocol before training.

## Data

Put the unzipped ADNI CSV files in `data/raw/`.

Expected files include:

- All_Subjects_Key_MRI_*.csv
- UCSFFSX7_*.csv
- MMSE_*.csv
- PTDEMOG_*.csv
- DXSUM_*.csv
- optional MOCA_*.csv
- optional ADAS_*.csv
- optional FAQ_*.csv

Do not use CDR as a model feature in the core experiment.

The script discovers the newest matching CSV by prefix, so you do not need to rename files.

## Run locally

### 1. Create environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Put CSVs in `data/raw`

Unzip your ADNI downloads and copy the CSV files there.

### 3. Profile before selecting models

```powershell
python scripts/01_profile_data.py
```

This creates:
- `reports/profile_summary.json`
- `reports/profile_missingness.png`
- `reports/profile_distributions.png`
- `reports/profile_class_distribution.png`

The profiling step is intentionally before model selection.

### 4. Build the modelling tables

```powershell
python scripts/02_build_dataset.py --stage stage1
python scripts/02_build_dataset.py --stage stage3
```

Outputs:
- `data/processed/stage1.csv`
- `data/processed/stage3.csv`

### 5. Train and compare models

```powershell
python scripts/03_train.py --stage stage1
python scripts/03_train.py --stage stage3
```

Models compared:
- Logistic Regression
- Random Forest
- XGBoost

The training script evaluates:
- ROC-AUC
- PR-AUC
- recall
- precision
- calibration / Brier score
- top-k recall
- confusion matrix

It saves the comparison table and the selected calibrated model.

### 6. Start backend

```powershell
uvicorn backend.main:app --reload --port 8000
```

Open:
`http://localhost:8000/docs`

### 7. Start frontend

```powershell
cd frontend
npm install
npm run dev
```

Open:
`http://localhost:5173`

## Docker

```powershell
docker compose up --build
```

Services:
- frontend
- backend
- postgres

Frontend:
`http://localhost:3000`

Backend:
`http://localhost:8000/docs`

## AWS / cloud

The included deployment guide uses one EC2 host running the three Docker services, which satisfies the requested separation of frontend/backend/database containers.

For a real clinical deployment, use managed secrets, TLS, IAM, private networking, backups, monitoring, audit logging and institutional security controls.

## Safety / scope

This is a research prototype and clinical decision-support demonstration. It must not be presented as a validated diagnostic or treatment system. It does not diagnose Alzheimer's disease and does not recommend treatment.
