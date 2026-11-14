import type { ShiftPublic } from "@/client"

const SECONDS_PER_DAY = 24 * 60 * 60

/**
 * Convert an API time to the HH:MM value a minute-granularity time input uses.
 * The edit form compares this against the submitted value so unchanged times
 * are omitted from the PATCH and existing seconds are preserved.
 */
export function toTimeInputValue(value: string | null | undefined): string {
  return value ? value.slice(0, 5) : ""
}

/** Render an API time for display, keeping non-zero seconds visible. */
export function formatShiftTime(value: string | null | undefined): string {
  if (!value) return ""
  const match = /^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(value)
  if (!match) return value
  const seconds = match[3]
  return seconds && seconds !== "00"
    ? `${match[1]}:${match[2]}:${seconds}`
    : `${match[1]}:${match[2]}`
}

export function formatShiftRange(
  shift: Pick<ShiftPublic, "start_time" | "end_time">,
): string {
  return `${formatShiftTime(shift.start_time)}–${formatShiftTime(shift.end_time)}`
}

/** Parse HH:MM[:SS] into seconds; invalid values return null. */
export function timeToSeconds(value: string): number | null {
  const match = /^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(value)
  if (!match) return null
  const hours = Number(match[1])
  const minutes = Number(match[2])
  const seconds = match[3] ? Number(match[3]) : 0
  if (hours > 23 || minutes > 59 || seconds > 59) return null
  return hours * 3600 + minutes * 60 + seconds
}

/**
 * Shift span in seconds, normalized across midnight. A cross-day shift whose
 * times are equal is a full 24-hour shift. Returns null for unparseable times.
 */
export function shiftSpanSeconds(
  startTime: string,
  endTime: string,
  crossDay: boolean,
): number | null {
  const start = timeToSeconds(startTime)
  const end = timeToSeconds(endTime)
  if (start === null || end === null) return null
  const span = (end - start + SECONDS_PER_DAY) % SECONDS_PER_DAY
  return crossDay && span === 0 ? SECONDS_PER_DAY : span
}

export interface ShiftTimeFields {
  start_time: string
  end_time: string
  cross_day: boolean
  break_start: string
  break_end: string
  rest_minutes: number
}

export type ShiftTimeErrors = Partial<Record<keyof ShiftTimeFields, string>>

/**
 * Client-side mirror of the backend shift time rules. Server 409 field errors
 * remain authoritative; this only gives immediate feedback in the drawer.
 */
export function validateShiftTimeFields(
  fields: ShiftTimeFields,
): ShiftTimeErrors {
  const errors: ShiftTimeErrors = {}
  const start = timeToSeconds(fields.start_time)
  const end = timeToSeconds(fields.end_time)

  if (start === null) {
    errors.start_time = "请输入开始时间"
  }
  if (end === null) {
    errors.end_time = "请输入结束时间"
  }

  if (start !== null && end !== null) {
    if (fields.cross_day) {
      if (end > start) {
        errors.end_time = "跨天班次的结束时间必须早于或等于开始时间"
      }
    } else if (end <= start) {
      errors.end_time = "结束时间必须晚于开始时间"
    }
  }

  const hasBreakStart = fields.break_start !== ""
  const hasBreakEnd = fields.break_end !== ""
  if (hasBreakStart !== hasBreakEnd) {
    const missing = hasBreakStart ? "break_end" : "break_start"
    errors[missing] = "休息开始与结束时间必须同时填写"
  }

  const span =
    start !== null && end !== null
      ? shiftSpanSeconds(fields.start_time, fields.end_time, fields.cross_day)
      : null

  if (start !== null && hasBreakStart && hasBreakEnd) {
    const breakStart = timeToSeconds(fields.break_start)
    const breakEnd = timeToSeconds(fields.break_end)
    if (breakStart === null || breakEnd === null) {
      errors.break_start = "请输入有效的休息时间"
      errors.break_end = "请输入有效的休息时间"
    } else if (span !== null) {
      const relativeStart =
        (breakStart - start + SECONDS_PER_DAY) % SECONDS_PER_DAY
      const relativeEnd = (breakEnd - start + SECONDS_PER_DAY) % SECONDS_PER_DAY
      if (
        !(
          0 < relativeStart &&
          relativeStart < relativeEnd &&
          relativeEnd < span
        )
      ) {
        const message = "休息时间必须位于班次时间范围内，且开始时间早于结束时间"
        errors.break_start = message
        errors.break_end = message
      }
    }
  }

  if (span !== null && fields.rest_minutes * 60 > span) {
    errors.rest_minutes = `休息扣减不能超过班次时长（${Math.floor(span / 60)} 分钟）`
  }

  return errors
}
