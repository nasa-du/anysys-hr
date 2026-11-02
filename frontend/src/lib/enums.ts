import type { ContractType, EmployeeStatus, Gender } from "@/client"

/** Employee.gender is null when the value was never provided. */
export const GENDER_NOT_PROVIDED_LABEL = "未提供"

export const GENDER_LABELS: Record<Gender, string> = {
  male: "男",
  female: "女",
  unknown: "未说明",
}

export const GENDER_OPTIONS: Array<{ value: Gender; label: string }> = [
  { value: "male", label: GENDER_LABELS.male },
  { value: "female", label: GENDER_LABELS.female },
  { value: "unknown", label: GENDER_LABELS.unknown },
]

export const EMPLOYEE_STATUS_LABELS: Record<EmployeeStatus, string> = {
  active: "在职",
  probation: "试用期",
  resigned: "离职",
}

export const EMPLOYEE_STATUS_OPTIONS: Array<{
  value: EmployeeStatus
  label: string
}> = [
  { value: "active", label: EMPLOYEE_STATUS_LABELS.active },
  { value: "probation", label: EMPLOYEE_STATUS_LABELS.probation },
  { value: "resigned", label: EMPLOYEE_STATUS_LABELS.resigned },
]

/** Create accepts only the two non-terminal statuses. */
export const CREATE_EMPLOYEE_STATUS_OPTIONS = EMPLOYEE_STATUS_OPTIONS.filter(
  (option) => option.value !== "resigned",
)

/** The employee list defaults to the two current statuses. */
export type EmployeeStatusFilter = "current" | "all" | EmployeeStatus

export const EMPLOYEE_STATUS_FILTER_OPTIONS: Array<{
  value: EmployeeStatusFilter
  label: string
}> = [
  { value: "current", label: "在职 + 试用期" },
  { value: "all", label: "全部状态" },
  ...EMPLOYEE_STATUS_OPTIONS,
]

export const CONTRACT_TYPE_LABELS: Record<ContractType, string> = {
  full_time: "全职",
  part_time: "兼职",
  intern: "实习",
  labor: "劳务",
}

export const CONTRACT_TYPE_OPTIONS: Array<{
  value: ContractType
  label: string
}> = [
  { value: "full_time", label: CONTRACT_TYPE_LABELS.full_time },
  { value: "part_time", label: CONTRACT_TYPE_LABELS.part_time },
  { value: "intern", label: CONTRACT_TYPE_LABELS.intern },
  { value: "labor", label: CONTRACT_TYPE_LABELS.labor },
]

/** Manager references use 「已离职」 where the employee list uses 「离职」. */
export const MANAGER_STATUS_LABELS: Record<EmployeeStatus, string> = {
  active: "在职",
  probation: "试用期",
  resigned: "已离职",
}
