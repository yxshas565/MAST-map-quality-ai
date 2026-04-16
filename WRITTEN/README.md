---
title: MAST-Autofix
emoji: 🔬
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: "4.40.0"
app_file: app.py
pinned: true
---

# 🔬 MAST-Autofix  
### Autonomous Multi-Agent LLM Debugger

> Multi-agent AI systems fail **41–86% of the time** (MAST paper, 1,600+ annotated traces).  
> Existing tools surface failures — **they don’t fix them**.  
>  
> **MAST-Autofix closes the loop: diagnose → patch → validate.**

---

## 🧠 Overview

MAST-Autofix is a **7-agent autonomous debugging system** built on LangGraph that:

- Identifies failure patterns in agent workflows  
- Classifies them using the **MAST failure taxonomy**  
- Generates targeted patches (code-level fixes)  
- Validates improvements via benchmarking  
- Produces a complete **Autopsy & Fix Report**

---

## ⚙️ What It Does

The system executes a full debugging lifecycle:

1. **Trace Collection**  
   Captures execution traces from a failing LangGraph workflow  

2. **Failure Detection**  
   Identifies anomalies such as exceptions, timeouts, and contract violations  

3. **Failure Classification**  
   Uses few-shot prompting (Claude) to map failures to MAST taxonomy  

4. **Design Critique**  
   Pinpoints architectural weaknesses (node/edge-level issues)  

5. **Patch Generation**  
   Synthesizes a **unified diff** to fix the system  

6. **Evaluation & Benchmarking**  
   Compares original vs patched system across multiple tasks  

7. **Reporting**  
   Generates a structured **Autopsy Report** with metrics and explanations  

---

## 🧩 The Gap It Fills

| Tool        | Trace Analysis | Failure Classification | Patch Generation | Validation |
|------------|---------------|----------------------|------------------|------------|
| LangSmith  | ✅            | ❌                   | ❌               | ❌         |
| Langfuse   | ✅            | ❌                   | ❌               | ❌         |
| AgentOps   | ✅            | ❌                   | ❌               | ❌         |
| **MAST-Autofix** | ✅     | ✅                   | ✅               | ✅         |

> 🔥 Moves from *observability* → *autonomous debugging*

---

## 🧠 Failure Modes Implemented

| ID     | Failure Mode                  | Description |
|--------|------------------------------|-------------|
| FM-1.1 | Task Specification Failure   | Agent ignores parts of a compound task |
| FM-2.3 | Context Loss / Reset         | Agent loses memory mid-execution |
| FM-3.2 | Incomplete Verification      | Reviewer approves without validation |

---

## 📊 Benchmark Results (15 Tasks)

| Metric              | Before | After | Improvement |
|--------------------|--------|-------|-------------|
| Task Success Rate  | 60%    | 87%   | **+27%**    |
| Avg Steps / Task   | 15.2   | 9.1   | **-40%**    |
| Avg Token Cost     | 312    | 238   | **-23.7%**  |

---

## 🏗️ System Architecture

Broken LangGraph Application
↓
[1] Trace Collector → RunTrace
[2] Failure Detector → FailureWindow
[3] MAST Classifier → Classification (LLM-based)
[4] Design Critic → Architecture Analysis
[5] Patch Synthesizer → Code Diff (Fix)
[6] Evaluator → Benchmark Results
[7] Reporter → Autopsy Report


---

## 🛠️ Tech Stack

- **Orchestration:** LangGraph, LangChain  
- **LLM:** Claude Sonnet (Anthropic API)  
- **UI:** Gradio (3-panel interactive interface)  
- **Tracing:** LangSmith  
- **Deployment:** Hugging Face Spaces, Docker  

---

## 🚀 Local Setup

```bash
git clone https://github.com/yxshas565/mast-autofix
cd mast-autofix
pip install -r requirements.txt
cp .env.example .env  # Add your ANTHROPIC_API_KEY
python app.py
```

---

🧪 Key Capabilities
- Autonomous failure diagnosis
- Code-level patch generation
- Structured evaluation and benchmarking
- Explainable debugging via reports
- Modular multi-agent orchestration


---

⚠️ Challenges
- Mapping unstructured traces to structured failure taxonomy
- Generating safe and minimal code patches
- Designing reliable evaluation pipelines
- Balancing autonomy with correctness guarantees

---

🔮 Future Work
- Support for additional agent frameworks (CrewAI, AutoGen)
- Continuous self-improving debugging loops
- Production-grade monitoring + alerting
- Integration with CI/CD pipelines

---

👨‍💻 Author

Yashas Sadananda
Built for Orion Build Challenge 2026
