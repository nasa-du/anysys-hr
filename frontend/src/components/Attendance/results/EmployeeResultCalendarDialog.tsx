import type { AttendanceDayResultPublic } from "@/client"
import {
  monthDays,
  WEEKDAY_LABELS,
  weekdayIndex,
} from "@/components/Attendance/schedule/plan-utils"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { getErrorMessage } from "@/lib/api-error"

import { useResultCalendar } from "./queries"
import {
  dayStatusLabel,
  formatAmount,
  formatDecimal,
  formatFraction,
  formatHours,
  totalOtMinutes,
} from "./result-format"

type EmployeeResultCalendarDialogProps = {
  companyId: string
  month: string
  employeeId: string | null
  onOpenDay: (employeeId: string, workDate: string) => void
  onClose: () => void
}

function monthCells(month: string): Array<string | null> {
  const days = monthDays(month)
  const first = days[0]
  if (first === undefined) return []
  return [...Array<string | null>(weekdayIndex(first)).fill(null), ...days]
}

function CalendarDay({
  workDate,
  result,
  onOpen,
}: {
  workDate: string
  result: AttendanceDayResultPublic | undefined
  onOpen: () => void
}) {
  const day = Number(workDate.slice(8, 10))
  return (
    <button
      type="button"
      disabled={!result}
      onClick={onOpen}
      data-testid={`calendar-day-${workDate}`}
      className={`flex min-h-16 flex-col rounded-md border p-1 text-left text-xs transition-colors ${
        result
          ? result.is_abnormal
            ? "border-destructive/40 bg-destructive/10 hover:bg-destructive/20"
            : "hover:bg-accent"
          : "cursor-default text-muted-foreground/60"
      }`}
    >
      <span className="font-medium">{day}</span>
      {result ? (
        <>
          <span className="truncate">{dayStatusLabel(result.day_status)}</span>
          <span className="text-muted-foreground">
            出勤 {formatFraction(result.attendance_fraction)}
          </span>
          {totalOtMinutes(result) > 0 && (
            <span className="text-muted-foreground">
              加班 {formatHours(totalOtMinutes(result))}h
            </span>
          )}
        </>
      ) : (
        <span>无结果</span>
      )}
    </button>
  )
}

/** Employee result calendar: month summary plus one cell per calculated day. */
export function EmployeeResultCalendarDialog({
  companyId,
  month,
  employeeId,
  onOpenDay,
  onClose,
}: EmployeeResultCalendarDialogProps) {
  const query = useResultCalendar(companyId, month, employeeId)
  const calendar = query.data
  const byDate = new Map(
    (calendar?.days ?? []).map((day) => [day.work_date, day]),
  )
  const summary = calendar?.summary

  return (
    <Dialog
      open={employeeId !== null}
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
    >
      <DialogContent
        className="max-h-[90vh] overflow-y-auto sm:max-w-3xl"
        data-testid="result-calendar-dialog"
      >
        <DialogHeader>
          <DialogTitle>
            {calendar
              ? `${calendar.employee.employee_name} · ${month} 结果日历`
              : "员工结果日历"}
          </DialogTitle>
          <DialogDescription>
            {calendar
              ? `${calendar.employee.employee_no} · ${
                  calendar.employee.department_name ?? "—"
                }。点击有结果的日期查看四方对照。`
              : "月汇总与逐日结果"}
          </DialogDescription>
        </DialogHeader>

        {query.isLoading ? (
          <LoadingState rows={4} />
        ) : query.isError ? (
          <ErrorState
            message={getErrorMessage(query.error)}
            onRetry={() => void query.refetch()}
          />
        ) : calendar ? (
          (calendar.days ?? []).length === 0 && !summary ? (
            <EmptyState
              title={`${month} 还没有该员工的结果`}
              message="导入打卡与 OA 数据并重新计算后，这里会显示月汇总与逐日结果。"
            />
          ) : (
            <div className="space-y-4">
              {summary ? (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <div className="rounded-md border p-2 text-sm">
                    <div className="text-xs text-muted-foreground">应出勤</div>
                    <div className="text-lg font-semibold">
                      {formatFraction(
                        Number(summary.weekday_full) +
                          Number(summary.weekend_full),
                      )}
                    </div>
                  </div>
                  <div className="rounded-md border p-2 text-sm">
                    <div className="text-xs text-muted-foreground">
                      实际出勤
                    </div>
                    <div className="text-lg font-semibold">
                      {formatFraction(
                        Number(summary.weekday_attended) +
                          Number(summary.weekend_attended),
                      )}
                    </div>
                  </div>
                  <div className="rounded-md border p-2 text-sm">
                    <div className="text-xs text-muted-foreground">
                      加班合计
                    </div>
                    <div className="text-lg font-semibold">
                      {formatDecimal(
                        Number(summary.ot_weekday_hours) +
                          Number(summary.ot_weekend_hours) +
                          Number(summary.ot_holiday_hours),
                      )}{" "}
                      h
                    </div>
                  </div>
                  <div className="rounded-md border p-2 text-sm">
                    <div className="text-xs text-muted-foreground">
                      扣款建议
                    </div>
                    <div className="text-lg font-semibold">
                      {formatAmount(summary.attendance_deduct)}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="rounded-md border px-3 py-2 text-sm text-muted-foreground">
                  {month} 还没有该员工的月汇总。
                </p>
              )}

              <div className="grid grid-cols-7 gap-1 text-center text-xs font-medium text-muted-foreground">
                {WEEKDAY_LABELS.map((weekday) => (
                  <span key={weekday}>{weekday}</span>
                ))}
              </div>
              <div className="grid grid-cols-7 gap-1">
                {monthCells(month).map((workDate, index) =>
                  workDate === null ? (
                    <div key={`blank-${index}`} />
                  ) : (
                    <CalendarDay
                      key={workDate}
                      workDate={workDate}
                      result={byDate.get(workDate)}
                      onOpen={() =>
                        onOpenDay(calendar.employee.employee_id, workDate)
                      }
                    />
                  ),
                )}
              </div>
            </div>
          )
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
