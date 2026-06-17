from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date
from statistics import mean
from typing import Any


STANDARD = "SY/T 5945-2004 测井解释报告编写规范"

LITHOLOGY_ZH = {
    "mudstone": "泥岩",
    "siltstone": "粉砂岩",
    "fine_sandstone": "细砂岩",
    "medium_sandstone": "中砂岩",
}

FLUID_ZH = {
    "oil": "油层",
    "water": "水层",
    "oil_bearing_water": "含油水层",
    "dry": "干层",
}


@dataclass
class ReportMetadata:
    well_id: str
    report_name: str = "测井解释报告"
    standard: str = STANDARD
    oilfield: str | None = None
    block: str | None = None
    well_type: str | None = None
    operator: str | None = None
    contractor: str | None = None
    target_interval: str | None = None
    logging_date: str | None = None
    report_date: str = field(default_factory=lambda: date.today().isoformat())
    interpreter: str | None = None
    reviewer: str | None = None
    approver: str | None = None
    coordinate_system: str | None = None
    datum: str | None = None
    remarks: str | None = None

    @classmethod
    def from_dict(cls, well_id: str, value: dict[str, Any] | None = None) -> "ReportMetadata":
        allowed = cls.__dataclass_fields__
        supplied = {key: item for key, item in (value or {}).items() if key in allowed and key != "well_id"}
        return cls(well_id=well_id, **supplied)

    def missing_fields(self) -> list[str]:
        required = ("oilfield", "well_type", "operator", "contractor", "target_interval", "interpreter", "reviewer")
        return [name for name in required if not getattr(self, name)]


def _number(row: dict[str, Any], *names: str) -> float | None:
    for name in names:
        value = row.get(name)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _average(rows: list[dict[str, Any]], *names: str) -> float | None:
    values = [value for row in rows if (value := _number(row, *names)) is not None]
    return mean(values) if values else None


def _fmt(value: float | None, precision: int = 3, suffix: str = "") -> str:
    return "未提供" if value is None else f"{value:.{precision}f}{suffix}"


def _layers(records: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    layers: list[list[dict[str, Any]]] = []
    for row in sorted(records, key=lambda item: float(item["DEPTH"])):
        key = (row.get("LITHOLOGY"), row.get("FLUID"))
        last_key = None if not layers else (layers[-1][-1].get("LITHOLOGY"), layers[-1][-1].get("FLUID"))
        if key != last_key:
            layers.append([row])
        else:
            layers[-1].append(row)
    return layers


def _quality_summary(events: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for event in events:
        result = event.get("result", {})
        metrics = result.get("metrics", {})
        abnormalities = result.get("abnormalities", [])
        lines.append(
            f"- {event.get('task_name', event.get('task_id', '未命名步骤'))}: "
            f"状态={result.get('status', 'unknown')}；指标={metrics or '无'}；"
            f"异常={abnormalities or '无'}。"
        )
    return lines or ["- 未提供处理过程记录。"]


def _layer_table(records: list[dict[str, Any]]) -> list[str]:
    lines = [
        "|序号|顶深/m|底深/m|厚度/m|岩性|流体解释|GR/API|RT/(Ω·m)|泥质含量/%|孔隙度/%|含水饱和度/%|",
        "|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for index, layer in enumerate(_layers(records), 1):
        top = float(layer[0]["DEPTH"])
        bottom = float(layer[-1]["DEPTH"])
        sample_step = 0.0 if len(layer) < 2 else abs(float(layer[1]["DEPTH"]) - top)
        thickness = bottom - top + sample_step
        lines.append(
            f"|{index}|{top:.3f}|{bottom:.3f}|{thickness:.3f}|"
            f"{LITHOLOGY_ZH.get(str(layer[0].get('LITHOLOGY')), str(layer[0].get('LITHOLOGY', '未定')))}|"
            f"{FLUID_ZH.get(str(layer[0].get('FLUID')), str(layer[0].get('FLUID', '未定')))}|"
            f"{_fmt(_average(layer, 'GR'), 2)}|{_fmt(_average(layer, 'RT', 'RDEP'), 2)}|"
            f"{_fmt(None if (v := _average(layer, 'VSH')) is None else v * 100, 2)}|"
            f"{_fmt(None if (v := _average(layer, 'PHIF')) is None else v * 100, 2)}|"
            f"{_fmt(None if (v := _average(layer, 'SW')) is None else v * 100, 2)}|"
        )
    return lines


def build_report(
    well_id: str,
    records: list[dict[str, Any]],
    events: list[dict[str, Any]],
    metadata: dict[str, Any] | ReportMetadata | None = None,
) -> dict[str, Any]:
    if not records:
        raise ValueError("Cannot generate an interpretation report without records")
    meta = metadata if isinstance(metadata, ReportMetadata) else ReportMetadata.from_dict(well_id, metadata)
    missing = meta.missing_fields()
    depths = [float(row["DEPTH"]) for row in records]
    lithology_counts = Counter(LITHOLOGY_ZH.get(str(row.get("LITHOLOGY")), "未定") for row in records)
    fluid_counts = Counter(FLUID_ZH.get(str(row.get("FLUID")), "未定") for row in records)

    lines = [
        f"# {meta.well_id}井{meta.report_name}",
        "",
        f"> 编制依据：{meta.standard}",
        f"> 报告状态：{'资料待补充' if missing else '完整性校验通过'}",
        "",
        "## 1 基本信息",
        "",
        "|项目|内容|",
        "|---|---|",
        f"|井号|{meta.well_id}|",
        f"|油气田/区块|{meta.oilfield or '待补充'} / {meta.block or '待补充'}|",
        f"|井别|{meta.well_type or '待补充'}|",
        f"|作业者|{meta.operator or '待补充'}|",
        f"|测井施工单位|{meta.contractor or '待补充'}|",
        f"|目的层/解释井段|{meta.target_interval or '待补充'}|",
        f"|测井日期|{meta.logging_date or '待补充'}|",
        f"|报告日期|{meta.report_date}|",
        f"|编写/审核/批准|{meta.interpreter or '待补充'} / {meta.reviewer or '待补充'} / {meta.approver or '待补充'}|",
        "",
        "## 2 资料概况与质量评价",
        "",
        f"- 解释数据点数：{len(records)}。",
        f"- 数据深度范围：{min(depths):.3f}-{max(depths):.3f} m。",
        f"- 坐标系统/高程基准：{meta.coordinate_system or '待补充'} / {meta.datum or '待补充'}。",
        *_quality_summary(events),
        "",
        "## 3 资料处理与解释方法",
        "",
        "- 数据处理包括曲线有效范围检查、异常值处理、缺失段补全及深度顺序检查。",
        "- 岩性、储层参数和流体解释结果由已记录的小模型或规则组件产生。",
        "- 泥质含量、孔隙度和含水饱和度按无量纲小数计算，在成果表中换算为百分数。",
        "- 所有处理步骤、指标、异常和调度决策均保存在同次运行的审计记录中。",
        "",
        "## 4 解释成果",
        "",
        *_layer_table(records),
        "",
        "## 5 综合评价与结论",
        "",
        f"- 岩性样点分布：{dict(lithology_counts)}。",
        f"- 流体解释样点分布：{dict(fluid_counts)}。",
        "- 本报告中的定量结论仅适用于本次输入资料与所采用解释模型；关键层段应结合录井、测试及取心资料复核。",
        "",
        "## 6 建议",
        "",
        "- 对资料缺失、质量异常或物性边界附近层段进行人工复核。",
        "- 利用岩心分析、试油试气及邻井资料标定解释模型和流体识别结论。",
        "- 资料或模型更新后重新生成报告，并保留版本与审计记录。",
        "",
        "## 7 附件及成果文件",
        "",
        "- 解释层成果表：本报告第 4 章。",
        "- 测井处理与解释审计记录：`run.json`。",
        "- 数字化解释结果：`run.json` 中的 `records`。",
        "",
        "## 完整性检查",
        "",
        f"- 待补充必填项：{', '.join(missing) if missing else '无'}。",
        f"- 备注：{meta.remarks or '无'}。",
    ]
    return {
        "standard": meta.standard,
        "metadata": asdict(meta),
        "missing_required_fields": missing,
        "sections": ["基本信息", "资料概况与质量评价", "资料处理与解释方法", "解释成果", "综合评价与结论", "建议", "附件及成果文件"],
        "markdown": "\n".join(lines) + "\n",
    }


def generate_report(
    well_id: str,
    records: list[dict[str, Any]],
    events: list[dict[str, Any]],
    metadata: dict[str, Any] | ReportMetadata | None = None,
) -> str:
    return build_report(well_id, records, events, metadata)["markdown"]
