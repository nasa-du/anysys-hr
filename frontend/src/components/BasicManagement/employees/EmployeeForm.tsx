import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  type CostCenterPublic,
  type DepartmentTreeNode,
  type EmployeePublic,
  EmployeesService,
  type EmployeeUpdate,
  type PositionPublic,
} from "@/client"
import { FormDrawer } from "@/components/BasicManagement/shared/FormDrawer"
import { ManagerField } from "@/components/BasicManagement/shared/ManagerField"
import { flattenTree } from "@/components/BasicManagement/shared/tree-utils"
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
import { getErrorMessage, getFieldErrors } from "@/lib/api-error"
import { todayShanghai } from "@/lib/datetime"
import {
  CONTRACT_TYPE_OPTIONS,
  CREATE_EMPLOYEE_STATUS_OPTIONS,
  GENDER_NOT_PROVIDED_LABEL,
  GENDER_OPTIONS,
} from "@/lib/enums"

const NO_COST_CENTER = "__unassigned__"

const formSchema = z.object({
  employee_no: z
    .string()
    .min(1, "请输入工号")
    .max(32, "工号不能超过 32 个字符")
    .regex(/^[A-Z0-9_-]+$/, "只能包含大写字母、数字、下划线或短横线"),
  name: z.string().min(1, "请输入姓名").max(100, "姓名不能超过 100 个字符"),
  gender: z.string(),
  dept_id: z.string().min(1, "请选择部门"),
  position_id: z.string().min(1, "请选择岗位"),
  manager_id: z.string(),
  cost_org_id: z.string(),
  status: z.enum(["active", "probation"]),
  hire_date: z
    .string()
    .min(1, "请选择入职日期")
    .refine((value) => value <= todayShanghai(), "入职日期不能晚于今天"),
  resign_date: z.string(),
  contract_type: z.enum(["full_time", "part_time", "intern", "labor"]),
  daily_hours: z
    .string()
    .refine(
      (value) =>
        value.trim() === "" ||
        (/^\d+(\.\d{1,2})?$/.test(value.trim()) &&
          Number(value) > 0 &&
          Number(value) <= 24),
      "请输入大于 0、不超过 24 的工时，最多两位小数",
    ),
  monthly_rest: z
    .string()
    .refine(
      (value) => value.trim() === "" || /^\d+$/.test(value.trim()),
      "请输入不小于 0 的整数",
    ),
  confidentiality_level: z
    .string()
    .refine(
      (value) => value.trim() === "" || /^[1-5]$/.test(value.trim()),
      "请输入 1–5 的整数",
    ),
  note: z.string().max(500, "备注不能超过 500 个字符"),
})

type FormData = z.infer<typeof formSchema>

interface EmployeeFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  companyId: string
  departments: DepartmentTreeNode[]
  positions: PositionPublic[]
  costCenters: CostCenterPublic[]
  employee: EmployeePublic | null
  /** Resigned employees open a note/resign-date-only correction form. */
  correction?: boolean
}

function emptyValues(): FormData {
  return {
    employee_no: "",
    name: "",
    gender: "",
    dept_id: "",
    position_id: "",
    manager_id: "",
    cost_org_id: "",
    status: "active",
    hire_date: todayShanghai(),
    resign_date: "",
    contract_type: "full_time",
    daily_hours: "",
    monthly_rest: "",
    confidentiality_level: "",
    note: "",
  }
}

function valuesFrom(employee: EmployeePublic): FormData {
  return {
    employee_no: employee.employee_no,
    name: employee.name,
    gender: employee.gender ?? "",
    dept_id: employee.dept_id,
    position_id: employee.position_id,
    manager_id: employee.manager_id ?? "",
    cost_org_id: employee.cost_org_id ?? "",
    status: employee.status === "probation" ? "probation" : "active",
    hire_date: employee.hire_date,
    resign_date: employee.resign_date ?? "",
    contract_type: employee.contract_type,
    daily_hours: employee.daily_hours ?? "",
    monthly_rest: employee.monthly_rest?.toString() ?? "",
    confidentiality_level: employee.confidentiality_level?.toString() ?? "",
    note: employee.note ?? "",
  }
}

export function EmployeeForm({
  open,
  onOpenChange,
  companyId,
  departments,
  positions,
  costCenters,
  employee,
  correction = false,
}: EmployeeFormProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const isEditing = employee !== null

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: emptyValues(),
  })

  useEffect(() => {
    if (!open) return
    form.reset(employee ? valuesFrom(employee) : emptyValues())
  }, [employee, form, open])

  const departmentOptions = useMemo(() => {
    // Inactive departments cannot take new assignments; the current one stays
    // visible as a historical reference.
    return flattenTree(departments).filter(
      ({ node }) => node.is_active || node.id === employee?.dept_id,
    )
  }, [departments, employee?.dept_id])

  const positionOptions = useMemo(
    () =>
      positions.filter(
        (position) =>
          position.is_active || position.id === employee?.position_id,
      ),
    [employee?.position_id, positions],
  )

  const costCenterOptions = useMemo(
    () =>
      costCenters.filter(
        (costCenter) =>
          costCenter.is_active || costCenter.id === employee?.cost_org_id,
      ),
    [costCenters, employee?.cost_org_id],
  )

  const mutation = useMutation({
    mutationFn: async (data: FormData) => {
      const note = data.note.trim() === "" ? null : data.note

      if (correction && employee) {
        return EmployeesService.updateEmployee({
          path: { employee_id: employee.id },
          body: {
            resign_date: data.resign_date,
            note,
          },
        })
      }

      const common = {
        name: data.name,
        gender:
          data.gender === ""
            ? null
            : (data.gender as "male" | "female" | "unknown"),
        dept_id: data.dept_id,
        position_id: data.position_id,
        cost_org_id: data.cost_org_id === "" ? null : data.cost_org_id,
        status: data.status,
        hire_date: data.hire_date,
        contract_type: data.contract_type,
        daily_hours: data.daily_hours.trim() === "" ? null : data.daily_hours,
        monthly_rest:
          data.monthly_rest.trim() === "" ? null : Number(data.monthly_rest),
        confidentiality_level:
          data.confidentiality_level.trim() === ""
            ? null
            : Number(data.confidentiality_level),
        note,
      }

      if (employee) {
        const body: EmployeeUpdate = { ...common }
        // Keep an existing resigned manager reference without re-validating it
        // as a new assignment.
        if (data.manager_id !== (employee.manager_id ?? "")) {
          body.manager_id = data.manager_id === "" ? null : data.manager_id
        }
        return EmployeesService.updateEmployee({
          path: { employee_id: employee.id },
          body,
        })
      }

      return EmployeesService.createEmployee({
        body: {
          ...common,
          employee_no: data.employee_no,
          manager_id: data.manager_id === "" ? null : data.manager_id,
        },
      })
    },
    onSuccess: () => {
      showSuccessToast(
        isEditing
          ? correction
            ? "员工信息已更新"
            : "员工更新成功"
          : "员工创建成功",
      )
      onOpenChange(false)
    },
    onError: (error) => {
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
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["basic", "employees"] })
    },
  })

  const onSubmit = (data: FormData) => {
    if (correction && data.resign_date === "") {
      form.setError("resign_date", { message: "请选择离职日期" })
      return
    }
    if (correction && employee && data.resign_date < employee.hire_date) {
      form.setError("resign_date", {
        message: "离职日期不能早于入职日期",
      })
      return
    }
    mutation.mutate({ ...data, employee_no: data.employee_no.toUpperCase() })
  }

  return (
    <FormDrawer
      open={open}
      onOpenChange={onOpenChange}
      title={correction ? "修正离职信息" : isEditing ? "编辑员工" : "新增员工"}
      description={
        correction
          ? "离职员工档案只读，仅可修正备注与离职日期。"
          : "员工必须绑定部门与岗位；成本中心可留空；离职为终态，本期不做再入职。"
      }
    >
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
          {correction ? (
            <>
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
                      <Textarea placeholder="可选" rows={4} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </>
          ) : (
            <>
              <section className="space-y-4">
                <h3 className="text-sm font-medium">基本信息</h3>
                <div className="grid gap-4 sm:grid-cols-2">
                  <FormField
                    control={form.control}
                    name="employee_no"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          工号 <span className="text-destructive">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder="如 E1001"
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
                          全局唯一，创建后不可修改。
                        </FormDescription>
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
                          姓名 <span className="text-destructive">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input placeholder="如 张三" required {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="gender"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>性别</FormLabel>
                        <Select
                          value={field.value}
                          onValueChange={field.onChange}
                        >
                          <FormControl>
                            <SelectTrigger aria-label="性别">
                              <SelectValue
                                placeholder={GENDER_NOT_PROVIDED_LABEL}
                              />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {GENDER_OPTIONS.map((option) => (
                              <SelectItem
                                key={option.value}
                                value={option.value}
                              >
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
                    name="contract_type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          合同类型 <span className="text-destructive">*</span>
                        </FormLabel>
                        <Select
                          value={field.value}
                          onValueChange={field.onChange}
                        >
                          <FormControl>
                            <SelectTrigger aria-label="合同类型">
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {CONTRACT_TYPE_OPTIONS.map((option) => (
                              <SelectItem
                                key={option.value}
                                value={option.value}
                              >
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
                    name="hire_date"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          入职日期 <span className="text-destructive">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input
                            type="date"
                            max={todayShanghai()}
                            required
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>不晚于今天。</FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  {(!isEditing || employee?.status === "probation") && (
                    <FormField
                      control={form.control}
                      name="status"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>状态</FormLabel>
                          <Select
                            value={field.value}
                            onValueChange={field.onChange}
                          >
                            <FormControl>
                              <SelectTrigger aria-label="状态">
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {CREATE_EMPLOYEE_STATUS_OPTIONS.map((option) => (
                                <SelectItem
                                  key={option.value}
                                  value={option.value}
                                >
                                  {option.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormDescription>
                            {isEditing
                              ? "试用期员工可以转为在职；在职不能改回试用期。"
                              : "新建员工只能是在职或试用期。"}
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  )}
                </div>
              </section>

              <section className="space-y-4">
                <h3 className="text-sm font-medium">行政归属</h3>
                <FormField
                  control={form.control}
                  name="dept_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        部门 <span className="text-destructive">*</span>
                      </FormLabel>
                      <Select
                        value={field.value}
                        onValueChange={field.onChange}
                      >
                        <FormControl>
                          <SelectTrigger aria-label="部门">
                            <SelectValue placeholder="请选择部门" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent className="max-h-72">
                          {departmentOptions.map(({ node, depth }) => (
                            <SelectItem
                              key={node.id}
                              value={node.id}
                              disabled={!node.is_active}
                            >
                              <span style={{ paddingLeft: depth * 12 }}>
                                {node.dept_name}（{node.dept_code}）
                                {!node.is_active ? " 停用" : ""}
                              </span>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormDescription>
                        部门决定员工所属公司；停用部门不可用于新归属。
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="position_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        岗位 <span className="text-destructive">*</span>
                      </FormLabel>
                      <Select
                        value={field.value}
                        onValueChange={(value) => {
                          field.onChange(value)
                          // A position's default department prefills the
                          // employee department when none is chosen yet.
                          const selected = positions.find(
                            (position) => position.id === value,
                          )
                          const defaultDept = selected?.dept_id
                          const hasDefaultOption = departmentOptions.some(
                            ({ node }) =>
                              node.id === defaultDept && node.is_active,
                          )
                          if (
                            defaultDept &&
                            hasDefaultOption &&
                            form.getValues("dept_id") === ""
                          ) {
                            form.setValue("dept_id", defaultDept)
                          }
                        }}
                      >
                        <FormControl>
                          <SelectTrigger aria-label="岗位">
                            <SelectValue placeholder="请选择岗位" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent className="max-h-72">
                          {positionOptions.map((position) => (
                            <SelectItem
                              key={position.id}
                              value={position.id}
                              disabled={!position.is_active}
                            >
                              {position.position_name}（{position.position_code}
                              ）{!position.is_active ? " 停用" : ""}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormDescription>
                        岗位为公司级档案，与部门实际归属可以不同。
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </section>

              <section className="space-y-4">
                <h3 className="text-sm font-medium">汇报关系</h3>
                <FormField
                  control={form.control}
                  name="manager_id"
                  render={({ field }) => (
                    <ManagerField
                      companyId={companyId}
                      value={field.value === "" ? null : field.value}
                      onValueChange={(value) => field.onChange(value ?? "")}
                      excludeEmployeeId={employee?.id}
                      currentManager={
                        employee?.manager_id
                          ? {
                              id: employee.manager_id,
                              name: employee.manager_name ?? "离职员工",
                              status: employee.manager_status,
                            }
                          : null
                      }
                      description="不能选择本人或形成汇报环；已离职上级保留显示但不可选择。"
                    />
                  )}
                />
              </section>

              <section className="space-y-4">
                <h3 className="text-sm font-medium">成本归属</h3>
                <FormField
                  control={form.control}
                  name="cost_org_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>成本中心</FormLabel>
                      <Select
                        value={
                          field.value === "" ? NO_COST_CENTER : field.value
                        }
                        onValueChange={(value) =>
                          field.onChange(value === NO_COST_CENTER ? "" : value)
                        }
                      >
                        <FormControl>
                          <SelectTrigger aria-label="成本中心">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent className="max-h-72">
                          <SelectItem value={NO_COST_CENTER}>未分配</SelectItem>
                          {costCenterOptions.map((costCenter) => (
                            <SelectItem
                              key={costCenter.id}
                              value={costCenter.id}
                              disabled={!costCenter.is_active}
                            >
                              {costCenter.cost_org_name}（
                              {costCenter.cost_org_code}）
                              {!costCenter.is_active ? " 停用" : ""}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormDescription>
                        成本中心可留空，留空即「未分配」。
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </section>

              <section className="space-y-4">
                <h3 className="text-sm font-medium">更多档案字段</h3>
                <p className="text-xs text-muted-foreground">
                  仅作档案记录，本期不参与工资、考勤或任何计算。
                </p>
                <div className="grid gap-4 sm:grid-cols-3">
                  <FormField
                    control={form.control}
                    name="daily_hours"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>每日工时</FormLabel>
                        <FormControl>
                          <Input
                            inputMode="decimal"
                            placeholder="如 8"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="monthly_rest"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>月休天数</FormLabel>
                        <FormControl>
                          <Input
                            inputMode="numeric"
                            placeholder="如 8"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="confidentiality_level"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>保密等级</FormLabel>
                        <FormControl>
                          <Input
                            inputMode="numeric"
                            placeholder="1–5"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </section>

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
            </>
          )}

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
  )
}
