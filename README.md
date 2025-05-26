# Unlocking the Microscopic Code: Deep Learning for Mitosis Detection in Ki-67 Histological Images

This repository contains the thesis project focused on developing an advanced deep learning system for the automatic detection and counting of mitotic figures in medical histological images, particularly those stained with Ki-67 — a key biomarker in cancer research (also exploring ER & PR cases and comparisons with H&E developments).

## 🔍 Objective
The goal is to build a robust pipeline for processing and analyzing histopathological images using deep learning, addressing complex challenges such as cell overlap, staining variability, imaging artifacts, and domain adaptation between public and hospital datasets. (Benchmark and other steps will be added on the analysis to conclude best options).

## 📆 Progress Log
- **April 1:** Official thesis kickoff. Introduction to the lab and project.
- **April 7:** Initial meetings. Definition of core challenges and research goals.
- **April 8–17:** Exploration of histology fundamentals, dataset analysis, and initial HPC setup.
- **April 21:** Dataset comparison report and evaluation of deep learning model baselines.
- **April 24:** Methodology consolidation and dataset issue tracking initiated.
- **May 1:** Exploration of the datasets.
_(See `/reports/` and commits for full details.)_

## 🧠 Key Topics Explored
- Medical image preprocessing (denoising, normalization, segmentation)
- CNN architectures for object detection and classification
- High-performance computing workflows (SLURM on HPC clusters)
- Domain shift and quality variance between public and hospital-provided data

## 🔗 External Resources
- Scientific literature on Ki-67 and mitotic activity in cancer diagnostics
- Public datasets used for benchmarking
- Technical documentation for cluster computing tools

## 🚀 Quick Start
```bash
# Clone the repository
git clone https://github.com/Efocor/ki67-mitosis-thesis.git
cd ki67-mitosis-thesis

# Install dependencies
pip install -r requirements.txt
