import { useMemo } from "react"

import type {
  DepartmentPublic,
  EmployeePublic,
  HolidayPublic,
  SchedulePlanPublic,
} from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { ROSTER_STATE_LABELS } from "@/lib/enums"
import {
  dayEmployeeRows,
  dayKind,
  dayKindLabel,
  employeeEmployedOn,
  resolvePlan,
} from "./plan-utils"

export function DaySheetDialog({
  open,
  month,
  day,
  plans,
  employees,
  departments,
  holidays,
  onClose,
}: {
  open: boolean
  month: string
  day: number | null
  plans: SchedulePlanPublic[]
  employees: EmployeePublic[]
  departments: DepartmentPublic[]
  holidays: HolidayPublic[]
  onClose: () => void
}) {
  const date = day === null ? "" : `${month}-${String(day).padStart(2, "0")}`
  const rows = useMemo(
    () => (day === null ? [] : dayEmployeeRows(plans, employees, date)),
    [plans, employees, day, date],
  )
  const departmentNames = useMemo(
    () =>
      new Map(
        departments.map((department) => [department.id, department.dept_name]),
      ),
    [departments],
  )
  const unscheduled = useMemo(
    () =>
      employees.filter(
        (employee) =>
          employeeEmployedOn(employee, date) &&
          resolvePlan(plans, employee) === null,
      ),
    [employees, plans, date],
  )

  const workRows = rows.filter((row) => row.state === "work")
  const restRows = rows.filter((row) => row.state === "rest")

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent
        className="max-h-[88vh] overflow-y-auto sm:max-w-2xl"
        data-testid="day-sheet"
      >
        <DialogHeader>
          <DialogTitle>{date} 这天谁上班</DialogTitle>
          <DialogDescription>
            {date && `${dayKindLabel(dayKind(date, holidays))} · `}
            上班 {workRows.length} 人、休息 {restRows.length} 人、未排班{" "}
            {unscheduled.length}{" "}
            人。合并视图按方案精确度解析，人工例外需在员工明细中处理。
          </DialogDescription>
        </DialogHeader>

        {workRows.length > 0 && (
          <EmployeeGroup
            title="上班"
            rows={workRows}
            departmentNames={departmentNames}
          />
        )}
        {restRows.length > 0 && (
          <EmployeeGroup
            title="休息"
            rows={restRows}
            departmentNames={departmentNames}
          />
        )}
        {unscheduled.length > 0 && (
          <div className="space-y-1">
            <div className="text-sm font-medium text-amber-700 dark:text-amber-300">
              未排班
            </div>
            <div className="rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground">
              {unscheduled
                .map(
                  (employee) =>
                    `${employee.name}（${departmentNames.get(employee.dept_id) ?? "—"}）`,
                )
                .join("、")}
            </div>
          </div>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            关闭
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function EmployeeGroup({
  title,
  rows,
  departmentNames,
}: {
  title: string
  rows: ReturnType<typeof dayEmployeeRows>
  departmentNames: Map<string, string>
}) {
  return (
    <div className="space-y-1">
      <div className="text-sm font-medium">{title}</div>
      <div className="divide-y rounded-md border">
        {rows.map((row) => (
          <div
            key={row.employee.id}
            className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm"
          >
            <div>
              <span className="font-medium">{row.employee.name}</span>
              <span className="ml-2 text-xs text-muted-foreground">
                {row.employee.employee_no} ·{" "}
                {departmentNames.get(row.employee.dept_id) ?? "—"}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-1">
              {row.state === "work" ? (
                row.shifts.map((shift) => (
                  <Badge
                    key={`${shift.id}-${shift.seq}`}
                    variant="secondary"
                    style={{
                      backgroundColor: shift.shift_color
                        ? `${shift.shift_color}22`
                        : undefined,
                    }}
                  >
                    {shift.shift_name ?? shift.shift_code}
                  </Badge>
                ))
              ) : (
                <Badge variant="outline">{ROSTER_STATE_LABELS.rest}</Badge>
              )}
              <span className="text-xs text-muted-foreground">
                {row.plan.plan_name}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
