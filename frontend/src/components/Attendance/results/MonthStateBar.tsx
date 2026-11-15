import { Loader2, RefreshCw } from "lucide-react"

import type { AttendanceMonthPublic } from "@/client"
import { Button } from "@/components/ui/button"
import { formatDateTimeShanghai } from "@/lib/datetime"
import {
  ATTENDANCE_MONTH_STATUS_LABELS,
  type AttendanceMonthStatus,
} from "@/lib/enums"

import { useRecalculateMonth } from "./queries"

const STATUS_ORDER: AttendanceMonthStatus[] = [
  "draft",
  "calculated",
  "confirmed",
  "locked",
]

const BANNER_CLASS =
  "rounded-md border px-3 py-2 text-sm data-[tone=warning]:border-amber-300 data-[tone=warning]:bg-amber-50 data-[tone=warning]:text-amber-900 dark:data-[tone=warning]:border-amber-900/60 dark:data-[tone=warning]:bg-amber-950/40 dark:data-[tone=warning]:text-amber-100 data-[tone=danger]:border-destructive/40 data-[tone=danger]:bg-destructive/10 data-[tone=danger]:text-destructive"

type MonthStateBarProps = {
  companyId: string
  month: string
  state: AttendanceMonthPublic | undefined
  isLoading: boolean
  isError: boolean
  onRetry: () => void
  onViewHistory: () => void
}

/** Month state timeline, stale/confirmed/locked banners, and recalculation. */
export function MonthStateBar({
  companyId,
  month,
  state,
  isLoading,
  isError,
  onRetry,
  onViewHistory,
}: MonthStateBarProps) {
  const recalculate = useRecalculateMonth(companyId, month)
  const loaded = state !== undefined
  const status: AttendanceMonthStatus = state?.status ?? "draft"
  const currentIndex = loaded ? STATUS_ORDER.indexOf(status) : -1
  const editable = loaded && (status === "draft" || status === "calculated")
  const disabledReason = !loaded
    ? isError
      ? "月份状态加载失败，请刷新或重试后再重新计算。"
      : "正在读取月份状态，请稍候。"
    : status === "locked"
      ? "本月已锁定，无法重新计算；请先解锁。"
      : status === "confirmed"
        ? "本月已确认，无法重新计算；请先取消确认。"
        : null
  const stale = Boolean(
    state?.exists && status === "calculated" && state.is_stale,
  )
  const timestamp =
    status === "locked" && state?.locked_at
      ? `锁定于 ${formatDateTimeShanghai(state.locked_at)}`
      : status === "confirmed" && state?.confirmed_at
        ? `确认于 ${formatDateTimeShanghai(state.confirmed_at)}`
        : state?.calculated_at
          ? `计算于 ${formatDateTimeShanghai(state.calculated_at)}`
          : "尚未计算"

  return (
    <section className="space-y-3" data-testid="month-state-bar">
      <div className="flex flex-col gap-3 rounded-lg border px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          {loaded ? (
            STATUS_ORDER.map((key, index) => {
              const current = key === status
              const done = index < currentIndex
              return (
                <div key={key} className="flex items-center gap-2">
                  <span
                    data-testid={`month-state-step-${key}`}
                    data-current={current}
                    className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${
                      current
                        ? "border-primary bg-primary text-primary-foreground"
                        : done
                          ? "border-primary/40 text-primary"
                          : "text-muted-foreground"
                    }`}
                  >
                    <span className="grid size-4 place-items-center rounded-full border text-[10px]">
                      {done ? "✓" : index + 1}
                    </span>
                    {ATTENDANCE_MONTH_STATUS_LABELS[key]}
                    {current && stale ? " · 已过期" : ""}
                  </span>
                  {index < STATUS_ORDER.length - 1 && (
                    <span aria-hidden="true" className="text-muted-foreground">
                      →
                    </span>
                  )}
                </div>
              )
            })
          ) : (
            <span className="text-xs text-muted-foreground">
              {isError ? "月份状态加载失败" : "正在读取月份状态…"}
            </span>
          )}
          {loaded && (
            <span className="text-xs text-muted-foreground">{timestamp}</span>
          )}
          {isError && (
            <Button type="button" size="sm" variant="ghost" onClick={onRetry}>
              重试
            </Button>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={onViewHistory}
            data-testid="view-calc-runs"
          >
            计算记录
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={!editable || isLoading || recalculate.isPending}
            title={disabledReason ?? undefined}
            onClick={() => recalculate.mutate()}
            data-testid="recalculate-button"
          >
            {recalculate.isPending ? (
              <Loader2 className="mr-1 size-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-1 size-4" />
            )}
            重新计算
          </Button>
        </div>
      </div>

      {disabledReason && !isLoading && (
        <p className="text-xs text-muted-foreground" data-testid="recalc-hint">
          {disabledReason}
        </p>
      )}

      {stale && (
        <div
          role="status"
          data-testid="month-stale-banner"
          data-tone="warning"
          className={BANNER_CLASS}
        >
          当前结果已过期：排班、导入、规则或节假日在本月计算后发生变化，重新计算后生效。
        </div>
      )}
      {status === "confirmed" && (
        <div
          role="status"
          data-testid="month-confirmed-banner"
          data-tone="warning"
          className={BANNER_CLASS}
        >
          本月已确认，结果只读。如需修改数据，请先取消确认。
        </div>
      )}
      {status === "locked" && (
        <div
          role="status"
          data-testid="month-locked-banner"
          data-tone="danger"
          className={BANNER_CLASS}
        >
          本月已锁定，结果只读。
          {state?.unlock_reason ? `上次解锁理由：${state.unlock_reason}。` : ""}
          解锁后结果会标记为过期，需要重新计算。
        </div>
      )}
    </section>
  )
}
