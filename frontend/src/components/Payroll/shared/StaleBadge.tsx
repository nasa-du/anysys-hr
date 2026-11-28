import { Badge } from "@/components/ui/badge"
import type { PayrollStaleBadge } from "@/lib/payroll-enums"
import { PAYROLL_STALE_BADGE_LABELS } from "@/lib/payroll-enums"

/** A month-bar badge explaining why a month needs attention. */
export function PayrollStaleBadgeView({ badge }: { badge: PayrollStaleBadge }) {
  return (
    <Badge
      variant="outline"
      className="border-amber-500/50 text-amber-700 dark:text-amber-400"
      data-testid={`payroll-stale-${badge}`}
    >
      {PAYROLL_STALE_BADGE_LABELS[badge]}
    </Badge>
  )
}
