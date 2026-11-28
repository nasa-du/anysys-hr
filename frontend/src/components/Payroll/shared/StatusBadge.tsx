import { Badge } from "@/components/ui/badge"
import type { PayrollMonthStatus } from "@/lib/payroll-enums"
import { PAYROLL_MONTH_STATUS_LABELS } from "@/lib/payroll-enums"

const MONTH_STATUS_VARIANTS: Record<
  PayrollMonthStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  draft: "secondary",
  calculated: "default",
  confirmed: "outline",
  paid: "default",
}

export function PayrollMonthStatusBadge({
  status,
}: {
  status: PayrollMonthStatus
}) {
  return (
    <Badge
      variant={MONTH_STATUS_VARIANTS[status]}
      data-testid="payroll-status-badge"
    >
      {PAYROLL_MONTH_STATUS_LABELS[status]}
    </Badge>
  )
}
