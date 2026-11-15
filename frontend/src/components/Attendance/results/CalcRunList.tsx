import { useState } from "react"

import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Badge } from "@/components/ui/badge"
import { getErrorMessage } from "@/lib/api-error"
import { formatDateTimeShanghai } from "@/lib/datetime"
import {
  ABNORMAL_DAY_STATUSES,
  type AttendanceDayStatus,
  CALC_RUN_STATUS_LABELS,
  CALC_RUN_TRIGGER_LABELS,
  DAY_STATUS_LABELS,
} from "@/lib/enums"

import { PaginationFooter } from "./PaginationFooter"
import { useCalcRuns } from "./queries"

const PAGE_SIZE = 20

/** Calculation history: every run is appended; failures roll results back. */
export function CalcRunList({
  companyId,
  month,
}: {
  companyId: string
  month: string
}) {
  const [skip, setSkip] = useState(0)
  const query = useCalcRuns(companyId, month, skip, PAGE_SIZE)
  const runs = query.data?.data ?? []
  const count = query.data?.count ?? 0

  if (query.isLoading) return <LoadingState rows={4} />
  if (query.isError) {
    return (
      <ErrorState
        message={getErrorMessage(query.error)}
        onRetry={() => void query.refetch()}
      />
    )
  }
  if (runs.length === 0) {
    return (
      <EmptyState
        title={`${month} 还没有计算记录`}
        message="点击「重新计算」后，每次计算都会留下一条记录。"
      />
    )
  }

  return (
    <div className="space-y-3" data-testid="calc-run-list">
      <div className="space-y-2">
        {runs.map((run) => {
          const failed = run.status === "failed"
          return (
            <div
              key={run.id}
              data-testid={`calc-run-row-${run.id}`}
              className={`rounded-lg border px-3 py-2 ${
                failed ? "border-destructive/40 bg-destructive/5" : ""
              }`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={failed ? "destructive" : "secondary"}>
                  {CALC_RUN_STATUS_LABELS[run.status]}
                </Badge>
                <span className="text-sm font-medium">
                  {CALC_RUN_TRIGGER_LABELS[run.trigger]}
                </span>
                <span className="text-xs text-muted-foreground">
                  {formatDateTimeShanghai(run.started_at)} →{" "}
                  {formatDateTimeShanghai(run.finished_at)}
                </span>
                <span className="ml-auto text-xs text-muted-foreground">
                  {run.calc_version}
                </span>
              </div>
              {failed ? (
                <p className="mt-1 text-sm text-destructive">
                  {run.error_code ? `${run.error_code}：` : ""}
                  {run.error_message ?? "计算失败"}
                </p>
              ) : (
                <p className="mt-1 text-xs text-muted-foreground">
                  计算 {run.summary?.employees_calculated ?? 0} 人 ·{" "}
                  {run.summary?.days_total ?? 0} 天 · 异常状态{" "}
                  {run.summary?.days_by_status
                    ? Object.entries(run.summary.days_by_status)
                        .filter(([status]) =>
                          ABNORMAL_DAY_STATUSES.has(
                            status as AttendanceDayStatus,
                          ),
                        )
                        .map(
                          ([status, value]) =>
                            `${DAY_STATUS_LABELS[status as AttendanceDayStatus] ?? status} ${value}`,
                        )
                        .join("、") || "无"
                    : "无"}
                </p>
              )}
            </div>
          )
        })}
      </div>
      <PaginationFooter
        count={count}
        skip={skip}
        pageSize={PAGE_SIZE}
        onSkipChange={setSkip}
      />
    </div>
  )
}
