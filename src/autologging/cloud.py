from __future__ import annotations

import csv
import io
import math
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit


class CloudConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class CloudSettings:
    access_key_id: str
    access_key_secret: str
    bucket_name: str
    oss_endpoint: str = "https://oss-cn-shanghai.aliyuncs.com"
    region: str = "cn-shanghai"
    cluster_id: str = "cn-shanghai"
    output_prefix: str = "auto-logging/results"

    @classmethod
    def from_env(cls) -> "CloudSettings":
        required = {
            "access_key_id": "ALIBABA_CLOUD_ACCESS_KEY_ID",
            "access_key_secret": "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
            "bucket_name": "AUTO_LOGGING_OSS_BUCKET",
        }
        values = {field: os.getenv(env_name) for field, env_name in required.items()}
        missing = [env_name for field, env_name in required.items() if not values[field]]
        if missing:
            raise CloudConfigurationError(f"Missing environment variables: {', '.join(missing)}")
        return cls(
            **values,  # type: ignore[arg-type]
            oss_endpoint=os.getenv("AUTO_LOGGING_OSS_ENDPOINT", cls.oss_endpoint),
            region=os.getenv("AUTO_LOGGING_EAS_REGION", cls.region),
            cluster_id=os.getenv("AUTO_LOGGING_EAS_CLUSTER_ID", cls.cluster_id),
            output_prefix=os.getenv("AUTO_LOGGING_OUTPUT_PREFIX", cls.output_prefix),
        )


@dataclass(frozen=True)
class ModelRoute:
    component: str
    service_field: str
    features: tuple[str, ...]
    outputs: tuple[str, ...]
    route: str
    log_features: tuple[str, ...] = ()


MODEL_ROUTES = {
    "imputation": ModelRoute(
        "imputation",
        "LSTM_fill",
        ("CAL", "DEN", "RXO", "GR"),
        ("IMPUTED",),
        "/lstmfill",
    ),
    "lithology": ModelRoute(
        "lithology",
        "2DCNN_conclusion",
        ("AC", "CAL", "CNL", "DEN", "GR", "RT", "RXO", "SP"),
        ("LITHOLOGY", "CONFIDENCE"),
        "/2DCNN_conclusion",
        ("RT", "RXO"),
    ),
    "parameters": ModelRoute(
        "parameters",
        "Atten_multi_predict",
        ("DEN", "GR", "NEU", "PEF", "RDEP", "RMED"),
        ("PHIF", "SW", "VSH"),
        "/Atten_multi_predict",
        ("RDEP", "RMED"),
    ),
    "fluid": ModelRoute(
        "fluid",
        "KNN_fluid_identify",
        ("PHIF", "SW", "RT"),
        ("FLUID", "CONFIDENCE"),
        "/knn_fluid_identify",
        ("RT",),
    ),
}


def parse_csv_records(content: bytes, well: int | str) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig")
    records: list[dict[str, Any]] = []
    for row in csv.DictReader(io.StringIO(text)):
        if "WELLNUM" in row and str(row["WELLNUM"]) != str(well):
            continue
        parsed: dict[str, Any] = {}
        for key, value in row.items():
            if value in ("", "-9999", None):
                parsed[key] = None
            else:
                try:
                    parsed[key] = float(value)
                except ValueError:
                    parsed[key] = value
        records.append(parsed)
    if not records:
        raise ValueError(f"No records found for well {well}")
    return records


def prepare_matrix(records: list[dict[str, Any]], route: ModelRoute) -> list[float]:
    matrix: list[float] = []
    for index, row in enumerate(records):
        for feature in route.features:
            value = row.get(feature)
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError(f"Missing or invalid {feature} at row {index}")
            number = float(value)
            if feature in route.log_features:
                if number <= 0:
                    raise ValueError(f"{feature} must be positive for log10 transformation")
                number = math.log10(number)
            matrix.append(number)
    return matrix


def records_to_csv(records: list[dict[str, Any]]) -> bytes:
    if not records:
        return b""
    buffer = io.StringIO()
    fields = list(dict.fromkeys(key for row in records for key in row))
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue().encode("utf-8")


class EasOssGateway:
    """Lazy Alibaba Cloud adapter so the local workflow stays dependency-free."""

    def __init__(self, settings: CloudSettings):
        self.settings = settings

    def _clients(self):
        try:
            import oss2
            from alibabacloud_eas20210701.client import Client as EasClient
            from alibabacloud_tea_openapi import models as open_api_models
        except ImportError as exc:
            raise CloudConfigurationError(
                "Install the 'cloud' optional dependencies before using EAS/OSS routes"
            ) from exc
        auth = oss2.Auth(self.settings.access_key_id, self.settings.access_key_secret)
        bucket = oss2.Bucket(auth, self.settings.oss_endpoint, self.settings.bucket_name)
        config = open_api_models.Config(
            access_key_id=self.settings.access_key_id,
            access_key_secret=self.settings.access_key_secret,
            endpoint=f"pai-eas.{self.settings.region}.aliyuncs.com",
        )
        return bucket, EasClient(config)

    def invoke(self, route: ModelRoute, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            from eas_prediction import PredictClient, TFRequest
        except ImportError as exc:
            raise CloudConfigurationError("Install eas-prediction before invoking EAS models") from exc

        service_name = str(payload.get(route.service_field) or payload.get("model_name") or "").strip()
        object_key = str(payload.get("data") or "").strip()
        well = payload.get("well")
        if not service_name or not object_key or well is None:
            raise ValueError(f"Required fields: {route.service_field} (or model_name), data, well")

        bucket, eas_client = self._clients()
        records = parse_csv_records(bucket.get_object(object_key).read(), well)
        matrix = prepare_matrix(records, route)
        service = eas_client.describe_service(
            cluster_id=self.settings.cluster_id, service_name=service_name
        ).body
        hostname = urlsplit(service.internet_endpoint).hostname
        if not hostname:
            raise RuntimeError("EAS returned an invalid internet endpoint")
        client = PredictClient(hostname, service.service_name)
        client.set_token(service.access_token)
        client.init()

        request = TFRequest(str(payload.get("signature_name", "serving_default")))
        request.add_feed(
            str(payload.get("input_name", "input_1")),
            [len(records), len(route.features)],
            TFRequest.DT_FLOAT,
            matrix,
        )
        response = client.predict(request)
        output_records = [
            {"WELLNUM": row.get("WELLNUM", well), "DEPTH": row.get("DEPTH")} for row in records
        ]
        for output_name in route.outputs:
            tensor = response.response.outputs.get(output_name)
            if tensor is None:
                raise RuntimeError(f"EAS response is missing output tensor: {output_name}")
            values = list(tensor.float_val) or list(tensor.int64_val) or list(tensor.string_val)
            if len(values) != len(output_records):
                raise RuntimeError(f"Output {output_name} length does not match input records")
            for row, value in zip(output_records, values):
                row[output_name] = value.decode() if isinstance(value, bytes) else value

        output_key = f"{self.settings.output_prefix}/{well}/{route.component}.csv"
        bucket.put_object(output_key, records_to_csv(output_records))
        return {
            "success": True,
            "component": route.component,
            "service_name": service_name,
            "input_object": object_key,
            "output_object": output_key,
            "records": len(output_records),
        }

