const SHANGHAI_OFFSET_MS = 8 * 60 * 60 * 1000

export const DATE_TIME_PATTERN = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/

/**
 * Convert an ISO 8601 timestamp to the wall-clock time in Asia/Shanghai
 * (UTC+8), formatted as YYYY-MM-DD HH:mm. Independent of the browser timezone.
 */
export function toShanghaiDateTime(isoTimestamp: string): string {
  return new Date(Date.parse(isoTimestamp) + SHANGHAI_OFFSET_MS)
    .toISOString()
    .slice(0, 16)
    .replace("T", " ")
}
