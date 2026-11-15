import type {
  AttendanceDayDetailPublic,
  AttendanceDayShiftResultPublic,
  OaLeavePublic,
  OaTripPublic,
  PunchRecordPublic,
} from "@/client"
import { ABNORMAL_DAY_STATUSES } from "@/lib/enums"

import {
  dayStatusLabel,
  formatClock,
  formatMinutes,
  minutesOfDay,
  shanghaiDate,
  shiftMinutes,
} from "./result-format"

const HOUR_TICKS = [0, 3, 6, 9, 12, 15, 18, 21, 24]

function percent(minutes: number): number {
  return Math.max(0, Math.min(100, (minutes / 1440) * 100))
}

function shiftSpan(shift: AttendanceDayShiftResultPublic): {
  start: number
  end: number
} {
  const start = shiftMinutes(shift.start_time)
  let end = shiftMinutes(shift.end_time)
  if (shift.cross_day || end <= start) {
    end += 1440
  }
  return {
    start: Math.max(0, Math.min(1440, start)),
    end: Math.max(0, Math.min(1440, end)),
  }
}

function daySpan(
  startAt: string,
  endAt: string,
  workDate: string,
): { start: number; end: number } | null {
  const startDate = shanghaiDate(startAt)
  const endDate = shanghaiDate(endAt)
  const start = startDate < workDate ? 0 : minutesOfDay(startAt)
  const end = endDate > workDate ? 1440 : minutesOfDay(endAt)
  if (end <= 0 || start >= 1440 || end <= start) return null
  return { start, end }
}

function TripBand({
  trip,
  workDate,
}: {
  trip: OaTripPublic
  workDate: string
}) {
  const span = daySpan(trip.start_at, trip.end_at, workDate)
  if (span === null) return null
  return (
    <div
      data-testid="timeline-trip"
      className="absolute top-9 h-3 rounded-sm bg-sky-500/50"
      style={{
        left: `${percent(span.start)}%`,
        width: `${Math.max(0.4, percent(span.end) - percent(span.start))}%`,
      }}
      title={`外出 / 出差 ${formatClock(trip.start_at)}–${formatClock(trip.end_at)}`}
    />
  )
}

function LeaveBand({
  leave,
  workDate,
}: {
  leave: OaLeavePublic
  workDate: string
}) {
  const span = daySpan(leave.rest_start_at, leave.rest_end_at, workDate)
  if (span === null) return null
  return (
    <div
      data-testid="timeline-leave"
      className="absolute top-13 h-3 rounded-sm bg-amber-500/50"
      style={{
        left: `${percent(span.start)}%`,
        width: `${Math.max(0.4, percent(span.end) - percent(span.start))}%`,
      }}
      title={`请假 ${formatClock(leave.rest_start_at)}–${formatClock(leave.rest_end_at)}`}
    />
  )
}

function PunchDot({ punch }: { punch: PunchRecordPublic }) {
  return (
    <div
      data-testid="timeline-punch"
      className="absolute top-19 size-2.5 -translate-x-1/2 rounded-full border-2 border-background bg-foreground"
      style={{ left: `${percent(minutesOfDay(punch.punch_time))}%` }}
      title={`打卡 ${formatClock(punch.punch_time)} ${punch.punch_result_raw}`}
    />
  )
}

/** Roster, punch, OA, and result in one 24-hour track (spec 9.2). */
export function FourWayTimeline({
  detail,
}: {
  detail: AttendanceDayDetailPublic
}) {
  const workDate = detail.day_result.work_date
  const punches = detail.punches ?? []
  const trips = detail.oa_trips ?? []
  const leaves = detail.oa_leaves ?? []
  const overtimeDays = detail.oa_overtime_days ?? []
  const sameDayPunches = punches.filter(
    (punch) => shanghaiDate(punch.punch_time) === workDate,
  )
  const nextDayPunches = punches.filter(
    (punch) => shanghaiDate(punch.punch_time) !== workDate,
  )

  return (
    <div className="space-y-2" data-testid="four-way-timeline">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">四方对照时间轴</h3>
        <span className="text-xs text-muted-foreground">
          排班 / 打卡 / OA / 结果
        </span>
      </div>
      <div className="rounded-md border bg-muted/20 p-2">
        <div className="flex justify-between px-1 text-[10px] text-muted-foreground">
          {HOUR_TICKS.map((hour) => (
            <span key={hour}>{hour}:00</span>
          ))}
        </div>
        <div
          className="relative mt-1 h-24 overflow-hidden rounded-sm border bg-background"
          data-testid="timeline-track"
        >
          {HOUR_TICKS.map((hour) => (
            <div
              key={hour}
              aria-hidden="true"
              className="absolute inset-y-0 border-l border-dashed border-border/70"
              style={{ left: `${percent(hour * 60)}%` }}
            />
          ))}
          {detail.shift_results.map((shift) => {
            const span = shiftSpan(shift)
            if (span.end <= span.start) return null
            return (
              <div
                key={shift.id}
                data-testid={`timeline-shift-${shift.seq}`}
                className="absolute top-2 h-5 truncate rounded-sm bg-primary/80 px-1 text-[10px] leading-5 text-primary-foreground"
                style={{
                  left: `${percent(span.start)}%`,
                  width: `${Math.max(0.5, percent(span.end) - percent(span.start))}%`,
                }}
                title={`${shift.shift_name} ${shift.start_time}–${shift.end_time}`}
              >
                {shift.shift_code}
                {shift.cross_day ? " →次日" : ""}
              </div>
            )
          })}
          {trips.map((trip) => (
            <TripBand key={trip.id} trip={trip} workDate={workDate} />
          ))}
          {leaves.map((leave) => (
            <LeaveBand key={leave.id} leave={leave} workDate={workDate} />
          ))}
          {detail.shift_results.map((shift) => {
            const span = shiftSpan(shift)
            if (span.end <= span.start) return null
            const abnormal = ABNORMAL_DAY_STATUSES.has(shift.shift_status)
            return (
              <div
                key={`result-${shift.id}`}
                data-testid={`timeline-result-${shift.seq}`}
                className={`absolute top-15 h-3 truncate rounded-sm px-1 text-[9px] leading-3 ${
                  abnormal
                    ? "bg-destructive/60 text-white"
                    : "bg-emerald-500/50 text-emerald-950"
                }`}
                style={{
                  left: `${percent(span.start)}%`,
                  width: `${Math.max(0.5, percent(span.end) - percent(span.start))}%`,
                }}
                title={`结果 ${dayStatusLabel(shift.shift_status)}`}
              >
                {dayStatusLabel(shift.shift_status)}
              </div>
            )
          })}
          {sameDayPunches.map((punch) => (
            <PunchDot key={punch.id} punch={punch} />
          ))}
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-4 rounded-sm bg-primary/80" />
            班次
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block size-2 rounded-full bg-foreground" />
            打卡
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-4 rounded-sm bg-sky-500/50" />
            外出 / 出差
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-4 rounded-sm bg-amber-500/50" />
            请假
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-4 rounded-sm bg-emerald-500/50" />
            结果
          </span>
          {overtimeDays.length > 0 && (
            <span className="flex items-center gap-1">
              <span className="inline-block size-2 rounded-full bg-purple-500" />
              OA 加班：
              {overtimeDays.map((day) => formatMinutes(day.minutes)).join("、")}
            </span>
          )}
          {nextDayPunches.length > 0 && (
            <span>
              次日打卡：
              {nextDayPunches
                .map(
                  (punch) =>
                    `${shanghaiDate(punch.punch_time).slice(5)} ${formatClock(punch.punch_time)}`,
                )
                .join("、")}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
