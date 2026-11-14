import { createFileRoute } from "@tanstack/react-router"

import { AttendancePage } from "@/components/Attendance/shared/AttendancePage"

export const Route = createFileRoute("/_layout/attendance/shifts")({
  component: ShiftsPage,
  head: () => ({
    meta: [{ title: "班次 - AnySys" }],
  }),
})

function ShiftsPage() {
  return (
    <AttendancePage
      title="班次"
      description="维护可复用的班次模板，作为排班方案与排班明细的基础。"
    />
  )
}
