import { useQuery } from "@tanstack/react-query"

import { type EmployeeStatus, EmployeesService } from "@/client"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { MANAGER_STATUS_LABELS } from "@/lib/enums"

export const NO_MANAGER_VALUE = "__none__"

export interface ManagerOption {
  id: string
  name: string
  employee_no?: string | null
  status?: EmployeeStatus | null
}

interface ManagerSelectProps {
  companyId: string
  value: string | null
  onValueChange: (value: string | null) => void
  /** The employee being edited: never offer itself or a report that closes a cycle. */
  excludeEmployeeId?: string
  /** Keep an existing manager visible even after resignation. */
  currentManager?: ManagerOption | null
  disabled?: boolean
  ariaLabel?: string
}

function optionLabel(option: ManagerOption): string {
  const number = option.employee_no ? `（${option.employee_no}）` : ""
  const resigned =
    option.status === "resigned" ? ` · ${MANAGER_STATUS_LABELS.resigned}` : ""
  return `${option.name}${number}${resigned}`
}

/**
 * Same-company manager selector. Resigned employees are shown but disabled;
 * the existing manager remains visible as a historical reference.
 */
export function ManagerSelect({
  companyId,
  value,
  onValueChange,
  excludeEmployeeId,
  currentManager,
  disabled,
  ariaLabel = "直属上级",
}: ManagerSelectProps) {
  const employeesQuery = useQuery({
    queryKey: ["basic", "employees", "manager-options", companyId],
    queryFn: async () => {
      const response = await EmployeesService.readEmployees({
        query: {
          company_id: companyId,
          status: ["active", "probation", "resigned"],
          skip: 0,
          limit: 500,
        },
      })
      return response.data.data
    },
  })

  const employees = employeesQuery.data ?? []
  const byId = new Map(employees.map((employee) => [employee.id, employee]))

  const wouldCreateCycle = (managerId: string): boolean => {
    if (!excludeEmployeeId) return false
    let current = byId.get(managerId)
    const seen = new Set<string>()
    while (current) {
      if (current.id === excludeEmployeeId) return true
      if (seen.has(current.id)) return true
      seen.add(current.id)
      current = current.manager_id ? byId.get(current.manager_id) : undefined
    }
    return false
  }

  // Resigned employees stay visible but disabled so historical references and
  // the reason a manager is unavailable are both clear.
  const options: ManagerOption[] = employees.map((employee) => ({
    id: employee.id,
    name: employee.name,
    employee_no: employee.employee_no,
    status: employee.status,
  }))
  if (
    currentManager &&
    !options.some((option) => option.id === currentManager.id)
  ) {
    options.unshift(currentManager)
  }

  return (
    <Select
      value={value ?? NO_MANAGER_VALUE}
      onValueChange={(next) =>
        onValueChange(next === NO_MANAGER_VALUE ? null : next)
      }
      disabled={disabled || employeesQuery.isLoading}
    >
      <SelectTrigger aria-label={ariaLabel}>
        <SelectValue placeholder="选择直属上级" />
      </SelectTrigger>
      <SelectContent className="max-h-72">
        <SelectItem value={NO_MANAGER_VALUE}>无直属上级</SelectItem>
        {options.map((option) => (
          <SelectItem
            key={option.id}
            value={option.id}
            disabled={
              option.id === excludeEmployeeId ||
              option.status === "resigned" ||
              wouldCreateCycle(option.id)
            }
          >
            {optionLabel(option)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
