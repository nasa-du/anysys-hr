import { useState } from "react"

import type { ImportCommitPublic, ImportPreviewPublic } from "@/client"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useCustomToast from "@/hooks/useCustomToast"
import { getRequestErrorMessage } from "@/lib/api-error"
import {
  type AttendanceImportDataType,
  IMPORT_COMMIT_BLOCKED_LABELS,
  IMPORT_DATA_TYPE_LABELS,
  IMPORT_ROW_CODE_LABELS,
  IMPORT_SEVERITY_LABELS,
} from "@/lib/enums"
import { ImportIssueBadges } from "./ImportIssueBadges"
import { formatDateTime, isPreviewExpired } from "./import-format"
import { useCommitImport } from "./queries"
import { SampleTable } from "./SampleTable"

interface PreviewStepProps {
  dataType: AttendanceImportDataType
  preview: ImportPreviewPublic
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

/** Preview statistics, errors/warnings, samples, impact, and commit action. */
export function PreviewStep({ dataType, preview }: PreviewStepProps) {
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const commitMutation = useCommitImport()
  const [commitResult, setCommitResult] = useState<ImportCommitPublic | null>(
    null,
  )
  const [commitError, setCommitError] = useState<string | null>(null)
  const { batch, stats, employees, impact } = preview
  const errors = preview.errors ?? []
  const samples = (preview.samples ?? []) as Record<string, unknown>[]
  const errorTotal = preview.error_total ?? errors.length
  const expired = isPreviewExpired(batch)
  const blockedReason = preview.commit_blocked_reason
  const blockedLabel = blockedReason
    ? (IMPORT_COMMIT_BLOCKED_LABELS[blockedReason] ?? blockedReason)
    : null
  const commitAllowed =
    preview.can_commit && !expired && batch.status === "preview"

  const submitCommit = async () => {
    setCommitError(null)
    try {
      const result = await commitMutation.mutateAsync(batch.id)
      setCommitResult(result)
      showSuccessToast(
        result.superseded_batch_id
          ? "导入批次已提交生效，旧批次已置为「已替代」。"
          : "导入批次已提交生效。",
      )
    } catch (error) {
      const message = getRequestErrorMessage(error)
      setCommitError(message)
      showErrorToast(message)
    }
  }

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
            <Badge variant={commitResult ? "default" : "outline"}>
              {commitResult
                ? "已提交生效"
                : expired
                  ? "预览已过期"
                  : `有效期至 ${formatDateTime(batch.expires_at)}`}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-5 pt-6">
          {expired && (
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
              <ImportIssueBadges counts={stats.skip_counts} />
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">告警</p>
              <ImportIssueBadges counts={stats.warning_counts} />
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
              {formatDateTime(impact.current_batch.committed_at)} · 有效{" "}
              {impact.current_batch.valid_records} 条 / 源{" "}
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
          <SampleTable dataType={dataType} samples={samples} />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex flex-col gap-3 pt-6">
          {commitResult ? (
            <Alert data-testid="commit-success">
              <AlertTitle>已提交生效</AlertTitle>
              <AlertDescription>
                {commitResult.superseded_batch_id
                  ? `同范围的旧生效批次 ${commitResult.superseded_batch_id} 已置为「已替代」。`
                  : "该数据类型在该月份首次生效。"}
                考勤月份已标记为待重算；本次提交不会自动重算。
              </AlertDescription>
            </Alert>
          ) : commitError ? (
            <Alert variant="destructive" data-testid="commit-error">
              <AlertTitle>提交失败</AlertTitle>
              <AlertDescription>{commitError}</AlertDescription>
            </Alert>
          ) : !commitAllowed ? (
            <Alert variant="destructive">
              <AlertTitle>{expired ? "预览已过期" : "当前不可提交"}</AlertTitle>
              <AlertDescription>
                {expired
                  ? "请重新上传或粘贴内容生成新的预览后再提交。"
                  : (blockedLabel ?? "请重新预览后再提交。")}
              </AlertDescription>
            </Alert>
          ) : (
            <Alert>
              <AlertTitle>预览校验通过</AlertTitle>
              <AlertDescription>
                提交后本批次生效，同公司、同月份、同类型的旧生效批次将自动置为「已替代」，考勤月份标记为待重算。
              </AlertDescription>
            </Alert>
          )}
          {!commitResult && (
            <div>
              <LoadingButton
                type="button"
                loading={commitMutation.isPending}
                disabled={!commitAllowed}
                onClick={() => void submitCommit()}
                data-testid="commit-import"
              >
                提交生效
              </LoadingButton>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
