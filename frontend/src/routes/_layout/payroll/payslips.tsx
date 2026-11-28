import { createFileRoute, Outlet } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/payroll/payslips")({
  component: PayslipsLayout,
})

function PayslipsLayout() {
  return <Outlet />
}
