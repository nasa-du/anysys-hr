import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type EmployeePublic, EmployeesService } from "@/client"
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
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorMessage, getFieldErrors } from "@/lib/api-error"
import { todayShanghai } from "@/lib/datetime"

const formSchema = z.object({
  resign_date: z
    .string()
    .min(1, "请选择离职日期")
    .refine((value) => value <= todayShanghai(), "离职日期不能晚于今天"),
  note: z.string().max(500, "备注不能超过 500 个字符"),
})

type FormData = z.infer<typeof formSchema>

interface LeaveDialogProps {
  employee: EmployeePublic | null
  onOpenChange: (open: boolean) => void
}

export function LeaveDialog({ employee, onOpenChange }: LeaveDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    defaultValues: { resign_date: todayShanghai(), note: "" },
  })

  useEffect(() => {
    if (!employee) return
    form.reset({ resign_date: todayShanghai(), note: "" })
  }, [employee, form])

  const mutation = useMutation({
    mutationFn: async (data: FormData) => {
      if (!employee) throw new Error("未选择员工")
      return EmployeesService.updateEmployee({
        path: { employee_id: employee.id },
        body: {
          status: "resigned",
          resign_date: data.resign_date,
          note: data.note.trim() === "" ? null : data.note,
        },
      })
    },
    onSuccess: () => {
      showSuccessToast("员工已办理离职")
      onOpenChange(false)
    },
    onError: (error) => {
      const fieldErrors = getFieldErrors(error)
      for (const [field, message] of Object.entries(fieldErrors)) {
        if (field in formSchema.shape) {
          form.setError(field as keyof FormData, { message })
        }
      }
      if (Object.keys(fieldErrors).length === 0) {
        showErrorToast(getErrorMessage(error))
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["basic", "employees"] })
    },
  })

  const onSubmit = (data: FormData) => {
    if (employee && data.resign_date < employee.hire_date) {
      form.setError("resign_date", {
        message: "离职日期不能早于入职日期",
      })
      return
    }
    mutation.mutate(data)
  }

  return (
    <Dialog open={employee !== null} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>办理离职</DialogTitle>
          <DialogDescription>
            {employee?.name}（{employee?.employee_no}
            ）离职后档案只读，只能修正备注与离职日期。
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="resign_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    离职日期 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input type="date" max={todayShanghai()} {...field} />
                  </FormControl>
                  <FormDescription>
                    不得早于入职日期 {employee?.hire_date}，且不能晚于今天。
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
            <DialogFooter>
              <LoadingButton
                type="submit"
                variant="destructive"
                loading={mutation.isPending}
              >
                确认离职
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
