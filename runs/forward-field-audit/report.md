# FORWARD-18井测井解释报告

> 编制依据：SY/T 5945-2004 测井解释报告编写规范
> 报告状态：资料待补充

## 1 基本信息

|项目|内容|
|---|---|
|井号|FORWARD-18|
|油气田/区块|待补充 / 待补充|
|井别|待补充|
|作业者|待补充|
|测井施工单位|待补充|
|目的层/解释井段|待补充|
|测井日期|待补充|
|报告日期|2026-06-17|
|编写/审核/批准|待补充 / 待补充 / 待补充|

## 2 资料概况与质量评价

- 解释数据点数：20。
- 数据深度范围：1500.000-1502.375 m。
- 坐标系统/高程基准：待补充 / 待补充。
- Data Quality Control: 状态=success；指标={'outlier_ratio': 0.0125, 'missing_values': 0, 'depth_monotonic': True}；异常=无。
- Data Preprocessing: 状态=success；指标={'outliers_removed': 2, 'sporadic_values_filled': 2}；异常=无。
- Extended Missing-Curve Imputation: 状态=success；指标={'skipped': True, 'reason': 'no extended missing intervals'}；异常=无。
- Lithology Identification: 状态=success；指标={'class_counts': {'mudstone': 20}, 'model': 'bundled-forward-dataset-labels', 'source_records': 20}；异常=无。
- Reservoir Parameter Prediction: 状态=success；指标={'model': 'bundled-dataset-reservoir-parameters', 'source_records': 20}；异常=无。
- Fluid Identification: 状态=success；指标={'class_counts': {'non_reservoir': 20}, 'model': 'bundled-forward-dataset-fluid-labels', 'source_records': 20}；异常=无。
- Interpretation Report: 状态=success；指标=无；异常=无。

## 3 资料处理与解释方法

- 数据处理包括曲线有效范围检查、异常值处理、缺失段补全及深度顺序检查。
- 岩性、储层参数和流体解释结果由已记录的小模型或规则组件产生。
- 泥质含量、孔隙度和含水饱和度按无量纲小数计算，在成果表中换算为百分数。
- 所有处理步骤、指标、异常和调度决策均保存在同次运行的审计记录中。

## 4 解释成果

|序号|顶深/m|底深/m|厚度/m|岩性|流体解释|GR/API|RT/(Ω·m)|泥质含量/%|孔隙度/%|含水饱和度/%|
|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---:|
|1|1500.000|1502.375|2.500|泥岩|non_reservoir|155.67|0.60|84.09|80.44|89.22|

## 5 综合评价与结论

- 岩性样点分布：{'泥岩': 20}。
- 流体解释样点分布：{'未定': 20}。
- 本报告中的定量结论仅适用于本次输入资料与所采用解释模型；关键层段应结合录井、测试及取心资料复核。

## 6 建议

- 对资料缺失、质量异常或物性边界附近层段进行人工复核。
- 利用岩心分析、试油试气及邻井资料标定解释模型和流体识别结论。
- 资料或模型更新后重新生成报告，并保留版本与审计记录。

## 7 附件及成果文件

- 解释层成果表：本报告第 4 章。
- 测井处理与解释审计记录：`run.json`。
- 数字化解释结果：`run.json` 中的 `records`。

## 完整性检查

- 待补充必填项：oilfield, well_type, operator, contractor, target_interval, interpreter, reviewer。
- 备注：无。
