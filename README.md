# 🚀 MAST: Multi-Agent System for Map Quality Assurance

> ⚡ An AI-powered multi-agent pipeline to detect, analyze, and explain geospatial data inconsistencies with high accuracy and interpretability.

---

## 🌍 Problem Statement

Geospatial data underpins critical systems such as navigation, logistics, and urban planning.  
However, ensuring **data quality at scale** remains a significant challenge due to:

- Geometry inconsistencies  
- Missing or incorrect attributes  
- Structural anomalies  
- Limited explainability in existing validation systems  

Current approaches are either:
- **Rule-based** → deterministic but rigid  
- **ML-based** → flexible but often opaque  

---

## 💡 Our Approach

**MAST (Multi-Agent System for Map Quality Assurance)** introduces a hybrid architecture that combines:

- Deterministic rule-based validation  
- Machine learning–driven anomaly detection  
- Context-aware reasoning  

This enables **accurate, scalable, and explainable validation** of geospatial data.

---

## 🧠 System Architecture

```text
Input Map Data
      ↓
[1] Geometry Validation Agent
      ↓
[2] Feature Extraction Agent
      ↓
[3] ML Anomaly Detection Agent
      ↓
[4] Contextual Reasoning Agent
      ↓
[5] Decision Fusion Engine
      ↓
[6] Explanation Generator
      ↓
Final Output → PASS / WARNING / FAIL + Explanation
```

---

⚙️ Key Features
- Multi-agent pipeline architecture
- Hybrid validation (Rule-based + ML)
- Context-aware decision making
- Explainable outputs (non–black box)
- Modular and scalable system design

---


📊 Sample 
```text
  {
    "feature_id": "road_1023",
    "status": "WARNING",
    "issues": [
      "Geometry misalignment detected",
      "Missing attribute: road_type"
    ],
    "confidence_score": 0.87,
    "explanation": "The road segment shows deviation from expected alignment and lacks critical metadata."
  }
```
---


🏗️ Tech Stack

| Layer            | Technologies Used     |
| ---------------- | --------------------- |
| Language         | Python                |
| Machine Learning | Scikit-learn, PyTorch |
| Geospatial       | GeoPandas, Shapely    |
| Backend          | FastAPI               |
| AI Integration   | OpenAI APIs           |
| Deployment       | Docker                |

---


📂 Project Structure

```text
MAST/
├── agents/        # Agent-specific logic
├── core/          # Pipeline orchestration
├── utils/         # Utility functions
├── demo_app/      # Demo interface
├── tests/         # Test cases
├── main.py        # Entry point
├── Dockerfile     # Containerization
├── requirements.txt
└── README.md
```

---


🚀 Getting Started

1. Clone the repository
git clone https://github.com/yxshas565/MAST-map-quality-ai.git
cd MAST-map-quality-ai

2. Install dependencies
pip install -r requirements.txt

3. Run the system
python main.py

---


🧪 How It Works
- Geospatial data is ingested into the pipeline
- Each agent independently evaluates different aspects of the data
- Outputs are aggregated via the decision fusion engine
- Final classification (PASS / WARNING / FAIL) is generated
- Explanation layer provides human-readable reasoning

---

⚠️ Challenges
- Balancing deterministic rules with probabilistic ML outputs
- Designing a modular multi-agent architecture
- Handling noisy and incomplete geospatial datasets
- Generating meaningful and interpretable explanations

---


🔮 Future Scope
- Real-time map validation APIs
- Advanced LLM-based explanation generation
- Interactive visualization dashboards
- Cloud-native scalable deployment

---

🤝 Contributors
Yashas Sadananda
