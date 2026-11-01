import type { EmployeeStatus } from "@/client"

/** Manager references use 「已离职」 where the employee list uses 「离职」. */
export const MANAGER_STATUS_LABELS: Record<EmployeeStatus, string> = {
  active: "在职",
  probation: "试用期",
  resigned: "已离职",
}
