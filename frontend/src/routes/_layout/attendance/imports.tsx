import { createFileRoute } from "@tanstack/react-router"

import { AttendancePage } from "@/components/Attendance/shared/AttendancePage"

export const Route = createFileRoute("/_layout/attendance/imports")({
  component: ImportsPage,
  head: () => ({
    meta: [{ title: "导入中心 - AnySys" }],
  }),
})

function ImportsPage() {
  return (
    <AttendancePage
      title="导入中心"
      description="导入打卡与 OA 申请数据，预览校验结果后提交生效。"
    />
  )
}
