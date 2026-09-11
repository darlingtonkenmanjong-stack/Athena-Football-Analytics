# ⚽ Athena — Real-Time Football Analytics & Decision-Support Platform

Athena is an AI-driven football analytics platform developed as part of an MSc Data Science project. It combines historical player performance, live match events, machine learning, spatial context, and real-time stream processing to assess player performance during a match and provide explainable tactical decision support.

The system integrates **StatsBomb Open Data**, **StatsBomb 360**, **Apache Kafka**, **Apache Spark Structured Streaming**, **machine learning**, and **Streamlit** into an end-to-end football analytics pipeline.

> Athena is designed as an advisory decision-support system. Its outputs support human interpretation and are not intended to replace coaches, analysts, or domain experts.

---

## 🎯 Project Objectives

Athena was developed to investigate how real-time football data can be combined with historical player information and machine learning to:

- Compare live player performance with pre-match expectations.
- Forecast second-half player performance from first-half observations.
- Evaluate pass difficulty using expected pass completion (**xPass**).
- Incorporate StatsBomb 360 spatial information into event analysis.
- Identify meaningful changes in player performance during a match.
- Generate persistent and explainable player alerts.
- Translate analytical evidence into tactical decision-support outputs.
- Deliver results through a live interactive dashboard.

---

## 🏗️ System Architecture

Athena uses the following real-time architecture:

```text
StatsBomb Events + StatsBomb 360
                │
                ▼
        Python Event Producer
        (kafka_producer.py)
                │
                ▼
         Apache Kafka
        football-events
                │
                ▼
 Apache Spark Structured Streaming
       (spark_streaming.py)
                │
                ▼
         Apache Kafka
       football-processed
                │
                ▼
      ML / Inference Engine
       (model_inference.py)
                │
        ┌───────┴────────┐
        ▼                ▼
 Player Assessment   Decision Support
 & Forecasting       & Alert Engine
        │                │
        └───────┬────────┘
                ▼
    live_dashboard_state.json
                │
                ▼
       Streamlit Dashboard
          (dashboard.py)
```

This architecture separates event ingestion, stream processing, machine-learning inference, decision support, and presentation.

---

## 🧠 Machine Learning & Analytics

Athena contains several analytical components.

### Player Performance Forecasting

Historical player-match data is used to construct pre-match baselines. First-half match observations are then compared with historical expectations to forecast second-half performance.

Example performance indicators include:

- Pass completion rate
- Progressive passes
- Actions per 90
- Miscontrols
- Expected goals (xG)

The forecasting workflow includes validation, held-out testing, residual analysis, regression-to-the-mean analysis, and ablation experiments.

### Expected Pass Completion — xPass

Athena estimates the probability that an attempted pass should be successfully completed.

The xPass analysis combines event-level information with spatial features derived from StatsBomb 360 where available. This allows the system to distinguish between raw pass completion and the difficulty/context of the attempted pass.

### StatsBomb 360 Spatial Context

360 freeze-frame information provides contextual information about players surrounding an event.

Derived spatial features include information such as:

- Player and opponent locations
- Distance to the nearest opponent
- Pressure/context around passes and shots
- Spatial relationships at the moment of an event

This allows Athena to move beyond purely event-based football statistics.

---

## ⚡ Real-Time Processing

Athena implements a replay-based real-time pipeline using **Apache Kafka** and **Apache Spark Structured Streaming**.

During system validation, the pipeline successfully processed a complete development match containing:

- **4,160 match events**
- **4,160 events processed end-to-end**
- **0 event loss**
- **1,150 xPass predictions**
- **32 players tracked during live processing**

Kafka provides the event-streaming layer, while Spark performs structured real-time processing before events reach the inference and dashboard components.

---

## 📊 Half-Time Forecasting

At half-time, Athena creates player-specific forecasts for eligible players by combining:

```text
Historical Pre-Match Baseline
            +
Observed First-Half Performance
            ↓
Machine-Learning Forecast
            ↓
Expected Second-Half Performance
```

In the final system replay, Athena produced half-time forecasts for **22 eligible players**.

The forecasts are used as evidence within the wider player assessment and decision-support system rather than being treated as isolated predictions.

---

## 🚨 Explainable Decision Support

Athena converts analytical outputs into human-readable decision-support information.

The decision engine considers evidence such as:

- Live performance relative to historical expectations
- Model forecasts
- Player exposure/minutes
- Match events
- Passing performance
- Spatial context
- Performance deterioration or improvement
- Match-state information

The final validated replay generated **seven traceable AI decision-support outputs**.

Recommendations are evidence-based and explainable rather than presented as guaranteed or mathematically optimal coaching decisions.

---

## 🖥️ Live Dashboard

The Streamlit dashboard provides a live view of the state of the match and the analytics generated by Athena.

The dashboard can display:

- Match clock and period
- Event-processing progress
- Player assessments
- Pre-match versus live performance
- Half-time forecasts
- Active alerts
- Tactical decision-support information
- System/match stage
- Processing completion status

A dedicated state-management layer connects the inference pipeline to the dashboard:

```text
Kafka
  ↓
Spark
  ↓
model_inference.py
  ↓
live_dashboard_state.py
  ↓
live_dashboard_state.json
  ↓
Streamlit
```

---

## 📁 Repository Structure

```text
Athena-Football-Analytics/
│
├── 01_Data_Understanding.ipynb
├── 02_Data_Preparation.ipynb
├── 03_Feature_Engineering.ipynb
├── 04_Modelling.ipynb
├── 05_Evaluation_and_Visualisation.ipynb
├── 06_Real_Time_Pipeline.ipynb
├── 07_Dashboard_System_Integration.ipynb
│
├── kafka_producer.py
├── spark_streaming.py
├── model_inference.py
├── ai_decision_engine.py
├── live_dashboard_state.py
├── dashboard.py
│
├── *.csv                     # Selected evaluation/system outputs
├── *.png                     # Model evaluation visualisations
├── .gitignore
└── README.md
```

Large intermediate datasets, serialized model artefacts, runtime state files, and the local StatsBomb Open Data repository are excluded from version control.

---

## 🔬 Development Methodology

The project follows the **CRISP-DM** data science methodology:

1. Business Understanding
2. Data Understanding
3. Data Preparation
4. Modelling
5. Evaluation
6. Deployment / System Integration

The numbered notebooks document the progression from raw football data exploration through feature engineering, modelling, evaluation, real-time streaming, and dashboard integration.

---

## 🛠️ Technology Stack

**Programming & Analysis**

- Python
- Pandas
- NumPy
- Jupyter Notebook

**Machine Learning**

- Scikit-learn
- Tree-based machine-learning methods
- Classification and regression modelling

**Real-Time Data Engineering**

- Apache Kafka
- Apache Spark
- Spark Structured Streaming

**Visualisation & Application**

- Streamlit
- Matplotlib

**Data**

- StatsBomb Open Data
- StatsBomb 360

**Development & Version Control**

- Visual Studio Code
- Git
- GitHub

---

## 📈 Evaluation

Athena evaluates models and system behaviour using several forms of evidence, including:

- Held-out model testing
- Validation-versus-test comparisons
- R² analysis for forecasting targets
- Classification discrimination metrics
- Calibration analysis
- Residual analysis
- Ablation experiments
- Regression-to-the-mean analysis
- End-to-end event-count validation

Selected evaluation results and visualisations are included in this repository.

---

## ⚠️ Limitations

Athena is a research prototype rather than a production football-club system.

Important limitations include:

- The real-time environment is simulated through historical match replay.
- StatsBomb 360 information is available only for selected events/matches.
- Model performance depends on the quantity and representativeness of historical data.
- Tactical recommendations are decision-support outputs rather than causal claims.
- The system does not claim to identify an objectively optimal substitution or tactical action.
- Production deployment would require additional scalability, monitoring, security, testing, and live-data integration.

---

## 🔮 Future Development

Potential extensions include:

- Integration with genuine live event feeds
- Player tracking and wearable data
- Expanded spatial and pressure modelling
- Temporal and graph-based machine-learning approaches
- Larger multi-league training datasets
- Automated model monitoring and retraining
- Cloud deployment
- Enhanced tactical recommendation evaluation
- Club-specific player and tactical baselines

---

## 📚 Data Attribution

This project uses **StatsBomb Open Data** and **StatsBomb 360 data** made available for football analytics research.

StatsBomb should be credited when publishing or sharing analysis based on its open data.

The original data is not redistributed through this repository. Users should obtain the open dataset directly from StatsBomb's official Open Data repository and comply with its applicable terms and attribution requirements.

---

## 👤 Author

**Darlington Ken**  
MSc Data Science  
Manchester Metropolitan University

Project: **Athena — Real-Time Football Analytics & Decision-Support Platform**

---

## 📌 Project Status

**MSc Data Science research prototype — completed and validated through full-match replay.**