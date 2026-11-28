import { createFileRoute } from "@tanstack/react-router"

import { PayrollMonthlyPage } from "@/components/Payroll/shared/PayrollPage"

export const Route = createFileRoute("/_layout/payroll/payslips/")({
  component: PayslipsPage,
  head: () => ({ meta: [{ title: "工资条 - AnySys" }] }),
})

const DESCRIPTION =
  "按正式或预览口径查看工资条，下载单人 PDF 或发起批量导出任务。"

function PayslipsPage() {
  return <PayrollMonthlyPage title="工资条" description={DESCRIPTION} />
}
