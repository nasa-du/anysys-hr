import type { ImportBatchPublic, ImportMappingTemplatePublic } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { AttendanceImportDataType } from "@/lib/enums"
import { IMPORT_FIELDS } from "./import-fields"
import type { ImportColumnMapping } from "./queries"

interface MappingStepProps {
  dataType: AttendanceImportDataType
  batch: ImportBatchPublic
  overrides: ImportColumnMapping
  applying: boolean
  template: ImportMappingTemplatePublic | null
  onChange: (field: string, index: number | null) => void
  onApplyTemplate: (mapping: ImportColumnMapping) => void
  onApply: () => void
}

type MappingEntry = { column?: string; index?: number }

function mappingEntries(
  raw: Record<string, unknown> | undefined,
): Record<string, MappingEntry> {
  if (!raw) return {}
  const entries: Record<string, MappingEntry> = {}
  for (const [field, value] of Object.entries(raw)) {
    if (value && typeof value === "object") {
      entries[field] = value as MappingEntry
    }
  }
  return entries
}

/** Detected aliases, manual overrides, and ignored columns (spec §6.2). */
export function MappingStep({
  dataType,
  batch,
  overrides,
  applying,
  template,
  onChange,
  onApplyTemplate,
  onApply,
}: MappingStepProps) {
  const headerColumns = (batch.header_columns ?? []).map((column) =>
    String(column),
  )
  const detected = mappingEntries(batch.column_mapping)
  const fields = IMPORT_FIELDS[dataType]
  const usedIndexes = new Set(
    Object.values(detected)
      .map((entry) => entry.index)
      .filter((index): index is number => typeof index === "number"),
  )
  const ignoredColumns = headerColumns.filter(
    (_column, index) => !usedIndexes.has(index),
  )

  const templateMapping = mappingEntries(template?.mapping)
  const templateOverrides: ImportColumnMapping = {}
  for (const field of fields) {
    const entry = templateMapping[field.key]
    if (!entry) continue
    const index =
      typeof entry.column === "string"
        ? headerColumns.indexOf(entry.column)
        : typeof entry.index === "number" &&
            headerColumns[entry.index] !== undefined
          ? entry.index
          : -1
    if (index >= 0) {
      templateOverrides[field.key] = index
    }
  }
  const requiredFields = fields.filter((field) => field.required)
  const canApplyTemplate =
    requiredFields.length > 0 &&
    requiredFields.every((field) => templateOverrides[field.key] !== undefined)

  return (
    <Card data-testid="import-mapping-step">
      <CardHeader className="border-b">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-lg">2. 列映射</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              已根据表头自动识别；可手动改列后重新预览。没有位置兜底，必填列必须映射。
            </p>
          </div>
          <Badge variant="outline">第 {batch.header_row_number} 行为表头</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-5 pt-6">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {fields.map((field) => {
            const value = overrides[field.key]
            return (
              <div key={field.key} className="space-y-1.5">
                <Label
                  className="flex items-center gap-1.5"
                  htmlFor={`mapping-${field.key}`}
                >
                  {field.label}
                  {field.required ? (
                    <span className="text-destructive">*</span>
                  ) : (
                    <span className="text-xs text-muted-foreground">可选</span>
                  )}
                </Label>
                <Select
                  value={
                    value === null || value === undefined
                      ? "none"
                      : String(value)
                  }
                  onValueChange={(next) =>
                    onChange(field.key, next === "none" ? null : Number(next))
                  }
                >
                  <SelectTrigger
                    id={`mapping-${field.key}`}
                    aria-label={`${field.label}映射列`}
                  >
                    <SelectValue placeholder="选择源列" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">未映射</SelectItem>
                    {headerColumns.map((column, index) => (
                      <SelectItem
                        key={`${index}-${column}`}
                        value={String(index)}
                      >
                        {column || `第 ${index + 1} 列`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )
          })}
        </div>

        <div
          className="flex flex-wrap items-center gap-2 text-sm"
          data-testid="ignored-columns"
        >
          <span className="text-muted-foreground">已忽略列：</span>
          {ignoredColumns.length === 0 ? (
            <span className="text-muted-foreground">无</span>
          ) : (
            ignoredColumns.map((column, index) => (
              <Badge key={`${column}-${index}`} variant="secondary">
                {column || "空列名"}
              </Badge>
            ))
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <LoadingButton
            type="button"
            onClick={onApply}
            loading={applying}
            data-testid="apply-mapping"
          >
            应用映射并重新预览
          </LoadingButton>
          {canApplyTemplate && (
            <Button
              type="button"
              variant="outline"
              onClick={() => onApplyTemplate(templateOverrides)}
            >
              套用上次成功映射
            </Button>
          )}
          <span className="text-xs text-muted-foreground">
            修改映射会创建新的预览批次；旧预览 24
            小时后过期，并在下次导入时自动清理。
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
