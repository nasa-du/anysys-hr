import { AlertTriangle, Info } from "lucide-react"

import type { AttendanceMonthPublic } from "@/client"
import { useAttendanceMonth } from "@/contexts/AttendanceMonthContext"
import { ATTENDANCE_MONTH_STATUS_LABELS } from "@/lib/enums"

function MonthStateList({
  months,
  emptyMessage,
}: {
  months: AttendanceMonthPublic[]
  emptyMessage: string
}) {
  if (months.length === 0) {
    return <p className="text-xs text-muted-foreground">{emptyMessage}</p>
  }
  return (
    <ul className="max-h-40 space-y-1 overflow-y-auto text-xs">
      {months.map((month) => (
        <li key={month.month} className="flex flex-wrap items-center gap-1.5">
          <span className="font-medium">{month.month}</span>
          <span className="text-muted-foreground">
            {ATTENDANCE_MONTH_STATUS_LABELS[month.status]}
          </span>
          {month.is_stale && (
            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[11px] text-amber-900 dark:bg-amber-950/60 dark:text-amber-100">
              结果过期
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}

/**
 * Rules, overrides, and holidays never recalculate automatically. The hint
 * lists the actual draft/calculated months that will be flagged stale and the
 * confirmed/locked months whose results stay untouched.
 */
export function ImpactHint({
  months,
  isLoading,
}: {
  months: AttendanceMonthPublic[]
  isLoading: boolean
}) {
  const { month } = useAttendanceMonth()
  const affected = months.filter(
    (item) => item.status === "draft" || item.status === "calculated",
  )
  const protectedMonths = months.filter(
    (item) => item.status === "confirmed" || item.status === "locked",
  )

  return (
    <div
      className="rounded-lg border bg-muted/30 p-4 text-sm"
      data-testid="impact-hint"
    >
      <div className="flex items-center gap-2 font-medium">
        <AlertTriangle className="size-4 text-amber-600" />
        修改影响
      </div>

      <p className="mt-3 flex items-start gap-2 text-muted-foreground">
        <Info className="mt-0.5 size-3.5 shrink-0" />
        <span>
          {month} 等草稿 / 已计算月份保存后标记为「结果过期」，不会自动重算；
          已确认 / 已锁定月份的结果保持不变。
        </span>
      </p>

      {isLoading ? (
        <p className="mt-3 text-xs text-muted-foreground">正在读取月份状态…</p>
      ) : months.length === 0 ? (
        <p className="mt-3 text-xs text-muted-foreground">
          尚无已创建的考勤月份；首次排班或计算后会在这里列出。
        </p>
      ) : (
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <p className="text-xs font-medium">将标记为「结果过期」</p>
            <MonthStateList
              months={affected}
              emptyMessage="当前没有草稿 / 已计算月份"
            />
          </div>
          <div className="space-y-1.5">
            <p className="text-xs font-medium">结果保持不变</p>
            <MonthStateList
              months={protectedMonths}
              emptyMessage="当前没有已确认 / 已锁定月份"
            />
          </div>
        </div>
      )}
    </div>
  )
}
