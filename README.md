# Auto-Logging System

This repository produces the **system architecture and closed-loop behavior**
described in `science_template_auto_logging.pdf`:

- dependency-aware Planner grounded by a structured petrophysical knowledge base;
- Executor with a standardized component registry;
- quality control, preprocessing, missing-curve imputation, lithology,
  reservoir-parameter, fluid-identification, and report tools;
- physical validation, fallback behavior, expert-review flags, and a complete
  JSON audit trail;
- CLI and Flask-compatible HTTP API.

The repository can run in two modes. If bundled `model/`, `SPWLA_dataset/`, and
`forward_dataset/` assets are present, Auto-Logging detects them and preserves
their small-model outputs in the audit trail. If a runtime dependency is missing
or an input does not match a local model, the workflow falls back to deterministic,
physics-informed reference implementations.

## Quick start

```powershell
$env:PYTHONPATH="src"
python scripts/generate_demo.py
python -m autologging.cli run examples/demo_well.csv --well-id DEMO-01 --output runs/demo --report-metadata examples/report_metadata.json
python -m unittest discover -s tests -v
```

### Bundled models and datasets

The dataset loader normalizes SPWLA columns such as `DTC`, `CALI`, `NEU`,
`RDEP`, and `RMED` to internal curve names, converts `-9999` to missing values,
and converts forward-simulation percentage parameters to fractions.

```powershell
$env:PYTHONPATH="src"
python -m autologging.cli run forward_dataset/data_test_18.csv --well-id FORWARD-18 --limit 200 --output runs/forward-demo
python -m autologging.cli run SPWLA_dataset/test.csv --well-id SPWLA-100 --well 100 --limit 200 --output runs/spwla-demo
```

Forward-simulation files that contain `lithology_CNN`, `Vsh_multi`,
`POR_multi`, `Sw_multi`, and `Fluid_KNN` are treated as bundled small-model
outputs. TensorFlow SavedModel assets are listed in the model catalog, but
executing them requires a TensorFlow runtime. Use `--reference-only` to disable
local assets.

The report generator follows a structured implementation of
`SY/T 5945-2004 测井解释报告编写规范`. The final report is written to
`runs/demo/report.md`; `report.json` records standard/version, required-field
completeness, metadata, and sections. `run.json` contains the plan, every
invocation, validation result, fallback, and final records.

## HTTP API

The core workflow has no third-party dependency. The paper-compatible HTTP
deployment layer is optional; install Flask, then run:

```powershell
$env:PYTHONPATH="src"
python -m autologging.api
```

`POST /interpret` accepts:

```json
{
  "well_id": "A123",
  "request": "Complete full-process logging interpretation",
  "records": [{"DEPTH": 2500.0, "GR": 80, "AC": 260, "DEN": 2.35, "CNL": 0.2, "RT": 20}]
}
```

`GET /models/catalog` returns the detected local model assets and whether the
current Python runtime can load sklearn or TensorFlow components.

### Alibaba Cloud small-model routes

The Flask app has the routing pattern found in the provided example:

| Route | Small model | Expected outputs |
|---|---|---|
| `POST /lstmfill` | LSTM missing-curve imputation | `IMPUTED` |
| `POST /2DCNN_conclusion` | 2D-CNN lithology classification | `LITHOLOGY`, `CONFIDENCE` |
| `POST /Atten_multi_predict` | Multi-task reservoir parameters | `PHIF`, `SW`, `VSH` |
| `POST /knn_fluid_identify` | KNN fluid identification | `FLUID`, `CONFIDENCE` |

Cloud routes read credentials only from environment variables. Configure the
variables documented in `.env.example`; do not put access keys in source code.
Each request accepts `data`, `well`, and either the legacy service-name field
shown in the route table or the common `model_name` field. Successful requests
return the OSS key of the generated CSV.

```json
{
  "model_name": "logging-parameter-service",
  "data": "inputs/well.csv",
  "well": 1
}
```

### Standards-based report tool

`POST /report/generate` generates a report independently from interpreted
records. It returns Markdown plus a machine-readable completeness result.

```json
{
  "well_id": "A123",
  "records": [{"DEPTH": 2500, "LITHOLOGY": "fine_sandstone", "FLUID": "oil", "VSH": 0.2, "PHIF": 0.18, "SW": 0.35}],
  "events": [],
  "report_metadata": {
    "oilfield": "XX油田",
    "well_type": "评价井",
    "operator": "作业单位",
    "contractor": "测井单位",
    "target_interval": "2500-2600 m",
    "interpreter": "编写人",
    "reviewer": "审核人"
  }
}
```

The implementation follows the standard's report-oriented structure while
marking unavailable source data as `待补充`. A licensed copy of the complete
standard should be used for final organizational acceptance review.

## Paper-to-code map

| Paper component | Implementation |
|---|---|
| Planner + RAG | `src/autologging/planner.py`, `knowledge/rules.json` |
| Executor + feedback | `src/autologging/executor.py` |
| Model/tool library | `src/autologging/tools.py` |
| Closed-loop workflow | `src/autologging/pipeline.py` |
| Standardized Flask interface | `src/autologging/api.py` |
| Traceable report | `src/autologging/report.py` |
