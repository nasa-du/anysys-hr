import { createFileRoute } from "@tanstack/react-router"

import { PayrollConfigPage } from "@/components/Payroll/shared/PayrollPage"

export const Route = createFileRoute("/_layout/payroll/config/positions")({
  component: PositionsPage,
  head: () => ({ meta: [{ title: "岗位装配 - AnySys" }] }),
})

const DESCRIPTION =
  "为每个岗位装配一份薪资构成、计算方案与工作日参数；未配置岗位会阻断核算。"

function PositionsPage() {
  return <PayrollConfigPage title="岗位装配" description={DESCRIPTION} />
}
