import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"

import {
  AttendanceHolidaysService,
  AttendanceRosterService,
  type DepartmentPublic,
  type EmployeePublic,
  type ShiftPublic,
} from "@/client"
import { holidaysQueryKey } from "@/components/Attendance/rules/queries"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorMessage, getFieldErrors } from "@/lib/api-error"
import {
  employeeEmployedOn,
  employeeIsEmployedInMonth,
  monthDays,
  WEEKDAY_LABELS,
  weekdayIndex,
} from "./plan-utils"
import {
  fetchAllManualEntries,
  invalidateRosterQueries,
  rosterEntriesQueryKey,
} from "./roster-queries"

type BatchMode = "workdays" | "month" | "clear"
type BatchState = "work" | "rest"

const WEEKDAY_INDEXES = [0, 1, 2, 3, 4, 5, 6]

export function BatchFillDialog({
  open,
  companyId,
  month,
  employees,
  departments,
  shifts,
  onClose,
  onApplied,
}: {
  open: boolean
  companyId: string
  month: string
  employees: EmployeePublic[]
  departments: DepartmentPublic[]
  shifts: ShiftPublic[]
  onClose: () => void
  onApplied: () => void
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [mode, setMode] = useState<BatchMode>("workdays")
  const [state, setState] = useState<BatchState>("work")
  const [weekdays, setWeekdays] = useState<number[]>([0, 1, 2, 3, 4])
  const [selectedShiftIds, setSelectedShiftIds] = useState<string[]>([])
  const [deptId, setDeptId] = useState<string>("all")
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!open) return
    setMode("workdays")
    setState("work")
    setWeekdays([0, 1, 2, 3, 4])
    setSelectedShiftIds([])
    setDeptId("all")
    setError(null)
    setFieldErrors({})
  }, [open])

  const year = Number(month.slice(0, 4))
  const holidaysQuery = useQuery({
    queryKey: holidaysQueryKey(companyId, year),
    enabled: open,
    queryFn: async () => {
      const response = await AttendanceHolidaysService.readHolidays({
        query: { company_id: companyId, year, limit: 500 },
      })
      // Share the same cached shape as HolidayCalendar (the paginated
      // response); both use holidaysQueryKey, so the cache must agree.
      return response.data
    },
  })
  const manualEntriesQuery = useQuery({
    queryKey: rosterEntriesQueryKey(companyId, { month, source: "manual" }),
    enabled: open,
    queryFn: () => fetchAllManualEntries(companyId, month),
  })

  const activeShifts = useMemo(
    () => shifts.filter((shift) => shift.is_active),
    [shifts],
  )

  const scopeEmployees = useMemo(
    () =>
      employees.filter(
        (employee) =>
          employeeIsEmployedInMonth(employee, month) &&
          (deptId === "all" || employee.dept_id === deptId),
      ),
    [employees, month, deptId],
  )

  const holidayDates = useMemo(
    () =>
      new Set(
        (holidaysQuery.data?.data ?? [])
          .filter((holiday) => holiday.day_type === "holiday")
          .map((holiday) => holiday.date),
      ),
    [holidaysQuery.data],
  )

  const eligibleDates = useMemo(() => {
    const allDates = monthDays(month)
    if (mode === "clear") return allDates
    const weekdayDates =
      mode === "month"
        ? allDates
        : allDates.filter((date) => weekdays.includes(weekdayIndex(date)))
    return state === "work"
      ? weekdayDates.filter((date) => !holidayDates.has(date))
      : weekdayDates
  }, [mode, month, weekdays, state, holidayDates])

  const personDays = useMemo(() => {
    let count = 0
    for (const employee of scopeEmployees) {
      for (const date of eligibleDates) {
        if (employeeEmployedOn(employee, date)) count += 1
      }
    }
    return count
  }, [scopeEmployees, eligibleDates])

  const eligibleDateSet = useMemo(() => new Set(eligibleDates), [eligibleDates])

  const employeeById = useMemo(
    () => new Map(employees.map((employee) => [employee.id, employee])),
    [employees],
  )

  const manualEntriesInRange = useMemo(() => {
    const employeeIds = new Set(scopeEmployees.map((employee) => employee.id))
    return (manualEntriesQuery.data ?? []).filter((entry) => {
      const employee = employeeById.get(entry.employee_id)
      return (
        employee !== undefined &&
        employeeIds.has(entry.employee_id) &&
        eligibleDateSet.has(entry.work_date) &&
        employeeEmployedOn(employee, entry.work_date)
      )
    })
  }, [manualEntriesQuery.data, scopeEmployees, eligibleDateSet, employeeById])

  const toggleWeekday = (index: number) => {
    setWeekdays((current) =>
      current.includes(index)
        ? current.filter((item) => item !== index)
        : [...current, index],
    )
  }

  const toggleShift = (shiftId: string) => {
    setSelectedShiftIds((current) =>
      current.includes(shiftId)
        ? current.filter((item) => item !== shiftId)
        : [...current, shiftId],
    )
  }

  const applyMutation = useMutation({
    mutationFn: async () => {
      if (mode === "clear") {
        return (
          await AttendanceRosterService.batchRosterEntries({
            body: {
              company_id: companyId,
              entries: [],
              delete_entry_ids: manualEntriesInRange.map((entry) => entry.id),
            },
          })
        ).data
      }
      const shiftRows = selectedShiftIds.map((shiftId, seq) => ({
        seq,
        shift_id: shiftId,
      }))
      const entries: Array<{
        employee_id: string
        work_date: string
        state: BatchState
        shifts: typeof shiftRows
      }> = []
      for (const employee of scopeEmployees) {
        for (const date of eligibleDates) {
          if (!employeeEmployedOn(employee, date)) continue
          entries.push({
            employee_id: employee.id,
            work_date: date,
            state,
            shifts: state === "work" ? shiftRows : [],
          })
        }
      }
      return (
        await AttendanceRosterService.batchRosterEntries({
          body: {
            company_id: companyId,
            entries,
            delete_entry_ids: [],
          },
        })
      ).data
    },
    onSuccess: (result) => {
      invalidateRosterQueries(queryClient)
      onApplied()
      showSuccessToast(
        mode === "clear"
          ? `已清除 ${result.deleted} 条人工例外并恢复方案排班`
          : `已批量调整 ${result.created + result.updated} 人日`,
      )
    },
    onError: (mutationError) => {
      setFieldErrors(getFieldErrors(mutationError))
      setError(getErrorMessage(mutationError))
      showErrorToast(getErrorMessage(mutationError))
    },
  })

  const submit = () => {
    setError(null)
    setFieldErrors({})
    if (mode !== "clear" && state === "work" && selectedShiftIds.length === 0) {
      setError("上班填充至少选择一个班次")
      return
    }
    if (mode !== "clear" && scopeEmployees.length === 0) {
      setError("当前范围内没有可排班的员工")
      return
    }
    applyMutation.mutate()
  }

  const busy = applyMutation.isPending
  const disabled =
    busy ||
    (mode !== "clear" && state === "work" && selectedShiftIds.length === 0) ||
    (mode === "clear" && manualEntriesInRange.length === 0)

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent
        className="max-h-[90vh] overflow-y-auto sm:max-w-2xl"
        data-testid="batch-fill-dialog"
      >
        <DialogHeader>
          <DialogTitle>批量填充</DialogTitle>
          <DialogDescription>
            批量创建人工例外，按当前范围覆盖方案排班；清除会删除范围内的人工例外并立即恢复方案解析。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1">
            <Label>部门范围</Label>
            <Select value={deptId} onValueChange={setDeptId}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部部门</SelectItem>
                {departments
                  .filter((department) => department.is_active)
                  .map((department) => (
                    <SelectItem key={department.id} value={department.id}>
                      {department.dept_name}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label>填充方式</Label>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant={mode === "workdays" ? "default" : "outline"}
                onClick={() => setMode("workdays")}
              >
                工作日填充
              </Button>
              <Button
                type="button"
                size="sm"
                variant={mode === "month" ? "default" : "outline"}
                onClick={() => setMode("month")}
              >
                整月填充
              </Button>
              <Button
                type="button"
                size="sm"
                variant={mode === "clear" ? "default" : "outline"}
                onClick={() => setMode("clear")}
              >
                清除人工例外
              </Button>
            </div>
          </div>

          {mode === "workdays" && (
            <div className="space-y-1">
              <Label>星期</Label>
              <div className="flex flex-wrap gap-1">
                {WEEKDAY_INDEXES.map((index) => (
                  <Button
                    key={index}
                    type="button"
                    size="sm"
                    variant={weekdays.includes(index) ? "default" : "outline"}
                    onClick={() => toggleWeekday(index)}
                  >
                    周{WEEKDAY_LABELS[index]}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {mode !== "clear" && (
            <>
              <div className="space-y-1">
                <Label>填充状态</Label>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant={state === "work" ? "default" : "outline"}
                    onClick={() => setState("work")}
                  >
                    上班
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant={state === "rest" ? "default" : "outline"}
                    onClick={() => setState("rest")}
                  >
                    休息
                  </Button>
                </div>
              </div>

              {state === "work" && (
                <div className="space-y-1">
                  <Label>班次（可多选）</Label>
                  <div className="grid gap-1 rounded-md border p-2 sm:grid-cols-2">
                    {activeShifts.map((shift) => (
                      <label
                        key={shift.id}
                        className="flex items-center gap-2 rounded px-1 py-1 text-sm"
                        htmlFor={`batch-shift-${shift.id}`}
                      >
                        <Checkbox
                          id={`batch-shift-${shift.id}`}
                          aria-label={`班次 ${shift.shift_name}`}
                          checked={selectedShiftIds.includes(shift.id)}
                          onCheckedChange={() => toggleShift(shift.id)}
                        />
                        <span>{shift.shift_name}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          <div className="space-y-1">
            <Label>影响预览</Label>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <PreviewTile label="影响员工" value={scopeEmployees.length} />
              <PreviewTile label="影响日期" value={eligibleDates.length} />
              <PreviewTile
                label={mode === "clear" ? "删除例外" : "预计人日"}
                value={
                  mode === "clear" ? manualEntriesInRange.length : personDays
                }
              />
              <PreviewTile
                label="人工例外"
                value={manualEntriesInRange.length}
                hint={mode === "clear" ? "将被删除" : "将被覆盖"}
              />
            </div>
          </div>

          {mode === "clear" && (
            <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100">
              清除只删除人工例外；方案生成的排班会在删除后立即恢复。
            </div>
          )}

          {error && (
            <div
              role="alert"
              data-testid="batch-fill-error"
              className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
            >
              <div>{error}</div>
              {Object.keys(fieldErrors).length > 0 && (
                <ul className="mt-1 list-disc space-y-1 pl-5 text-xs">
                  {Object.entries(fieldErrors)
                    .slice(0, 5)
                    .map(([field, message]) => (
                      <li key={field}>
                        {formatBatchField(field)}：{message}
                      </li>
                    ))}
                </ul>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            取消
          </Button>
          <LoadingButton
            type="button"
            loading={busy}
            disabled={disabled}
            onClick={submit}
          >
            应用批量调整
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

const FIELD_LABELS: Record<string, string> = {
  employee_id: "员工",
  work_date: "日期",
  shifts: "班次",
  entry_id: "明细",
  note: "备注",
}

/** Turn ``entries[2].work_date`` into a user-facing Chinese label. */
function formatBatchField(field: string): string {
  const entryMatch = field.match(/^entries\[(\d+)\]\.(.+)$/)
  if (entryMatch) {
    const index = Number(entryMatch[1]) + 1
    const label = FIELD_LABELS[entryMatch[2]] ?? entryMatch[2]
    return `第 ${index} 条 · ${label}`
  }
  const deleteMatch = field.match(/^delete_entry_ids\[(\d+)\]$/)
  if (deleteMatch) {
    return `删除第 ${Number(deleteMatch[1]) + 1} 条`
  }
  return field
}

function PreviewTile({
  label,
  value,
  hint,
}: {
  label: string
  value: number
  hint?: string
}) {
  return (
    <div className="rounded-lg border px-3 py-2">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-xl font-semibold">{value}</div>
      {hint && <div className="text-[10px] text-muted-foreground">{hint}</div>}
    </div>
  )
}
