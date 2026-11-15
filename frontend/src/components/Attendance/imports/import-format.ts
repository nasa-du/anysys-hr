import type { ImportBatchPublic } from "@/client"
import {
  type AttendanceImportBatchStatus,
  IMPORT_BATCH_STATUS_LABELS,
  IMPORT_DISCARD_REASON_EXPIRED,
} from "@/lib/enums"

export const dateTimeFormatter = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
})

/** Format an ISO timestamp for display; missing/invalid values render as a dash. */
export function formatDateTime(
  value: string | Date | null | undefined,
): string {
  if (!value) return "—"
  const parsed = value instanceof Date ? value : new Date(value)
  return Number.isNaN(parsed.getTime())
    ? String(value)
    : dateTimeFormatter.format(parsed)
}

export function sampleText(row: Record<string, unknown>, key: string): string {
  const value = row[key]
  return value === null || value === undefined || value === ""
    ? "—"
    : String(value)
}

export function sampleDateTime(value: unknown): string {
  return typeof value === "string" ? formatDateTime(value) : "—"
}

export function overtimeDaysText(value: unknown): string {
  if (!Array.isArray(value)) return "—"
  return value
    .map((day) => {
      if (!day || typeof day !== "object") return ""
      const item = day as { work_date?: unknown; minutes?: unknown }
      return `${String(item.work_date ?? "")} ${String(item.minutes ?? 0)} 分钟`
    })
    .filter(Boolean)
    .join("；")
}

/** A preview is expired once its 24-hour window has passed. */
export function isPreviewExpired(
  batch: Pick<ImportBatchPublic, "status" | "expires_at">,
): boolean {
  if (batch.status !== "preview" || !batch.expires_at) return false
  return new Date(batch.expires_at).getTime() <= Date.now()
}

export type BatchStatusView = {
  label: string
  variant: "default" | "secondary" | "destructive" | "outline"
}

export function batchStatusView(
  batch: Pick<ImportBatchPublic, "status" | "expires_at" | "discard_reason">,
): BatchStatusView {
  if (isPreviewExpired(batch)) {
    return { label: "已过期", variant: "destructive" }
  }
  if (
    batch.status === "discarded" &&
    batch.discard_reason === IMPORT_DISCARD_REASON_EXPIRED
  ) {
    return { label: "已过期", variant: "destructive" }
  }
  const variant =
    batch.status === "committed"
      ? "default"
      : batch.status === "preview"
        ? "outline"
        : "secondary"
  return {
    label:
      IMPORT_BATCH_STATUS_LABELS[batch.status as AttendanceImportBatchStatus],
    variant,
  }
}

export function batchSourceLabel(
  batch: Pick<ImportBatchPublic, "file_name" | "source">,
): string {
  if (batch.file_name) return batch.file_name
  return batch.source === "paste" ? "粘贴内容" : "未命名文件"
}
