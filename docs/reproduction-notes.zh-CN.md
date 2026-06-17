# Auto-Logging 说明


## 现有功能

- Planner/Executor 双代理职责分离
- 基于结构化测井规则的检索式规划
- 带前置依赖的七步解释流程
- 数据质控、预处理、扩展缺失段补全、岩性、储层参数、流体和报告组件
- 中间结果反馈、异常标记、后备策略与人工复核建议
- 每一步命令、指标、异常和 Planner 决策的 JSON 审计轨迹
- CLI 与论文所述 Flask 风格 HTTP 部署接口

## 需要自行配置的部分

论文附带训练数据、模型权重，但完整知识库、阿里云 EAS/Bailian 配置需在阿里云和百炼平台进行配置。因此，本项目使用确定性的物理启发式参考组件，使系统可立即运行。真实模型可以通过
`ComponentRegistry` 替换，而不改变 Planner、Executor 或审计流程。

## 对应论文组件

| 论文描述 | 当前实现 |
|---|---|
| Qianwen-32B Planner/Executor | 可审计的确定性 Planner/Executor；预留组件替换位置 |
| RAG petrophysical knowledge base | `knowledge/rules.json` |
| LSTM missing-curve model | 扩展缺失段检测 + 参考插值后备模型 |
| 2D-CNN lithology model | 可替换的参考岩性分类器 |
| Bi-LSTM multi-task model | 物理约束 VSH/PHI/SW 参考计算器 |
| KNN fluid model | 可替换的参考流体分类器 |
| Flask + EAS + Bailian | 可选 Flask API + 本地组件注册表 |

## 云端路由与秘钥

真实秘钥已被隐去；部署时通过
`ALIBABA_CLOUD_ACCESS_KEY_ID`、`ALIBABA_CLOUD_ACCESS_KEY_SECRET` 和
`AUTO_LOGGING_OSS_BUCKET` 注入。完整变量列表见 `.env.example`。

云端适配器直接从 OSS 读取 CSV，在内存中完成输入变换并把结果写回 OSS，不再将含井数据的
临时 CSV 落盘。每个路由会校验必需字段、特征完整性、对数变换的正值约束及 EAS 输出长度。

## SY/T 5945-2004 报告工具

报告模块按《SY/T 5945-2004 测井解释报告编写规范》组织为基本信息、资料概况与质量评价、
资料处理与解释方法、解释成果、综合评价与结论、建议、附件及成果文件，并生成解释层成果表。
缺少的井史、施工、签署或目的层资料会被明确列入完整性检查，不由模型编造。

CLI 使用 `--report-metadata examples/report_metadata.json` 注入报告元数据；HTTP 可调用
`POST /report/generate` 独立生成报告。正式交付前仍应由所在单位使用持有的完整标准文本进行
最终符合性审查。
