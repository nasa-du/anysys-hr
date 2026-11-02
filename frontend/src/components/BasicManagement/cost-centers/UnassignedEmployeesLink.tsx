import { Link } from "@tanstack/react-router"
import { UserRoundX } from "lucide-react"

/** Tree tail entry that opens the employee list filtered to unassigned costs. */
export function UnassignedEmployeesLink() {
  return (
    <Link
      to="/employees"
      search={{ unassigned_cost_org: true }}
      className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted"
      data-testid="cost-center-unassigned"
    >
      <UserRoundX className="size-4 shrink-0 text-muted-foreground" />
      <span>未分配</span>
    </Link>
  )
}
