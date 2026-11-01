import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  type DepartmentPublic,
  DepartmentsService,
  type DepartmentTreeNode,
  type DepartmentUpdate,
  type ErrorDetail,
} from "@/client"
import { DeleteBlockedDialog } from "@/components/BasicManagement/shared/DeleteBlockedDialog"
import { FormDrawer } from "@/components/BasicManagement/shared/FormDrawer"
import { StatusSwitch } from "@/components/BasicManagement/shared/StatusSwitch"
import {
  collectDescendantIds,
  flattenTree,
} from "@/components/BasicManagement/shared/tree-utils"
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

const ROOT_OPTION_VALUE = "__root__"

const formSchema = z.object({
  dept_code: z
    .string()
    .min(1, "请输入部门编码")
    .max(32, "部门编码不能超过 32 个字符")
    .regex(/^[A-Z0-9_-]+$/, "只能包含大写字母、数字、下划线或短横线"),
  dept_name: z
    .string()
    .min(1, "请输入部门名称")
    .max(100, "部门名称不能超过 100 个字符"),
  parent_id: z.string(),
  order_no: z.number({ message: "请输入有效的整数" }).int("请输入整数"),
  is_active: z.boolean(),
  note: z.string().max(500, "备注不能超过 500 个字符"),
})

type FormData = z.infer<typeof formSchema>

interface DepartmentFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  companyId: string
  tree: DepartmentTreeNode[]
  department: DepartmentPublic | null
  defaultParentId: string | null
}

export function DepartmentForm({
  open,
  onOpenChange,
  companyId,
  tree,
  department,
  defaultParentId,
}: DepartmentFormProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [blocked, setBlocked] = useState<ErrorDetail | null>(null)
  const isEditing = department !== null

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      dept_code: "",
      dept_name: "",
      parent_id: ROOT_OPTION_VALUE,
      order_no: 0,
      is_active: true,
      note: "",
    },
  })

  useEffect(() => {
    if (!open) return
    form.reset(
      department
        ? {
            dept_code: department.dept_code,
            dept_name: department.dept_name,
            parent_id: department.parent_id ?? ROOT_OPTION_VALUE,
            order_no: department.order_no,
            is_active: department.is_active,
            note: department.note ?? "",
          }
        : {
            dept_code: "",
            dept_name: "",
            parent_id: defaultParentId ?? ROOT_OPTION_VALUE,
            order_no: 0,
            is_active: true,
            note: "",
          },
    )
  }, [defaultParentId, department, form, open])

  const disabledIds = useMemo(() => {
    if (!department) return new Set<string>()
    return new Set([
      department.id,
      ...collectDescendantIds(tree, department.id),
    ])
  }, [department, tree])

  const parentOptions = useMemo(() => {
    // Inactive departments are not selectable; the current parent stays
    // visible as a historical reference, labeled 「停用」.
    return flattenTree(tree).filter(
      ({ node: option }) =>
        option.is_active || option.id === department?.parent_id,
    )
  }, [department?.parent_id, tree])

  const mutation = useMutation({
    mutationFn: async (data: FormData) => {
      const note = data.note.trim() === "" ? null : data.note
      const parentId =
        data.parent_id === ROOT_OPTION_VALUE ? null : data.parent_id
      if (department) {
        const body: DepartmentUpdate = {
          dept_name: data.dept_name,
          order_no: data.order_no,
          is_active: data.is_active,
          note,
        }
        // Omit an unchanged parent so editing an inactive department does not
        // trip the structural-change rule.
        if (parentId !== (department.parent_id ?? null)) {
          body.parent_id = parentId
        }
        return DepartmentsService.updateDepartment({
          path: { department_id: department.id },
          body,
        })
      }
      return DepartmentsService.createDepartment({
        body: {
          dept_code: data.dept_code,
          dept_name: data.dept_name,
          company_id: companyId,
          parent_id: parentId,
          order_no: data.order_no,
          is_active: data.is_active,
          note,
        },
      })
    },
    onSuccess: () => {
      showSuccessToast(isEditing ? "部门更新成功" : "部门创建成功")
      onOpenChange(false)
    },
    onError: (error) => {
      const detail = getErrorDetail(error)
      if (detail?.code === "deactivate_blocked") {
        form.setValue("is_active", department?.is_active ?? true)
        setBlocked(detail)
        return
      }

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
      queryClient.invalidateQueries({ queryKey: ["basic", "departments"] })
    },
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate({ ...data, dept_code: data.dept_code.toUpperCase() })
  }

  const isCreatingChild = !isEditing && defaultParentId !== null

  return (
    <>
      <FormDrawer
        open={open}
        onOpenChange={onOpenChange}
        title={
          isEditing ? "编辑部门" : isCreatingChild ? "新建下级部门" : "新建部门"
        }
        description="部门编码在公司内唯一且创建后不可修改；上级部门必须属于同一公司且处于启用状态。"
      >
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
            <FormField
              control={form.control}
              name="dept_code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    部门编码 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      placeholder="如 D1"
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
              name="dept_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    部门名称 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input placeholder="如 生产部" required {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="parent_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>上级部门</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger aria-label="上级部门">
                        <SelectValue placeholder="选择上级部门" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent className="max-h-72">
                      <SelectItem value={ROOT_OPTION_VALUE}>
                        无（作为根部门）
                      </SelectItem>
                      {parentOptions.map(({ node: option, depth }) => (
                        <SelectItem
                          key={option.id}
                          value={option.id}
                          disabled={
                            disabledIds.has(option.id) || !option.is_active
                          }
                        >
                          <span style={{ paddingLeft: depth * 12 }}>
                            {option.dept_name}（{option.dept_code}）
                            {!option.is_active ? " 停用" : ""}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    自身和下级部门不可选；停用部门不可作为上级。
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
                    数字越小越靠前，同级按编码升序排列。
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
                    停用前必须先停用下级部门并移走在职/试用期员工；停用后部门数据保留。
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
        title="无法停用部门"
        detail={blocked}
        confirmLabel="无法停用"
      />
    </>
  )
}
