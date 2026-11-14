import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"

import {
  AttendanceRosterService,
  type EmployeePublic,
  type RosterEntryPublic,
  type RosterEntryShiftPublic,
  type ShiftPublic,
} from "@/client"
import { Badge } from "@/components/ui/badge"
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
import { Label } from "@/components/ui/label"
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
import { ROSTER_STATE_LABELS } from "@/lib/enums"
import { ConfirmDialog } from "./PreviewDialog"
import { invalidateRosterQueries } from "./roster-queries"

interface ManualExceptionDialogProps {
  open: boolean
  month: string
  employees: EmployeePublic[]
  shifts: ShiftPublic[]
  initialEmployeeId: string | null
  initialDate: string | null
  entry: RosterEntryPublic | null
  onClose: () => void
  onSaved: () => void
}

function employeesForDate(
  employees: EmployeePublic[],
  workDate: string,
): EmployeePublic[] {
  return employees.filter(
    (employee) =>
      employee.hire_date <= workDate &&
      (!employee.resign_date || employee.resign_date >= workDate),
  )
}

function initialShiftIds(
  entry: RosterEntryPublic | null,
  shifts: RosterEntryShiftPublic[] | undefined,
): string[] {
  if (!entry) return []
  return (shifts ?? entry.shifts ?? []).map((shift) => shift.shift_id)
}

export function ManualExceptionDialog({
  open,
  month,
  employees,
  shifts,
  initialEmployeeId,
  initialDate,
  entry,
  onClose,
  onSaved,
}: ManualExceptionDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const firstDay = `${month}-01`
  const [employeeId, setEmployeeId] = useState(initialEmployeeId ?? "")
  const [workDate, setWorkDate] = useState(initialDate ?? firstDay)
  const [state, setState] = useState<"work" | "rest">("work")
  const [selectedShiftIds, setSelectedShiftIds] = useState<string[]>([])
  const [note, setNote] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [deleteOpen, setDeleteOpen] = useState(false)

  const activeShifts = useMemo(
    () => shifts.filter((shift) => shift.is_active),
    [shifts],
  )

  useEffect(() => {
    if (!open) return
    const seededEmployeeId = entry?.employee_id ?? initialEmployeeId ?? ""
    const seededEmployee = employees.find(
      (employee) => employee.id === seededEmployeeId,
    )
    const earliestDate =
      seededEmployee && seededEmployee.hire_date > firstDay
        ? seededEmployee.hire_date
        : firstDay
    setEmployeeId(seededEmployeeId)
    setWorkDate(entry?.work_date ?? initialDate ?? earliestDate)
    setState(entry?.state ?? "work")
    setSelectedShiftIds(initialShiftIds(entry, entry?.shifts))
    setNote(entry?.note ?? "")
    setError(null)
    setFieldErrors({})
    setDeleteOpen(false)
  }, [open, entry, initialEmployeeId, initialDate, firstDay, employees])

  const employeeOptions = useMemo(
    () => employeesForDate(employees, workDate),
    [employees, workDate],
  )

  const toggleShift = (shiftId: string) => {
    setSelectedShiftIds((current) =>
      current.includes(shiftId)
        ? current.filter((item) => item !== shiftId)
        : [...current, shiftId],
    )
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      const shiftRows =
        state === "rest"
          ? []
          : selectedShiftIds.map((shiftId, seq) => ({ seq, shift_id: shiftId }))
      if (entry) {
        return (
          await AttendanceRosterService.updateRosterEntry({
            path: { entry_id: entry.id },
            body: { state, shifts: shiftRows, note: note || null },
          })
        ).data
      }
      return (
        await AttendanceRosterService.createRosterEntry({
          body: {
            employee_id: employeeId,
            work_date: workDate,
            state,
            shifts: shiftRows,
            note: note || null,
          },
        })
      ).data
    },
    onSuccess: () => {
      showSuccessToast(entry ? "人工例外已更新" : "人工例外已保存")
      invalidateRosterQueries(queryClient)
      onSaved()
    },
    onError: (mutationError) => {
      setFieldErrors(getFieldErrors(mutationError))
      setError(getErrorMessage(mutationError))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (!entry) throw new Error("missing entry")
      await AttendanceRosterService.deleteRosterEntry({
        path: { entry_id: entry.id },
      })
    },
    onSuccess: () => {
      showSuccessToast("人工例外已删除，已恢复方案排班或未排班")
      invalidateRosterQueries(queryClient)
      setDeleteOpen(false)
      onSaved()
    },
    onError: (mutationError) => {
      setError(getErrorMessage(mutationError))
      setDeleteOpen(false)
    },
  })

  const submit = () => {
    setError(null)
    setFieldErrors({})
    if (state === "work" && selectedShiftIds.length === 0) {
      setFieldErrors({ shifts: "上班至少选择一个班次" })
      setError("上班至少选择一个班次")
      return
    }
    if (!employeeId) {
      setFieldErrors({ employee_id: "请选择员工" })
      setError("请选择员工")
      return
    }
    saveMutation.mutate()
  }

  const title = entry ? "编辑人工例外" : "新建人工例外"
  const shiftError = fieldErrors.shifts
  const employeeError = fieldErrors.employee_id
  const dateError = fieldErrors.work_date

  return (
    <>
      <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
        <DialogContent
          className="max-h-[90vh] overflow-y-auto sm:max-w-lg"
          data-testid="manual-exception-dialog"
        >
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            <DialogDescription>
              人工例外优先于方案，删除后立即恢复当前方案解析；已确认或锁定的月份不可修改。
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="manual-employee">员工</Label>
              <Select
                value={employeeId}
                onValueChange={setEmployeeId}
                disabled={entry !== null}
              >
                <SelectTrigger id="manual-employee" className="w-full">
                  <SelectValue placeholder="选择员工" />
                </SelectTrigger>
                <SelectContent>
                  {employeeOptions.map((employee) => (
                    <SelectItem key={employee.id} value={employee.id}>
                      {employee.employee_no} {employee.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {employeeError && (
                <p className="text-sm text-destructive">{employeeError}</p>
              )}
            </div>

            <div className="space-y-1">
              <Label htmlFor="manual-date">日期</Label>
              <Input
                id="manual-date"
                type="date"
                value={workDate}
                min={`${month}-01`}
                max={`${month}-31`}
                disabled={entry !== null}
                onChange={(event) => setWorkDate(event.target.value)}
              />
              {dateError && (
                <p className="text-sm text-destructive">{dateError}</p>
              )}
            </div>

            <div className="space-y-1">
              <Label>状态</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant={state === "work" ? "default" : "outline"}
                  onClick={() => setState("work")}
                >
                  {ROSTER_STATE_LABELS.work}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={state === "rest" ? "default" : "outline"}
                  onClick={() => setState("rest")}
                >
                  {ROSTER_STATE_LABELS.rest}
                </Button>
              </div>
            </div>

            {state === "work" && (
              <div className="space-y-1">
                <Label>班次（可多选，勾选顺序即班次顺序）</Label>
                <div className="grid gap-1 rounded-md border p-2 sm:grid-cols-2">
                  {activeShifts.map((shift) => (
                    <label
                      key={shift.id}
                      className="flex items-center gap-2 rounded px-1 py-1 text-sm"
                      htmlFor={`manual-shift-${shift.id}`}
                    >
                      <Checkbox
                        id={`manual-shift-${shift.id}`}
                        aria-label={`班次 ${shift.shift_name}`}
                        checked={selectedShiftIds.includes(shift.id)}
                        onCheckedChange={() => toggleShift(shift.id)}
                      />
                      <span>{shift.shift_name}</span>
                      <span className="text-xs text-muted-foreground">
                        {shift.start_time.slice(0, 5)}–
                        {shift.end_time.slice(0, 5)}
                      </span>
                    </label>
                  ))}
                </div>
                {selectedShiftIds.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {selectedShiftIds.map((shiftId, index) => {
                      const shift = activeShifts.find(
                        (item) => item.id === shiftId,
                      )
                      return (
                        <Badge key={`${shiftId}-${index}`} variant="secondary">
                          {index + 1}. {shift?.shift_name ?? shiftId}
                        </Badge>
                      )
                    })}
                  </div>
                )}
                {shiftError && (
                  <p className="text-sm text-destructive">{shiftError}</p>
                )}
              </div>
            )}

            <div className="space-y-1">
              <Label htmlFor="manual-note">备注</Label>
              <Textarea
                id="manual-note"
                rows={2}
                value={note}
                maxLength={500}
                onChange={(event) => setNote(event.target.value)}
              />
            </div>

            {error && (
              <div
                role="alert"
                data-testid="manual-exception-error"
                className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
              >
                {error}
              </div>
            )}
          </div>

          <DialogFooter className="gap-2 sm:justify-between">
            <div>
              {entry && (
                <Button
                  type="button"
                  variant="destructive"
                  onClick={() => setDeleteOpen(true)}
                >
                  删除例外
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={onClose}>
                取消
              </Button>
              <LoadingButton
                type="button"
                loading={saveMutation.isPending}
                onClick={submit}
              >
                保存例外
              </LoadingButton>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteOpen}
        title="删除人工例外"
        description="删除后立即按当前启用方案重新解析该员工当天：有方案时恢复方案排班，没有方案时回到未排班。"
        confirmLabel="确认删除"
        destructive
        busy={deleteMutation.isPending}
        onConfirm={() => deleteMutation.mutate()}
        onClose={() => setDeleteOpen(false)}
      />
    </>
  )
}
