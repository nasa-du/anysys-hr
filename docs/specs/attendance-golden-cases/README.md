# 考勤计算黄金用例

本目录是 wayfinder ticket [#25](https://github.com/nasa-du/anysys-hr/issues/25)「考勤计算规则、日结果与月汇总定稿」的配套黄金用例。

- 目标是让实现者可以直接读取 JSON、按用例输入的规范化记录计算，并逐字段比对期望结果。
- 输入处于**计算契约层**（已通过导入解析与过滤的 `punch_record` / `oa_trip` / `oa_overtime_day` / `oa_leave`），不重复测试导入解析。
- 用例使用 `docs/specs/attendance-fixtures/` 的 2026-09 钉钉样本与三类 OA 样例；少量 fixture 未覆盖的边界（一天多班、午休 4 次卡、补休有加班可抵等）使用标注为 `synthetic` 的记录补齐。

## 目录

```text
attendance-golden-cases/
├── README.md
├── schema.json                 # 用例 JSON Schema（draft 2020-12）
├── base/
│   ├── employees.json          # 员工种子（与 fixtures README 一致）
│   ├── shifts.json             # 班次定义
│   ├── rules.json              # 公司默认考勤规则
│   ├── holidays-2026-09.json   # 2026-09 节假日
│   └── holidays-2026-10.json   # 2026-10 节假日
└── cases/
    └── case-XX-*.json          # 一案一文件
```

## 如何执行一个用例

1. 从 `base/employees.json`、`base/shifts.json` 读取员工与班次。
2. 读取用例的 `input`：
   - `employee_ids`：参与计算的员工。
   - `roster_default = "rest"`：未在 `roster_overrides` 列出的日期一律为休息。
   - `roster_overrides`：显式指定某员工某日为 `work`（1..N 个班次）或 `rest`。
   - `adjacent_roster_overrides`：仅用于跨月请假/补休的分母计算；列出相邻月份的排班日，不参与本月日结果。
   - `holidays`：该月的完整节假日日历（含 `holiday` 与 `adjusted_workday`）。
   - `rules`：本用例生效的完整考勤规则。
   - `punches` / `oa_trips` / `oa_overtime_days` / `oa_leaves`：本用例涉及的规范化记录。
3. 按 ticket #25 的决议计算该月。
4. 比对：
   - `expected.day_results`：只列出用例断言的日子；其余日期忽略。
   - `expected.month_summaries`：只列出用例断言的员工；其余员工忽略。
   - `expected.calc_run_summary`：整个输入集合的计算计数。

> 用例采用“目标排班”而不是整月铺满：未列出的日期为休息，因此 `calc_run_summary.days_total` 会包含 30/31 天 × 人数的休息行。生产环境可以存储全部休息日，也可以只存有排班/数据的日期；这不影响日结果与月汇总的断言。

## 数值口径

| 项 | 口径 |
|---|---|
| 时区 | `Asia/Shanghai`；输入时间均带 `+08:00` |
| 分钟 | 整数分钟；卡点截断到分钟（导入层已完成） |
| 小时 | 2 位小数（`minutes / 60`，四舍五入） |
| 天数 / 出勤比例 | 1 位小数，常见 0.5；区间重叠比例按最终值四舍五入 |
| 金额 | 2 位小数；扣款为负数 |
| 中间计算 | 用整数分钟与十进制天数，只在最终展示值四舍五入 |
| 日状态优先级 | 整日请假 > 旷工 > 缺卡 > 迟到 > 早退 > 外出/出差 > 加班 > 正常 > 休息 |
| 加班分类 | 法定节假日 → `holiday`；调休上班/有排班工作日 → `weekday`；周末有排班或无排班休息日 → `weekend` |

## 覆盖矩阵

| 场景 | 用例 |
|---|---|
| 正常出勤、实际工时 | `case-01-normal` |
| 迟到、早退、宽限、扣款 | `case-02-late-early` |
| 缺上班卡 / 缺下班卡 | `case-03-missing-punch` |
| 旷工、日期不一致打卡落在窗口外 | `case-04-absent` |
| 跨天夜班、次日凌晨下班卡、午休缺卡 | `case-05-cross-day-night` |
| 一天多班、14:00 接力卡 | `case-06-multi-shift` |
| 午休段 4 次卡 / 缺午休卡 | `case-07-break-four-punch` |
| 整日外出/出差计出勤 | `case-08-trip-full` |
| 半天外出按重叠比例 | `case-09-trip-half` |
| 出差 + 打卡：打卡优先、出差仅标注 | `case-10-trip-with-punch` |
| 半天带薪假、无打卡 | `case-11-paid-leave-half` |
| 多日事假折算、超天数、假落休息日、假与出差冲突 | `case-12-unpaid-leave` |
| 补休抵扣、无加班可抵、缺上班开始时间 | `case-13-comp-offset` |
| 跨月补休：9 月只抵上班日 / 10 月只扣休息日 | `case-14a-comp-cross-month-september`、`case-14b-comp-cross-month-october` |
| OA 加班就高、OA-only 加班、缺卡但 OA 加班 | `case-15-oa-ot-higher` |
| 休息日 / 未排班日 OA 加班分类 | `case-16-rest-day-ot` |
| 调休上班日按工作日 | `case-17-adjusted-workday` |
| 未排班/休息日打卡出勤 | `case-18-unscheduled-attendance` |
| 迟早早退、缺卡、旷工、半天假的扣款汇总 | `case-19-deduction` |
| 31 天月份、月末日期、节假日加班、补休 | `case-20-big-small-month-october` |
| 加班起算 30 分钟、`ot_max` 600、下一班约束 | `case-21-ot-threshold-cap` |
| 同一天多张假单按假别拆分 | `case-22-multiple-leave` |
| 跨月事假按排班日分摊到两个月 | `case-23a-cross-month-leave-september`、`case-23b-cross-month-leave-october` |
| 同日多张补休单的抵扣与剩余 | `case-24-multiple-comp-offset` |

## 与 fixtures 的对应

- 打卡 `source = fixture` 的记录带 `source_row`，对应 `docs/specs/attendance-fixtures/punch-2026-09.csv` 的源数据行号（含表头，从 1 开始）。
- OA `source = fixture` 的记录使用 fixture 的 `id`（如 `TRIP-001`、`OT-001`、`LEAVE-002`），对应三份 OA CSV。
- `source = synthetic` 的记录用于 fixtures 没有覆盖的排班/打卡组合：
  - `case-06` 双班日 05:58 / 14:00 / 22:05；
  - `case-07` 园林班 4 次卡；
  - `case-13` 为 E104 09-13 补一笔 480 分钟加班，用于验证补休抵扣；
  - `case-14a` 为 E103 09-25 补一笔 480 分钟节假日加班；
  - `case-21` 加班阈值/上限/下一班约束的卡点。

## 需要特别说明的口径

1. **出勤按日、不按班次**：一天多班仍只算 1 天；部分出勤用 `attendance_fraction` 表示。
2. **`worked_minutes` 不含加班**：末班下班卡晚于排班结束的部分计入 `ot_*_minutes`，不计入 `worked_minutes`；早到时间按实际计入工时（如 `case-01` 的 08:18 上班卡）。
3. **半天外出按重叠比例**：`case-09` 的 14:00–18:00 外出与 08:30–17:30 行政班重叠 210/540，`attendance_fraction = 0.4`，不是申请单上填的 0.5；`days_declared` 在导入契约中是参考字段。
4. **部分请假 + 无打卡**：请假覆盖的部分免考勤；未覆盖部分没有打卡/出差证据时，`attendance_fraction = 0`、状态 `missing_punch`，不记旷工（`case-11` / `case-19`）。
5. **请假 + 出差同一天**：请假优先，出差保留 `trip` 标注并记 `leave_trip_conflict`（`case-12` 的 09-28）。
6. **补休抵扣**：只抵 `work_start_date` 当天“就高”后的加班；剩余不结转，记 `comp_offset_unused_minutes`；上班开始时间缺失时不抵任何日期，剩余记在补休当天（`case-13` 的 E105）。
7. **午休 4 次卡**：缺午休卡计入 `missing_punch_count`，但 `worked_minutes` 仍按上下班卡 − `rest_minutes` 计算（`case-07` 的 09-16）。
8. **休息日/未排班日加班**：只有 OA 审批加班单才产生加班；仅打卡不产生加班，只记 `unscheduled_attendance`（`case-18`）。
9. **节假日打卡**：`case-18` 的 09-25 打卡计 `unscheduled_attendance`，但不进入 `weekday_attended` / `weekend_attended`，因为这两个计薪字段只拆工作日/周末。
10. **多张假单同日**：按 `带薪假 > 补休 > 事假` 占用当天比例，总比例封顶 1；日结果按假别分别存 `paid_leave_days` / `unpaid_leave_days` / `comp_leave_days`，`leave_kind` 只表示占主导的假别（`case-22`）。
11. **目标排班**：用例的未列出日期都是休息，所以月汇总里的 `*_full` 只统计显式排班的日期；这不是“整月应出勤天数”的产品示例，而是为了让每个用例的月汇总可读、可断言。
12. **跨月请假**：分母用完整休息区间内的排班日（可跨月），分子只用当月覆盖的排班日；`case-23a/23b` 用同一张 1.5 天事假单验证 9 月分 0.5、10 月分 1.0，合计 1.5，不重复。
13. **同日多张补休单**：先求和再封顶到当日“就高”后的加班；`case-24` 的 720 分钟只抵 480，剩余 240 记 `comp_offset_unused_minutes`。

## 不在这批用例里的内容

- 导入解析、过滤、批次覆盖：见 `docs/specs/attendance-fixtures/` 与 ticket #24。
- 方案级规则覆盖（`plan_rule_override`）的解析：见 ticket #23；用例的 `rules` 直接给出已生效的规则。
- 人工调整后重算：语义见 ticket #25 决议；API/UI 由 #26/#27 落。
- 月结快照、导出列顺序：字段与顺序见 ticket #25 决议；实现由 #27/#28 落。
