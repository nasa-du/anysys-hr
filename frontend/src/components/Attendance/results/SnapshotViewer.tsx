import { useState } from "react"

import type { AttendanceMonthSnapshotPublic } from "@/client"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { getErrorMessage } from "@/lib/api-error"
import { formatDateTimeShanghai } from "@/lib/datetime"

import { useSnapshotDetail, useSnapshots } from "./queries"

function asList(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

function SnapshotPayload({
  companyId,
  snapshot,
}: {
  companyId: string
  snapshot: AttendanceMonthSnapshotPublic
}) {
  const query = useSnapshotDetail(companyId, snapshot.id, true)
  if (query.isLoading) return <LoadingState rows={3} />
  if (query.isError) {
    return (
      <ErrorState
        message={getErrorMessage(query.error)}
        onRetry={() => void query.refetch()}
      />
    )
  }
  const payload = query.data?.payload
  if (!payload) return null
  return (
    <div
      className="space-y-2"
      data-testid={`snapshot-payload-${snapshot.version}`}
    >
      <div className="grid gap-1 text-xs text-muted-foreground sm:grid-cols-2">
        <span>日结果：{asList(payload.day_results).length} 条</span>
        <span>班次结果：{asList(payload.shift_results).length} 条</span>
        <span>月汇总：{asList(payload.month_summaries).length} 条</span>
        <span>人工调整：{asList(payload.adjustments).length} 条</span>
        <span>导出列：{asList(payload.export.columns).length} 列</span>
        <span>导出行：{asList(payload.export.rows).length} 行</span>
      </div>
      <pre className="max-h-64 overflow-auto rounded-md border bg-muted/40 p-3 text-xs">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </div>
  )
}

type SnapshotViewerProps = {
  companyId: string
  month: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

/** Read-only history of immutable lock snapshots; payloads load on demand. */
export function SnapshotViewer({
  companyId,
  month,
  open,
  onOpenChange,
}: SnapshotViewerProps) {
  const query = useSnapshots(companyId, month, open)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const snapshots = query.data?.data ?? []

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-h-[85vh] overflow-y-auto sm:max-w-3xl"
        data-testid="snapshot-viewer"
      >
        <DialogHeader>
          <DialogTitle>{month} 锁定快照</DialogTitle>
          <DialogDescription>
            每次锁定都会追加一个版本；解锁不会删除历史快照。快照明细按需加载。
          </DialogDescription>
        </DialogHeader>

        {query.isLoading ? (
          <LoadingState rows={3} />
        ) : query.isError ? (
          <ErrorState
            message={getErrorMessage(query.error)}
            onRetry={() => void query.refetch()}
          />
        ) : snapshots.length === 0 ? (
          <EmptyState
            title="还没有锁定快照"
            message="月份锁定后会在这里生成第一份不可变快照。"
          />
        ) : (
          <div className="space-y-3">
            {snapshots.map((snapshot) => {
              const expanded = expandedId === snapshot.id
              return (
                <div
                  key={snapshot.id}
                  className="space-y-2 rounded-lg border p-3"
                  data-testid={`snapshot-row-${snapshot.version}`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">版本 {snapshot.version}</Badge>
                    <span className="text-sm">
                      {formatDateTimeShanghai(snapshot.locked_at)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      锁定人：{snapshot.locked_by_name ?? snapshot.locked_by}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      计算记录：{snapshot.calc_run_id.slice(0, 8)}…
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    计算 {snapshot.summary?.employees_calculated ?? 0} 人 ·{" "}
                    {snapshot.summary?.days_total ?? 0} 天 · 锁定快照不可修改
                  </p>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    data-testid={`snapshot-toggle-${snapshot.version}`}
                    aria-expanded={expanded}
                    onClick={() => setExpandedId(expanded ? null : snapshot.id)}
                  >
                    {expanded ? "收起明细" : "查看明细"}
                  </Button>
                  {expanded && (
                    <SnapshotPayload
                      companyId={companyId}
                      snapshot={snapshot}
                    />
                  )}
                </div>
              )
            })}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
