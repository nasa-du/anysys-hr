# 薪资公式黄金用例

本目录是 wayfinder ticket [#47](https://github.com/nasa-du/anysys-hr/issues/47)「公式引擎与字段公式自助配置定稿」的配套黄金用例，并被 map [#45](https://github.com/nasa-du/anysys-hr/issues/45) 的最终实施方案 `docs/specs/payroll-management.md` 引用。

- 目标是让实现者可以直接读取 JSON，按用例输入运行公式引擎，并逐字段比对期望值或错误。
- 输入处于**公式计算契约层**：`values` 是构成输入、考勤拉取值与薪资自有导入值，`params` 是工作日参数与全局数值参数；不重复测试月度导入的文件解析、列映射与考勤拉取流程（由 #48 定稿）。
- 本目录不包含生产代码；执行器由 #54 的测试计划接入 CI。

## 目录

```text
payroll-golden-cases/
├── README.md
├── schema.json                 # case 的 JSON Schema（draft 2020-12）
├── security-schema.json        # 安全语料的 JSON Schema
├── security-corpus.json        # 攻击字符串与限额语料
├── base/
│   ├── field-defs.json         # 32 个系统字段（类别、计算方式、来源键、默认公式、顺序）
│   ├── compositions.json       # 示例薪资构成（版本 1）
│   ├── workday-params.json     # 示例工作日/考勤参数
│   ├── global-params.json      # 示例全局数值参数
│   └── schemes.json            # 默认计算方案（无公式覆盖）
└── cases/
    └── case-XX-*.json          # 一案一文件
```

## 数值口径

| 项 | 口径 |
| --- | --- |
| 金额 | 2 位小数；存储/计算/展示一致；扣减为负数 |
| 天数 | 1 位小数（与考勤导出口径一致） |
| 小时 | 2 位小数 |
| 引擎数值 | 全部 `Decimal`，不使用二进制浮点 |
| `ROUND` | `Decimal.quantize` + `ROUND_HALF_UP`（四舍五入，负数远离零） |
| 用例中的数值 | **一律使用十进制字符串**；禁止 JSON 数字，避免解析精度歧义 |
| 金额精度 | 金额字段结果必须可精确表示为 2 位小数；否则报 `formula_value_scale`，引擎不隐式取整 |

## 字段来源

| `calc_mode` | 取值方式 |
| --- | --- |
| `plan` | 从员工当前岗位薪资构成的版本金额中按 `source_key` 取值（如 `hightemp` ← `hightemp_subsidy`） |
| `import` | 从月度输入快照中按 `source_key` 取值；来源可为文件列或服务器拉取的考勤值，#48 定稿优先级 |
| `fixed` | 使用字段定义上的 `fixed_value` |
| `formula` | 求值生效公式：方案级覆盖优先，否则使用字段定义的默认公式 |

构成输入 `base_salary`、`hightemp_subsidy`、`performance_salary`、`overtime_pay`、`confidentiality_allowance`、`social_subsidy`、`noncompete_subsidy`、`total_package` 以及参数 `{avg_pay_days}`、`{work_hours}`、`{ot_mult_weekday}`、`{ot_mult_weekend}`、`{ot_mult_holiday}`、`{min_wage}`、`{tax_threshold}`、`{tax_rate}`、`{social_rate}` 可直接被公式引用，但不是字段定义，不出现在工资列表。

## 如何执行一个用例

1. 读取 `base/field-defs.json` 得到系统字段；用例的 `input.field_defs` 按 `field_key` 追加或覆盖字段定义。
2. 读取 `base/workday-params.json` 与 `base/global-params.json` 得到参数；用例的 `input.params` 覆盖同名参数。
3. 用例的 `input.formula_overrides` 按 `field_key` 覆盖默认公式；未覆盖的 `formula` 字段使用字段定义的 `default_formula`。
4. 用例的 `input.values` 提供 `plan`/`import` 输入键、构成输入键与 `fixed` 之外的运行值。`fixed` 字段不读 `values`。
5. 按依赖图求值所有 `formula` 字段；对每个员工/作用域执行五条一致性校验。
6. 比对：
   - `expected.value`：`kind = formula` 的单表达式结果。
   - `expected.values`：`kind = scheme` 的所有 `formula` 字段值；用例必须覆盖全部公式字段（系统 + 用例新增）。
   - `expected.error`：期望的域错误；`code` 必填，`field_key`、`position`、`path` 按需断言。
   - `expected.consistency`：`"pass"` 或五条校验的违规列表。

### 两种 `kind`

- `kind = "formula"`：`formula` 是单个表达式，`input.values` / `input.params` 提供作用域；用于取整、惰性 `IF`、语法、安全与限额。`input` 必须存在，可为 `{}`。
- `kind = "scheme"`：验证完整字段图、默认公式、来源解析与一致性校验；`input.values`/`input.params` 至少覆盖被求值字段所需的输入。

所有用例都带 `engine_version`；CI 只接受与当前引擎版本一致的用例。引擎语义变更必须同时升版本并更新用例。

## 五条类别锚定校验

| 校验 | 关系 |
| --- | --- |
| `normal_pay` | `normal_pay = ROUND(Σ earning, 2)` |
| `addon_sum` | `addon_sum = ROUND(Σ addon, 2)` |
| `gross` | `gross = ROUND(normal_pay + addon_sum, 2)` |
| `deduct_sum` | `deduct_sum = ROUND(Σ deduction, 2)` |
| `net` | `net = ROUND(gross + deduct_sum, 2)` |

任一条失败即整批核算失败，不写入结果；`expected.consistency` 的违规项记录 `check`、`expected` 与 `actual`。`attendance_deduct` 与 `admin_deduct` 属于负数加减项，已包含在 `addon_sum` 中，不属于 `deduct_sum`。

## 错误码

| 阶段 | 错误码 |
| --- | --- |
| 保存时 | `formula_syntax_error`、`formula_unknown_field`、`formula_unknown_parameter`、`formula_unknown_function`、`formula_arity_error`、`formula_reserved_key`、`formula_cycle`、`formula_limit_exceeded` |
| 核算/试算时 | `formula_missing_value`、`formula_division_by_zero`、`formula_type_error`、`formula_value_scale`、`formula_value_range`、`formula_inactive_field`、`formula_consistency_failed` |

错误对用户呈现中文字段键/位置与中文消息；不返回 Python traceback。HTTP 状态与响应封装由 #53 定稿。

## 覆盖矩阵

| 用例 | 覆盖 |
| --- | --- |
| `case-01-default-formulas` | 默认 10 条公式、`plan`/`import` 来源、五条校验通过、金额取整 |
| `case-02-rounding` | `ROUND` 四类边界、字段级取整 vs 公式级取整（`0.005+0.005`） |
| `case-03-custom-fields` | 自定义 `earning`/`addon` 字段、方案覆盖小计公式、类别校验 |
| `case-04-cycle` | 三节点依赖环与环路径 |
| `case-05-lazy-if-and-comparisons` | 惰性 `IF`、`=`/`<>`/`==`/`!=`、`0`/非零真值 |
| `case-05b-chained-comparison` | 拒绝链式比较 |
| `case-05c-unknown-function` | 未知函数 |
| `case-05d-arity-error` | 函数参数个数错误 |
| `case-06a-unknown-field` | 未知字段 |
| `case-06b-unknown-parameter` | 未知参数 |
| `case-06c-division-by-zero` | 显式零除 |
| `case-06d-missing-value` | 已知输入缺失值 |
| `case-06e-zero-denominator` | 默认公式零分母（不自动加护栏） |
| `case-07-scale-violation` | 金额公式未收敛到 2 位 |
| `case-08-consistency-violations` | 五条一致性校验各失败一次 |
| `case-09-negative-adjustments` | 负数考勤/行政扣减、负数代扣与实发 |
| `case-10-plan-import-fixed` | `plan`/`import`/`fixed` 三种来源 |
| `security-corpus.json` | 15 条攻击字符串 + 3 条限额（长度/嵌套/数字字面量） |

## 引擎版本与 CI

- 当前引擎版本：`1.0.0`。`base/` 与所有用例的 `engine_version` 必须一致；升版时同步更新全部用例。
- 执行器应复用与生产相同的 tokenizer/parser/evaluator/graph 编译路径，不得为黄金用例另写一套计算逻辑。
- 建议 CI 至少执行：schema 校验、全部 case、安全语料、默认公式全链路、五条一致性失败、500×40 性能冒烟（性能门禁由 #54 定）。

## 边界

- **#48 月度导入**：负责 `import` 字段的来源键注册、考勤拉取、空值归零、负数与精度归一；本目录的 `values` 是该契约的计算层输入。
- **#49 生命周期**：负责核算失败后的状态、结果版本与待重算转换；本目录只断言“整批失败、不写结果”。
- **#50 工资条与报表**：沿用 `visible` 与 `display_order` 及字段类别，不另建第二套显隐/顺序。
- **#53 API**：负责错误码到 HTTP 的映射与响应形状。
- **#54 实现与测试**：负责把本目录接入 CI、性能门禁与覆盖率目标。
