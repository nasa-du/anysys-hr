import { ChevronLeft, ChevronRight, RotateCcw, Trash2 } from "lucide-react"
import { type ReactNode, useState } from "react"

import type { ImportSeverity } from "@/client"
import {
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
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
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorMessage, getRequestErrorMessage } from "@/lib/api-error"
import {
  type AttendanceImportDataType,
  IMPORT_DATA_TYPE_LABELS,
  IMPORT_ROW_CODE_LABELS,
  IMPORT_SEVERITY_LABELS,
  IMPORT_SOURCE_LABELS,
  LEAVE_KIND_LABELS,
} from "@/lib/enums"
import { ImportIssueBadges } from "./ImportIssueBadges"
import { IMPORT_FIELDS } from "./import-fields"
import {
  batchSourceLabel,
  batchStatusView,
  formatDateTime,
  isPreviewExpired,
  overtimeDaysText,
  sampleDateTime,
  sampleText,
} from "./import-format"
import {
  useDiscardImport,
  useImportBatch,
  useImportBatchErrors,
  useImportBatchRecords,
  useRevokeImport,
} from "./queries"
import { SampleTable } from "./SampleTable"

const ERROR_PAGE_SIZE = 10
const RECORD_PAGE_SIZE = 10

type RecordRow = Record<string, unknown>
type RecordColumn = {
  label: string
  render: (row: RecordRow) => string
}

const RECORD_COLUMNS: Record<AttendanceImportDataType, RecordColumn[]> = {
  punch: [
    { label: "行", render: (row) => sampleText(row, "source_row_number") },
    { label: "工号", render: (row) => sampleText(row, "employee_no_raw") },
    { label: "姓名", render: (row) => sampleText(row, "employee_name_raw") },
    { label: "考勤日期", render: (row) => sampleText(row, "attendance_date") },
    { label: "打卡时间", render: (row) => sampleDateTime(row.punch_time) },
    { label: "结果", render: (row) => sampleText(row, "punch_result_raw") },
  ],
  trip: [
    { label: "行", render: (row) => sampleText(row, "source_row_number") },
    { label: "拆分", render: (row) => sampleText(row, "split_index") },
    { label: "姓名", render: (row) => sampleText(row, "employee_name_raw") },
    { label: "审批编号", render: (row) => sampleText(row, "approval_no") },
    { label: "开始", render: (row) => sampleDateTime(row.start_at) },
    { label: "结束", render: (row) => sampleDateTime(row.end_at) },
    { label: "天数", render: (row) => sampleText(row, "days_declared") },
  ],
  ot: [
    { label: "行", render: (row) => sampleText(row, "source_row_number") },
    { label: "姓名", render: (row) => sampleText(row, "employee_name_raw") },
    { label: "审批编号", render: (row) => sampleText(row, "approval_no") },
    { label: "开始", render: (row) => sampleDateTime(row.start_at) },
    { label: "结束", render: (row) => sampleDateTime(row.end_at) },
    { label: "按日分钟", render: (row) => overtimeDaysText(row.days) },
  ],
  leave: [
    { label: "行", render: (row) => sampleText(row, "source_row_number") },
    { label: "姓名", render: (row) => sampleText(row, "employee_name_raw") },
    { label: "类型", render: (row) => sampleText(row, "leave_type_raw") },
    {
      label: "归类",
      render: (row) => {
        const kind = row.leave_kind
        return typeof kind === "string" && kind in LEAVE_KIND_LABELS
          ? LEAVE_KIND_LABELS[kind as keyof typeof LEAVE_KIND_LABELS]
          : sampleText(row, "leave_kind")
      },
    },
    { label: "天数", render: (row) => sampleText(row, "days") },
    { label: "休息开始", render: (row) => sampleDateTime(row.rest_start_at) },
    { label: "休息结束", render: (row) => sampleDateTime(row.rest_end_at) },
  ],
}

function PageControls({
  skip,
  count,
  pageSize,
  onChange,
  testId,
}: {
  skip: number
  count: number
  pageSize: number
  onChange: (next: number) => void
  testId: string
}) {
  const start = count === 0 ? 0 : skip + 1
  const end = Math.min(skip + pageSize, count)
  return (
    <div
      className="flex flex-wrap items-center justify-between gap-2"
      data-testid={testId}
    >
      <span className="text-sm text-muted-foreground">
        第 {start}–{end} 条 / 共 {count} 条
      </span>
      <div className="flex gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={skip <= 0}
          onClick={() => onChange(Math.max(0, skip - pageSize))}
        >
          <ChevronLeft className="mr-1 size-4" />
          上一页
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={end >= count}
          onClick={() => onChange(skip + pageSize)}
        >
          下一页
          <ChevronRight className="ml-1 size-4" />
        </Button>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-card px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-xl font-semibold tabular-nums">{value}</p>
    </div>
  )
}

function SectionTitle({ children }: { children: ReactNode }) {
  return <h3 className="text-sm font-semibold">{children}</h3>
}

type PendingAction = "discard" | "revoke"

const CONFIRM_COPY: Record<
  PendingAction,
  { title: string; description: string; confirm: string }
> = {
  discard: {
    title: "确认丢弃预览",
    description: "丢弃会立即删除已解析的记录、错误和原始行内容，且不可恢复。",
    confirm: "确认丢弃",
  },
  revoke: {
    title: "确认撤销生效批次",
    description:
      "撤销会立即删除该批次记录，且不会恢复上一批次；考勤月份会标记为待重算。",
    confirm: "确认撤销",
  },
}

export function BatchDetailDialog({
  batchId,
  open,
  onOpenChange,
}: {
  batchId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const detailQuery = useImportBatch(batchId)
  const [severity, setSeverity] = useState<ImportSeverity | "all">("all")
  const [errorSkip, setErrorSkip] = useState(0)
  const [recordSkip, setRecordSkip] = useState(0)
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const errorsQuery = useImportBatchErrors(
    batchId,
    severity,
    errorSkip,
    ERROR_PAGE_SIZE,
  )
  const recordsQuery = useImportBatchRecords(
    batchId,
    recordSkip,
    RECORD_PAGE_SIZE,
  )
  const discardMutation = useDiscardImport()
  const revokeMutation = useRevokeImport()
  const batch = detailQuery.data
  const actionPending = discardMutation.isPending || revokeMutation.isPending

  const runAction = async () => {
    if (!pendingAction) return
    setActionError(null)
    try {
      if (pendingAction === "discard") {
        await discardMutation.mutateAsync(batchId)
        showSuccessToast("预览批次已丢弃。")
      } else {
        await revokeMutation.mutateAsync(batchId)
        showSuccessToast("生效批次已撤销。")
      }
      setPendingAction(null)
      onOpenChange(false)
    } catch (error) {
      const message = getRequestErrorMessage(error)
      setActionError(message)
      showErrorToast(message)
    }
  }

  const dataType = (batch?.data_type ?? "punch") as AttendanceImportDataType
  const statusView = batch ? batchStatusView(batch) : null
  const samples = (batch?.samples ?? []) as Record<string, unknown>[]
  const mapping = (batch?.column_mapping ?? {}) as Record<
    string,
    { column?: string; index?: number } | undefined
  >
  const headerColumns = (batch?.header_columns ?? []).map((column) =>
    String(column),
  )
  const mappingRows = IMPORT_FIELDS[dataType]
    .map((field) => ({ field, entry: mapping[field.key] }))
    .filter(({ entry }) => entry !== undefined)
  const errors = errorsQuery.data?.data ?? []
  const recordRows = (recordsQuery.data?.records ??
    []) as unknown as RecordRow[]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-h-[90vh] max-w-5xl overflow-y-auto"
        data-testid="batch-detail-dialog"
      >
        <DialogHeader>
          <DialogTitle>批次详情</DialogTitle>
          <DialogDescription>
            查看解析计数、列映射快照、错误报告与规范化记录；丢弃和撤销会立即删除批次数据。
          </DialogDescription>
        </DialogHeader>

        {detailQuery.isLoading ? (
          <LoadingState rows={3} />
        ) : detailQuery.isError || !batch || !statusView ? (
          <ErrorState
            message={getErrorMessage(detailQuery.error)}
            onRetry={() => void detailQuery.refetch()}
          />
        ) : (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">
                {IMPORT_DATA_TYPE_LABELS[dataType]}
              </Badge>
              <Badge variant={statusView.variant}>{statusView.label}</Badge>
              <Badge variant="secondary">
                {IMPORT_SOURCE_LABELS[batch.source]}
              </Badge>
              <span className="text-sm text-muted-foreground">
                {batch.month} · {batchSourceLabel(batch)} ·{" "}
                {formatDateTime(batch.created_at)}
              </span>
            </div>

            {isPreviewExpired(batch) && (
              <Alert variant="destructive" data-testid="batch-expired">
                <AlertTitle>预览已过期</AlertTitle>
                <AlertDescription>
                  该预览批次已超过 24 小时，不能提交；可以丢弃以立即清理数据。
                </AlertDescription>
              </Alert>
            )}

            {batch.superseded_by_batch_id && (
              <Alert data-testid="batch-superseded-by">
                <AlertTitle>已被后续批次替代</AlertTitle>
                <AlertDescription>
                  替代批次 ID：{batch.superseded_by_batch_id}
                  。本批次记录保留用于审计；原始行内容在 90 天后清理。
                </AlertDescription>
              </Alert>
            )}

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
              <Stat label="源数据行" value={batch.source_rows} />
              <Stat label="有效记录" value={batch.valid_records} />
              <Stat label="跳过记录" value={batch.skipped_records} />
              <Stat label="数据错误" value={batch.error_records} />
              <Stat label="带告警记录" value={batch.warning_records} />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1.5">
                <SectionTitle>跳过原因</SectionTitle>
                <ImportIssueBadges counts={batch.skip_counts} />
              </div>
              <div className="space-y-1.5">
                <SectionTitle>告警</SectionTitle>
                <ImportIssueBadges counts={batch.warning_counts} />
              </div>
            </div>

            <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
              <span>提交时间：{formatDateTime(batch.committed_at)}</span>
              <span>替代时间：{formatDateTime(batch.superseded_at)}</span>
              <span>丢弃时间：{formatDateTime(batch.discarded_at)}</span>
              <span>撤销时间：{formatDateTime(batch.revoked_at)}</span>
              <span>过期时间：{formatDateTime(batch.expires_at)}</span>
            </div>

            <div className="space-y-2">
              <SectionTitle>表头与列映射</SectionTitle>
              <p className="text-sm text-muted-foreground">
                表头第 {batch.header_row_number ?? "—"} 行 · 共{" "}
                {headerColumns.length} 列
              </p>
              <div className="flex flex-wrap gap-1.5">
                {headerColumns.map((column, index) => (
                  <Badge key={`${index}-${column}`} variant="outline">
                    {column || `第 ${index + 1} 列`}
                  </Badge>
                ))}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {mappingRows.length === 0 ? (
                  <span className="text-sm text-muted-foreground">
                    没有映射快照。
                  </span>
                ) : (
                  mappingRows.map(({ field, entry }) => (
                    <Badge key={field.key} variant="secondary">
                      {field.label}
                      {" → "}
                      {entry?.column ??
                        headerColumns[entry?.index ?? -1] ??
                        "未映射"}
                    </Badge>
                  ))
                )}
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <SectionTitle>样例数据（前 20 条）</SectionTitle>
                <span className="text-xs text-muted-foreground">
                  解析器 {batch.parser_version}
                </span>
              </div>
              <SampleTable dataType={dataType} samples={samples} />
            </div>

            <div className="space-y-2" data-testid="batch-errors">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <SectionTitle>错误与告警</SectionTitle>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">级别</span>
                  <Select
                    value={severity}
                    onValueChange={(value) => {
                      setSeverity(value as ImportSeverity | "all")
                      setErrorSkip(0)
                    }}
                  >
                    <SelectTrigger
                      className="w-32"
                      aria-label="错误级别"
                      data-testid="error-severity-filter"
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">全部</SelectItem>
                      <SelectItem value="error">仅错误</SelectItem>
                      <SelectItem value="warning">仅告警</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              {errorsQuery.isLoading ? (
                <p className="text-sm text-muted-foreground">正在加载错误…</p>
              ) : errorsQuery.isError ? (
                <p className="text-sm text-destructive">
                  错误报告加载失败：{getErrorMessage(errorsQuery.error)}
                </p>
              ) : errors.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  没有错误或告警。
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>行</TableHead>
                        <TableHead>级别</TableHead>
                        <TableHead>代码</TableHead>
                        <TableHead>列</TableHead>
                        <TableHead>说明</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {errors.map((error) => (
                        <TableRow key={error.id}>
                          <TableCell className="tabular-nums">
                            {error.source_row_number}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant={
                                error.severity === "error"
                                  ? "destructive"
                                  : "secondary"
                              }
                            >
                              {IMPORT_SEVERITY_LABELS[error.severity]}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {IMPORT_ROW_CODE_LABELS[error.code] ?? error.code}
                          </TableCell>
                          <TableCell>{error.column_name ?? "—"}</TableCell>
                          <TableCell className="min-w-[220px]">
                            {error.message}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
              {errorsQuery.data && (
                <PageControls
                  skip={errorSkip}
                  count={errorsQuery.data.count}
                  pageSize={ERROR_PAGE_SIZE}
                  onChange={setErrorSkip}
                  testId="error-pagination"
                />
              )}
            </div>

            <div className="space-y-2" data-testid="batch-records">
              <SectionTitle>规范化记录</SectionTitle>
              {recordsQuery.isLoading ? (
                <p className="text-sm text-muted-foreground">正在加载记录…</p>
              ) : recordsQuery.isError ? (
                <p className="text-sm text-destructive">
                  规范化记录加载失败：{getErrorMessage(recordsQuery.error)}
                </p>
              ) : recordRows.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  没有规范化记录。
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {RECORD_COLUMNS[dataType].map((column) => (
                          <TableHead key={column.label}>
                            {column.label}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {recordRows.map((record, index) => (
                        <TableRow key={String(record.id ?? index)}>
                          {RECORD_COLUMNS[dataType].map((column) => (
                            <TableCell key={column.label}>
                              {column.render(record)}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
              {recordsQuery.data && (
                <PageControls
                  skip={recordSkip}
                  count={recordsQuery.data.count}
                  pageSize={RECORD_PAGE_SIZE}
                  onChange={setRecordSkip}
                  testId="record-pagination"
                />
              )}
            </div>

            {pendingAction && (
              <Alert variant="destructive" data-testid="batch-action-confirm">
                <AlertTitle>{CONFIRM_COPY[pendingAction].title}</AlertTitle>
                <AlertDescription>
                  <p>{CONFIRM_COPY[pendingAction].description}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <LoadingButton
                      type="button"
                      size="sm"
                      variant="destructive"
                      loading={actionPending}
                      onClick={() => void runAction()}
                      data-testid={`confirm-${pendingAction}`}
                    >
                      {CONFIRM_COPY[pendingAction].confirm}
                    </LoadingButton>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => setPendingAction(null)}
                    >
                      取消
                    </Button>
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {actionError && (
              <Alert variant="destructive" data-testid="batch-action-error">
                <AlertTitle>操作失败</AlertTitle>
                <AlertDescription>{actionError}</AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {batch && (
          <DialogFooter className="flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span className="text-xs text-muted-foreground">
              批次 ID：{batch.id}
            </span>
            <div className="flex flex-wrap gap-2">
              {batch.status === "preview" ? (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => setPendingAction("discard")}
                  data-testid="discard-batch"
                >
                  <Trash2 className="mr-1 size-4" />
                  丢弃预览
                </Button>
              ) : batch.status === "committed" ? (
                <Button
                  type="button"
                  size="sm"
                  variant="destructive"
                  onClick={() => setPendingAction("revoke")}
                  data-testid="revoke-batch"
                >
                  <RotateCcw className="mr-1 size-4" />
                  撤销生效批次
                </Button>
              ) : (
                <span className="text-sm text-muted-foreground">
                  终态批次不可再操作。
                </span>
              )}
            </div>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
