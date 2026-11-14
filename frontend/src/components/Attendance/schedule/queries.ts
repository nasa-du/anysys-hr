import type { QueryClient } from "@tanstack/react-query"

import { invalidateRosterQueries } from "./roster-queries"

export function planListQueryKey(companyId: string, month: string) {
  return ["attendance", "schedule-plans", "list", companyId, { month }] as const
}

export function planEmployeesQueryKey(companyId: string) {
  return ["attendance", "schedule", "employees", companyId] as const
}

export function planDepartmentsQueryKey(companyId: string) {
  return ["attendance", "schedule", "departments", companyId] as const
}

export function planPositionsQueryKey(companyId: string) {
  return ["attendance", "schedule", "positions", companyId] as const
}

export function planShiftsQueryKey(companyId: string) {
  return ["attendance", "schedule", "shifts", companyId] as const
}

export function planHolidaysQueryKey(companyId: string, year: number) {
  return ["attendance", "schedule", "holidays", companyId, year] as const
}

export function planMonthStateQueryKey(companyId: string) {
  return ["attendance", "months", "list", companyId, null] as const
}

/** A plan change expands roster entries and stales editable months. */
export function invalidatePlanQueries(queryClient: QueryClient): void {
  void queryClient.invalidateQueries({
    queryKey: ["attendance", "schedule-plans"],
  })
  invalidateRosterQueries(queryClient)
}
