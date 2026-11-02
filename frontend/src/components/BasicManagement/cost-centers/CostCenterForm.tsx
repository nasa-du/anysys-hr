import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  type CostCenterPublic,
  CostCentersService,
  type CostCenterTreeNode,
  type CostCenterUpdate,
  type ErrorDetail,
} from "@/client"
import { DeleteBlockedDialog } from "@/components/BasicManagement/shared/DeleteBlockedDialog"
import { FormDrawer } from "@/components/BasicManagement/shared/FormDrawer"
import { ManagerField } from "@/components/BasicManagement/shared/ManagerField"
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
const MAX_BUDGET = 999_999_999_999.99

const formSchema = z.object({
  cost_org_code: z
    .string()
    .min(1, "请输入成本中心编码")
    .max(32, "成本中心编码不能超过 32 个字符")
    .regex(/^[A-Z0-9_-]+$/, "只能包含大写字母、数字、下划线或短横线"),
  cost_org_name: z
    .string()
    .min(1, "请输入成本中心名称")
    .max(100, "成本中心名称不能超过 100 个字符"),
  parent_id: z.string(),
  manager_id: z.string(),
  budget: z
    .string()
    .min(1, "请输入预算")
    .refine(
      (value) => /^\d+(\.\d{1,2})?$/.test(value.trim()),
      "请输入不小于 0、最多两位小数的金额",
    )
    .refine(
      (value) => Number(value) <= MAX_BUDGET,
      "预算不能超过 999999999999.99",
    ),
  warn_pct: z
    .number({ message: "请输入有效的整数" })
    .int("请输入整数")
    .min(1, "预警比例不能小于 1")
    .max(100, "预警比例不能大于 100"),
  order_no: z.number({ message: "请输入有效的整数" }).int("请输入整数"),
  is_active: z.boolean(),
  note: z.string().max(500, "备注不能超过 500 个字符"),
})

type FormData = z.infer<typeof formSchema>

interface CostCenterFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  companyId: string
  tree: CostCenterTreeNode[]
  costCenter: CostCenterPublic | null
  defaultParentId: string | null
}

const emptyValues: FormData = {
  cost_org_code: "",
  cost_org_name: "",
  parent_id: ROOT_OPTION_VALUE,
  manager_id: "",
  budget: "0.00",
  warn_pct: 85,
  order_no: 0,
  is_active: true,
  note: "",
}

export function CostCenterForm({
  open,
  onOpenChange,
  companyId,
  tree,
  costCenter,
  defaultParentId,
}: CostCenterFormProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [blocked, setBlocked] = useState<ErrorDetail | null>(null)
  const isEditing = costCenter !== null

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: emptyValues,
  })

  useEffect(() => {
    if (!open) return
    form.reset(
      costCenter
        ? {
            cost_org_code: costCenter.cost_org_code,
            cost_org_name: costCenter.cost_org_name,
            parent_id: costCenter.parent_id ?? ROOT_OPTION_VALUE,
            manager_id: costCenter.manager_id ?? "",
            budget: costCenter.budget,
            warn_pct: costCenter.warn_pct,
            order_no: costCenter.order_no,
            is_active: costCenter.is_active,
            note: costCenter.note ?? "",
          }
        : {
            ...emptyValues,
            parent_id: defaultParentId ?? ROOT_OPTION_VALUE,
          },
    )
  }, [costCenter, defaultParentId, form, open])

  const disabledIds = useMemo(() => {
    if (!costCenter) return new Set<string>()
    return new Set([
      costCenter.id,
      ...collectDescendantIds(tree, costCenter.id),
    ])
  }, [costCenter, tree])

  const parentOptions = useMemo(() => {
    // Inactive cost centers are not selectable; the current parent stays
    // visible as a historical reference, labeled 「停用」.
    return flattenTree(tree).filter(
      ({ node: option }) =>
        option.is_active || option.id === costCenter?.parent_id,
    )
  }, [costCenter?.parent_id, tree])

  const mutation = useMutation({
    mutationFn: async (data: FormData) => {
      const note = data.note.trim() === "" ? null : data.note
      const parentId =
        data.parent_id === ROOT_OPTION_VALUE ? null : data.parent_id
      const managerId = data.manager_id === "" ? null : data.manager_id
      if (costCenter) {
        const body: CostCenterUpdate = {
          cost_org_name: data.cost_org_name,
          budget: data.budget.trim(),
          warn_pct: data.warn_pct,
          order_no: data.order_no,
          is_active: data.is_active,
          note,
        }
        // Omit an unchanged parent so editing an inactive cost center does not
        // trip the structural-change rule.
        if (parentId !== (costCenter.parent_id ?? null)) {
          body.parent_id = parentId
        }
        // An unchanged resigned manager must stay visible and is not
        // re-validated as a new assignment.
        if (managerId !== (costCenter.manager_id ?? null)) {
          body.manager_id = managerId
        }
        return CostCentersService.updateCostCenter({
          path: { cost_center_id: costCenter.id },
          body,
        })
      }
      return CostCentersService.createCostCenter({
        body: {
          cost_org_code: data.cost_org_code,
          cost_org_name: data.cost_org_name,
          company_id: companyId,
          parent_id: parentId,
          manager_id: managerId,
          budget: data.budget.trim(),
          warn_pct: data.warn_pct,
          order_no: data.order_no,
          is_active: data.is_active,
          note,
        },
      })
    },
    onSuccess: () => {
      showSuccessToast(isEditing ? "成本中心更新成功" : "成本中心创建成功")
      onOpenChange(false)
    },
    onError: (error) => {
      const detail = getErrorDetail(error)
      if (detail?.code === "deactivate_blocked") {
        form.setValue("is_active", costCenter?.is_active ?? true)
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
      queryClient.invalidateQueries({ queryKey: ["basic", "cost-centers"] })
    },
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate({
      ...data,
      cost_org_code: data.cost_org_code.toUpperCase(),
    })
  }

  const isCreatingChild = !isEditing && defaultParentId !== null

  return (
    <>
      <FormDrawer
        open={open}
        onOpenChange={onOpenChange}
        title={
          isEditing
            ? "编辑成本中心"
            : isCreatingChild
              ? "新建下级成本中心"
              : "新建成本中心"
        }
        description="成本中心编码在公司内唯一且创建后不可修改；上级成本中心必须属于同一公司且处于启用状态。"
      >
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
            <FormField
              control={form.control}
              name="cost_org_code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    成本中心编码 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      placeholder="如 K1"
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
              name="cost_org_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    成本中心名称 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input placeholder="如 生产成本中心" required {...field} />
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
                  <FormLabel>上级成本中心</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger aria-label="上级成本中心">
                        <SelectValue placeholder="选择上级成本中心" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent className="max-h-72">
                      <SelectItem value={ROOT_OPTION_VALUE}>
                        无（作为根成本中心）
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
                            {option.cost_org_name}（{option.cost_org_code}）
                            {!option.is_active ? " 已停用" : ""}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    自身和下级成本中心不可选；停用成本中心不可作为上级。
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="manager_id"
              render={({ field }) => (
                <ManagerField
                  companyId={companyId}
                  value={field.value === "" ? null : field.value}
                  onValueChange={(value) => field.onChange(value ?? "")}
                  currentManager={
                    costCenter?.manager_id
                      ? {
                          id: costCenter.manager_id,
                          name: costCenter.manager_name ?? "离职员工",
                          status: costCenter.manager_status,
                        }
                      : null
                  }
                />
              )}
            />

            <div className="grid gap-5 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="budget"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>预算（元）</FormLabel>
                    <FormControl>
                      <Input
                        inputMode="decimal"
                        placeholder="0.00"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>不小于 0，最多两位小数。</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="warn_pct"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>预警比例（%）</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step={1}
                        value={Number.isNaN(field.value) ? "" : field.value}
                        onChange={(event) =>
                          field.onChange(
                            event.target.value === ""
                              ? Number.NaN
                              : event.target.valueAsNumber,
                          )
                        }
                        onBlur={field.onBlur}
                        name={field.name}
                        ref={field.ref}
                      />
                    </FormControl>
                    <FormDescription>1–100，用于预算预警。</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

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
                    停用前必须先停用下级成本中心并移走在职/试用期员工；停用后成本中心数据保留。
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
        title="无法停用成本中心"
        detail={blocked}
        confirmLabel="无法停用"
      />
    </>
  )
}
