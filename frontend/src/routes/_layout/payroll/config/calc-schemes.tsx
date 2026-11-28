import { createFileRoute } from "@tanstack/react-router"

import { PayrollConfigPage } from "@/components/Payroll/shared/PayrollPage"

export const Route = createFileRoute("/_layout/payroll/config/calc-schemes")({
  component: CalcSchemesPage,
  head: () => ({ meta: [{ title: "计算方案 - AnySys" }] }),
})

const DESCRIPTION = "维护公式覆盖集合；方案只覆盖公式，不携带金额或工作日参数。"

function CalcSchemesPage() {
  return <PayrollConfigPage title="计算方案" description={DESCRIPTION} />
}
