import { createFileRoute } from "@tanstack/react-router"

import { AttendancePage } from "@/components/Attendance/shared/AttendancePage"

export const Route = createFileRoute("/_layout/attendance/schedule")({
  component: SchedulePage,
  head: () => ({
    meta: [{ title: "排班工作台 - AnySys" }],
  }),
})

function SchedulePage() {
  return (
    <AttendancePage
      title="排班工作台"
      description="维护月度排班方案、展开月度排班明细，并处理人工例外。"
    />
  )
}
