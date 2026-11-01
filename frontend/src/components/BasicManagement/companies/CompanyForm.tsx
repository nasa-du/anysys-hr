import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  CompaniesService,
  type CompanyPublic,
  type ErrorDetail,
} from "@/client"
import { DeleteBlockedDialog } from "@/components/BasicManagement/shared/DeleteBlockedDialog"
import { FormDrawer } from "@/components/BasicManagement/shared/FormDrawer"
import { StatusSwitch } from "@/components/BasicManagement/shared/StatusSwitch"
import { Button } from "@/components/ui/button"
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

const formSchema = z.object({
  company_code: z
    .string()
    .min(1, "请输入公司编码")
    .max(32, "公司编码不能超过 32 个字符")
    .regex(/^[A-Z0-9_-]+$/, "只能包含大写字母、数字、下划线或短横线"),
  company_name: z
    .string()
    .min(1, "请输入公司名称")
    .max(100, "公司名称不能超过 100 个字符"),
  is_active: z.boolean(),
  note: z.string().max(500, "备注不能超过 500 个字符"),
})

type FormData = z.infer<typeof formSchema>

interface CompanyFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  company: CompanyPublic | null
}

const emptyValues: FormData = {
  company_code: "",
  company_name: "",
  is_active: true,
  note: "",
}

export function CompanyForm({ open, onOpenChange, company }: CompanyFormProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [blocked, setBlocked] = useState<ErrorDetail | null>(null)
  const isEditing = company !== null

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: emptyValues,
  })

  useEffect(() => {
    if (!open) return
    form.reset(
      company
        ? {
            company_code: company.company_code,
            company_name: company.company_name,
            is_active: company.is_active,
            note: company.note ?? "",
          }
        : emptyValues,
    )
  }, [company, form, open])

  const mutation = useMutation({
    mutationFn: async (data: FormData) => {
      const note = data.note.trim() === "" ? null : data.note
      if (company) {
        return CompaniesService.updateCompany({
          path: { company_id: company.id },
          body: {
            company_name: data.company_name,
            is_active: data.is_active,
            note,
          },
        })
      }
      return CompaniesService.createCompany({
        body: {
          company_code: data.company_code,
          company_name: data.company_name,
          is_active: data.is_active,
          note,
        },
      })
    },
    onSuccess: () => {
      showSuccessToast(isEditing ? "公司更新成功" : "公司创建成功")
      onOpenChange(false)
    },
    onError: (error) => {
      const detail = getErrorDetail(error)
      if (detail?.code === "deactivate_blocked") {
        form.setValue("is_active", company?.is_active ?? true)
        setBlocked(detail)
        return
      }

      const fieldErrors = getFieldErrors(error)
      for (const [field, message] of Object.entries(fieldErrors)) {
        if (field in emptyValues) {
          form.setError(field as keyof FormData, { message })
        }
      }
      if (Object.keys(fieldErrors).length === 0) {
        showErrorToast(getErrorMessage(error))
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["basic", "companies"] })
    },
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate({ ...data, company_code: data.company_code.toUpperCase() })
  }

  return (
    <>
      <FormDrawer
        open={open}
        onOpenChange={onOpenChange}
        title={isEditing ? "编辑公司" : "新建公司"}
        description="公司之间扁平，不设上下级；业务编码创建后不可修改，名称允许重复。"
      >
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
            <FormField
              control={form.control}
              name="company_code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    公司编码 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      placeholder="如 RX"
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
              name="company_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    公司名称 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input placeholder="如 荣新建设" required {...field} />
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
                    停用后不再出现在切换器中；已存在的部门、岗位、成本中心与员工数据保留。
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

      <DeleteBlockedDialog
        open={blocked !== null}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) setBlocked(null)
        }}
        title="无法停用公司"
        detail={blocked}
        confirmLabel="无法停用"
      />
    </>
  )
}
