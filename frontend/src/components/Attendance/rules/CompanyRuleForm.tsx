import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  type AttendanceRulePublic,
  AttendanceRulesService,
  type AttendanceRuleUpdate,
} from "@/client"
import {
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { StatusSwitch } from "@/components/BasicManagement/shared/StatusSwitch"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorMessage, getFieldErrors } from "@/lib/api-error"
import { invalidateRuleHolidayQueries, rulesQueryKey } from "./queries"
import {
  RULE_GROUPS,
  RULE_MONEY_MESSAGE,
  RULE_MONEY_PATTERN,
  type RuleGroupDefinition,
  type RuleKey,
} from "./rule-fields"

const nonNegativeInt = z
  .number({ message: "请输入有效的整数" })
  .int("请输入整数")
  .min(0, "不能小于 0")

const money = z
  .string()
  .min(1, "请输入金额")
  .refine((value) => RULE_MONEY_PATTERN.test(value.trim()), RULE_MONEY_MESSAGE)

const formSchema = z.object({
  punch_window_min: nonNegativeInt,
  late_cap_min: nonNegativeInt,
  early_cap_min: nonNegativeInt,
  ot_max_min: nonNegativeInt,
  late_grace_min: nonNegativeInt,
  early_grace_min: nonNegativeInt,
  ot_threshold_min: nonNegativeInt,
  absent_if_no_punch: z.boolean(),
  break_punch_required: z.boolean(),
  break_punch_tolerance_min: nonNegativeInt,
  absent_deduct_per_day: money,
  late_deduct_per_occurrence: money,
  early_deduct_per_occurrence: money,
  missing_punch_deduct_per_occurrence: money,
})

type FormData = z.infer<typeof formSchema>

function valuesFrom(rule: AttendanceRulePublic): FormData {
  return {
    punch_window_min: rule.punch_window_min,
    late_cap_min: rule.late_cap_min,
    early_cap_min: rule.early_cap_min,
    ot_max_min: rule.ot_max_min,
    late_grace_min: rule.late_grace_min,
    early_grace_min: rule.early_grace_min,
    ot_threshold_min: rule.ot_threshold_min,
    absent_if_no_punch: rule.absent_if_no_punch,
    break_punch_required: rule.break_punch_required,
    break_punch_tolerance_min: rule.break_punch_tolerance_min,
    absent_deduct_per_day: String(rule.absent_deduct_per_day),
    late_deduct_per_occurrence: String(rule.late_deduct_per_occurrence),
    early_deduct_per_occurrence: String(rule.early_deduct_per_occurrence),
    missing_punch_deduct_per_occurrence: String(
      rule.missing_punch_deduct_per_occurrence,
    ),
  }
}

function toUpdateBody(data: FormData): AttendanceRuleUpdate {
  return {
    punch_window_min: data.punch_window_min,
    late_cap_min: data.late_cap_min,
    early_cap_min: data.early_cap_min,
    ot_max_min: data.ot_max_min,
    late_grace_min: data.late_grace_min,
    early_grace_min: data.early_grace_min,
    ot_threshold_min: data.ot_threshold_min,
    absent_if_no_punch: data.absent_if_no_punch,
    break_punch_required: data.break_punch_required,
    break_punch_tolerance_min: data.break_punch_tolerance_min,
    absent_deduct_per_day: data.absent_deduct_per_day.trim(),
    late_deduct_per_occurrence: data.late_deduct_per_occurrence.trim(),
    early_deduct_per_occurrence: data.early_deduct_per_occurrence.trim(),
    missing_punch_deduct_per_occurrence:
      data.missing_punch_deduct_per_occurrence.trim(),
  }
}

export function CompanyRuleForm({ companyId }: { companyId: string }) {
  const ruleQuery = useQuery({
    queryKey: rulesQueryKey(companyId),
    queryFn: async () => {
      const response = await AttendanceRulesService.readCompanyRule({
        query: { company_id: companyId },
      })
      return response.data
    },
  })

  return (
    <Card data-testid="company-rule-section">
      <CardHeader className="border-b">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-lg">公司默认规则</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              所有方案先继承公司默认；空值继承在方案覆盖中配置。规则变更只影响草稿和已计算月份的过期标记。
            </p>
          </div>
          {ruleQuery.data && (
            <Badge
              variant={ruleQuery.data.is_default ? "secondary" : "default"}
            >
              {ruleQuery.data.is_default ? "系统默认" : "公司已配置"}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-6">
        {ruleQuery.isLoading ? (
          <LoadingState rows={4} />
        ) : ruleQuery.isError ? (
          <ErrorState
            message={getErrorMessage(ruleQuery.error)}
            onRetry={() => {
              void ruleQuery.refetch()
            }}
          />
        ) : ruleQuery.data ? (
          <CompanyRuleEditor companyId={companyId} rule={ruleQuery.data} />
        ) : null}
      </CardContent>
    </Card>
  )
}

function CompanyRuleEditor({
  companyId,
  rule,
}: {
  companyId: string
  rule: AttendanceRulePublic
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: valuesFrom(rule),
  })

  useEffect(() => {
    form.reset(valuesFrom(rule))
  }, [form, rule])

  const mutation = useMutation({
    mutationFn: async (data: FormData) =>
      AttendanceRulesService.updateCompanyRule({
        query: { company_id: companyId },
        body: toUpdateBody(data),
      }),
    onSuccess: (response) => {
      showSuccessToast(
        "规则已保存；草稿 / 已计算月份已标记为「结果过期」，不会自动重算",
      )
      form.reset(valuesFrom(response.data))
      // Only invalidate after a successful save: refetching on a validation
      // error would reset the form and discard the user's edits.
      invalidateRuleHolidayQueries(queryClient)
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
  })

  return (
    <Form {...form}>
      <form
        className="space-y-6"
        data-testid="company-rule-form"
        onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
      >
        {rule.is_default && (
          <div className="rounded-md border border-dashed px-4 py-3 text-sm text-muted-foreground">
            当前没有公司规则记录，界面显示系统默认值；首次保存会创建公司规则行，之后的保存为幂等更新。
          </div>
        )}

        {RULE_GROUPS.map((group) => (
          <RuleGroupSection key={group.key} group={group} form={form} />
        ))}

        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={mutation.isPending}
            onClick={() => form.reset(valuesFrom(rule))}
          >
            重置
          </Button>
          <LoadingButton
            type="submit"
            loading={mutation.isPending}
            data-testid="save-company-rule"
          >
            保存规则
          </LoadingButton>
        </div>
      </form>
    </Form>
  )
}

type RuleForm = ReturnType<typeof useForm<FormData>>

function RuleGroupSection({
  group,
  form,
}: {
  group: RuleGroupDefinition
  form: RuleForm
}) {
  return (
    <section className="rounded-lg border">
      <div className="border-b px-4 py-3">
        <h3 className="text-sm font-semibold">{group.title}</h3>
        <p className="text-xs text-muted-foreground">{group.description}</p>
      </div>
      <div className="grid gap-4 p-4 sm:grid-cols-2 xl:grid-cols-3">
        {group.fields.map((field) =>
          field.kind === "boolean" ? (
            <BooleanRuleField
              key={field.key}
              form={form}
              fieldKey={field.key}
              label={field.label}
              hint={field.hint}
            />
          ) : (
            <NumericRuleField
              key={field.key}
              form={form}
              fieldKey={field.key}
              label={field.label}
              hint={field.hint}
              kind={field.kind}
            />
          ),
        )}
      </div>
    </section>
  )
}

function BooleanRuleField({
  form,
  fieldKey,
  label,
  hint,
}: {
  form: RuleForm
  fieldKey: RuleKey
  label: string
  hint: string
}) {
  return (
    <FormField
      control={form.control}
      name={fieldKey as "absent_if_no_punch"}
      render={({ field }) => (
        <FormItem>
          <FormLabel>{label}</FormLabel>
          <div className="flex items-center gap-3">
            <FormControl>
              <StatusSwitch
                checked={field.value}
                onCheckedChange={field.onChange}
                aria-label={label}
              />
            </FormControl>
            <span className="text-sm text-muted-foreground">
              {field.value ? "开启" : "关闭"}
            </span>
          </div>
          <FormDescription>{hint}</FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  )
}

function NumericRuleField({
  form,
  fieldKey,
  label,
  hint,
  kind,
}: {
  form: RuleForm
  fieldKey: RuleKey
  label: string
  hint: string
  kind: "int" | "money"
}) {
  const name = fieldKey as "punch_window_min" | "absent_deduct_per_day"

  return (
    <FormField
      control={form.control}
      name={name}
      render={({ field }) =>
        kind === "money" ? (
          <FormItem>
            <FormLabel>{label}</FormLabel>
            <FormControl>
              <Input
                inputMode="decimal"
                aria-label={label}
                {...field}
                value={String(field.value)}
              />
            </FormControl>
            <FormDescription>{hint}</FormDescription>
            <FormMessage />
          </FormItem>
        ) : (
          <FormItem>
            <FormLabel>{label}</FormLabel>
            <FormControl>
              <Input
                type="number"
                min={0}
                step={1}
                aria-label={label}
                value={field.value}
                onChange={(event) =>
                  field.onChange(
                    event.target.value === "" ? 0 : event.target.valueAsNumber,
                  )
                }
                onBlur={field.onBlur}
                name={field.name}
                ref={field.ref}
              />
            </FormControl>
            <FormDescription>{hint}</FormDescription>
            <FormMessage />
          </FormItem>
        )
      }
    />
  )
}
