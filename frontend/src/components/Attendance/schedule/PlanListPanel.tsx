import type {
  DepartmentPublic,
  EmployeePublic,
  PositionPublic,
  SchedulePlanPublic,
} from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { PLAN_STATUS_LABELS } from "@/lib/enums"
import { planCoverage, scopeLabel } from "./plan-utils"

export function PlanListPanel({
  plans,
  employees,
  departments,
  positions,
  selectedPlanId,
  onSelect,
  onCreate,
  editable,
}: {
  plans: SchedulePlanPublic[]
  employees: EmployeePublic[]
  departments: DepartmentPublic[]
  positions: PositionPublic[]
  selectedPlanId: string
  onSelect: (planId: string) => void
  onCreate: () => void
  editable: boolean
}) {
  const enabled = plans.filter((plan) => plan.status === "enabled")
  const archived = plans.filter((plan) => plan.status === "archived")

  return (
    <Card data-testid="plan-list">
      <CardHeader className="border-b">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-lg">排班方案</CardTitle>
            <p className="text-sm text-muted-foreground">
              {enabled.length} 张启用 · {archived.length} 张已归档
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={!editable}
            title={editable ? undefined : "本月已确认或锁定"}
            onClick={onCreate}
          >
            新建
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 pt-4">
        <button
          type="button"
          data-testid="plan-card-all"
          onClick={() => onSelect("all")}
          className={`w-full rounded-lg border p-3 text-left transition ${
            selectedPlanId === "all"
              ? "border-primary bg-primary/5 ring-1 ring-primary/30"
              : "hover:border-primary/40"
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <div className="font-medium">全部方案 · 合并视图</div>
            <Badge variant="secondary">合并</Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            按精确度解析：员工 &gt; 岗位 &gt; 部门 &gt; 全公司
          </p>
        </button>

        {plans.length === 0 ? (
          <p className="px-1 py-4 text-sm text-muted-foreground">
            当前月份还没有排班方案。新建方案后保存即展开为员工日明细。
          </p>
        ) : (
          plans.map((plan) => {
            const coverage = planCoverage(plan, employees).length
            return (
              <button
                key={plan.id}
                type="button"
                data-testid={`plan-card-${plan.id}`}
                onClick={() => onSelect(plan.id)}
                className={`w-full rounded-lg border p-3 text-left transition ${
                  selectedPlanId === plan.id
                    ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                    : "hover:border-primary/40"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate font-medium">{plan.plan_name}</div>
                    <div className="mt-0.5 truncate text-xs text-muted-foreground">
                      {scopeLabel(plan, departments, positions)} · 覆盖{" "}
                      {coverage} 人
                    </div>
                  </div>
                  <Badge
                    variant={
                      plan.status === "enabled" ? "default" : "secondary"
                    }
                  >
                    {PLAN_STATUS_LABELS[plan.status]}
                  </Badge>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {[...new Set((plan.days ?? []).map((day) => day.shift_code))]
                    .filter((code): code is string => Boolean(code))
                    .slice(0, 5)
                    .map((code) => (
                      <span
                        key={code}
                        className="rounded bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground"
                      >
                        {code}
                      </span>
                    ))}
                  {plans.some(
                    (item) => item.copied_from_plan_id === plan.id,
                  ) && (
                    <span className="rounded bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground">
                      已复制
                    </span>
                  )}
                </div>
              </button>
            )
          })
        )}
      </CardContent>
    </Card>
  )
}
