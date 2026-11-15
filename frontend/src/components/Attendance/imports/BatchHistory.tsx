import { ChevronLeft, ChevronRight } from "lucide-react"
import { useState } from "react"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { getErrorMessage } from "@/lib/api-error"
import {
  type AttendanceImportBatchStatus,
  type AttendanceImportDataType,
  IMPORT_BATCH_STATUS_LABELS,
  IMPORT_DATA_TYPE_LABELS,
  IMPORT_DATA_TYPE_OPTIONS,
} from "@/lib/enums"
import { BatchDetailDialog } from "./BatchDetailDialog"
import {
  batchSourceLabel,
  batchStatusView,
  formatDateTime,
} from "./import-format"
import { useImportBatches } from "./queries"

const PAGE_SIZE = 10

const STATUS_FILTER_OPTIONS: Array<{
  value: AttendanceImportBatchStatus | "all"
  label: string
}> = [
  { value: "all", label: "全部状态" },
  ...(
    Object.entries(IMPORT_BATCH_STATUS_LABELS) as Array<
      [AttendanceImportBatchStatus, string]
    >
  ).map(([value, label]) => ({ value, label })),
]

/** Batch history for the selected company/month with filters and detail actions. */
export function BatchHistory({
  companyId,
  month,
}: {
  companyId: string
  month: string
}) {
  const [dataType, setDataType] = useState<AttendanceImportDataType | "all">(
    "all",
  )
  const [status, setStatus] = useState<AttendanceImportBatchStatus | "all">(
    "all",
  )
  const [skip, setSkip] = useState(0)
  const [detailId, setDetailId] = useState<string | null>(null)
  const query = useImportBatches(companyId, month, {
    dataType,
    status,
    skip,
    limit: PAGE_SIZE,
  })
  const batches = query.data?.data ?? []
  const count = query.data?.count ?? 0
  const start = count === 0 ? 0 : skip + 1
  const end = Math.min(skip + PAGE_SIZE, count)

  return (
    <>
      <Card data-testid="batch-history">
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="text-lg">批次历史</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                {month} · 预览 24
                小时后过期；生效批次可撤销，已替代批次保留用于审计。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Select
                value={dataType}
                onValueChange={(value) => {
                  setDataType(value as AttendanceImportDataType | "all")
                  setSkip(0)
                }}
              >
                <SelectTrigger className="w-40" aria-label="批次类型">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部类型</SelectItem>
                  {IMPORT_DATA_TYPE_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select
                value={status}
                onValueChange={(value) => {
                  setStatus(value as AttendanceImportBatchStatus | "all")
                  setSkip(0)
                }}
              >
                <SelectTrigger className="w-40" aria-label="批次状态">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STATUS_FILTER_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          {query.isLoading ? (
            <LoadingState rows={4} />
          ) : query.isError ? (
            <ErrorState
              message={getErrorMessage(query.error)}
              onRetry={() => void query.refetch()}
            />
          ) : batches.length === 0 ? (
            <EmptyState
              title="当前筛选下没有批次"
              message="上传或粘贴内容并解析后，预览批次会出现在这里。"
            />
          ) : (
            <div className="space-y-4">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>类型</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>文件 / 来源</TableHead>
                      <TableHead className="text-right">有效记录</TableHead>
                      <TableHead className="text-right">错误 / 告警</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>提交时间</TableHead>
                      <TableHead className="text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {batches.map((batch) => {
                      const statusView = batchStatusView(batch)
                      return (
                        <TableRow
                          key={batch.id}
                          data-testid={`batch-row-${batch.id}`}
                        >
                          <TableCell>
                            <Badge variant="outline">
                              {
                                IMPORT_DATA_TYPE_LABELS[
                                  batch.data_type as AttendanceImportDataType
                                ]
                              }
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={statusView.variant}>
                              {statusView.label}
                            </Badge>
                          </TableCell>
                          <TableCell className="max-w-[220px] truncate">
                            {batchSourceLabel(batch)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {batch.valid_records}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {batch.error_records} / {batch.warning_records}
                          </TableCell>
                          <TableCell className="whitespace-nowrap text-sm text-muted-foreground">
                            {formatDateTime(batch.created_at)}
                          </TableCell>
                          <TableCell className="whitespace-nowrap text-sm text-muted-foreground">
                            {formatDateTime(batch.committed_at)}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => setDetailId(batch.id)}
                              data-testid={`view-batch-${batch.id}`}
                            >
                              查看详情
                            </Button>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm text-muted-foreground">
                  第 {start}–{end} 条 / 共 {count} 条
                </span>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={skip <= 0}
                    onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
                  >
                    <ChevronLeft className="mr-1 size-4" />
                    上一页
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={end >= count}
                    onClick={() => setSkip(skip + PAGE_SIZE)}
                  >
                    下一页
                    <ChevronRight className="ml-1 size-4" />
                  </Button>
                </div>
              </div>
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
