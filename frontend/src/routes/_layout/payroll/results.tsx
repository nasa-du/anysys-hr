import { createFileRoute } from "@tanstack/react-router"

import { PayrollMonthlyPage } from "@/components/Payroll/shared/PayrollPage"

export const Route = createFileRoute("/_layout/payroll/results")({
  component: ResultsPage,
  head: () => ({ meta: [{ title: "工资列表 - AnySys" }] }),
})

const DESCRIPTION =
  "按薪资月份查看全员核算结果、动态字段与合计，并进入明细或手工输入。"

function ResultsPage() {
  return <PayrollMonthlyPage title="工资列表" description={DESCRIPTION} />
}
