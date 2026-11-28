import { createFileRoute, Outlet } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/payroll")({
  component: PayrollLayout,
})

function PayrollLayout() {
  return <Outlet />
}
