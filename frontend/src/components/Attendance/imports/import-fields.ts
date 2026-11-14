import type { AttendanceImportDataType } from "@/lib/enums"

export type ImportFieldDefinition = {
  key: string
  label: string
  required: boolean
}

/** Canonical fields and Chinese labels from spec §6.2. */
export const IMPORT_FIELDS: Record<
  AttendanceImportDataType,
  ImportFieldDefinition[]
> = {
  punch: [
    { key: "employee_no", label: "工号", required: true },
    { key: "employee_name", label: "姓名", required: false },
    { key: "department_raw", label: "部门", required: false },
    { key: "attendance_date", label: "考勤日期", required: true },
    { key: "punch_time", label: "打卡时间", required: true },
    { key: "scheduled_time", label: "考勤时间（仅参考）", required: false },
    { key: "punch_result", label: "打卡结果", required: true },
    { key: "device_raw", label: "打卡设备", required: false },
    { key: "address_raw", label: "打卡地址", required: false },
  ],
  trip: [
    { key: "employee_name", label: "出差人", required: true },
    { key: "application_type_raw", label: "申请类型", required: false },
    { key: "department_raw", label: "部门", required: false },
    { key: "start_at", label: "开始时间", required: true },
    { key: "end_at", label: "结束时间", required: true },
    { key: "days_declared", label: "出差天数（仅参考）", required: false },
    { key: "reason", label: "外出事由", required: false },
    { key: "approval_result", label: "审批结果", required: true },
    { key: "approval_status", label: "审批状态", required: false },
    { key: "approval_no", label: "审批编号", required: false },
  ],
  ot: [
    { key: "employee_name", label: "创建人", required: true },
    { key: "department_raw", label: "部门", required: false },
    { key: "start_at", label: "加班开始时间", required: true },
    { key: "end_at", label: "加班结束时间", required: true },
    { key: "declared_raw", label: "加班时长（仅参考）", required: false },
    { key: "reason", label: "加班原因", required: false },
    { key: "approval_result", label: "审批结果", required: true },
    { key: "approval_status", label: "审批状态", required: false },
    { key: "approval_no", label: "审批编号", required: false },
  ],
  leave: [
    { key: "employee_name", label: "创建人", required: true },
    { key: "department_raw", label: "部门", required: false },
    { key: "leave_type_raw", label: "请假类型", required: true },
    { key: "days", label: "请假天数", required: true },
    { key: "rest_start_at", label: "休息开始时间", required: true },
    { key: "rest_end_at", label: "休息结束时间", required: true },
    { key: "work_start_at", label: "上班开始时间", required: false },
    { key: "work_end_at", label: "上班结束时间", required: false },
    { key: "balance_days_declared", label: "结余补休天数", required: false },
    { key: "reason", label: "请假说明", required: false },
    { key: "approval_result", label: "审批结果", required: true },
    { key: "approval_status", label: "审批状态", required: false },
    { key: "approval_no", label: "审批编号", required: false },
  ],
}
