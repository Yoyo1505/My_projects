# Applied Mathematics Portfolio: Finance, AI, and Quantum Computing

**Author**: Applied Mathematician  
**Repository**: Portfolio Projects 2026  
**License**: MIT

---

## 🎯 Overview

This repository showcases rigorous implementations of cutting-edge algorithms across four domains:

1. **Quantitative Trading** - Optimal execution, portfolio optimization, derivatives pricing
2. **Data Science** - Bayesian nonparametrics, causal inference, compressed sensing
3. **AI Engineering** - RAG systems, multi-agent coordination, fine-tuning
4. **Quantum Computing** - VQE, QAOA, error correction

Each project is **theory-driven**, **production-quality**, and includes full implementations.

---

## 📁 Project Structure

```
├── 00_INDEX_ALL_PROJECTS.md                  # Master project index
├── 01_RESEARCH_FOUNDATIONS.md                # Deep theory & quotes
├── README.md                                  # This file
│
├── SECTION_1_TRADING/
│   ├── README.md
│   ├── 02_Trading_Optimal_Execution.ipynb
│   ├── 04_Trading_PortfolioOptimization.ipynb
│   └── 05_Trading_HestonVolatility.ipynb
│
├── SECTION_2_DATA_SCIENCE/
│   ├── README.md
│   ├── 03_DataScience_BayesianNonparametrics.ipynb
│   └── [More notebooks - generate with agy]
│
├── SECTION_3_AI_ENGINEERING/
│   ├── README.md
│   └── [Notebooks to be generated with agy]
│
└── SECTION_4_QUANTUM/
    ├── README.md
    └── [Notebooks to be generated with agy]
```

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install numpy scipy pandas matplotlib scikit-learn jupyter

# Run a notebook
cd SECTION_1_TRADING
jupyter notebook 02_Trading_Optimal_Execution.ipynb
```

---

## 📊 Status

✅ **Complete**:
- Section 1: All 3 trading projects (500+ lines)
- Section 2: 1 data science project (400+ lines)
- All section READMEs and theory foundations

🔄 **Next (Use agy CLI)**:
```bash
agy generate notebook --section 2 --count 2
agy generate notebook --section 3 --count 3
agy generate notebook --section 4 --count 3
```

---

## 📚 Projects Overview

| Section | Projects | Status | Time |
|---------|----------|--------|------|
| **Trading** | Optimal Execution, Portfolio Opt., Heston | ✅ | 14-19h |
| **Data Science** | DPM, Causal Inference, Compressed Sensing | 🔄 | 14-19h |
| **AI Engineering** | RAG, Multi-Agent, LoRA | 🔄 | 14-18h |
| **Quantum** | VQE, QAOA, Error Correction | 🔄 | 18-24h |

**Total**: ~75-100 hours of rigorous applied mathematics

---

## 🎓 Learning Paths

**Finance**: Section 1 → DS → AI  
**ML/AI**: Section 2 → Section 3 → Trading (bridge)  
**Quantum**: Section 4 (all) → optional: Trading bridge  
**Complete**: All sections, all projects

---

## 💡 Key Features

✅ Theory-driven with Nobel Prize context  
✅ Production-quality implementations  
✅ Complete code + visualizations  
✅ Reproducible with realistic data  
✅ Clear extension paths  

---

## 📖 Start Here

1. Read `01_RESEARCH_FOUNDATIONS.md` (theory + context)
2. Pick a section README based on your interests
3. Run a notebook end-to-end
4. Explore, modify, experiment

---

**Last Updated**: August 2026  
**Status**: v1.0 core projects complete; expanding with agy CLI
