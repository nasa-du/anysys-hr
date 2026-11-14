import type {
  DepartmentPublic,
  EmployeePublic,
  HolidayPublic,
  PlanDayPublic,
  PositionPublic,
  SchedulePlanPublic,
} from "@/client"
import type { AttendanceScheduleScopeType } from "@/lib/enums"

export const WEEKDAY_LABELS = ["一", "二", "三", "四", "五", "六", "日"]

export type DayKind = "workday" | "weekend" | "holiday" | "adjusted_workday"

const SCOPE_PRIORITY: Record<AttendanceScheduleScopeType, number> = {
  employee: 0,
  position: 1,
  dept: 2,
  all: 3,
}

export function monthLastDay(month: string): number {
  const [year, monthIndex] = month.split("-").map(Number)
  return new Date(Date.UTC(year, monthIndex, 0)).getUTCDate()
}

export function monthDays(month: string): string[] {
  const lastDay = monthLastDay(month)
  return Array.from(
    { length: lastDay },
    (_, index) => `${month}-${String(index + 1).padStart(2, "0")}`,
  )
}

/** Monday = 0 … Sunday = 6, matching the backend seed convention. */
export function weekdayIndex(date: string): number {
  const [year, month, day] = date.split("-").map(Number)
  return (new Date(Date.UTC(year, month - 1, day)).getUTCDay() + 6) % 7
}

export function nextMonth(month: string): string {
  const [year, monthNumber] = month.split("-").map(Number)
  return monthNumber === 12
    ? `${year + 1}-01`
    : `${year}-${String(monthNumber + 1).padStart(2, "0")}`
}

export function dayOfMonth(date: string): number {
  return Number(date.slice(8, 10))
}

export function dayKind(date: string, holidays: HolidayPublic[]): DayKind {
  const holiday = holidays.find((item) => item.date === date)
  if (holiday?.day_type === "adjusted_workday") return "adjusted_workday"
  if (holiday?.day_type === "holiday") return "holiday"
  return weekdayIndex(date) >= 5 ? "weekend" : "workday"
}

export function dayKindLabel(kind: DayKind): string {
  if (kind === "holiday") return "法定节假日"
  if (kind === "adjusted_workday") return "调休上班"
  if (kind === "weekend") return "周末"
  return "工作日"
}

function planMatches(
  plan: SchedulePlanPublic,
  employee: EmployeePublic,
): boolean {
  if (plan.scope_type === "all") return true
  if (plan.scope_type === "employee") {
    return (plan.scopes ?? []).some((scope) => scope.scope_id === employee.id)
  }
  if (plan.scope_type === "position") {
    return (plan.scopes ?? []).some(
      (scope) => scope.scope_id === employee.position_id,
    )
  }
  return (plan.scopes ?? []).some(
    (scope) => scope.scope_id === employee.dept_id,
  )
}

/** Preview-only mirror of the backend priority resolution (spec section 5.1). */
export function resolvePlan(
  plans: SchedulePlanPublic[],
  employee: EmployeePublic,
): SchedulePlanPublic | null {
  const matches = plans.filter(
    (plan) => plan.status === "enabled" && planMatches(plan, employee),
  )
  if (matches.length === 0) return null
  return matches.reduce((winner, candidate) =>
    SCOPE_PRIORITY[candidate.scope_type] < SCOPE_PRIORITY[winner.scope_type]
      ? candidate
      : winner,
  )
}

export function planCoverage(
  plan: SchedulePlanPublic,
  employees: EmployeePublic[],
): EmployeePublic[] {
  return employees.filter((employee) => planMatches(plan, employee))
}

export function planShiftsForDay(
  plan: SchedulePlanPublic,
  day: number,
): PlanDayPublic[] {
  return (plan.days ?? [])
    .filter((item) => item.day_of_month === day)
    .sort((left, right) => left.seq - right.seq)
}

export function scopeLabel(
  plan: SchedulePlanPublic,
  departments: DepartmentPublic[],
  positions: PositionPublic[],
): string {
  if (plan.scope_type === "all") return "全公司"
  const names = (plan.scopes ?? [])
    .map((scope) => {
      if (scope.scope_name) return scope.scope_name
      if (scope.scope_code) return scope.scope_code
      if (plan.scope_type === "dept") {
        return departments.find((item) => item.id === scope.scope_id)?.dept_name
      }
      if (plan.scope_type === "position") {
        return positions.find((item) => item.id === scope.scope_id)
          ?.position_name
      }
      return undefined
    })
    .filter((name): name is string => Boolean(name))
  return names.length ? names.join("、") : "—"
}

export function employeeEmployedOn(
  employee: EmployeePublic,
  date: string,
): boolean {
  if (employee.hire_date > date) return false
  if (employee.resign_date && employee.resign_date < date) return false
  return true
}

export function employeeIsEmployedInMonth(
  employee: EmployeePublic,
  month: string,
): boolean {
  const firstDay = `${month}-01`
  const lastDay = `${month}-${String(monthLastDay(month)).padStart(2, "0")}`
  if (employee.hire_date > lastDay) return false
  if (employee.resign_date && employee.resign_date < firstDay) return false
  return true
}

export interface DayEmployeeRow {
  employee: EmployeePublic
  plan: SchedulePlanPublic
  state: "work" | "rest"
  shifts: PlanDayPublic[]
}

export function dayEmployeeRows(
  plans: SchedulePlanPublic[],
  employees: EmployeePublic[],
  date: string,
): DayEmployeeRow[] {
  const day = dayOfMonth(date)
  const rows: DayEmployeeRow[] = []
  for (const employee of employees) {
    if (!employeeEmployedOn(employee, date)) continue
    const plan = resolvePlan(plans, employee)
    if (!plan) continue
    const shifts = planShiftsForDay(plan, day)
    rows.push({
      employee,
      plan,
      state: shifts.length ? "work" : "rest",
      shifts,
    })
  }
  return rows
}

export interface ShiftCount {
  shiftCode: string
  shiftName: string
  color: string | null
  count: number
}

export interface MergedDaySummary {
  shiftCounts: ShiftCount[]
  workCount: number
  restCount: number
  unscheduledCount: number
}

export function mergedDaySummary(
  plans: SchedulePlanPublic[],
  employees: EmployeePublic[],
  date: string,
): MergedDaySummary {
  const counts = new Map<string, ShiftCount>()
  let workCount = 0
  let restCount = 0
  let unscheduledCount = 0
  for (const row of dayEmployeeRows(plans, employees, date)) {
    if (row.state === "rest") {
      restCount += 1
      continue
    }
    workCount += 1
    for (const shift of row.shifts) {
      const code = shift.shift_code ?? shift.shift_id
      const existing = counts.get(code)
      if (existing) {
        existing.count += 1
      } else {
        counts.set(code, {
          shiftCode: code,
          shiftName: shift.shift_name ?? code,
          color: shift.shift_color ?? null,
          count: 1,
        })
      }
    }
  }
  for (const employee of employees) {
    if (!employeeEmployedOn(employee, date)) continue
    if (!resolvePlan(plans, employee)) unscheduledCount += 1
  }
  return {
    shiftCounts: [...counts.values()].sort((left, right) =>
      left.shiftCode.localeCompare(right.shiftCode),
    ),
    workCount,
    restCount,
    unscheduledCount,
  }
}
