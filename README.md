
# SmartBPM

**Designing an AI-Augmented Business Process Management Platform**

Bachelor Thesis · Business Informatics · German International University (GIU)  
**Author:** Maryam Nasser Mosaad

## Description

SmartBPM is a Python-based research prototype that helps users explore historical business process event logs, investigate process performance, and examine predictive insights through an interactive web dashboard. It combines process mining, machine learning, and explainable AI (XAI) to support evidence-based process analysis.

The current implementation focuses on historical process analysis and predictive validation using the **BPI Challenge 2020 Domestic Declarations** event log. LLM-assisted improvement recommendations, human approval of interventions, baseline and improved-scenario simulation, and an optional AI investigation agent are **planned**, not currently implemented.

## Implemented Features

| Feature | Description |
| --- | --- |
| Data preparation | Import and validate XES event logs; audit timestamps and data quality; generate processed Parquet data. |
| Interactive dashboard | Explore cases, activities, resources, process durations, and individual case histories using filters and charts. |
| Process mining | Explore directly-follows relationships, interactive process maps, variants, transitions, and repeated activities. |
| Performance analysis | Investigate case-duration distributions, repetition patterns, and longer-running cases. |
| Predictive machine learning | Compare historical validation results for baseline models, Logistic Regression, Decision Tree, Random Forest, and Gradient Boosting. |
| Explainable AI | Inspect feature importance and case-level explanations for saved predictions. |
| Data export | Download supported analytical reports and results. |

**Prediction scope:** The model estimates whether a case's total observed duration exceeds a training-derived threshold, using information available after its second recorded event. The dashboard presents saved validation results; it is not a live prediction service for newly uploaded cases.

## Tech Stack

| Area | Technology |
| --- | --- |
| Programming language | Python 3.12 |
| Web application | Streamlit |
| Data processing | pandas, NumPy, PyArrow / Parquet |
| Process mining | PM4Py |
| Machine learning | scikit-learn |
| Explainability | Permutation importance and project-implemented Shapley explanations |
| Visualization | Plotly, Streamlit ECharts, Matplotlib |
| Testing | pytest, Streamlit AppTest |
| Data format | XES event log; generated Parquet, CSV, and JSON outputs |

## Launch SmartBPM

The following commands are for **Windows PowerShell**, run from the repository root. Python **3.12** and the Windows `py` launcher are required. The dataset and generated model artifacts are not included in a fresh clone.

### 1. Install dependencies

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Add and prepare the dataset

Place the original `DomesticDeclarations.xes` file in `data/raw/`, then run:

```powershell
New-Item -ItemType Directory -Force data/raw | Out-Null
.\.venv\Scripts\python.exe scripts/inspect_dataset.py
.\.venv\Scripts\python.exe scripts/run_day2.py --no-figures
```

The historical exploration dashboard can be started after this step. To enable the saved ML and XAI views on a fresh setup, also generate their artifacts in order:

```powershell
.\.venv\Scripts\python.exe scripts/run_day6.py
.\.venv\Scripts\python.exe scripts/prepare_ml_dataset.py
.\.venv\Scripts\python.exe scripts/run_day9_10.py
.\.venv\Scripts\python.exe scripts/run_day11_12.py
```

### 3. Start the application

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open **http://localhost:8501** in your browser, or use the address shown in the terminal. Press `Ctrl+C` to stop the server.

**Note:** The commands and features above are based on the supplied project README and have not been independently verified against the complete source repository. No API keys or environment variables are documented as required for the current application.
