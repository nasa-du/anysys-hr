import { createFileRoute, Outlet } from "@tanstack/react-router"

import { AttendanceMonthProvider } from "@/contexts/AttendanceMonthContext"

export const Route = createFileRoute("/_layout/attendance")({
  component: AttendanceLayout,
})

function AttendanceLayout() {
  return (
    <AttendanceMonthProvider>
      <Outlet />
    </AttendanceMonthProvider>
  )
}
