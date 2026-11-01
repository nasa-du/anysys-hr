const SHANGHAI_TIME_ZONE = "Asia/Shanghai"

const dateFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: SHANGHAI_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
})

const dateTimeFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: SHANGHAI_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
})

function partsOf(
  formatter: Intl.DateTimeFormat,
  date: Date,
): Record<string, string> {
  return Object.fromEntries(
    formatter.formatToParts(date).map(({ type, value }) => [type, value]),
  )
}

const EMPTY_VALUE = "-"

/**
 * Format an ISO 8601 timestamp as a date in Asia/Shanghai: YYYY-MM-DD.
 */
export function formatDateShanghai(value?: string | null): string {
  if (!value) return EMPTY_VALUE

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return EMPTY_VALUE

  const parts = partsOf(dateFormatter, date)
  return `${parts.year}-${parts.month}-${parts.day}`
}

/**
 * Format an ISO 8601 timestamp as a date and time in Asia/Shanghai:
 * YYYY-MM-DD HH:mm. Never renders relative time.
 */
export function formatDateTimeShanghai(value?: string | null): string {
  if (!value) return EMPTY_VALUE

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return EMPTY_VALUE

  const parts = partsOf(dateTimeFormatter, date)
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}`
}
