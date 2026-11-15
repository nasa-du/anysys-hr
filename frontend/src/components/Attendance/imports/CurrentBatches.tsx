import { useState } from "react"

import {
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getErrorMessage } from "@/lib/api-error"
import {
  ATTENDANCE_MONTH_STATUS_LABELS,
  type AttendanceMonthStatus,
  IMPORT_DATA_TYPE_LABELS,
  IMPORT_DATA_TYPE_OPTIONS,
} from "@/lib/enums"
import { BatchDetailDialog } from "./BatchDetailDialog"
import { batchSourceLabel, formatDateTime } from "./import-format"
import { useAttendanceMonthOverview, useImportBatches } from "./queries"

/** The one active committed batch per data type for the selected month. */
export function CurrentBatches({
  companyId,
  month,
}: {
  companyId: string
  month: string
}) {
  const [detailId, setDetailId] = useState<string | null>(null)
  const query = useImportBatches(companyId, month, {
    dataType: "all",
    status: "committed",
    skip: 0,
    limit: 100,
  })
  const monthQuery = useAttendanceMonthOverview(companyId, month)
  const overview = monthQuery.data
  const monthClosed =
    overview?.status === "confirmed" || overview?.status === "locked"
  const byType = new Map(
    (query.data?.data ?? []).map((batch) => [batch.data_type, batch]),
  )

  return (
    <>
      <Card data-testid="current-batches">
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="text-lg">当前生效批次</CardTitle>
            {overview && (
              <Badge
                variant={monthClosed ? "destructive" : "outline"}
                data-testid="import-month-status"
              >
                {
                  ATTENDANCE_MONTH_STATUS_LABELS[
                    overview.status as AttendanceMonthStatus
                  ]
                }
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            「公司 + 月份 +
            数据类型」同时只有一个生效批次；提交新批次会覆盖旧批次。
          </p>
        </CardHeader>
        <CardContent className="space-y-4 pt-6">
          {overview?.is_stale && (
            <Alert data-testid="import-month-stale">
              <AlertTitle>考勤月份待重算</AlertTitle>
              <AlertDescription>
                导入提交或撤销已把该月份标记为待重算；系统不会自动重算，请在考勤结果页手动重算。
              </AlertDescription>
            </Alert>
          )}
          {monthClosed && (
            <Alert variant="destructive" data-testid="import-month-closed">
              <AlertTitle>考勤月份已关闭</AlertTitle>
              <AlertDescription>
                当前月份已
                {overview?.status === "confirmed" ? "确认" : "锁定"}
                ，预览仍可查看，但提交会被拒绝。
              </AlertDescription>
            </Alert>
          )}
          {query.isLoading ? (
            <LoadingState rows={1} />
          ) : query.isError ? (
            <ErrorState
              message={getErrorMessage(query.error)}
              onRetry={() => void query.refetch()}
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {IMPORT_DATA_TYPE_OPTIONS.map((option) => {
                const batch = byType.get(option.value)
                return (
                  <div
                    key={option.value}
                    className="flex flex-col gap-2 rounded-lg border bg-card p-4"
                    data-testid={`current-batch-${option.value}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">
                        {IMPORT_DATA_TYPE_LABELS[option.value]}
                      </span>
                      {batch ? (
                        <Badge>生效</Badge>
                      ) : (
                        <Badge variant="outline">未生效</Badge>
                      )}
                    </div>
                    {batch ? (
                      <>
                        <p className="truncate text-sm text-muted-foreground">
                          {batchSourceLabel(batch)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          提交于 {formatDateTime(batch.committed_at)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          有效 {batch.valid_records} 条 / 源 {batch.source_rows}{" "}
                          行
                        </p>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="mt-1 self-start"
                          onClick={() => setDetailId(batch.id)}
                        >
                          查看详情
                        </Button>
                      </>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        该类型本月还没有生效批次。
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {detailId && (
        <BatchDetailDialog
          batchId={detailId}
          open
          onOpenChange={(open) => {
            if (!open) setDetailId(null)
          }}
        />
      )}
    </>
  )
}
