import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  AttendanceShiftsService,
  type ErrorDetail,
  type ShiftPublic,
  type ShiftUpdate,
} from "@/client"
import { FormDrawer } from "@/components/BasicManagement/shared/FormDrawer"
import { StatusSwitch } from "@/components/BasicManagement/shared/StatusSwitch"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"
import {
  getErrorDetail,
  getErrorMessage,
  getFieldErrors,
} from "@/lib/api-error"
import { invalidateShiftQueries } from "./queries"
import { ReferenceBlockedDialog } from "./ReferenceBlockedDialog"
import { toTimeInputValue, validateShiftTimeFields } from "./shift-time"

const COLOR_PATTERN = /^#[0-9A-Fa-f]{6}$/

const formSchema = z
  .object({
    shift_code: z
      .string()
      .min(1, "请输入班次编码")
      .max(32, "班次编码不能超过 32 个字符")
      .regex(/^[A-Z0-9_-]+$/, "只能包含大写字母、数字、下划线或短横线"),
    shift_name: z
      .string()
      .min(1, "请输入班次名称")
      .max(100, "班次名称不能超过 100 个字符"),
    start_time: z.string().min(1, "请输入开始时间"),
    end_time: z.string().min(1, "请输入结束时间"),
    cross_day: z.boolean(),
    break_start: z.string(),
    break_end: z.string(),
    rest_minutes: z
      .number({ message: "请输入有效的整数" })
      .int("请输入整数")
      .min(0, "不能小于 0"),
    color: z.string(),
    note: z.string().max(500, "备注不能超过 500 个字符"),
    is_active: z.boolean(),
  })
  .superRefine((data, ctx) => {
    const timeErrors = validateShiftTimeFields(data)
    for (const [field, message] of Object.entries(timeErrors)) {
      ctx.addIssue({
        code: "custom",
        path: [field],
        message,
      })
    }
    if (data.color !== "" && !COLOR_PATTERN.test(data.color)) {
      ctx.addIssue({
        code: "custom",
        path: ["color"],
        message: "颜色格式应为 #RRGGBB",
      })
    }
  })

type FormData = z.infer<typeof formSchema>

const emptyValues: FormData = {
  shift_code: "",
  shift_name: "",
  start_time: "",
  end_time: "",
  cross_day: false,
  break_start: "",
  break_end: "",
  rest_minutes: 0,
  color: "",
  note: "",
  is_active: true,
}

function valuesFrom(shift: ShiftPublic): FormData {
  return {
    shift_code: shift.shift_code,
    shift_name: shift.shift_name,
    start_time: toTimeInputValue(shift.start_time),
    end_time: toTimeInputValue(shift.end_time),
    cross_day: shift.cross_day,
    break_start: toTimeInputValue(shift.break_start),
    break_end: toTimeInputValue(shift.break_end),
    rest_minutes: shift.rest_minutes,
    color: shift.color ?? "",
    note: shift.note ?? "",
    is_active: shift.is_active,
  }
}

/**
 * Send only edited fields. Unchanged times stay out of the PATCH, so the
 * minute-granularity inputs never rewrite API-valid seconds.
 */
function updateBodyFrom(data: FormData, shift: ShiftPublic): ShiftUpdate {
  const body: ShiftUpdate = {}
  if (data.shift_name !== shift.shift_name) {
    body.shift_name = data.shift_name
  }
  if (data.start_time !== toTimeInputValue(shift.start_time)) {
    body.start_time = data.start_time
  }
  if (data.end_time !== toTimeInputValue(shift.end_time)) {
    body.end_time = data.end_time
  }
  if (data.cross_day !== shift.cross_day) {
    body.cross_day = data.cross_day
  }
  if (data.break_start !== toTimeInputValue(shift.break_start)) {
    body.break_start = data.break_start === "" ? null : data.break_start
  }
  if (data.break_end !== toTimeInputValue(shift.break_end)) {
    body.break_end = data.break_end === "" ? null : data.break_end
  }
  if (data.rest_minutes !== shift.rest_minutes) {
    body.rest_minutes = data.rest_minutes
  }
  const color = data.color.trim() === "" ? null : data.color.trim()
  if (color !== shift.color) {
    body.color = color
  }
  const note = data.note.trim() === "" ? null : data.note.trim()
  if (note !== shift.note) {
    body.note = note
  }
  if (data.is_active !== shift.is_active) {
    body.is_active = data.is_active
  }
  return body
}

interface ShiftFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  companyId: string
  shift: ShiftPublic | null
}

export function ShiftForm({
  open,
  onOpenChange,
  companyId,
  shift,
}: ShiftFormProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [blocked, setBlocked] = useState<ErrorDetail | null>(null)
  const isEditing = shift !== null

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: emptyValues,
  })

  useEffect(() => {
    if (!open) return
    form.reset(shift ? valuesFrom(shift) : emptyValues)
  }, [form, open, shift])

  const mutation = useMutation({
    mutationFn: async (data: FormData) => {
      if (shift) {
        return AttendanceShiftsService.updateShift({
          path: { shift_id: shift.id },
          body: updateBodyFrom(data, shift),
        })
      }
      return AttendanceShiftsService.createShift({
        body: {
          company_id: companyId,
          shift_code: data.shift_code,
          shift_name: data.shift_name,
          start_time: data.start_time,
          end_time: data.end_time,
          cross_day: data.cross_day,
          break_start: data.break_start === "" ? null : data.break_start,
          break_end: data.break_end === "" ? null : data.break_end,
          rest_minutes: data.rest_minutes,
          color: data.color.trim() === "" ? null : data.color.trim(),
          note: data.note.trim() === "" ? null : data.note.trim(),
          is_active: data.is_active,
        },
      })
    },
    onSuccess: () => {
      showSuccessToast(isEditing ? "班次更新成功" : "班次创建成功")
      onOpenChange(false)
    },
    onError: (error) => {
      const detail = getErrorDetail(error)
      if (detail?.code === "deactivate_blocked") {
        form.setValue("is_active", shift?.is_active ?? true)
        setBlocked(detail)
        return
      }

      const fieldErrors = getFieldErrors(error)
      let mappedFields = 0
      for (const [field, message] of Object.entries(fieldErrors)) {
        if (field in formSchema.shape) {
          form.setError(field as keyof FormData, { message })
          mappedFields += 1
        }
      }
      if (mappedFields === 0) {
        showErrorToast(getErrorMessage(error))
      }
    },
    onSettled: () => {
      invalidateShiftQueries(queryClient)
    },
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate({
      ...data,
      shift_code: data.shift_code.toUpperCase(),
    })
  }

  return (
    <>
      <FormDrawer
        open={open}
        onOpenChange={onOpenChange}
        title={isEditing ? "编辑班次" : "新建班次"}
        description="班次编码在公司内唯一且创建后不可修改；修改班次不会重写已有的排班快照。"
      >
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
            <FormField
              control={form.control}
              name="shift_code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    班次编码 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      placeholder="如 ADM"
                      required
                      disabled={isEditing}
                      className="uppercase"
                      {...field}
                      onChange={(event) =>
                        field.onChange(event.target.value.toUpperCase())
                      }
                    />
                  </FormControl>
                  <FormDescription>
                    大写字母、数字、下划线或短横线，1–32 位
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="shift_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    班次名称 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input placeholder="如 行政班" required {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="start_time"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      开始时间 <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input type="time" step={60} required {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="end_time"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      结束时间 <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input type="time" step={60} required {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="cross_day"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-center gap-2">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={(checked) =>
                          field.onChange(checked === true)
                        }
                      />
                    </FormControl>
                    <FormLabel className="font-normal">跨天班次</FormLabel>
                  </div>
                  <FormDescription>
                    跨天班次的结束时间必须早于或等于开始时间；两者相等表示 24
                    小时班次。
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="break_start"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>休息开始</FormLabel>
                    <FormControl>
                      <Input type="time" step={60} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="break_end"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>休息结束</FormLabel>
                    <FormControl>
                      <Input type="time" step={60} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <p className="text-sm text-muted-foreground">
              休息开始与结束须同时填写，并位于班次时间范围内。
            </p>

            <FormField
              control={form.control}
              name="rest_minutes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>休息扣减（分钟）</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step={1}
                      min={0}
                      value={field.value}
                      onChange={(event) =>
                        field.onChange(
                          event.target.value === ""
                            ? 0
                            : event.target.valueAsNumber,
                        )
                      }
                      onBlur={field.onBlur}
                      name={field.name}
                      ref={field.ref}
                    />
                  </FormControl>
                  <FormDescription>
                    不计入工作时长的休息分钟数，不能超过班次时长。
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="color"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>颜色</FormLabel>
                  <div className="flex items-center gap-2">
                    <FormControl>
                      <Input
                        placeholder="#2563EB"
                        className="font-mono"
                        {...field}
                      />
                    </FormControl>
                    {COLOR_PATTERN.test(field.value) && (
                      <span
                        className="size-8 shrink-0 rounded border"
                        style={{ backgroundColor: field.value }}
                        aria-hidden="true"
                      />
                    )}
                  </div>
                  <FormDescription>
                    日历展示色，格式 #RRGGBB；留空表示不设置。
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="note"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>备注</FormLabel>
                  <FormControl>
                    <Textarea placeholder="可选" rows={3} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>状态</FormLabel>
                  <div className="flex items-center gap-3">
                    <FormControl>
                      <StatusSwitch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <span className="text-sm text-muted-foreground">
                      {field.value ? "启用" : "停用"}
                    </span>
                  </div>
                  <FormDescription>
                    停用前必须没有启用中的排班方案引用该班次；停用后班次数据保留，但不再出现在新方案的选择器中。
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                disabled={mutation.isPending}
                onClick={() => onOpenChange(false)}
              >
                取消
              </Button>
              <LoadingButton type="submit" loading={mutation.isPending}>
                保存
              </LoadingButton>
            </div>
          </form>
        </Form>
      </FormDrawer>

      <ReferenceBlockedDialog
        detail={blocked}
        action="deactivate"
        onDismiss={() => setBlocked(null)}
      />
    </>
  )
}
