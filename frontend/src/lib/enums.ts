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

// Attendance Chinese labels and option arrays. Codes come from the backend
// enum vocabulary; components must import labels from here instead of
// hardcoding Chinese strings.

export type AttendanceShiftStatus = "active" | "inactive"

/** Inactive shifts stay visible in history as 「已停用」. */
export const SHIFT_STATUS_LABELS: Record<AttendanceShiftStatus, string> = {
  active: "启用",
  inactive: "已停用",
}

export type AttendanceShiftStatusFilter = "all" | AttendanceShiftStatus

export const SHIFT_STATUS_FILTER_OPTIONS: Array<{
  value: AttendanceShiftStatusFilter
  label: string
}> = [
  { value: "all", label: "全部状态" },
  { value: "active", label: SHIFT_STATUS_LABELS.active },
  { value: "inactive", label: SHIFT_STATUS_LABELS.inactive },
]

export type AttendanceScheduleScopeType =
  | "all"
  | "dept"
  | "position"
  | "employee"

export const SCHEDULE_SCOPE_TYPE_LABELS: Record<
  AttendanceScheduleScopeType,
  string
> = {
  all: "全公司",
  dept: "部门",
  position: "岗位",
  employee: "员工",
}

export const SCHEDULE_SCOPE_TYPE_OPTIONS: Array<{
  value: AttendanceScheduleScopeType
  label: string
}> = [
  { value: "all", label: SCHEDULE_SCOPE_TYPE_LABELS.all },
  { value: "dept", label: SCHEDULE_SCOPE_TYPE_LABELS.dept },
  { value: "position", label: SCHEDULE_SCOPE_TYPE_LABELS.position },
  { value: "employee", label: SCHEDULE_SCOPE_TYPE_LABELS.employee },
]

export type AttendancePlanStatus = "enabled" | "archived"

export const PLAN_STATUS_LABELS: Record<AttendancePlanStatus, string> = {
  enabled: "启用",
  archived: "已归档",
}

export const PLAN_STATUS_OPTIONS: Array<{
  value: AttendancePlanStatus
  label: string
}> = [
  { value: "enabled", label: PLAN_STATUS_LABELS.enabled },
  { value: "archived", label: PLAN_STATUS_LABELS.archived },
]

export type AttendanceRosterState = "work" | "rest"
export type AttendanceRosterStateWithUnscheduled =
  | AttendanceRosterState
  | "unscheduled"

export const ROSTER_STATE_LABELS: Record<
  AttendanceRosterStateWithUnscheduled,
  string
> = {
  work: "上班",
  rest: "休息",
  unscheduled: "未排班",
}

export type AttendanceRosterSource = "plan" | "manual"

export const ROSTER_SOURCE_LABELS: Record<AttendanceRosterSource, string> = {
  plan: "方案",
  manual: "人工例外",
}

export const ROSTER_SOURCE_OPTIONS: Array<{
  value: AttendanceRosterSource
  label: string
}> = [
  { value: "plan", label: ROSTER_SOURCE_LABELS.plan },
  { value: "manual", label: ROSTER_SOURCE_LABELS.manual },
]

export type AttendanceHolidayDayType = "holiday" | "adjusted_workday"

export const HOLIDAY_DAY_TYPE_LABELS: Record<AttendanceHolidayDayType, string> =
  {
    holiday: "法定节假日",
    adjusted_workday: "调休上班",
  }

export const HOLIDAY_DAY_TYPE_OPTIONS: Array<{
  value: AttendanceHolidayDayType
  label: string
}> = [
  { value: "holiday", label: HOLIDAY_DAY_TYPE_LABELS.holiday },
  {
    value: "adjusted_workday",
    label: HOLIDAY_DAY_TYPE_LABELS.adjusted_workday,
  },
]

export type AttendanceMonthStatus =
  | "draft"
  | "calculated"
  | "confirmed"
  | "locked"

export const ATTENDANCE_MONTH_STATUS_LABELS: Record<
  AttendanceMonthStatus,
  string
> = {
  draft: "草稿",
  calculated: "已计算",
  confirmed: "已确认",
  locked: "已锁定",
}

export type AttendanceCalcRunTrigger =
  | "initial"
  | "manual"
  | "reimport"
  | "roster_change"
  | "rule_change"
  | "holiday_change"

export const CALC_RUN_TRIGGER_LABELS: Record<AttendanceCalcRunTrigger, string> =
  {
    initial: "首次",
    manual: "手动",
    reimport: "重新导入",
    roster_change: "排班变化",
    rule_change: "规则变化",
    holiday_change: "节假日变化",
  }

export type AttendanceCalcRunStatus = "success" | "failed"

export const CALC_RUN_STATUS_LABELS: Record<AttendanceCalcRunStatus, string> = {
  success: "成功",
  failed: "失败",
}

export type AttendanceDayType = "workday" | "weekend" | "holiday"

export const DAY_TYPE_LABELS: Record<AttendanceDayType, string> = {
  workday: "工作日",
  weekend: "周末",
  holiday: "节假日",
}

export type AttendanceDayStatus =
  | "normal"
  | "late"
  | "early"
  | "missing_punch"
  | "absent"
  | "overtime"
  | "trip_out"
  | "trip_business"
  | "personal_leave"
  | "paid_leave"
  | "comp_leave"
  | "rest"
  | "unscheduled_attendance"

export const DAY_STATUS_LABELS: Record<AttendanceDayStatus, string> = {
  normal: "正常",
  late: "迟到",
  early: "早退",
  missing_punch: "缺卡",
  absent: "旷工",
  overtime: "加班",
  trip_out: "外出",
  trip_business: "出差",
  personal_leave: "事假",
  paid_leave: "带薪假",
  comp_leave: "补休",
  rest: "休息",
  unscheduled_attendance: "未排班出勤",
}

export const DAY_STATUS_OPTIONS: Array<{
  value: AttendanceDayStatus
  label: string
}> = (
  Object.entries(DAY_STATUS_LABELS) as Array<[AttendanceDayStatus, string]>
).map(([value, label]) => ({ value, label }))

export type AttendanceLeaveKind = "paid" | "unpaid" | "comp"

export const LEAVE_KIND_LABELS: Record<AttendanceLeaveKind, string> = {
  paid: "带薪假",
  unpaid: "事假",
  comp: "补休",
}

export type AttendanceTripKind = "out" | "business"

export const TRIP_KIND_LABELS: Record<AttendanceTripKind, string> = {
  out: "外出",
  business: "出差",
}

export type AttendanceAdjustmentStatus = "active" | "superseded" | "orphaned"

export const ADJUSTMENT_STATUS_LABELS: Record<
  AttendanceAdjustmentStatus,
  string
> = {
  active: "生效",
  superseded: "已替代",
  orphaned: "已孤立",
}

export type AttendanceImportDataType = "punch" | "trip" | "ot" | "leave"

export const IMPORT_DATA_TYPE_LABELS: Record<AttendanceImportDataType, string> =
  {
    punch: "打卡",
    trip: "外出/出差",
    ot: "加班单",
    leave: "请假/补休",
  }

export const IMPORT_DATA_TYPE_OPTIONS: Array<{
  value: AttendanceImportDataType
  label: string
}> = [
  { value: "punch", label: IMPORT_DATA_TYPE_LABELS.punch },
  { value: "trip", label: IMPORT_DATA_TYPE_LABELS.trip },
  { value: "ot", label: IMPORT_DATA_TYPE_LABELS.ot },
  { value: "leave", label: IMPORT_DATA_TYPE_LABELS.leave },
]

export type AttendanceImportBatchStatus =
  | "preview"
  | "committed"
  | "superseded"
  | "discarded"
  | "revoked"

export const IMPORT_BATCH_STATUS_LABELS: Record<
  AttendanceImportBatchStatus,
  string
> = {
  preview: "预览",
  committed: "生效",
  superseded: "已替代",
  discarded: "已丢弃",
  revoked: "已撤销",
}

export type AttendanceImportSeverity = "error" | "warning"

export const IMPORT_SEVERITY_LABELS: Record<AttendanceImportSeverity, string> =
  {
    error: "错误",
    warning: "告警",
  }

export type AttendanceImportSource = "upload" | "paste"

export const IMPORT_SOURCE_LABELS: Record<AttendanceImportSource, string> = {
  upload: "上传",
  paste: "粘贴",
}

export type AttendanceDayFlag =
  | "late"
  | "early"
  | "missing_punch"
  | "break_punch_missing"
  | "absent"
  | "overtime"
  | "oa_ot_only"
  | "trip"
  | "leave"
  | "unscheduled_attendance"
  | "punch_during_leave"
  | "leave_trip_conflict"
  | "leave_ot_conflict"
  | "multiple_leave_requests"
  | "leave_on_non_workday"
  | "leave_days_excess"
  | "leave_range_uncovered"
  | "comp_offset_no_ot"
  | "comp_offset_unused"
  | "out_of_window_punch"
  | "no_valid_punch"
  | "manual_adjustment"

export const DAY_FLAG_LABELS: Record<AttendanceDayFlag, string> = {
  late: "迟到",
  early: "早退",
  missing_punch: "缺卡",
  break_punch_missing: "缺休息打卡",
  absent: "旷工",
  overtime: "加班",
  oa_ot_only: "仅 OA 加班",
  trip: "外出/出差",
  leave: "请假",
  unscheduled_attendance: "未排班出勤",
  punch_during_leave: "请假期间打卡",
  leave_trip_conflict: "请假与外出冲突",
  leave_ot_conflict: "请假与加班冲突",
  multiple_leave_requests: "多次请假",
  leave_on_non_workday: "非工作日请假",
  leave_days_excess: "请假天数超出",
  leave_range_uncovered: "请假范围未覆盖",
  comp_offset_no_ot: "补休未抵扣加班",
  comp_offset_unused: "补休未用完",
  out_of_window_punch: "窗口外打卡",
  no_valid_punch: "无有效打卡",
  manual_adjustment: "人工调整",
}
