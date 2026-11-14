import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"

import {
  AttendanceSchedulePlansService,
  type DepartmentPublic,
  type EmployeePublic,
  type PositionPublic,
  type SchedulePlanPreview,
  type SchedulePlanPublic,
  type ShiftPublic,
} from "@/client"
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
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorMessage, getFieldErrors } from "@/lib/api-error"
import {
  type AttendanceScheduleScopeType,
  SCHEDULE_SCOPE_TYPE_LABELS,
} from "@/lib/enums"
import { PreviewBody } from "./PreviewDialog"
import {
  employeeIsEmployedInMonth,
  monthDays,
  monthLastDay,
  WEEKDAY_LABELS,
  weekdayIndex,
} from "./plan-utils"
import { invalidatePlanQueries } from "./queries"

interface PlanDraft {
  plan_name: string
  scope_type: AttendanceScheduleScopeType
  scope_ids: string[]
  days: Record<number, string[]>
  note: string
}

function draftFromPlan(plan: SchedulePlanPublic | null): PlanDraft {
  if (!plan) {
    return {
      plan_name: "",
      scope_type: "all",
      scope_ids: [],
      days: {},
      note: "",
    }
  }
  const days: Record<number, string[]> = {}
  for (const day of [...(plan.days ?? [])].sort(
    (left, right) => left.seq - right.seq,
  )) {
    days[day.day_of_month] = [...(days[day.day_of_month] ?? []), day.shift_id]
  }
  return {
    plan_name: plan.plan_name,
    scope_type: plan.scope_type,
    scope_ids: (plan.scopes ?? []).map((scope) => scope.scope_id),
    days,
    note: plan.note ?? "",
  }
}

export function PlanEditorDialog({
  open,
  companyId,
  month,
  plan,
  initialDay = 1,
  departments,
  positions,
  employees,
  shifts,
  onClose,
  onSaved,
}: {
  open: boolean
  companyId: string
  month: string
  plan: SchedulePlanPublic | null
  initialDay?: number
  departments: DepartmentPublic[]
  positions: PositionPublic[]
  employees: EmployeePublic[]
  shifts: ShiftPublic[]
  onClose: () => void
  onSaved: () => void
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [draft, setDraft] = useState<PlanDraft>(() => draftFromPlan(plan))
  const [selectedDay, setSelectedDay] = useState(initialDay)
  const [preview, setPreview] = useState<SchedulePlanPreview | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setDraft(draftFromPlan(plan))
      setSelectedDay(initialDay)
      setPreview(null)
      setError(null)
    }
  }, [open, plan, initialDay])

  const activeShifts = useMemo(
    () => shifts.filter((shift) => shift.is_active),
    [shifts],
  )
  const lastDay = monthLastDay(month)

  const employeeOptions = useMemo(
    () =>
      employees
        .filter((employee) => employeeIsEmployedInMonth(employee, month))
        .sort((left, right) =>
          left.employee_no.localeCompare(right.employee_no),
        ),
    [employees, month],
  )

  const setDayShifts = (day: number, shiftIds: string[]) => {
    setDraft((current) => ({
      ...current,
      days: { ...current.days, [day]: shiftIds },
    }))
  }

  const toggleShift = (day: number, shiftId: string) => {
    const current = draft.days[day] ?? []
    setDayShifts(
      day,
      current.includes(shiftId)
        ? current.filter((item) => item !== shiftId)
        : [...current, shiftId],
    )
  }

  const applyToWeekdays = () => {
    const selected = draft.days[selectedDay] ?? []
    const next = { ...draft.days }
    for (let day = 1; day <= lastDay; day += 1) {
      const date = `${month}-${String(day).padStart(2, "0")}`
      if (weekdayIndex(date) < 5) next[day] = [...selected]
    }
    setDraft((current) => ({ ...current, days: next }))
  }

  const clearDay = () => setDayShifts(selectedDay, [])

  const clearAll = () => setDraft((current) => ({ ...current, days: {} }))

  const toggleScope = (scopeId: string) => {
    setDraft((current) => ({
      ...current,
      scope_ids: current.scope_ids.includes(scopeId)
        ? current.scope_ids.filter((item) => item !== scopeId)
        : [...current.scope_ids, scopeId],
    }))
  }

  const scopeOptions = useMemo(() => {
    if (draft.scope_type === "dept") {
      return departments.map((department) => ({
        id: department.id,
        label: `${department.dept_code} ${department.dept_name}${
          department.is_active ? "" : "（已停用）"
        }`,
        disabled:
          !department.is_active && !draft.scope_ids.includes(department.id),
      }))
    }
    if (draft.scope_type === "position") {
      return positions.map((position) => ({
        id: position.id,
        label: `${position.position_code} ${position.position_name}${
          position.is_active ? "" : "（已停用）"
        }`,
        disabled: !position.is_active && !draft.scope_ids.includes(position.id),
      }))
    }
    if (draft.scope_type === "employee") {
      return employeeOptions.map((employee) => ({
        id: employee.id,
        label: `${employee.employee_no} ${employee.name}`,
        disabled: false,
      }))
    }
    return []
  }, [
    draft.scope_type,
    draft.scope_ids,
    departments,
    positions,
    employeeOptions,
  ])

  const invalidate = () => {
    invalidatePlanQueries(queryClient)
    onSaved()
  }

  const previewMutation = useMutation({
    mutationFn: async () => {
      const response = await AttendanceSchedulePlansService.previewSchedulePlan(
        {
          body: {
            company_id: companyId,
            month,
            plan_id: plan?.id ?? null,
            scope_type: draft.scope_type,
            scope_ids: draft.scope_ids,
            days: serializeDays(draft),
          },
        },
      )
      return response.data
    },
    onSuccess: (data) => {
      setError(null)
      setPreview(data)
    },
    onError: (mutationError) => {
      const fieldErrors = getFieldErrors(mutationError)
      setError(
        fieldErrors.scope_ids ??
          fieldErrors.days ??
          getErrorMessage(mutationError),
      )
    },
  })

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (plan) {
        const response =
          await AttendanceSchedulePlansService.updateSchedulePlan({
            path: { plan_id: plan.id },
            body: {
              plan_name: draft.plan_name.trim(),
              scope_type: draft.scope_type,
              scope_ids: draft.scope_ids,
              days: serializeDays(draft),
              note: draft.note.trim() || null,
            },
          })
        return response.data
      }
      const response = await AttendanceSchedulePlansService.createSchedulePlan({
        body: {
          company_id: companyId,
          month,
          plan_name: draft.plan_name.trim(),
          scope_type: draft.scope_type,
          scope_ids: draft.scope_ids,
          days: serializeDays(draft),
          note: draft.note.trim() || null,
        },
      })
      return response.data
    },
    onSuccess: () => {
      showSuccessToast(
        plan
          ? "排班方案已保存并重新展开；已计算月份标记为结果过期"
          : "排班方案已创建并展开为员工日明细",
      )
      setPreview(null)
      invalidate()
    },
    onError: (mutationError) => {
      showErrorToast(getErrorMessage(mutationError))
    },
  })

  const requestPreview = () => {
    const name = draft.plan_name.trim()
    if (!name) {
      setError("请填写方案名称")
      return
    }
    if (draft.scope_type !== "all" && draft.scope_ids.length === 0) {
      setError("请至少选择一个排班范围")
      return
    }
    setError(null)
    previewMutation.mutate()
  }

  const busy = previewMutation.isPending || saveMutation.isPending

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent
        className="max-h-[92vh] overflow-y-auto sm:max-w-4xl"
        data-testid="plan-editor"
      >
        <DialogHeader>
          <DialogTitle>{plan ? "编辑排班方案" : "新建排班方案"}</DialogTitle>
          <DialogDescription>
            方案按「公司 + 月份 +
            范围」创建，保存即展开为员工日明细；同精确度范围不能重叠。
          </DialogDescription>
        </DialogHeader>

        {preview ? (
          <div className="space-y-4">
            <PreviewBody data={preview} />
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setPreview(null)}
              >
                返回修改
              </Button>
              <LoadingButton
                type="button"
                loading={saveMutation.isPending}
                disabled={!preview.can_apply}
                onClick={() => saveMutation.mutate()}
              >
                {plan ? "保存并重新展开" : "保存并展开"}
              </LoadingButton>
            </DialogFooter>
          </div>
        ) : (
          <div className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="plan-name">
                  方案名称
                </label>
                <Input
                  id="plan-name"
                  aria-label="方案名称"
                  maxLength={100}
                  placeholder={`例如：${month} 标准班`}
                  value={draft.plan_name}
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      plan_name: event.target.value,
                    }))
                  }
                />
              </div>
              <div className="space-y-2">
                <label
                  className="text-sm font-medium"
                  htmlFor="plan-scope-type"
                >
                  排班范围
                </label>
                <Select
                  value={draft.scope_type}
                  onValueChange={(value) =>
                    setDraft((current) => ({
                      ...current,
                      scope_type: value as AttendanceScheduleScopeType,
                      scope_ids: [],
                    }))
                  }
                >
                  <SelectTrigger id="plan-scope-type" aria-label="排班范围">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(["all", "dept", "position", "employee"] as const).map(
                      (value) => (
                        <SelectItem key={value} value={value}>
                          {SCHEDULE_SCOPE_TYPE_LABELS[value]}
                        </SelectItem>
                      ),
                    )}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {draft.scope_type !== "all" && (
              <div className="space-y-2">
                <div className="text-sm font-medium">
                  选择{SCHEDULE_SCOPE_TYPE_LABELS[draft.scope_type]}
                  <span className="ml-2 text-xs font-normal text-muted-foreground">
                    已选 {draft.scope_ids.length} 项
                  </span>
                </div>
                <div className="max-h-40 space-y-1 overflow-y-auto rounded-md border p-2">
                  {scopeOptions.length === 0 ? (
                    <p className="px-2 py-1 text-sm text-muted-foreground">
                      当前公司暂无可用选项。
                    </p>
                  ) : (
                    scopeOptions.map((option) => (
                      <label
                        key={option.id}
                        htmlFor={`scope-${option.id}`}
                        className="flex items-center gap-2 rounded px-2 py-1 text-sm hover:bg-muted/60"
                      >
                        <Checkbox
                          id={`scope-${option.id}`}
                          checked={draft.scope_ids.includes(option.id)}
                          disabled={option.disabled}
                          onCheckedChange={() => toggleScope(option.id)}
                          aria-label={option.label}
                        />
                        {option.label}
                      </label>
                    ))
                  )}
                </div>
              </div>
            )}

            <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
              <div className="space-y-2">
                <div className="text-sm font-medium">按日期排班</div>
                <div className="grid grid-cols-7 gap-1 text-center text-xs text-muted-foreground">
                  {WEEKDAY_LABELS.map((label) => (
                    <div key={label} className="py-1">
                      周{label}
                    </div>
                  ))}
                  {Array.from({
                    length: weekdayIndex(`${month}-01`),
                  }).map((_, index) => (
                    <div key={`lead-${index}`} />
                  ))}
                  {monthDays(month).map((date) => {
                    const day = Number(date.slice(8, 10))
                    const shiftIds = draft.days[day] ?? []
                    const isSelected = selectedDay === day
                    return (
                      <button
                        key={date}
                        type="button"
                        data-testid={`plan-day-${day}`}
                        aria-label={`第 ${day} 天`}
                        onClick={() => setSelectedDay(day)}
                        className={`min-h-16 rounded-md border p-1 text-left transition ${
                          isSelected
                            ? "border-primary ring-2 ring-primary/30"
                            : "hover:border-primary/40"
                        }`}
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-medium">{day}</span>
                          <span className="text-[10px] text-muted-foreground">
                            周{WEEKDAY_LABELS[weekdayIndex(date)]}
                          </span>
                        </div>
                        <div className="mt-1 space-y-0.5">
                          {shiftIds.length === 0 ? (
                            <span className="text-[11px] text-muted-foreground">
                              休
                            </span>
                          ) : (
                            shiftIds.map((shiftId) => (
                              <div
                                key={shiftId}
                                className="truncate rounded bg-primary/10 px-1 text-[10px] text-primary"
                              >
                                {shifts.find((shift) => shift.id === shiftId)
                                  ?.shift_code ?? shiftId}
                              </div>
                            ))
                          )}
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>

              <div className="space-y-3">
                <div className="text-sm font-medium">
                  第 {selectedDay} 天班次
                  <span className="ml-2 text-xs font-normal text-muted-foreground">
                    不勾选即为休息
                  </span>
                </div>
                <div className="max-h-56 space-y-1 overflow-y-auto rounded-md border p-2">
                  {activeShifts.length === 0 ? (
                    <p className="px-2 py-1 text-sm text-muted-foreground">
                      当前公司没有启用中的班次，请先到「班次」页面创建。
                    </p>
                  ) : (
                    activeShifts.map((shift) => (
                      <label
                        key={shift.id}
                        htmlFor={`day-${selectedDay}-shift-${shift.id}`}
                        className="flex items-center gap-2 rounded px-2 py-1 text-sm hover:bg-muted/60"
                      >
                        <Checkbox
                          id={`day-${selectedDay}-shift-${shift.id}`}
                          checked={(draft.days[selectedDay] ?? []).includes(
                            shift.id,
                          )}
                          onCheckedChange={() =>
                            toggleShift(selectedDay, shift.id)
                          }
                          aria-label={`第 ${selectedDay} 天 ${shift.shift_name}`}
                        />
                        {shift.shift_name}
                        <span className="ml-auto text-xs text-muted-foreground">
                          {shift.start_time.slice(0, 5)}–
                          {shift.end_time.slice(0, 5)}
                        </span>
                      </label>
                    ))
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={applyToWeekdays}
                  >
                    应用到工作日
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={clearDay}
                  >
                    清空第 {selectedDay} 天
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={clearAll}
                  >
                    清空全部
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  当前方案共{" "}
                  {
                    Object.values(draft.days).filter((value) => value.length)
                      .length
                  }{" "}
                  个工作日、
                  {Object.values(draft.days).reduce(
                    (sum, value) => sum + value.length,
                    0,
                  )}{" "}
                  个班次。
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="plan-note">
                备注
              </label>
              <Textarea
                id="plan-note"
                aria-label="方案备注"
                maxLength={500}
                rows={2}
                value={draft.note}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    note: event.target.value,
                  }))
                }
              />
            </div>

            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                取消
              </Button>
              <LoadingButton
                type="button"
                loading={previewMutation.isPending}
                disabled={busy}
                onClick={requestPreview}
              >
                预览并保存
              </LoadingButton>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

function serializeDays(draft: PlanDraft) {
  return Object.entries(draft.days)
    .flatMap(([day, shiftIds]) =>
      shiftIds.map((shiftId, seq) => ({
        day_of_month: Number(day),
        seq,
        shift_id: shiftId,
      })),
    )
    .sort(
      (left, right) =>
        left.day_of_month - right.day_of_month || left.seq - right.seq,
    )
}
