import { createFileRoute } from "@tanstack/react-router"

import { PayrollConfigPage } from "@/components/Payroll/shared/PayrollPage"

export const Route = createFileRoute("/_layout/payroll/config/workday-params")({
  component: WorkdayParamsPage,
  head: () => ({ meta: [{ title: "工作日参数 - AnySys" }] }),
})

const DESCRIPTION =
  "维护平均计薪天数、工时、加班倍数与最低工资；引用中的参数不可停用。"

function WorkdayParamsPage() {
  return <PayrollConfigPage title="工作日参数" description={DESCRIPTION} />
}
