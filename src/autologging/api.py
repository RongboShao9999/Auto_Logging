from __future__ import annotations

from flask import Flask, jsonify, request

from .cloud import CloudConfigurationError, CloudSettings, EasOssGateway, MODEL_ROUTES
from .pipeline import AutoLogging
from .report import build_report

app = Flask(__name__)
system = AutoLogging()


@app.post("/interpret")
def interpret():
    payload = request.get_json(force=True)
    result = system.run(
        payload["well_id"],
        payload["records"],
        payload.get("request", "Complete full-process logging interpretation"),
        report_metadata=payload.get("report_metadata"),
    )
    return jsonify(result)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/models/catalog")
def models_catalog():
    return jsonify(system.model_catalog or {})


@app.post("/report/generate")
def report_generate():
    payload = request.get_json(force=True)
    try:
        package = build_report(
            payload["well_id"],
            payload["records"],
            payload.get("events", []),
            payload.get("report_metadata"),
        )
        return jsonify(package)
    except (KeyError, ValueError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


def _invoke_cloud(component: str):
    try:
        result = EasOssGateway(CloudSettings.from_env()).invoke(
            MODEL_ROUTES[component], request.get_json(force=True)
        )
        return jsonify(result)
    except (CloudConfigurationError, ValueError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        app.logger.exception("Cloud model invocation failed")
        return jsonify({"success": False, "error": "Cloud model invocation failed"}), 502


@app.post("/lstmfill")
def lstm_fill():
    return _invoke_cloud("imputation")


@app.post("/2DCNN_conclusion")
def lithology_predict():
    return _invoke_cloud("lithology")


@app.post("/Atten_multi_predict")
def parameters_predict():
    return _invoke_cloud("parameters")


@app.post("/knn_fluid_identify")
def fluid_identify():
    return _invoke_cloud("fluid")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
