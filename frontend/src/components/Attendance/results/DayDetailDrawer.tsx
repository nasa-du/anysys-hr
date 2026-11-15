import type { ReactNode } from "react"

import type { AttendanceDayDetailPublic } from "@/client"
import {
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Badge } from "@/components/ui/badge"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { getErrorMessage } from "@/lib/api-error"
import { formatDateTimeShanghai } from "@/lib/datetime"
import {
  ADJUSTMENT_STATUS_LABELS,
  type AttendanceDayStatus,
  DAY_TYPE_LABELS,
  ROSTER_SOURCE_LABELS,
} from "@/lib/enums"

import { FourWayTimeline } from "./FourWayTimeline"
import { useDayDetail } from "./queries"
import {
  dayFlagLabel,
  dayStatusLabel,
  dayStatusVariant,
  formatAmount,
  formatClock,
  formatFraction,
  formatHours,
  formatMinutes,
  formatWorkDate,
  leaveKindLabel,
  rosterStateLabel,
  shanghaiDate,
  totalOtMinutes,
  tripKindLabel,
} from "./result-format"

function shiftPunch(value: string | null | undefined, workDate: string) {
  if (!value) return <span className="text-destructive">缺</span>
  const nextDay = shanghaiDate(value) !== workDate ? "次日 " : ""
  return `${nextDay}${formatClock(value)}`
}

function FourCard({
  title,
  testId,
  children,
}: {
  title: string
  testId: string
  children: ReactNode
}) {
  return (
    <div className="rounded-lg border p-3" data-testid={testId}>
      <h4 className="mb-2 text-sm font-medium">{title}</h4>
      <div className="space-y-1 text-sm">{children}</div>
    </div>
  )
}

function Line({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right">{children}</span>
    </div>
  )
}

function adjustmentValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return "—"
  if (key === "day_status") {
    return dayStatusLabel(value as AttendanceDayStatus)
  }
  return String(value)
}

function DetailBody({ detail }: { detail: AttendanceDayDetailPublic }) {
  const result = detail.day_result
  const workDate = result.work_date
  const roster = detail.roster_entry
  const rosterShifts = roster?.shifts ?? []
  const punches = detail.punches ?? []
  const trips = detail.oa_trips ?? []
  const leaves = detail.oa_leaves ?? []
  const overtimeDays = detail.oa_overtime_days ?? []
  const dayFlags = result.day_flags ?? []
  const adjustments = detail.adjustments ?? []

  return (
    <div className="space-y-5">
      <div
        className="grid gap-3 sm:grid-cols-2"
        data-testid="four-way-comparison"
      >
        <FourCard title="排班" testId="four-card-roster">
          {roster ? (
            <>
              <Line label="状态">{rosterStateLabel(roster.state)}</Line>
              <Line label="来源">
                {ROSTER_SOURCE_LABELS[roster.source] ?? roster.source}
              </Line>
              <Line label="班次">
                {rosterShifts.length > 0
                  ? rosterShifts
                      .map(
                        (shift) =>
                          `${shift.shift_name} ${shift.start_time.slice(0, 5)}–${shift.end_time.slice(0, 5)}`,
                      )
                      .join("、")
                  : "—"}
              </Line>
              <Line label="排班工时">
                {formatHours(result.scheduled_minutes)} h
              </Line>
            </>
          ) : (
            <p className="text-muted-foreground">当天没有排班明细</p>
          )}
        </FourCard>

        <FourCard title="打卡" testId="four-card-punch">
          {punches.length > 0 ? (
            <>
              {punches.map((punch) => (
                <Line
                  key={punch.id}
                  label={`${shanghaiDate(punch.punch_time).slice(5)} ${formatClock(punch.punch_time)}`}
                >
                  {punch.punch_result_raw}
                </Line>
              ))}
              <Line label="迟到 / 早退">
                {result.late_minutes} / {result.early_minutes} 分钟
              </Line>
            </>
          ) : (
            <p className="text-muted-foreground">无有效打卡</p>
          )}
        </FourCard>

        <FourCard title="OA 申请" testId="four-card-oa">
          {trips.length === 0 &&
          leaves.length === 0 &&
          overtimeDays.length === 0 ? (
            <p className="text-muted-foreground">无 OA 申请</p>
          ) : (
            <>
              {trips.map((trip) => (
                <Line
                  key={trip.id}
                  label={tripKindLabel(
                    trip.application_type_raw?.includes("出差")
                      ? "business"
                      : "out",
                  )}
                >
                  {formatClock(trip.start_at)}–{formatClock(trip.end_at)}
                  {trip.approval_no ? ` · ${trip.approval_no}` : ""}
                </Line>
              ))}
              {leaves.map((leave) => (
                <Line key={leave.id} label={leaveKindLabel(leave.leave_kind)}>
                  {formatFraction(leave.days)} 天
                  {leave.approval_no ? ` · ${leave.approval_no}` : ""}
                </Line>
              ))}
              {overtimeDays.map((day) => (
                <Line key={day.id} label="OA 加班">
                  {formatMinutes(day.minutes)}
                </Line>
              ))}
            </>
          )}
        </FourCard>

        <FourCard title="结果" testId="four-card-result">
          <Line label="出勤比例">
            {formatFraction(result.attendance_fraction)}
          </Line>
          <Line label="实际工时">{formatHours(result.worked_minutes)} h</Line>
          <Line label="加班">{formatHours(totalOtMinutes(result))} h</Line>
          <Line label="缺卡张数">{result.missing_punch_count}</Line>
          <Line label="扣款">{formatAmount(result.deduction_total)}</Line>
        </FourCard>
      </div>

      <FourWayTimeline detail={detail} />

      <section className="space-y-2">
        <h3 className="text-sm font-medium">班次结果</h3>
        {detail.shift_results.length === 0 ? (
          <p className="rounded-md border px-3 py-2 text-sm text-muted-foreground">
            当天没有排班班次；结果按未排班 / 休息日规则处理。
          </p>
        ) : (
          <div className="overflow-x-auto rounded-md border">
            <Table data-testid="shift-result-table">
              <TableHeader>
                <TableRow>
                  <TableHead>班次</TableHead>
                  <TableHead>排班</TableHead>
                  <TableHead>上班卡</TableHead>
                  <TableHead>下班卡</TableHead>
                  <TableHead>午休卡</TableHead>
                  <TableHead className="text-right">排班工时</TableHead>
                  <TableHead className="text-right">实际工时</TableHead>
                  <TableHead>迟到 / 早退</TableHead>
                  <TableHead className="text-right">缺卡</TableHead>
                  <TableHead className="text-right">加班</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {detail.shift_results.map((shift) => (
                  <TableRow key={shift.id}>
                    <TableCell>
                      <div className="font-medium">{shift.shift_name}</div>
                      <div className="text-xs text-muted-foreground">
                        {shift.shift_code}
                      </div>
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      {shift.start_time.slice(0, 5)}–
                      {shift.end_time.slice(0, 5)}
                      {shift.cross_day ? " 次日" : ""}
                    </TableCell>
                    <TableCell>
                      {shiftPunch(shift.punch_in_at, workDate)}
                    </TableCell>
                    <TableCell>
                      {shiftPunch(shift.punch_out_at, workDate)}
                    </TableCell>
                    <TableCell>
                      {shift.break_out_at || shift.break_in_at
                        ? `${shiftPunch(shift.break_out_at, workDate)} / ${shiftPunch(shift.break_in_at, workDate)}`
                        : "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatHours(shift.scheduled_minutes)} h
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatHours(shift.worked_minutes)} h
                    </TableCell>
                    <TableCell>
                      {shift.late_minutes} / {shift.early_minutes} 分
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {shift.missing_punch_count}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatHours(shift.ot_minutes)} h
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </section>

      <section className="space-y-2">
        <h3 className="text-sm font-medium">差异与标记</h3>
        <div className="flex flex-wrap gap-1">
          {dayFlags.length === 0 ? (
            <span className="text-sm text-muted-foreground">无异常标记</span>
          ) : (
            dayFlags.map((flag) => (
              <Badge key={flag} variant="outline">
                {dayFlagLabel(flag)}
              </Badge>
            ))
          )}
        </div>
      </section>

      <section className="space-y-2">
        <h3 className="text-sm font-medium">扣款建议</h3>
        <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
          <div className="rounded-md border px-2 py-1">
            旷工 <strong>{formatAmount(result.absent_deduct_amount)}</strong>
          </div>
          <div className="rounded-md border px-2 py-1">
            迟到 <strong>{formatAmount(result.late_deduct_amount)}</strong>
          </div>
          <div className="rounded-md border px-2 py-1">
            早退 <strong>{formatAmount(result.early_deduct_amount)}</strong>
          </div>
          <div className="rounded-md border px-2 py-1">
            缺卡{" "}
            <strong>{formatAmount(result.missing_punch_deduct_amount)}</strong>
          </div>
        </div>
        <p className="text-sm">
          合计 <strong>{formatAmount(result.deduction_total)}</strong>{" "}
          <span className="text-muted-foreground">
            元；负值表示扣减，不直接写薪酬表。
          </span>
        </p>
      </section>

      <section className="space-y-2">
        <h3 className="text-sm font-medium">人工调整</h3>
        {adjustments.length === 0 ? (
          <p className="rounded-md border px-3 py-2 text-sm text-muted-foreground">
            当前没有人工调整。调整会保留原值、调整值与理由，并记录操作者。
          </p>
        ) : (
          <div className="space-y-2" data-testid="adjustment-history">
            {adjustments.map((adjustment) => (
              <div
                key={adjustment.id}
                className="rounded-md border px-3 py-2 text-sm"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge
                    variant={
                      adjustment.status === "active" ? "default" : "secondary"
                    }
                  >
                    版本 {adjustment.version} ·{" "}
                    {ADJUSTMENT_STATUS_LABELS[adjustment.status]}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {adjustment.adjusted_by_name ?? adjustment.adjusted_by} ·{" "}
                    {formatDateTimeShanghai(adjustment.adjusted_at)}
                  </span>
                </div>
                <p className="mt-1">{adjustment.reason}</p>
                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  {Object.entries(adjustment.adjusted_values).map(
                    ([key, value]) => (
                      <span key={key}>
                        {key}:{" "}
                        {adjustmentValue(key, adjustment.original_values[key])}{" "}
                        → {adjustmentValue(key, value)}
                      </span>
                    ),
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

type DayDetailDrawerProps = {
  companyId: string
  employeeId: string | null
  workDate: string | null
  onClose: () => void
}

/** Day detail drawer with the four-way comparison and calculation history. */
export function DayDetailDrawer({
  companyId,
  employeeId,
  workDate,
  onClose,
}: DayDetailDrawerProps) {
  const query = useDayDetail(companyId, employeeId, workDate)
  const detail = query.data

  return (
    <Sheet
      open={employeeId !== null && workDate !== null}
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
    >
      <SheetContent
        side="right"
        className="w-full overflow-y-auto sm:max-w-xl xl:max-w-3xl"
        data-testid="day-detail-drawer"
      >
        <SheetHeader>
          <SheetTitle>
            {detail
              ? `${detail.day_result.employee_name ?? detail.day_result.employee_id} · ${formatWorkDate(workDate ?? "")}`
              : "日结果详情"}
          </SheetTitle>
          <SheetDescription>
            {detail
              ? `${detail.day_result.department_name ?? "—"} · ${
                  detail.day_result.employee_no ?? ""
                } · ${DAY_TYPE_LABELS[detail.day_result.day_type]}`
              : "排班 / 打卡 / OA / 结果四方对照"}
          </SheetDescription>
          {detail && (
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <Badge variant={dayStatusVariant(detail.day_result.day_status)}>
                {dayStatusLabel(detail.day_result.day_status)}
              </Badge>
              {detail.day_result.is_adjusted && (
                <Badge variant="secondary">已调整</Badge>
              )}
              {detail.day_result.is_abnormal && (
                <Badge variant="destructive">异常</Badge>
              )}
            </div>
          )}
        </SheetHeader>

        {query.isLoading ? (
          <div className="px-4">
            <LoadingState rows={5} />
          </div>
        ) : query.isError ? (
          <div className="px-4">
            <ErrorState
              message={getErrorMessage(query.error)}
              onRetry={() => void query.refetch()}
            />
          </div>
        ) : detail ? (
          <div className="px-4 pb-6">
            <DetailBody detail={detail} />
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  )
}
