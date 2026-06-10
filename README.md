# Auto_Logging
Reproducibility Package for Auto-Logging: Domain-grounded LLM Agents for Physics-Constrained Scientific Workflow Orchestration
## 1. Overview
This code repository hosts all essential resources to reproduce the Auto-Logging system proposed in the manuscript Domain-grounded LLM agents for reliable orchestration of physics-constrained scientific workflows. The provided assets cover trained machine learning models, experimental datasets, and service deployment scripts, which work together with the prompt engineering schemes described in the supplementary materials of the above paper to realize the full functions of the Auto-Logging framework for automated well log interpretation.
This repository mainly focuses on the deployment and invocation of domain-specific lightweight models and functional tools for well log interpretation. All pre-trained model weights are fully released, and integrated Flask service files are provided to implement unified management, scheduling and invocation of all functional modules and computing tools.
## 2. Repository Contents
The repository is organized into three core categories of resources, detailed as follows:
### 2.1 Pre-trained Model Weights
All released files are well-trained weight files of lightweight machine learning models dedicated to well log interpretation, which serve as the core computational executors of the Auto-Logging system:
Models for logging curve imputation
Models for lithology classification
Models for reservoir parameter prediction
Models for fluid identification and reservoir potential evaluation
These models undertake professional numerical computation tasks throughout the entire log interpretation workflow.
### 2.2 Experimental Datasets
Two standard datasets adopted for system validation in our research are included:
SPWLA Competition Dataset: Real-world field logging data used for practical performance testing and evaluation.
Forward-modeled Logging Dataset: Synthetic logging data generated based on physical petrophysical mechanisms, applied for end-to-end functional verification and benchmark tests.
### 2.3 Flask Service Scripts
A complete set of Flask application files is provided. Based on the lightweight web service framework, these scripts enable centralized management of all embedded tools and models within the system, including service startup, component registration, unified interface invocation, task scheduling, and operational status monitoring. The Flask module standardizes the calling logic of each functional component and guarantees stable interaction between the LLM-based planner and underlying computing executors.
Important Security & Usage Notice
For security protection, the real access_key_id and access_key_secret for cloud service authentication are not displayed or filled in within the released Flask files.
The Flask scripts uploaded here are not the official production files deployed in the actual Auto-Logging system. They are only used to demonstrate standard file directory structures, path rules and encoding specifications for reference.
Users are allowed and recommended to modify, adjust and reconfigure the Flask source files independently according to their own deployment environment, service requirements and authentication rules during local construction and secondary development.
## 3. System Reproduction Instructions
To fully reproduce the Auto-Logging system and its workflow orchestration functions, please follow the requirements below:
Deploy the provided Flask services to load pre-trained model weights and activate all logging interpretation tools. Please supplement valid authentication credentials (access_key_id, access_key_secret) and adjust relevant configurations based on your actual environment.
Prepare experimental datasets and configure corresponding data loading paths in the service configuration files.
Adopt the prompt engineering strategies and rule settings documented in the Supplementary Materials of the paper Domain-grounded LLM agents for reliable orchestration of physics-constrained scientific workflows.
Connect the LLM-based Planner module with the Flask service interfaces to construct the complete dual-agent architecture, so as to realize autonomous, adaptive and closed-loop well log interpretation workflows.
## 4. Core Functions
Load and run pre-trained machine learning models for full-process well log interpretation.
Realize unified management, invocation and operation monitoring of multiple functional tools via Flask services.
Support end-to-end testing on both real SPWLA dataset and physically forward-modeled dataset.
Collaborate with LLM prompt engineering schemes to reproduce the agent-based scientific workflow orchestration mechanism of Auto-Logging.
## 5. Citation
If you use the resources in this repository for your research, please cite our original article: “Domain-grounded LLM agents for reliable orchestration of physics-constrained scientific workflows”
## 6. Contact & Declaration
For technical questions and problems during reproduction, please contact the corresponding author of the manuscript.
All resources in this repository are released for academic research purposes only.
