import { createFileRoute } from "@tanstack/react-router"

import { PayrollConfigPage } from "@/components/Payroll/shared/PayrollPage"

export const Route = createFileRoute("/_layout/payroll/config/fields")({
  component: FieldsPage,
  head: () => ({ meta: [{ title: "字段与公式 - AnySys" }] }),
})

const DESCRIPTION =
  "维护全局薪资字段、显示顺序与公式；编辑器插入中文标签，保存为 ASCII 字段键。"

function FieldsPage() {
  return <PayrollConfigPage title="字段与公式" description={DESCRIPTION} />
}
