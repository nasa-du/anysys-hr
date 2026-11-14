import type { QueryClient } from "@tanstack/react-query"

export function rulesQueryKey(companyId: string) {
  return ["attendance", "rules", companyId] as const
}

export function holidaysQueryKey(companyId: string, year: number) {
  return ["attendance", "holidays", "list", companyId, year] as const
}

export function planListQueryKey(
  companyId: string,
  month: string,
  keyword: string,
) {
  return [
    "attendance",
    "schedule-plans",
    "list",
    companyId,
    month,
    { keyword },
  ] as const
}

export function planOverridesQueryKey(planId: string) {
  return ["attendance", "schedule-plans", "rule-overrides", planId] as const
}

export function monthsQueryKey(companyId: string, year: number | null) {
  return ["attendance", "months", "list", companyId, year] as const
}

/** Rules and holidays invalidate their own views plus month/result staleness. */
export function invalidateRuleHolidayQueries(queryClient: QueryClient): void {
  void queryClient.invalidateQueries({ queryKey: ["attendance", "rules"] })
  void queryClient.invalidateQueries({ queryKey: ["attendance", "holidays"] })
  void queryClient.invalidateQueries({
    queryKey: ["attendance", "schedule-plans"],
  })
  void queryClient.invalidateQueries({ queryKey: ["attendance", "months"] })
  void queryClient.invalidateQueries({ queryKey: ["attendance", "results"] })
}
