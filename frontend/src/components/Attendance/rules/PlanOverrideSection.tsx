import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"

import {
  type AttendanceMonthPublic,
  AttendanceSchedulePlansService,
  type PlanRuleOverridesPublic,
  type RulePatch_Input,
  type RuleValues,
  type SchedulePlanPublic,
} from "@/client"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorMessage, getFieldErrors } from "@/lib/api-error"
import { PLAN_STATUS_LABELS, SCHEDULE_SCOPE_TYPE_LABELS } from "@/lib/enums"
import {
  invalidateRuleHolidayQueries,
  planListQueryKey,
  planOverridesQueryKey,
} from "./queries"
import {
  formatRuleValue,
  RULE_FIELDS,
  RULE_MONEY_MESSAGE,
  RULE_MONEY_PATTERN,
  type RuleFieldDefinition,
  type RuleKey,
} from "./rule-fields"

type FieldValue = string | number | boolean
type Modes = Record<RuleKey, boolean>
type Values = Record<RuleKey, FieldValue>
type Errors = Partial<Record<RuleKey, string>>

function planScopeLabel(plan: SchedulePlanPublic): string {
  const scope = SCHEDULE_SCOPE_TYPE_LABELS[plan.scope_type]
  const names = (plan.scopes ?? [])
    .map((item) => item.scope_name ?? item.scope_code)
    .filter(Boolean)
  return names.length > 0 ? `${scope} · ${names.join("、")}` : scope
}

function initialFrom(
  overrides: PlanRuleOverridesPublic["overrides"],
  effective: RuleValues,
): { modes: Modes; values: Values } {
  const modes = {} as Modes
  const values = {} as Values
  for (const field of RULE_FIELDS) {
    const overrideValue = overrides[field.key]
    modes[field.key] = overrideValue !== null && overrideValue !== undefined
    const source =
      overrideValue !== null && overrideValue !== undefined
        ? overrideValue
        : effective[field.key]
    if (field.kind === "money") {
      values[field.key] = String(source)
    } else if (field.kind === "boolean") {
      values[field.key] = Boolean(source)
    } else {
      values[field.key] = Number(source)
    }
  }
  return { modes, values }
}

function validateField(
  field: RuleFieldDefinition,
  value: FieldValue,
): string | null {
  if (field.kind === "boolean") {
    return null
  }
  if (field.kind === "money") {
    return RULE_MONEY_PATTERN.test(String(value).trim())
      ? null
      : RULE_MONEY_MESSAGE
  }
  return Number.isInteger(Number(value)) && Number(value) >= 0
    ? null
    : "请输入不小于 0 的整数"
}

function payloadFrom(modes: Modes, values: Values): RulePatch_Input {
  const payload = {} as Record<RuleKey, string | number | boolean | null>
  for (const field of RULE_FIELDS) {
    const key = field.key
    if (!modes[key]) {
      payload[key] = null
    } else if (field.kind === "money") {
      payload[key] = String(values[key]).trim()
    } else if (field.kind === "boolean") {
      payload[key] = Boolean(values[key])
    } else {
      payload[key] = Number(values[key])
    }
  }
  return payload as RulePatch_Input
}

export function PlanOverrideSection({
  companyId,
  month,
  monthState,
}: {
  companyId: string
  month: string
  monthState: AttendanceMonthPublic | null
}) {
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null)
  const readOnly =
    monthState?.status === "confirmed" || monthState?.status === "locked"

  const plansQuery = useQuery({
    queryKey: planListQueryKey(companyId, month, ""),
    queryFn: async () => {
      const response = await AttendanceSchedulePlansService.readSchedulePlans({
        query: {
          company_id: companyId,
          month,
          status: "enabled",
          limit: 500,
        },
      })
      return response.data
    },
  })
  const plans = plansQuery.data?.data ?? []

  useEffect(() => {
    if (plans.length === 0) {
      setSelectedPlanId(null)
      return
    }
    if (!plans.some((plan) => plan.id === selectedPlanId)) {
      setSelectedPlanId(plans[0].id)
    }
  }, [plans, selectedPlanId])

  const selectedPlan = plans.find((plan) => plan.id === selectedPlanId) ?? null

  const overridesQuery = useQuery({
    queryKey: planOverridesQueryKey(selectedPlanId ?? "none"),
    enabled: selectedPlanId !== null,
    queryFn: async () => {
      const response =
        await AttendanceSchedulePlansService.readPlanRuleOverrides({
          path: { plan_id: selectedPlanId as string },
        })
      return response.data
    },
  })

  return (
    <Card data-testid="plan-override-section">
      <CardHeader className="border-b">
        <CardTitle className="text-lg">方案级规则覆盖</CardTitle>
        <p className="text-sm text-muted-foreground">
          空值 =
          继承公司默认；显式覆盖的字段合并后生效。保存会整体替换该方案的覆盖项。
        </p>
      </CardHeader>
      <CardContent className="pt-6">
        {plansQuery.isLoading ? (
          <LoadingState rows={2} />
        ) : plansQuery.isError ? (
          <ErrorState
            message={getErrorMessage(plansQuery.error)}
            onRetry={() => {
              void plansQuery.refetch()
            }}
          />
        ) : plans.length === 0 ? (
          <EmptyState
            title="当前月份没有可配置的排班方案"
            message="方案创建后，可在这里为公司默认规则添加方案级覆盖。"
          />
        ) : (
          <div className="space-y-5">
            {readOnly && (
              <div
                role="status"
                className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100"
              >
                该考勤月份已{monthState?.status === "locked" ? "锁定" : "确认"}
                ，方案规则覆盖为只读。请先在「考勤结果」页面
                {monthState?.status === "locked" ? "解锁" : "取消确认"}
                后再修改。
              </div>
            )}
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <label
                className="text-sm font-medium"
                htmlFor="plan-override-plan"
              >
                排班方案
              </label>
              <Select
                value={selectedPlanId ?? "__none__"}
                onValueChange={setSelectedPlanId}
              >
                <SelectTrigger
                  id="plan-override-plan"
                  aria-label="选择需要覆盖规则的排班方案"
                  className="w-full sm:w-[320px]"
                >
                  <SelectValue placeholder="选择方案" />
                </SelectTrigger>
                <SelectContent>
                  {plans.map((plan) => (
                    <SelectItem key={plan.id} value={plan.id}>
                      {plan.month} · {plan.plan_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedPlan && (
                <>
                  <span className="text-sm text-muted-foreground">
                    {planScopeLabel(selectedPlan)}
                  </span>
                  <Badge variant="secondary">
                    {PLAN_STATUS_LABELS[selectedPlan.status]}
                  </Badge>
                </>
              )}
            </div>

            {overridesQuery.isLoading ? (
              <LoadingState rows={4} />
            ) : overridesQuery.isError ? (
              <ErrorState
                message={getErrorMessage(overridesQuery.error)}
                onRetry={() => {
                  void overridesQuery.refetch()
                }}
              />
            ) : overridesQuery.data && selectedPlanId ? (
              <PlanOverrideEditor
                key={selectedPlanId}
                planId={selectedPlanId}
                data={overridesQuery.data}
                readOnly={readOnly}
              />
            ) : null}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function PlanOverrideEditor({
  planId,
  data,
  readOnly,
}: {
  planId: string
  data: PlanRuleOverridesPublic
  readOnly: boolean
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const initial = initialFrom(data.overrides, data.effective)
  const [modes, setModes] = useState<Modes>(initial.modes)
  const [values, setValues] = useState<Values>(initial.values)
  const [errors, setErrors] = useState<Errors>({})

  const reset = () => {
    const next = initialFrom(data.overrides, data.effective)
    setModes(next.modes)
    setValues(next.values)
    setErrors({})
  }

  const mutation = useMutation({
    mutationFn: async () =>
      AttendanceSchedulePlansService.updatePlanRuleOverrides({
        path: { plan_id: planId },
        body: { overrides: payloadFrom(modes, values) },
      }),
    onSuccess: (response) => {
      showSuccessToast("方案覆盖已保存；草稿 / 已计算月份已标记为「结果过期」")
      const next = initialFrom(response.data.overrides, response.data.effective)
      setModes(next.modes)
      setValues(next.values)
      setErrors({})
      invalidateRuleHolidayQueries(queryClient)
    },
    onError: (error) => {
      const fieldErrors = getFieldErrors(error)
      const nextErrors: Errors = {}
      for (const field of RULE_FIELDS) {
        if (fieldErrors[field.key]) {
          nextErrors[field.key] = fieldErrors[field.key]
        }
      }
      if (Object.keys(nextErrors).length > 0) {
        setErrors(nextErrors)
      } else {
        showErrorToast(getErrorMessage(error))
      }
    },
  })

  const submit = () => {
    const nextErrors: Errors = {}
    for (const field of RULE_FIELDS) {
      if (!modes[field.key]) continue
      const message = validateField(field, values[field.key])
      if (message) nextErrors[field.key] = message
    }
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return
    mutation.mutate()
  }

  return (
    <div className="space-y-4" data-testid="plan-override-form">
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="bg-muted/40 text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">字段</th>
              <th className="px-3 py-2 font-medium">方式</th>
              <th className="px-3 py-2 font-medium">覆盖值</th>
              <th className="px-3 py-2 font-medium">当前生效值</th>
            </tr>
          </thead>
          <tbody>
            {RULE_FIELDS.map((field) => (
              <tr key={field.key} className="border-t align-top">
                <td className="px-3 py-3">
                  <div className="font-medium">{field.label}</div>
                  <div className="text-xs text-muted-foreground">
                    {field.hint}
                  </div>
                </td>
                <td className="px-3 py-3">
                  <Select
                    value={modes[field.key] ? "override" : "inherit"}
                    disabled={readOnly}
                    onValueChange={(value) => {
                      setModes((current) => ({
                        ...current,
                        [field.key]: value === "override",
                      }))
                      setErrors((current) => ({
                        ...current,
                        [field.key]: undefined,
                      }))
                    }}
                  >
                    <SelectTrigger
                      size="sm"
                      className="w-[100px]"
                      aria-label={`${field.label} 继承方式`}
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="inherit">继承</SelectItem>
                      <SelectItem value="override">覆盖</SelectItem>
                    </SelectContent>
                  </Select>
                </td>
                <td className="px-3 py-3">
                  <OverrideValueInput
                    field={field}
                    disabled={readOnly || !modes[field.key]}
                    value={values[field.key]}
                    onChange={(value) =>
                      setValues((current) => ({
                        ...current,
                        [field.key]: value,
                      }))
                    }
                  />
                  {errors[field.key] && (
                    <p className="mt-1 text-xs text-destructive">
                      {errors[field.key]}
                    </p>
                  )}
                </td>
                <td className="px-3 py-3 text-muted-foreground">
                  {formatRuleValue(field, data.effective[field.key])}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={readOnly || mutation.isPending}
          onClick={reset}
        >
          重置
        </Button>
        <LoadingButton
          type="button"
          loading={mutation.isPending}
          disabled={readOnly}
          onClick={submit}
          data-testid="save-plan-override"
        >
          保存覆盖
        </LoadingButton>
      </div>
    </div>
  )
}

function OverrideValueInput({
  field,
  disabled,
  value,
  onChange,
}: {
  field: RuleFieldDefinition
  disabled: boolean
  value: FieldValue
  onChange: (value: FieldValue) => void
}) {
  if (field.kind === "boolean") {
    return (
      <Select
        value={value ? "on" : "off"}
        onValueChange={(next) => onChange(next === "on")}
        disabled={disabled}
      >
        <SelectTrigger
          size="sm"
          className="w-[120px]"
          aria-label={`${field.label} 覆盖值`}
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="on">开启</SelectItem>
          <SelectItem value="off">关闭</SelectItem>
        </SelectContent>
      </Select>
    )
  }

  return (
    <Input
      aria-label={`${field.label} 覆盖值`}
      className="w-[140px]"
      disabled={disabled}
      inputMode={field.kind === "money" ? "decimal" : "numeric"}
      type={field.kind === "money" ? "text" : "number"}
      min={field.kind === "money" ? undefined : 0}
      step={field.kind === "money" ? undefined : 1}
      value={String(value)}
      onChange={(event) => {
        if (field.kind === "money") {
          onChange(event.target.value)
        } else {
          onChange(event.target.value === "" ? "" : event.target.valueAsNumber)
        }
      }}
    />
  )
}
