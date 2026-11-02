import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  type DepartmentPublic,
  type ErrorDetail,
  type PositionPublic,
  PositionsService,
  type PositionUpdate,
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

const NO_DEPARTMENT = "__none__"

const formSchema = z.object({
  position_code: z
    .string()
    .min(1, "请输入岗位编码")
    .max(32, "岗位编码不能超过 32 个字符")
    .regex(/^[A-Z0-9_-]+$/, "只能包含大写字母、数字、下划线或短横线"),
  position_name: z
    .string()
    .min(1, "请输入岗位名称")
    .max(100, "岗位名称不能超过 100 个字符"),
  dept_id: z.string(),
  order_no: z.number({ message: "请输入有效的整数" }).int("请输入整数"),
  is_active: z.boolean(),
  note: z.string().max(500, "备注不能超过 500 个字符"),
})

type FormData = z.infer<typeof formSchema>

interface PositionFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  companyId: string
  position: PositionPublic | null
  departments: DepartmentPublic[]
}

const emptyValues: FormData = {
  position_code: "",
  position_name: "",
  dept_id: NO_DEPARTMENT,
  order_no: 0,
  is_active: true,
  note: "",
}

export function PositionForm({
  open,
  onOpenChange,
  companyId,
  position,
  departments,
}: PositionFormProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [blocked, setBlocked] = useState<ErrorDetail | null>(null)
  const isEditing = position !== null

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: emptyValues,
  })

  useEffect(() => {
    if (!open) return
    form.reset(
      position
        ? {
            position_code: position.position_code,
            position_name: position.position_name,
            dept_id: position.dept_id ?? NO_DEPARTMENT,
            order_no: position.order_no,
            is_active: position.is_active,
            note: position.note ?? "",
          }
        : emptyValues,
    )
  }, [form, open, position])

  const departmentOptions = useMemo(() => {
    // Inactive departments are not selectable; the current default stays
    // visible as a historical reference, labeled 「停用」.
    return departments.filter(
      (department) =>
        department.is_active || department.id === position?.dept_id,
    )
  }, [departments, position?.dept_id])

  const mutation = useMutation({
    mutationFn: async (data: FormData) => {
      const note = data.note.trim() === "" ? null : data.note
      const deptId = data.dept_id === NO_DEPARTMENT ? null : data.dept_id
      if (position) {
        const body: PositionUpdate = {
          position_name: data.position_name,
          order_no: data.order_no,
          is_active: data.is_active,
          note,
        }
        // Omit an unchanged default department so editing an inactive
        // position does not trip the structural-change rule.
        if (deptId !== (position.dept_id ?? null)) {
          body.dept_id = deptId
        }
        return PositionsService.updatePosition({
          path: { position_id: position.id },
          body,
        })
      }
      return PositionsService.createPosition({
        body: {
          position_code: data.position_code,
          position_name: data.position_name,
          company_id: companyId,
          dept_id: deptId,
          order_no: data.order_no,
          is_active: data.is_active,
          note,
        },
      })
    },
    onSuccess: () => {
      showSuccessToast(isEditing ? "岗位更新成功" : "岗位创建成功")
      onOpenChange(false)
    },
    onError: (error) => {
      const detail = getErrorDetail(error)
      if (detail?.code === "deactivate_blocked") {
        form.setValue("is_active", position?.is_active ?? true)
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
      // A company_id error has no form field to attach to, so surface it as
      // a toast rather than failing silently.
      if (mappedFields === 0) {
        showErrorToast(getErrorMessage(error))
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["basic", "positions"] })
    },
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate({
      ...data,
      position_code: data.position_code.toUpperCase(),
    })
  }

  return (
    <>
      <FormDrawer
        open={open}
        onOpenChange={onOpenChange}
        title={isEditing ? "编辑岗位" : "新建岗位"}
        description="岗位编码在公司内唯一且创建后不可修改；默认部门只用于员工建档时带出部门，员工的实际部门可以不同。"
      >
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
            <FormField
              control={form.control}
              name="position_code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    岗位编码 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      placeholder="如 P1"
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
              name="position_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    岗位名称 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input placeholder="如 项目经理" required {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="dept_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>默认部门</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger aria-label="默认部门">
                        <SelectValue placeholder="选择默认部门" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent className="max-h-72">
                      <SelectItem value={NO_DEPARTMENT}>
                        无（不预设部门）
                      </SelectItem>
                      {departmentOptions.map((department) => (
                        <SelectItem
                          key={department.id}
                          value={department.id}
                          disabled={!department.is_active}
                        >
                          {department.dept_name}（{department.dept_code}）
                          {!department.is_active ? " 停用" : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    仅用于员工建档时带出部门；员工的实际部门可以与该默认部门不同。
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="order_no"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>排序号</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step={1}
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
                    数字越小越靠前，相同排序号按编码升序排列。
                  </FormDescription>
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
                    停用前必须先转移在职/试用期员工；停用后岗位数据保留，且不再出现在员工建档的岗位选择器中。
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
        title="无法停用岗位"
        detail={blocked}
        confirmLabel="无法停用"
      />
    </>
  )
}
