import { createFileRoute } from "@tanstack/react-router"

import { PayrollConfigPage } from "@/components/Payroll/shared/PayrollPage"

export const Route = createFileRoute("/_layout/payroll/config/globals")({
  component: GlobalsPage,
  head: () => ({ meta: [{ title: "全局参数 - AnySys" }] }),
})

const DESCRIPTION =
  "维护系统级税务、社保与津贴档参数；数值参数可直接在公式中引用。"

function GlobalsPage() {
  return <PayrollConfigPage title="全局参数" description={DESCRIPTION} />
}
