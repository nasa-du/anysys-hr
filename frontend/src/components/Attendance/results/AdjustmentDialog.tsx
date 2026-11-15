import { zodResolver } from "@hookform/resolvers/zod"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type {
  AttendanceAdjustmentPublic,
  AttendanceAdjustmentValues,
  AttendanceDayDetailPublic,
  AttendanceDayResultPublic,
} from "@/client"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
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
import {
  getErrorDetail,
  getErrorMessage,
  getFieldErrors,
} from "@/lib/api-error"
import {
  type AttendanceDayStatus,
  DAY_STATUS_LABELS,
  DAY_STATUS_OPTIONS,
} from "@/lib/enums"

import { useCreateAdjustment } from "./queries"
import { formatWorkDate } from "./result-format"

const NUMERIC_FIELDS = [
  { key: "worked_minutes", label: "实际工时（分钟）" },
  { key: "ot_weekday_minutes", label: "平日加班（分钟）" },
  { key: "ot_weekend_minutes", label: "周末加班（分钟）" },
  { key: "ot_holiday_minutes", label: "节假日加班（分钟）" },
  { key: "late_minutes", label: "迟到（分钟）" },
  { key: "early_minutes", label: "早退（分钟）" },
  { key: "missing_punch_count", label: "缺卡（张）" },
] as const

const FRACTION_FIELDS = [
  { key: "attendance_fraction", label: "出勤比例（0–1）" },
  { key: "leave_days", label: "请假天数（0–1）" },
] as const

type NumericKey = (typeof NUMERIC_FIELDS)[number]["key"]
type FractionKey = (typeof FRACTION_FIELDS)[number]["key"]
type ValueKey = NumericKey | FractionKey

const DAY_STATUS_VALUES = DAY_STATUS_OPTIONS.map((option) => option.value) as [
  AttendanceDayStatus,
  ...AttendanceDayStatus[],
]

function minuteText(label: string) {
  return z
    .string()
    .refine((value) => value.trim() !== "", `${label}不能为空`)
    .refine((value) => {
      const number = Number(value)
      return Number.isInteger(number) && number >= 0
    }, `${label}请输入不小于 0 的整数`)
}

function fractionText(label: string) {
  return z
    .string()
    .refine((value) => value.trim() !== "", `${label}不能为空`)
    .refine((value) => {
      const number = Number(value)
      return Number.isFinite(number) && number >= 0 && number <= 1
    }, `${label}请输入 0 到 1 之间的数字`)
}

const formSchema = z.object({
  day_status: z.enum(DAY_STATUS_VALUES),
  worked_minutes: minuteText("实际工时"),
  ot_weekday_minutes: minuteText("平日加班"),
  ot_weekend_minutes: minuteText("周末加班"),
  ot_holiday_minutes: minuteText("节假日加班"),
  late_minutes: minuteText("迟到"),
  early_minutes: minuteText("早退"),
  missing_punch_count: minuteText("缺卡"),
  attendance_fraction: fractionText("出勤比例"),
  leave_days: fractionText("请假天数"),
  note: z.string().max(500, "备注不能超过 500 个字符"),
  reason: z
    .string()
    .refine((value) => value.trim() !== "", "请填写调整理由")
    .max(500, "调整理由不能超过 500 个字符"),
})

type FormData = z.infer<typeof formSchema>

function asText(value: unknown): string {
  if (value === null || value === undefined) return ""
  return String(value)
}

function adjustedValue(
  dayResult: AttendanceDayResultPublic,
  active: AttendanceAdjustmentPublic | null,
  field: string,
): unknown {
  if (active && field in active.adjusted_values) {
    return active.adjusted_values[field]
  }
  return dayResult[field as keyof AttendanceDayResultPublic]
}

function baselineValue(
  dayResult: AttendanceDayResultPublic,
  active: AttendanceAdjustmentPublic | null,
  field: string,
): unknown {
  if (active && field in active.adjusted_values) {
    return active.original_values[field]
  }
  return dayResult[field as keyof AttendanceDayResultPublic]
}

function initialForm(
  dayResult: AttendanceDayResultPublic,
  active: AttendanceAdjustmentPublic | null,
): FormData {
  const values = Object.fromEntries(
    [...NUMERIC_FIELDS, ...FRACTION_FIELDS].map(({ key }) => [
      key,
      asText(adjustedValue(dayResult, active, key)),
    ]),
  ) as Record<ValueKey, string>
  return {
    day_status: asText(
      adjustedValue(dayResult, active, "day_status"),
    ) as AttendanceDayStatus,
    note: asText(adjustedValue(dayResult, active, "note")),
    reason: "",
    ...values,
  }
}

function originalLabel(field: string, value: unknown): string {
  if (value === null || value === undefined || value === "") return "—"
  if (field === "day_status") {
    return DAY_STATUS_LABELS[value as AttendanceDayStatus] ?? String(value)
  }
  return String(value)
}

type AdjustmentDialogProps = {
  open: boolean
  detail: AttendanceDayDetailPublic
  onOpenChange: (open: boolean) => void
  onSaved: () => void
}

/**
 * Result-layer adjustment form. Each save creates a new version; the previous
 * active version is superseded. Fields left at the calculated value are not
 * sent, so the version is exactly the override set. ``base_version`` detects a
 * concurrent submission and shows a refresh path instead of overwriting it.
 */
export function AdjustmentDialog({
  open,
  detail,
  onOpenChange,
  onSaved,
}: AdjustmentDialogProps) {
  const dayResult = detail.day_result
  const active =
    (detail.adjustments ?? []).find((item) => item.status === "active") ?? null
  const createAdjustment = useCreateAdjustment()
  const { showSuccessToast } = useCustomToast()
  const [conflict, setConflict] = useState(false)

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: initialForm(dayResult, active),
  })

  useEffect(() => {
    if (!open) return
    form.reset(initialForm(dayResult, active))
    setConflict(false)
  }, [open, dayResult, active, form])

  const buildValues = (data: FormData): AttendanceAdjustmentValues | null => {
    const values: AttendanceAdjustmentValues = {}
    let changed = false
    const baseline = (field: string) => baselineValue(dayResult, active, field)

    if (data.day_status !== baseline("day_status")) {
      values.day_status = data.day_status
      changed = true
    }
    for (const { key } of NUMERIC_FIELDS) {
      const number = Number(data[key])
      if (number !== Number(baseline(key))) {
        values[key] = number
        changed = true
      }
    }
    for (const { key } of FRACTION_FIELDS) {
      const raw = data[key].trim()
      if (Number(raw) !== Number(baseline(key))) {
        values[key] = raw
        changed = true
      }
    }
    const nextNote = data.note.trim() === "" ? null : data.note.trim()
    if ((nextNote ?? "") !== asText(baseline("note"))) {
      values.note = nextNote
      changed = true
    }
    return changed ? values : null
  }

  const submit = form.handleSubmit((data) => {
    setConflict(false)
    form.clearErrors("root")
    const values = buildValues(data)
    if (values === null) {
      form.setError("root", { message: "请至少修改一个字段" })
      return
    }
    createAdjustment.mutate(
      {
        company_id: detail.day_result.company_id,
        employee_id: detail.day_result.employee_id,
        work_date: detail.day_result.work_date,
        base_version: active?.version ?? 0,
        adjusted_values: values,
        reason: data.reason.trim(),
      },
      {
        onSuccess: () => {
          showSuccessToast(active ? "已生成新的调整版本" : "人工调整已保存")
          onOpenChange(false)
          onSaved()
        },
        onError: (mutationError) => {
          const detailError = getErrorDetail(mutationError)
          if (detailError?.code === "adjustment_conflict") {
            setConflict(true)
            return
          }
          const fieldErrors = getFieldErrors(mutationError)
          let mapped = 0
          for (const [field, message] of Object.entries(fieldErrors)) {
            if (field in formSchema.shape) {
              form.setError(field as keyof FormData, { message })
              mapped += 1
            }
          }
          if (mapped === 0) {
            form.setError("root", { message: getErrorMessage(mutationError) })
          }
        },
      },
    )
  })

  const rootError = form.formState.errors.root?.message

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-h-[90vh] overflow-y-auto sm:max-w-2xl"
        data-testid="adjustment-dialog"
      >
        <DialogHeader>
          <DialogTitle>
            {active ? "再次调整考勤结果" : "人工调整考勤结果"}
          </DialogTitle>
          <DialogDescription>
            {dayResult.employee_name ?? dayResult.employee_id} ·{" "}
            {formatWorkDate(dayResult.work_date)}
            。保存后会生成新版本；原值来自当前计算结果，
            未修改的字段不进入覆盖集。每次保存都会记录操作者与理由。
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form className="space-y-4" onSubmit={submit}>
            <FormField
              control={form.control}
              name="day_status"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-center gap-3">
                    <span
                      className="w-32 shrink-0 text-sm text-muted-foreground"
                      data-testid="adjustment-original-day_status"
                    >
                      原值：
                      {originalLabel(
                        "day_status",
                        baselineValue(dayResult, active, "day_status"),
                      )}
                    </span>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger
                          className="w-full"
                          aria-label="考勤状态"
                          data-testid="adjustment-input-day_status"
                        >
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {DAY_STATUS_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            <section className="grid gap-3 sm:grid-cols-2">
              {[...NUMERIC_FIELDS, ...FRACTION_FIELDS].map(({ key, label }) => (
                <FormField
                  key={key}
                  control={form.control}
                  name={key}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{label}</FormLabel>
                      <p
                        className="text-xs text-muted-foreground"
                        data-testid={`adjustment-original-${key}`}
                      >
                        原值：
                        {originalLabel(
                          key,
                          baselineValue(dayResult, active, key),
                        )}
                      </p>
                      <FormControl>
                        <Input
                          type="number"
                          min={0}
                          max={
                            key === "attendance_fraction" ||
                            key === "leave_days"
                              ? 1
                              : undefined
                          }
                          step={
                            key === "attendance_fraction" ||
                            key === "leave_days"
                              ? 0.1
                              : 1
                          }
                          aria-label={label}
                          data-testid={`adjustment-input-${key}`}
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              ))}
            </section>

            <FormField
              control={form.control}
              name="note"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>备注</FormLabel>
                  <p
                    className="text-xs text-muted-foreground"
                    data-testid="adjustment-original-note"
                  >
                    原值：
                    {originalLabel(
                      "note",
                      baselineValue(dayResult, active, "note"),
                    )}
                  </p>
                  <FormControl>
                    <Textarea
                      aria-label="备注"
                      data-testid="adjustment-input-note"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="reason"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    调整理由 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Textarea
                      aria-label="调整理由"
                      data-testid="adjustment-reason"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {conflict && (
              <Alert variant="destructive" data-testid="adjustment-conflict">
                <AlertTitle>调整版本已变化</AlertTitle>
                <AlertDescription>
                  其他人已提交了新的调整版本，当前表单基于旧版本。请刷新后重试。
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    data-testid="adjustment-refresh"
                    onClick={() => {
                      onOpenChange(false)
                      onSaved()
                    }}
                  >
                    刷新
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            {rootError && (
              <p
                className="text-sm text-destructive"
                data-testid="adjustment-error"
              >
                {rootError}
              </p>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                取消
              </Button>
              <LoadingButton
                type="submit"
                loading={createAdjustment.isPending}
                data-testid="adjustment-submit"
              >
                保存调整
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
