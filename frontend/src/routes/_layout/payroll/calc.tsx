import { createFileRoute } from "@tanstack/react-router"

import { PayrollMonthlyPage } from "@/components/Payroll/shared/PayrollPage"

export const Route = createFileRoute("/_layout/payroll/calc")({
  component: CalcPage,
  head: () => ({ meta: [{ title: "核算与确认 - AnySys" }] }),
})

const DESCRIPTION =
  "核对月度检查项与核算历史，执行核算、确认、发放或解锁；失败批次保留且不覆盖结果。"

function CalcPage() {
  return <PayrollMonthlyPage title="核算与确认" description={DESCRIPTION} />
}
