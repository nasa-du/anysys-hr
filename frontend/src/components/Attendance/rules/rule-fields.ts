import type { RuleValues } from "@/client"

export type RuleKey = keyof RuleValues

export type RuleKind = "int" | "money" | "boolean"

export const RULE_MONEY_PATTERN = /^\d+(\.\d{1,2})?$/
export const RULE_MONEY_MESSAGE = "请输入不小于 0、最多两位小数的金额"

export interface RuleFieldDefinition {
  key: RuleKey
  label: string
  kind: RuleKind
  hint: string
}

export interface RuleGroupDefinition {
  key: string
  title: string
  description: string
  fields: RuleFieldDefinition[]
}

/** Grouped rule metadata shared by the company form and the override table. */
export const RULE_GROUPS: RuleGroupDefinition[] = [
  {
    key: "window",
    title: "打卡归属窗口",
    description: "决定一张卡算上班还是下班",
    fields: [
      {
        key: "punch_window_min",
        label: "上班卡可提前（分钟）",
        kind: "int",
        hint: "早于上班时间多久内的卡仍算本班上班卡",
      },
      {
        key: "late_cap_min",
        label: "上班卡最晚归属（分钟）",
        kind: "int",
        hint: "晚于上班时间多久内仍算本班上班卡",
      },
      {
        key: "early_cap_min",
        label: "下班卡最早归属（分钟）",
        kind: "int",
        hint: "早于下班时间多久内的卡仍算本班下班卡",
      },
    ],
  },
  {
    key: "grace",
    title: "迟到与早退",
    description: "按班次计次数与分钟",
    fields: [
      {
        key: "late_grace_min",
        label: "迟到宽限（分钟）",
        kind: "int",
        hint: "上班卡晚于该宽限才开始计迟到",
      },
      {
        key: "early_grace_min",
        label: "早退宽限（分钟）",
        kind: "int",
        hint: "下班卡早于该宽限才开始计早退",
      },
    ],
  },
  {
    key: "overtime",
    title: "加班",
    description: "只从当日最后一班产生打卡加班",
    fields: [
      {
        key: "ot_max_min",
        label: "单日加班上限（分钟）",
        kind: "int",
        hint: "打卡与 OA 加班都受此上限约束",
      },
      {
        key: "ot_threshold_min",
        label: "加班起算阈值（分钟）",
        kind: "int",
        hint: "仅作用于打卡推算值；OA 审批值不折减",
      },
    ],
  },
  {
    key: "break",
    title: "午休与旷工",
    description: "午休卡缺失不影响工时",
    fields: [
      {
        key: "break_punch_required",
        label: "班次配置午休段时要求 4 次卡",
        kind: "boolean",
        hint: "缺午休卡计缺卡，但工时仍按上下班卡 − 休息扣除",
      },
      {
        key: "break_punch_tolerance_min",
        label: "午休卡识别容差（分钟）",
        kind: "int",
        hint: "在午休开始/结束前后该范围内找卡",
      },
      {
        key: "absent_if_no_punch",
        label: "排班日完全无卡计旷工",
        kind: "boolean",
        hint: "关闭时改记缺卡（按 2 张计）",
      },
    ],
  },
  {
    key: "deduction",
    title: "扣款建议值",
    description: "负值写入月汇总；考勤模块不直接扣工资",
    fields: [
      {
        key: "absent_deduct_per_day",
        label: "旷工每日（元）",
        kind: "money",
        hint: "按日计；旷工日不再计迟到/早退/缺卡",
      },
      {
        key: "late_deduct_per_occurrence",
        label: "迟到每次（元）",
        kind: "money",
        hint: "按班次计次数",
      },
      {
        key: "early_deduct_per_occurrence",
        label: "早退每次（元）",
        kind: "money",
        hint: "按班次计次数",
      },
      {
        key: "missing_punch_deduct_per_occurrence",
        label: "缺卡每张（元）",
        kind: "money",
        hint: "缺上班/下班/午休各计 1 张",
      },
    ],
  },
]

export const RULE_FIELDS: RuleFieldDefinition[] = RULE_GROUPS.flatMap(
  (group) => group.fields,
)

export function formatRuleValue(
  field: RuleFieldDefinition,
  value: RuleValues[RuleKey],
): string {
  if (field.kind === "boolean") {
    return value ? "开启" : "关闭"
  }
  if (field.kind === "money") {
    return `${value} 元`
  }
  return `${value} 分钟`
}
