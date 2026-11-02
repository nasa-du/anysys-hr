import {
  FormControl,
  FormDescription,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { type ManagerOption, ManagerSelect } from "./ManagerSelect"

interface ManagerFieldProps {
  companyId: string
  value: string | null
  onValueChange: (value: string | null) => void
  /** The employee being edited: never offer itself or a cycle-closing report. */
  excludeEmployeeId?: string
  /** Keep an existing manager visible even after resignation. */
  currentManager?: ManagerOption | null
  description?: string
}

/** Shared manager form field for department, cost center, and employee forms. */
export function ManagerField({
  companyId,
  value,
  onValueChange,
  excludeEmployeeId,
  currentManager,
  description = "只能选择同公司在职或试用期员工；已离职上级保留显示但不可重新选择。",
}: ManagerFieldProps) {
  return (
    <FormItem>
      <FormLabel>直属上级</FormLabel>
      <FormControl>
        <ManagerSelect
          companyId={companyId}
          value={value}
          onValueChange={onValueChange}
          excludeEmployeeId={excludeEmployeeId}
          currentManager={currentManager}
        />
      </FormControl>
      <FormDescription>{description}</FormDescription>
      <FormMessage />
    </FormItem>
  )
}
