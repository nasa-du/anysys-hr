import type { ReactNode } from "react"

import type { ImportPreviewPublic } from "@/client"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  type AttendanceImportDataType,
  IMPORT_COMMIT_BLOCKED_LABELS,
  IMPORT_DATA_TYPE_LABELS,
  IMPORT_ROW_CODE_LABELS,
  IMPORT_SEVERITY_LABELS,
  LEAVE_KIND_LABELS,
} from "@/lib/enums"

interface PreviewStepProps {
  dataType: AttendanceImportDataType
  preview: ImportPreviewPublic
}

type SampleRow = { [key: string]: unknown }

type SampleColumn = {
  label: string
  render: (row: SampleRow) => ReactNode
}

const dateTimeFormatter = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
})

function text(row: SampleRow, key: string): string {
  const value = row[key]
  return value === null || value === undefined || value === ""
    ? "—"
    : String(value)
}

function dateTime(value: unknown): string {
  if (typeof value !== "string" || !value) return "—"
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime())
    ? value
    : dateTimeFormatter.format(parsed)
}

function overtimeDays(value: unknown): string {
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

const SAMPLE_COLUMNS: Record<AttendanceImportDataType, SampleColumn[]> = {
  punch: [
    { label: "行", render: (row) => text(row, "source_row_number") },
    { label: "工号", render: (row) => text(row, "employee_no") },
    { label: "姓名", render: (row) => text(row, "employee_name") },
    { label: "考勤日期", render: (row) => text(row, "attendance_date") },
    { label: "打卡时间", render: (row) => dateTime(row.punch_time) },
    { label: "结果", render: (row) => text(row, "punch_result") },
  ],
  trip: [
    { label: "行", render: (row) => text(row, "source_row_number") },
    { label: "拆分", render: (row) => text(row, "split_index") },
    { label: "姓名", render: (row) => text(row, "employee_name") },
    { label: "审批编号", render: (row) => text(row, "approval_no") },
    { label: "开始", render: (row) => dateTime(row.start_at) },
    { label: "结束", render: (row) => dateTime(row.end_at) },
  ],
  ot: [
    { label: "行", render: (row) => text(row, "source_row_number") },
    { label: "姓名", render: (row) => text(row, "employee_name") },
    { label: "审批编号", render: (row) => text(row, "approval_no") },
    { label: "开始", render: (row) => dateTime(row.start_at) },
    { label: "结束", render: (row) => dateTime(row.end_at) },
    { label: "按日分钟", render: (row) => overtimeDays(row.days) },
  ],
  leave: [
    { label: "行", render: (row) => text(row, "source_row_number") },
    { label: "姓名", render: (row) => text(row, "employee_name") },
    { label: "审批编号", render: (row) => text(row, "approval_no") },
    { label: "类型", render: (row) => text(row, "leave_type") },
    {
      label: "归类",
      render: (row) => {
        const kind = row.leave_kind
        return typeof kind === "string" && kind in LEAVE_KIND_LABELS
          ? LEAVE_KIND_LABELS[kind as keyof typeof LEAVE_KIND_LABELS]
          : text(row, "leave_kind")
      },
    },
    { label: "天数", render: (row) => text(row, "days") },
    { label: "休息开始", render: (row) => dateTime(row.rest_start_at) },
    { label: "休息结束", render: (row) => dateTime(row.rest_end_at) },
  ],
}

function StatCard({
  name,
  label,
  value,
}: {
  name: string
  label: string
  value: number | string
}) {
  return (
    <div
      className="rounded-lg border bg-card px-4 py-3"
      data-testid={`import-stat-${name}`}
    >
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  )
}

function CountBadges({
  counts,
  labels,
}: {
  counts: Record<string, number> | undefined
  labels: Record<string, string>
}) {
  const entries = Object.entries(counts ?? {}).filter(([, count]) => count > 0)
  if (entries.length === 0) {
    return <span className="text-sm text-muted-foreground">无</span>
  }
  return (
    <div className="flex flex-wrap gap-2">
      {entries.map(([code, count]) => (
        <Badge key={code} variant="secondary">
          {labels[code] ?? code} × {count}
        </Badge>
      ))}
    </div>
  )
}

/** Preview statistics, errors/warnings, samples, impact, and commit gate. */
export function PreviewStep({ dataType, preview }: PreviewStepProps) {
  const { batch, stats, employees, impact } = preview
  const errors = preview.errors ?? []
  const samples = (preview.samples ?? []) as SampleRow[]
  const errorTotal = preview.error_total ?? errors.length
  const expiresAt = batch.expires_at ? new Date(batch.expires_at) : null
  const isExpired = expiresAt !== null && expiresAt.getTime() <= Date.now()
  const blockedReason = preview.commit_blocked_reason
  const blockedLabel = blockedReason
    ? (IMPORT_COMMIT_BLOCKED_LABELS[blockedReason] ?? blockedReason)
    : null
  const sampleColumns = SAMPLE_COLUMNS[dataType]

  return (
    <div className="flex flex-col gap-6" data-testid="import-preview-step">
      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="text-lg">3. 预览</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                {IMPORT_DATA_TYPE_LABELS[dataType]} · {batch.month} ·{" "}
                {batch.file_name ?? "粘贴内容"}
                {batch.sheet_name ? ` · ${batch.sheet_name}` : ""} · 解析器{" "}
                {batch.parser_version}
              </p>
            </div>
            <Badge variant="outline">
              有效期至 {expiresAt ? dateTimeFormatter.format(expiresAt) : "—"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-5 pt-6">
          {isExpired && (
            <Alert variant="destructive" data-testid="preview-expired">
              <AlertTitle>预览已过期</AlertTitle>
              <AlertDescription>
                预览批次有效期为 24 小时，请重新上传或粘贴内容后再提交。
              </AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <StatCard
              name="source-rows"
              label="源数据行"
              value={stats.source_rows ?? 0}
            />
            <StatCard
              name="valid-records"
              label="有效记录"
              value={stats.valid_records ?? 0}
            />
            <StatCard
              name="skipped-records"
              label="跳过记录"
              value={stats.skipped_records ?? 0}
            />
            <StatCard
              name="error-records"
              label="数据错误"
              value={stats.error_records ?? 0}
            />
            <StatCard
              name="warning-records"
              label="带告警记录"
              value={stats.warning_records ?? 0}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <p className="text-sm font-medium">跳过原因</p>
              <CountBadges
                counts={stats.skip_counts}
                labels={IMPORT_ROW_CODE_LABELS}
              />
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">告警</p>
              <CountBadges
                counts={stats.warning_counts}
                labels={IMPORT_ROW_CODE_LABELS}
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-3 text-sm">
            <Badge variant="outline">匹配员工 {employees.matched ?? 0}</Badge>
            <Badge variant="outline">未知员工 {employees.unknown ?? 0}</Badge>
            <Badge variant="outline">
              重名 {employees.duplicate_name ?? 0}
            </Badge>
            <Badge variant="outline">
              受影响员工 {employees.affected ?? 0}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b">
          <CardTitle className="text-lg">与当前生效批次对比</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 pt-6 text-sm">
          {impact.current_batch ? (
            <p className="text-muted-foreground">
              当前生效批次：{impact.current_batch.file_name ?? "—"} ·{" "}
              {dateTimeFormatter.format(
                new Date(impact.current_batch.committed_at),
              )}{" "}
              · 有效 {impact.current_batch.valid_records} 条 / 源{" "}
              {impact.current_batch.source_rows} 行
            </p>
          ) : (
            <p className="text-muted-foreground">
              当前没有生效批次；提交后将新增本次有效记录。
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <Badge variant="secondary">
              有效记录变化{" "}
              {impact.valid_records_delta !== undefined &&
              impact.valid_records_delta > 0
                ? `+${impact.valid_records_delta}`
                : (impact.valid_records_delta ?? 0)}
            </Badge>
            <Badge variant="secondary">
              员工重合 {impact.employee_overlap ?? 0}
            </Badge>
            <Badge variant="secondary">
              新增员工 {impact.employees_added ?? 0}
            </Badge>
            <Badge variant="secondary">
              移除员工 {impact.employees_removed ?? 0}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="text-lg">错误与告警</CardTitle>
            <Badge variant="outline">
              显示 {errors.length} / 共 {errorTotal} 条
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          {errors.length === 0 ? (
            <p className="text-sm text-muted-foreground">没有错误或告警。</p>
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
                  {errors.map((error, index) => (
                    <TableRow key={`${error.source_row_number}-${index}`}>
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
                      <TableCell className="min-w-[240px]">
                        {error.message}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="text-lg">样例数据</CardTitle>
            <Badge variant="outline">最多显示前 20 条</Badge>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          {samples.length === 0 ? (
            <p className="text-sm text-muted-foreground">没有有效记录样例。</p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    {sampleColumns.map((column) => (
                      <TableHead key={column.label}>{column.label}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {samples.map((sample, index) => (
                    <TableRow
                      key={`${String(sample.source_row_number)}-${index}`}
                    >
                      {sampleColumns.map((column) => (
                        <TableCell key={column.label}>
                          {column.render(sample)}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex flex-col gap-3 pt-6">
          {!preview.can_commit && blockedLabel ? (
            <Alert variant="destructive">
              <AlertTitle>当前不可提交</AlertTitle>
              <AlertDescription>{blockedLabel}</AlertDescription>
            </Alert>
          ) : (
            <Alert>
              <AlertTitle>预览校验通过</AlertTitle>
              <AlertDescription>
                本阶段先提供解析与预览；提交、替换旧批次与撤销将在下一阶段开放。
              </AlertDescription>
            </Alert>
          )}
          <div>
            <Button type="button" disabled title="提交功能将在下一阶段开放">
              提交生效
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
