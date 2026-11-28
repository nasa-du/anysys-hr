import { createFileRoute } from "@tanstack/react-router"

import { PayrollMonthlyPage } from "@/components/Payroll/shared/PayrollPage"

export const Route = createFileRoute("/_layout/payroll/cost-stats")({
  component: CostStatsPage,
  head: () => ({ meta: [{ title: "成本统计 - AnySys" }] }),
})

const DESCRIPTION =
  "按冻结的成本中心路径汇总应发、社保、个税与实发，并查看预算三态预警。"

function CostStatsPage() {
  return <PayrollMonthlyPage title="成本统计" description={DESCRIPTION} />
}
