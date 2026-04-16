# 🚀 MAST: Multi-Agent System for Map Quality Assurance

## Overview
MAST is an AI-powered multi-agent system designed to validate and analyze geospatial data. It combines rule-based validation, machine learning anomaly detection, and contextual reasoning to ensure high-quality map data.

## Features
- Geometry validation
- ML-based anomaly detection
- Context-aware reasoning
- PASS / WARNING / FAIL classification
- Explainable outputs

## Architecture
Multi-stage pipeline:
1. Rule-based validation
2. Feature extraction
3. ML anomaly detection
4. Contextual reasoning
5. Decision fusion
6. Explanation generation

## Tech Stack
Python, PyTorch, Scikit-learn, GeoPandas, FastAPI

## Setup

```bash
git clone https://github.com/your-username/MAST-map-quality-ai.git
cd MAST-map-quality-ai
pip install -r requirements.txt
python main.py

agents/
core/
utils/
ui/
demo_app/