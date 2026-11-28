/** Calendar-month helpers shared by attendance and payroll. */

const MONTH_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/

export function isMonthString(value: unknown): value is string {
  return typeof value === "string" && MONTH_PATTERN.test(value)
}

/** The current calendar month in Asia/Shanghai, formatted as YYYY-MM. */
export function currentShanghaiMonth(now: Date = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(now)
  const year = parts.find((part) => part.type === "year")?.value
  const month = parts.find((part) => part.type === "month")?.value
  return `${year}-${month}`
}

/** Read a persisted YYYY-MM value, ignoring malformed or unavailable storage. */
export function readStoredMonth(storageKey: string): string | null {
  try {
    const stored = localStorage.getItem(storageKey)
    if (isMonthString(stored)) {
      return stored
    }
  } catch {
    // Storage can be unavailable in private browsing; the fallback still works.
  }
  return null
}

/** Persist a YYYY-MM value; selection still works when storage is unavailable. */
export function writeStoredMonth(storageKey: string, month: string): void {
  try {
    localStorage.setItem(storageKey, month)
  } catch {
    // The current page keeps the selection until it is reloaded.
  }
}
