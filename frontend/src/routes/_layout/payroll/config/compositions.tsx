import { createFileRoute } from "@tanstack/react-router"

import { PayrollConfigPage } from "@/components/Payroll/shared/PayrollPage"

export const Route = createFileRoute("/_layout/payroll/config/compositions")({
  component: CompositionsPage,
  head: () => ({ meta: [{ title: "薪资构成 - AnySys" }] }),
})

const DESCRIPTION =
  "维护公司级薪资构成及不可变金额版本；岗位和核算快照引用具体版本。"

function CompositionsPage() {
  return <PayrollConfigPage title="薪资构成" description={DESCRIPTION} />
}
