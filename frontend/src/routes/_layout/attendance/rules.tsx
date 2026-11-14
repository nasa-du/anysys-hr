import { createFileRoute } from "@tanstack/react-router"

import { AttendancePage } from "@/components/Attendance/shared/AttendancePage"

export const Route = createFileRoute("/_layout/attendance/rules")({
  component: RulesPage,
  head: () => ({
    meta: [{ title: "规则与节假日 - AnySys" }],
  }),
})

function RulesPage() {
  return (
    <AttendancePage
      title="规则与节假日"
      description="维护公司默认考勤规则、方案级规则覆盖与公司节假日日历。"
    />
  )
}
