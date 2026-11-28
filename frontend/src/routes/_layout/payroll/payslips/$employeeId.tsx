import { createFileRoute } from "@tanstack/react-router"

import { PayrollMonthlyPage } from "@/components/Payroll/shared/PayrollPage"

export const Route = createFileRoute("/_layout/payroll/payslips/$employeeId")({
  component: PayslipDetailPage,
  head: () => ({ meta: [{ title: "工资条详情 - AnySys" }] }),
})

const DESCRIPTION =
  "单人工资条的正式或预览版式、字段分组与四项合计；下载由服务端生成 PDF。"

function PayslipDetailPage() {
  return <PayrollMonthlyPage title="工资条详情" description={DESCRIPTION} />
}
