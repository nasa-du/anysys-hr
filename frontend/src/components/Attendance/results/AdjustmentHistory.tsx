import type { AttendanceAdjustmentPublic } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { formatDateTimeShanghai } from "@/lib/datetime"
import { ADJUSTMENT_STATUS_LABELS, type AttendanceDayStatus } from "@/lib/enums"

import { dayStatusLabel } from "./result-format"

function adjustmentValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return "—"
  if (key === "day_status") {
    return dayStatusLabel(value as AttendanceDayStatus)
  }
  return String(value)
}

type AdjustmentHistoryProps = {
  adjustments: AttendanceAdjustmentPublic[]
  readOnly: boolean
  onUndo: (adjustment: AttendanceAdjustmentPublic) => void
}

/** Version history with the active version's undo action. */
export function AdjustmentHistory({
  adjustments,
  readOnly,
  onUndo,
}: AdjustmentHistoryProps) {
  if (adjustments.length === 0) {
    return (
      <p className="rounded-md border px-3 py-2 text-sm text-muted-foreground">
        当前没有人工调整。调整会保留原值、调整值与理由，并记录操作者。
      </p>
    )
  }

  return (
    <div className="space-y-2" data-testid="adjustment-history">
      {adjustments.map((adjustment) => (
        <div
          key={adjustment.id}
          className="rounded-md border px-3 py-2 text-sm"
        >
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant={adjustment.status === "active" ? "default" : "secondary"}
            >
              版本 {adjustment.version} ·{" "}
              {ADJUSTMENT_STATUS_LABELS[adjustment.status]}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {adjustment.adjusted_by_name ?? adjustment.adjusted_by} ·{" "}
              {formatDateTimeShanghai(adjustment.adjusted_at)}
            </span>
            {adjustment.status === "active" && !readOnly && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="ml-auto"
                data-testid={`undo-adjustment-${adjustment.version}`}
                onClick={() => onUndo(adjustment)}
              >
                撤销
              </Button>
            )}
          </div>
          <p className="mt-1">{adjustment.reason}</p>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {Object.entries(adjustment.adjusted_values).map(([key, value]) => (
              <span key={key}>
                {key}: {adjustmentValue(key, adjustment.original_values[key])} →{" "}
                {adjustmentValue(key, value)}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
