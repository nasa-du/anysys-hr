// Payroll Chinese labels and option arrays. The codes mirror the backend
// enum vocabulary from ``docs/specs/payroll-management.md`` section 4.24.
// Components import labels from here instead of hardcoding Chinese strings.

function labelsToOptions<T extends string>(
  labels: Record<T, string>,
): Array<{ value: T; label: string }> {
  return (Object.entries(labels) as Array<[T, string]>).map(
    ([value, label]) => ({ value, label }),
  )
}

export type PayrollMonthStatus = "draft" | "calculated" | "confirmed" | "paid"

export const PAYROLL_MONTH_STATUS_LABELS: Record<PayrollMonthStatus, string> = {
  draft: "草稿",
  calculated: "已核算",
  confirmed: "已确认",
  paid: "已发放",
}

export const PAYROLL_MONTH_STATUS_OPTIONS = labelsToOptions(
  PAYROLL_MONTH_STATUS_LABELS,
)

export type PayrollCalcRunStatus = "running" | "succeeded" | "failed"

export const PAYROLL_CALC_RUN_STATUS_LABELS: Record<
  PayrollCalcRunStatus,
  string
> = {
  running: "核算中",
  succeeded: "成功",
  failed: "失败",
}

export type PayrollCalcRunTrigger = "initial" | "manual" | "attendance_refresh"

export const PAYROLL_CALC_RUN_TRIGGER_LABELS: Record<
  PayrollCalcRunTrigger,
  string
> = {
  initial: "首次",
  manual: "手动",
  attendance_refresh: "刷新考勤",
}

export type PayrollAttendanceLockState = "locked" | "unlocked" | "missing"

export const PAYROLL_ATTENDANCE_LOCK_LABELS: Record<
  PayrollAttendanceLockState,
  string
> = {
  locked: "已锁定",
  unlocked: "未锁定",
  missing: "缺月考勤",
}

export type PayrollImportBatchStatus =
  | "preview"
  | "committed"
  | "superseded"
  | "discarded"

export const PAYROLL_IMPORT_BATCH_STATUS_LABELS: Record<
  PayrollImportBatchStatus,
  string
> = {
  preview: "预览",
  committed: "已生效",
  superseded: "已替代",
  discarded: "已丢弃",
}

export type PayrollImportBatchSource = "upload" | "paste"

export const PAYROLL_IMPORT_SOURCE_LABELS: Record<
  PayrollImportBatchSource,
  string
> = {
  upload: "上传",
  paste: "粘贴",
}

export type PayrollImportRowStatus = "valid" | "error" | "skipped"

export const PAYROLL_IMPORT_ROW_STATUS_LABELS: Record<
  PayrollImportRowStatus,
  string
> = {
  valid: "有效",
  error: "错误",
  skipped: "跳过",
}

export type PayrollInputSource = "import" | "manual"

export const PAYROLL_INPUT_SOURCE_LABELS: Record<PayrollInputSource, string> = {
  import: "导入",
  manual: "手工",
}

export type PayrollResultSource =
  | "plan"
  | "import"
  | "formula"
  | "fixed"
  | "manual"

export const PAYROLL_RESULT_SOURCE_LABELS: Record<PayrollResultSource, string> =
  {
    plan: "薪资构成",
    import: "导入",
    formula: "公式",
    fixed: "固定值",
    manual: "手工",
  }

export type SalaryFieldCategory =
  | "earning"
  | "addon"
  | "deduction"
  | "total"
  | "reference"

export const SALARY_FIELD_CATEGORY_LABELS: Record<SalaryFieldCategory, string> =
  {
    earning: "计薪项",
    addon: "加减项",
    deduction: "代扣项",
    total: "合计项",
    reference: "参考项",
  }

export const SALARY_FIELD_CATEGORY_OPTIONS = labelsToOptions(
  SALARY_FIELD_CATEGORY_LABELS,
)

export type SalaryFieldCalcMode = "plan" | "import" | "formula" | "fixed"

export const SALARY_FIELD_CALC_MODE_LABELS: Record<
  SalaryFieldCalcMode,
  string
> = {
  plan: "薪资构成",
  import: "导入",
  formula: "公式",
  fixed: "固定值",
}

/** Custom fields may not use the composition-driven ``plan`` mode. */
export const CUSTOM_FIELD_CALC_MODE_OPTIONS = labelsToOptions(
  SALARY_FIELD_CALC_MODE_LABELS,
).filter((option) => option.value !== "plan")

export type PayrollGlobalParamType = "number" | "json"

export const PAYROLL_GLOBAL_PARAM_TYPE_LABELS: Record<
  PayrollGlobalParamType,
  string
> = {
  number: "数值",
  json: "JSON",
}

export type PayrollExportType =
  | "payslip_single"
  | "payslip_zip"
  | "payslip_merged"
  | "payroll_detail_xlsx"
  | "department_summary_xlsx"

export const PAYROLL_EXPORT_TYPE_LABELS: Record<PayrollExportType, string> = {
  payslip_single: "单人工资条",
  payslip_zip: "工资条 ZIP",
  payslip_merged: "工资条合并 PDF",
  payroll_detail_xlsx: "工资明细 Excel",
  department_summary_xlsx: "部门汇总 Excel",
}

export type PayrollExportStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "expired"

export const PAYROLL_EXPORT_STATUS_LABELS: Record<PayrollExportStatus, string> =
  {
    queued: "排队中",
    running: "生成中",
    succeeded: "已完成",
    failed: "失败",
    expired: "已过期",
  }

export type PayrollMonthEventType =
  | "confirmed"
  | "unconfirmed"
  | "paid"
  | "unlocked"

export const PAYROLL_MONTH_EVENT_LABELS: Record<PayrollMonthEventType, string> =
  {
    confirmed: "确认",
    unconfirmed: "取消确认",
    paid: "发工资条",
    unlocked: "解锁",
  }

export type PayrollConfigEntityType =
  | "compensation_composition"
  | "calc_scheme"
  | "workday_param"
  | "salary_field_def"
  | "payroll_global_param"
  | "position_payroll_config"

export const PAYROLL_CONFIG_ENTITY_LABELS: Record<
  PayrollConfigEntityType,
  string
> = {
  compensation_composition: "薪资构成",
  calc_scheme: "计算方案",
  workday_param: "工作日参数",
  salary_field_def: "薪资字段",
  payroll_global_param: "全局参数",
  position_payroll_config: "岗位装配",
}

// Month-bar staleness badges from section 13.1. They explain why a month
// needs attention; they never change money by themselves.
export type PayrollStaleBadge =
  | "needs_recalc"
  | "attendance_stale"
  | "scope_changed"
  | "config_updated"
  | "last_batch_failed"

export const PAYROLL_STALE_BADGE_LABELS: Record<PayrollStaleBadge, string> = {
  needs_recalc: "待重算",
  attendance_stale: "考勤过期",
  scope_changed: "范围变化",
  config_updated: "配置已更新",
  last_batch_failed: "最近批次失败",
}

export const PAYROLL_STALE_BADGE_OPTIONS = labelsToOptions(
  PAYROLL_STALE_BADGE_LABELS,
)
