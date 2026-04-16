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
**Autonomous Multi-Agent LLM Debugger**

> Multi-agent AI systems fail 41–86% of the time (MAST paper, 1,600+ annotated traces).  
> Every existing tool tells you *what* failed. Nobody closes the loop.  
> **MAST-Autofix diagnoses, patches, and proves the fix worked — without human intervention.**

---

## What It Does

MAST-Autofix is a **7-agent LangGraph pipeline** that:

1. **Collects** execution traces from a broken LangGraph app
2. **Detects** failure signals (exceptions, timeouts, contract violations)
3. **Classifies** the failure using the MAST taxonomy (few-shot Claude prompting)
4. **Critiques** the architecture — points to the exact broken node/edge
5. **Patches** the code — generates a unified diff
6. **Benchmarks** original vs patched graph on 15 tasks
7. **Reports** a full Autopsy & Fix report with before/after metrics

---

## The Gap It Fills

| Tool | Traces | Classifies Failure | Generates Patch | Proves Fix |
|------|--------|-------------------|-----------------|------------|
| LangSmith | ✅ | ❌ | ❌ | ❌ |
| Langfuse | ✅ | ❌ | ❌ | ❌ |
| AgentOps | ✅ | ❌ | ❌ | ❌ |
| **MAST-Autofix** | ✅ | ✅ | ✅ | ✅ |

---

## MAST Failure Modes Implemented

| Mode | Name | Signal |
|------|------|--------|
| FM-1.1 | Disobey Task Specification | Agent ignores part of compound task |
| FM-2.3 | Conversation Reset | Agent loses context mid-run |
| FM-3.2 | Incomplete Verification | Reviewer approves without checking |

---

## Demo Results (15-task benchmark)

| Metric | Before Patch | After Patch | Delta |
|--------|-------------|------------|-------|
| Task Success Rate | 60% | 87% | **+27%** |
| Avg Steps / Task | 15.2 | 9.1 | **-6.1** |
| Avg Token Cost | 312 | 238 | **-23.7%** |

---

## Tech Stack

- **Orchestration:** LangGraph + LangChain
- **LLM:** Claude Sonnet (Anthropic API) — classification + patch synthesis
- **UI:** Gradio (3-panel: trace → diagnosis → diff + metrics)
- **Deploy:** HuggingFace Spaces + Docker
- **Tracing:** LangSmith

---

## Local Setup

```bash
git clone https://github.com/yxshas565/mast-autofix
cd mast-autofix
pip install -r requirements.txt
cp .env.example .env  # add your ANTHROPIC_API_KEY
python app.py
```

---

## Architecture

```
broken LangGraph app
        ↓
[Agent 1] Trace Collector  →  RunTrace
[Agent 2] Failure Detector →  FailureWindow
[Agent 3] MAST Classifier  →  MASTClassification  (Claude few-shot)
[Agent 4] Design Critic    →  DesignCritique
[Agent 5] Patch Synthesizer→  Patch (unified diff)
[Agent 6] Evaluator        →  BenchmarkResult (before + after)
[Agent 7] Reporter         →  AutopsyReport + Markdown
```

---

*Built for Orion Build Challenge 2026 — github.com/yxshas565*