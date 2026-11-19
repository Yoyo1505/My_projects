# Applied AI & Quantitative Portfolio

Applied AI engineering projects across GenAI, predictive ML, scientific simulation and quantitative finance. Every project folder follows the same README format: **Problem → Approach → Results → Run → Stack → Limits & security**.

**Target roles:** Forward Deployed Engineer · Applied AI Engineer

## Projects

| Project | Domain | Technique | Status |
|---|---|---|---|
| [Cashi RAG](Cashi%20RAG/) | GenAI / RAG | Hybrid retrieval, numeric engine, HTTP API, Streamlit + static demo | Live demo |
| [LLM Experiment](LLM%20Experiment/) | GenAI / agents | Multi-plane graph agent, router, verifier, evals, authorization tests | Done |
| [F1 Las Vegas Predictor](F1%20Las%20Vegas%20Predictor/) | Sports ML | LightGBM win probabilities, season-wise backtest | New |
| [NFL Moneyball](NFL%20Moneyball/) | Sports ML | EPA ridge model vs market, value over replacement | New |
| [Optogenetics Neuron Simulation](Optogenetics%20Neuron%20Simulation/) | Scientific simulation | Hodgkin–Huxley + ChR2 photocycle, ABC inference | New |
| [Financial Risk Analysis](Financial%20Risk%20Analysis/) | Quant finance | VaR/CVaR, EWMA Monte Carlo, Kupiec/Christoffersen backtests | Updated |
| [Loan Assessment System](Loan%20Assessment%20System/) | Credit risk | sklearn pipelines, classification + regression | Done |
| [Territory Dashboard](Territory%20Dashboard/) | Analytics app | Streamlit KPI dashboard | Done |
| [Quantitative Trading](Quantitative%20Trading/) | Valuation | Almgren–Chriss, Markowitz/Black–Litterman, Heston | Notebooks |
| [Data Science Methods](Data%20Science%20Methods/) | Statistics | Dirichlet process mixtures, double ML, compressed sensing | Notebooks |
| [AI Engineering](AI%20Engineering/) | GenAI foundations | RAG, multi-agent VCG, LoRA | Notebooks |
| [Quantum Algorithms](Quantum%20Algorithms/) | Quantum | VQE, QAOA, surface codes, Qiskit/PennyLane starters | Notebooks |

Background and ideas: [Research Notes](Research%20Notes/). Roadmap: [ROADMAP.md](ROADMAP.md). Security notes: [SECURITY.md](SECURITY.md).

## Quick start
```bash
git clone https://github.com/Yoyo1505/My_projects.git
cd My_projects/"F1 Las Vegas Predictor"
pip install -r requirements.txt && python predict.py
```

## Honest results
The sports models report backtests against real baselines. The NFL model does not beat the betting market and the F1 model's edge over "pole wins" is modest; both READMEs say so.
