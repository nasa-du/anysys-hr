import { createFileRoute, redirect } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/payroll/")({
  beforeLoad: () => {
    throw redirect({ to: "/payroll/results" })
  },
})
