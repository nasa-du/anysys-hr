import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  AttendanceHolidaysService,
  type HolidayDayType,
  type HolidayPublic,
} from "@/client"
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
  FormDescription,
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
  type AttendanceHolidayDayType,
  HOLIDAY_DAY_TYPE_OPTIONS,
} from "@/lib/enums"
import { invalidateRuleHolidayQueries } from "./queries"

const formSchema = z.object({
  date: z.string().min(1, "请选择日期"),
  name: z
    .string()
    .min(1, "请输入节假日名称")
    .max(100, "名称不能超过 100 个字符"),
  day_type: z.enum(["holiday", "adjusted_workday"]),
  note: z.string().max(500, "备注不能超过 500 个字符"),
})

type FormData = z.infer<typeof formSchema>

function valuesFrom(
  holiday: HolidayPublic | null,
  defaultDate: string,
): FormData {
  return {
    date: holiday?.date ?? defaultDate,
    name: holiday?.name ?? "",
    day_type: (holiday?.day_type ?? "holiday") as AttendanceHolidayDayType,
    note: holiday?.note ?? "",
  }
}

interface HolidayFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  companyId: string
  holiday: HolidayPublic | null
  defaultDate: string
}

export function HolidayFormDialog({
  open,
  onOpenChange,
  companyId,
  holiday,
  defaultDate,
}: HolidayFormDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const isEditing = holiday !== null

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: valuesFrom(holiday, defaultDate),
  })

  useEffect(() => {
    if (!open) return
    form.reset(valuesFrom(holiday, defaultDate))
  }, [defaultDate, form, holiday, open])

  const mutation = useMutation({
    mutationFn: async (data: FormData) => {
      if (holiday) {
        return AttendanceHolidaysService.updateHoliday({
          path: { holiday_id: holiday.id },
          body: {
            name: data.name,
            day_type: data.day_type as HolidayDayType,
            note: data.note.trim() === "" ? null : data.note.trim(),
          },
        })
      }
      return AttendanceHolidaysService.createHoliday({
        body: {
          company_id: companyId,
          date: data.date,
          name: data.name,
          day_type: data.day_type as HolidayDayType,
          note: data.note.trim() === "" ? null : data.note.trim(),
        },
      })
    },
    onSuccess: () => {
      showSuccessToast(isEditing ? "节假日已更新" : "节假日已添加")
      onOpenChange(false)
      invalidateRuleHolidayQueries(queryClient)
    },
    onError: (error) => {
      const detail = getErrorDetail(error)
      if (detail?.code === "duplicate_holiday") {
        form.setError("date", {
          message: detail.field_errors?.date ?? "该日期已存在节假日记录",
        })
        return
      }

      const fieldErrors = getFieldErrors(error)
      let mapped = 0
      for (const [field, message] of Object.entries(fieldErrors)) {
        if (field in formSchema.shape) {
          form.setError(field as keyof FormData, { message })
          mapped += 1
        }
      }
      if (mapped === 0) {
        showErrorToast(getErrorMessage(error))
      }
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEditing ? "编辑节假日" : "添加节假日"}</DialogTitle>
          <DialogDescription>
            公司级日历，同一天只能有一条记录；调休上班优先于周末，法定节假日优先于周末。
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form
            className="space-y-4"
            data-testid="holiday-form"
            onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
          >
            <FormField
              control={form.control}
              name="date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    日期 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      type="date"
                      required
                      disabled={isEditing}
                      aria-label="节假日日期"
                      {...field}
                    />
                  </FormControl>
                  {isEditing && (
                    <FormDescription>
                      日期不可修改；如需移动节假日，请删除后重新创建。
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    名称 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      placeholder="如 中秋节 / 调休上班"
                      required
                      aria-label="节假日名称"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="day_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>日期类型</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger aria-label="日期类型">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {HOLIDAY_DAY_TYPE_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
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
                    <Textarea
                      rows={3}
                      placeholder="可选"
                      aria-label="节假日备注"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
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
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
