import { createFileRoute } from "@tanstack/react-router"

import { AttendancePage } from "@/components/Attendance/shared/AttendancePage"

export const Route = createFileRoute("/_layout/attendance/results")({
  component: ResultsPage,
  head: () => ({
    meta: [{ title: "考勤结果 - AnySys" }],
  }),
})

function ResultsPage() {
  return (
    <AttendancePage
      title="考勤结果"
      description="查看日结果、月汇总与异常明细，完成计算、确认、锁定与导出。"
    />
  )
}
