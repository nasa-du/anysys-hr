import { type ChangeEvent, useState } from "react"

import type { ImportPreviewPublic } from "@/client"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorDetail, getErrorMessage } from "@/lib/api-error"
import {
  type AttendanceImportDataType,
  IMPORT_DATA_TYPE_LABELS,
} from "@/lib/enums"
import { DataTypeCards } from "./DataTypeCards"
import { MappingStep } from "./MappingStep"
import { PreviewStep } from "./PreviewStep"
import {
  type ImportColumnMapping,
  useMappingTemplate,
  usePreviewImport,
} from "./queries"

const MAX_FILE_BYTES = 10 * 1024 * 1024
const ALLOWED_EXTENSIONS = [".csv", ".tsv", ".xlsx"]

const PASTE_PLACEHOLDERS: Record<AttendanceImportDataType, string> = {
  punch:
    "工号\t考勤日期\t打卡时间\t打卡结果\nE3001\t2026-09-01\t2026-09-01 08:18\t正常",
  trip: "出差人\t开始时间\t结束时间\t审批结果\n吕倩\t2026-09-16 08:00\t2026-09-16 12:00\t审批通过",
  ot: "创建人\t加班开始时间\t加班结束时间\t审批结果\n邓丹静\t2026-09-14 08:00\t2026-09-14 17:30\t审批通过",
  leave:
    "创建人\t请假类型\t请假天数\t休息开始时间\t休息结束时间\t审批结果\n吕倩\t事假\t2\t2026-09-27 08:30\t2026-09-28 17:30\t审批通过",
}

type InputMode = "upload" | "paste"

function overridesFromMapping(
  raw: Record<string, unknown>,
): ImportColumnMapping {
  const overrides: ImportColumnMapping = {}
  for (const [field, value] of Object.entries(raw)) {
    if (!value || typeof value !== "object") continue
    const index = (value as { index?: unknown }).index
    if (typeof index === "number") {
      overrides[field] = index
    }
  }
  return overrides
}

function fileProblem(file: File): string | null {
  const lowered = file.name.toLowerCase()
  if (!ALLOWED_EXTENSIONS.some((extension) => lowered.endsWith(extension))) {
    return "仅支持 .csv、.tsv、.xlsx 文件；旧版 .xls 和启用宏的文件请另存为 .xlsx。"
  }
  if (file.size > MAX_FILE_BYTES) {
    return "文件大小超过 10 MB 限制。"
  }
  return null
}

interface ImportWizardProps {
  companyId: string
  month: string
}

/** Upload/paste → mapping → preview wizard from spec §9.2 (B1). */
export function ImportWizard({ companyId, month }: ImportWizardProps) {
  const { showErrorToast } = useCustomToast()
  const previewMutation = usePreviewImport()
  const [dataType, setDataType] = useState<AttendanceImportDataType>("punch")
  const templateQuery = useMappingTemplate(companyId, dataType)
  const [mode, setMode] = useState<InputMode>("upload")
  const [file, setFile] = useState<File | null>(null)
  const [text, setText] = useState("")
  const [sheetName, setSheetName] = useState("")
  const [sheetOptions, setSheetOptions] = useState<string[]>([])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [preview, setPreview] = useState<ImportPreviewPublic | null>(null)
  const [overrides, setOverrides] = useState<ImportColumnMapping>({})

  const resetResult = () => {
    setPreview(null)
    setSheetOptions([])
    setErrorMessage(null)
    setOverrides({})
  }

  const changeDataType = (next: AttendanceImportDataType) => {
    if (next === dataType) return
    setDataType(next)
    setSheetName("")
    resetResult()
  }

  const changeMode = (next: InputMode) => {
    if (next === mode) return
    setMode(next)
    setSheetOptions([])
    setErrorMessage(null)
    setPreview(null)
  }

  const selectFile = (event: ChangeEvent<HTMLInputElement>) => {
    const next = event.target.files?.[0] ?? null
    if (!next) {
      setFile(null)
      return
    }
    const problem = fileProblem(next)
    if (problem) {
      showErrorToast(problem)
      event.target.value = ""
      setFile(null)
      return
    }
    setFile(next)
    resetResult()
  }

  const runPreview = async (
    options: {
      columnMapping?: ImportColumnMapping | null
      sheetName?: string | null
    } = {},
  ) => {
    const useFile = mode === "upload"
    if (useFile && !file) {
      showErrorToast("请先选择要导入的文件。")
      return
    }
    if (!useFile && !text.trim()) {
      showErrorToast("请先粘贴要导入的内容。")
      return
    }
    try {
      const result = await previewMutation.mutateAsync({
        companyId,
        dataType,
        month,
        file: useFile ? file : null,
        text: useFile ? null : text,
        sheetName: options.sheetName ?? (sheetName || null),
        columnMapping: options.columnMapping ?? null,
      })
      setPreview(result)
      setOverrides(overridesFromMapping(result.batch.column_mapping ?? {}))
      setSheetOptions([])
      setErrorMessage(null)
    } catch (error) {
      const detail = getErrorDetail(error)
      if (detail?.code === "sheet_required") {
        const names = (detail.field_errors?.sheet_name ?? "")
          .split(",")
          .map((name) => name.trim())
          .filter(Boolean)
        setSheetOptions(names)
        if (names.length > 0) setSheetName(names[0])
        setErrorMessage(detail.message)
        return
      }
      const message = detail?.message ?? getErrorMessage(error)
      setErrorMessage(message)
      showErrorToast(message)
    }
  }

  const applyMapping = () => {
    void runPreview({ columnMapping: overrides })
  }

  const applyTemplate = (mapping: ImportColumnMapping) => {
    setOverrides(mapping)
    void runPreview({ columnMapping: mapping })
  }

  const changeOverride = (field: string, index: number | null) => {
    setOverrides((current) => ({ ...current, [field]: index }))
  }

  return (
    <div className="flex flex-col gap-6">
      <DataTypeCards value={dataType} month={month} onChange={changeDataType} />

      <div className="rounded-lg border bg-card">
        <div className="border-b px-6 py-4">
          <h2 className="text-lg font-semibold">1. 上传或粘贴内容</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            当前数据类型：{IMPORT_DATA_TYPE_LABELS[dataType]} · 目标月份 {month}
            。解析在服务端完成，原始文件不会保留。
          </p>
        </div>
        <div className="space-y-4 px-6 py-5">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              aria-pressed={mode === "upload"}
              onClick={() => changeMode("upload")}
              className={`rounded-md border px-3 py-1.5 text-sm ${
                mode === "upload"
                  ? "border-primary bg-primary/5 font-medium"
                  : "text-muted-foreground"
              }`}
            >
              上传文件
            </button>
            <button
              type="button"
              aria-pressed={mode === "paste"}
              onClick={() => changeMode("paste")}
              className={`rounded-md border px-3 py-1.5 text-sm ${
                mode === "paste"
                  ? "border-primary bg-primary/5 font-medium"
                  : "text-muted-foreground"
              }`}
            >
              粘贴内容
            </button>
          </div>

          {mode === "upload" ? (
            <div className="space-y-1.5">
              <Label htmlFor="import-file">选择导入文件</Label>
              <Input
                id="import-file"
                aria-label="选择导入文件"
                type="file"
                accept=".csv,.tsv,.xlsx"
                onChange={selectFile}
              />
              <p className="text-xs text-muted-foreground">
                支持 .csv、.tsv、.xlsx；单文件不超过 10 MB，最多 100,000 行。
              </p>
              {file && (
                <p className="text-sm" data-testid="selected-file">
                  已选择：{file.name}（{(file.size / 1024).toFixed(1)} KB）
                </p>
              )}
            </div>
          ) : (
            <div className="space-y-1.5">
              <Label htmlFor="import-text">粘贴导入内容</Label>
              <Textarea
                id="import-text"
                aria-label="粘贴导入内容"
                className="min-h-32 font-mono text-sm"
                placeholder={PASTE_PLACEHOLDERS[dataType]}
                value={text}
                onChange={(event) => setText(event.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                支持 Tab、逗号或竖线分隔，第一段非空行必须是表头。
              </p>
            </div>
          )}

          {errorMessage && sheetOptions.length === 0 && (
            <Alert variant="destructive" data-testid="import-error">
              <AlertTitle>无法解析</AlertTitle>
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}

          {sheetOptions.length > 0 && (
            <Alert data-testid="sheet-required">
              <AlertTitle>需要选择工作表</AlertTitle>
              <AlertDescription>
                <div className="mt-2 flex flex-wrap items-end gap-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="import-sheet">工作表</Label>
                    <Select value={sheetName} onValueChange={setSheetName}>
                      <SelectTrigger id="import-sheet" className="w-48">
                        <SelectValue placeholder="选择工作表" />
                      </SelectTrigger>
                      <SelectContent>
                        {sheetOptions.map((name) => (
                          <SelectItem key={name} value={name}>
                            {name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <LoadingButton
                    type="button"
                    loading={previewMutation.isPending}
                    onClick={() =>
                      void runPreview({ sheetName: sheetName || null })
                    }
                  >
                    使用该工作表解析
                  </LoadingButton>
                </div>
              </AlertDescription>
            </Alert>
          )}

          <LoadingButton
            type="button"
            loading={previewMutation.isPending}
            onClick={() => void runPreview()}
            data-testid="parse-preview"
          >
            解析并预览
          </LoadingButton>
        </div>
      </div>

      {preview && (
        <>
          <MappingStep
            dataType={dataType}
            batch={preview.batch}
            overrides={overrides}
            applying={previewMutation.isPending}
            template={templateQuery.data ?? null}
            onChange={changeOverride}
            onApplyTemplate={applyTemplate}
            onApply={applyMapping}
          />
          <PreviewStep
            key={preview.batch.id}
            dataType={dataType}
            preview={preview}
          />
        </>
      )}
    </div>
  )
}
