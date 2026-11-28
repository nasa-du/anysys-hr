import { createFileRoute } from "@tanstack/react-router"

import { PayrollMonthlyPage } from "@/components/Payroll/shared/PayrollPage"

export const Route = createFileRoute("/_layout/payroll/imports")({
  component: ImportsPage,
  head: () => ({ meta: [{ title: "月度导入 - AnySys" }] }),
})

const DESCRIPTION =
  "上传或粘贴薪资自有列，映射列后预览并提交；考勤列只读展示，不可在薪资中覆盖。"

function ImportsPage() {
  return <PayrollMonthlyPage title="月度导入" description={DESCRIPTION} />
}
