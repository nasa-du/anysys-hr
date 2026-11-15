import type { AttendanceDayResultPublic } from "@/client"
import { formatDateShanghai } from "@/lib/datetime"
import {
  ABNORMAL_DAY_STATUSES,
  type AttendanceDayFlag,
  type AttendanceDayStatus,
  type AttendanceDayType,
  type AttendanceLeaveKind,
  type AttendanceRosterStateWithUnscheduled,
  type AttendanceTripKind,
  DAY_FLAG_LABELS,
  DAY_STATUS_LABELS,
  DAY_TYPE_LABELS,
  LEAVE_KIND_LABELS,
  ROSTER_STATE_LABELS,
  TRIP_KIND_LABELS,
} from "@/lib/enums"

const SHANGHAI_TIME_ZONE = "Asia/Shanghai"

const weekdayFormatter = new Intl.DateTimeFormat("zh-CN", {
  timeZone: SHANGHAI_TIME_ZONE,
  weekday: "short",
})

const clockFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: SHANGHAI_TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
})

const EMPTY = "—"

/** "2026-09-01" -> "2026-09-01 周二". */
export function formatWorkDate(value: string): string {
  if (!value) return EMPTY
  const date = new Date(`${value}T00:00:00+08:00`)
  if (Number.isNaN(date.getTime())) return value
  return `${value} ${weekdayFormatter.format(date)}`
}

/** Shanghai calendar date for an ISO timestamp. */
export function shanghaiDate(value: string): string {
  const date = formatDateShanghai(value)
  return date === "-" ? "" : date
}

/** Shanghai wall-clock time as HH:mm. */
export function formatClock(value?: string | null): string {
  if (!value) return EMPTY
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return EMPTY
  return clockFormatter.format(date)
}

/** Minutes after Shanghai midnight for an ISO timestamp. */
export function minutesOfDay(value: string): number {
  const formatted = formatClock(value)
  if (formatted === EMPTY) return 0
  const [hour, minute] = formatted.split(":").map(Number)
  return hour * 60 + minute
}

/** Minutes after midnight for an "HH:MM:SS" shift time. */
export function shiftMinutes(value: string): number {
  const [hour, minute] = value.split(":").map(Number)
  return hour * 60 + minute
}

export function formatHours(minutes: number): string {
  return (minutes / 60).toFixed(2)
}

/** "90" -> "1 小时 30 分", "0" -> "0 分钟". */
export function formatMinutes(minutes: number): string {
  if (minutes <= 0) return "0 分钟"
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (hours === 0) return `${rest} 分钟`
  if (rest === 0) return `${hours} 小时`
  return `${hours} 小时 ${rest} 分`
}

/** Decimal strings render with one digit for days and two for money. */
export function formatFraction(value: string | number): string {
  const number = typeof value === "number" ? value : Number(value)
  return Number.isFinite(number) ? number.toFixed(1) : "0.0"
}

export function formatAmount(value: string | number): string {
  return formatDecimal(value, 2)
}

export function formatDecimal(value: string | number, digits = 2): string {
  const number = typeof value === "number" ? value : Number(value)
  return Number.isFinite(number) ? number.toFixed(digits) : "0.00"
}

export function dayStatusLabel(status: AttendanceDayStatus): string {
  return DAY_STATUS_LABELS[status] ?? status
}

export function dayTypeLabel(dayType: AttendanceDayType): string {
  return DAY_TYPE_LABELS[dayType] ?? dayType
}

export function rosterStateLabel(
  state: AttendanceRosterStateWithUnscheduled,
): string {
  return ROSTER_STATE_LABELS[state] ?? state
}

export function leaveKindLabel(kind: AttendanceLeaveKind): string {
  return LEAVE_KIND_LABELS[kind] ?? kind
}

export function tripKindLabel(kind: AttendanceTripKind): string {
  return TRIP_KIND_LABELS[kind] ?? kind
}

export function dayFlagLabel(flag: string): string {
  return DAY_FLAG_LABELS[flag as AttendanceDayFlag] ?? flag
}

export function totalOtMinutes(result: AttendanceDayResultPublic): number {
  return (
    result.ot_weekday_minutes +
    result.ot_weekend_minutes +
    result.ot_holiday_minutes
  )
}

/** Abnormal rows use a destructive badge; benign special days stay secondary. */
export function dayStatusVariant(
  status: AttendanceDayStatus,
): "destructive" | "secondary" | "outline" {
  if (ABNORMAL_DAY_STATUSES.has(status)) {
    return "destructive"
  }
  if (
    status === "overtime" ||
    status === "trip_out" ||
    status === "trip_business" ||
    status === "personal_leave" ||
    status === "paid_leave" ||
    status === "comp_leave" ||
    status === "rest"
  ) {
    return "secondary"
  }
  return "outline"
}
