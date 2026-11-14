import type { QueryClient } from "@tanstack/react-query"

import { AttendanceRosterService, type RosterEntryPublic } from "@/client"

/** Roster query keys from spec section 8.9. */
export function rosterCalendarQueryKey(
  companyId: string,
  month: string,
  employeeId: string,
) {
  return [
    "attendance",
    "roster",
    "calendar",
    companyId,
    month,
    employeeId,
  ] as const
}

export function rosterDayQueryKey(companyId: string, date: string) {
  return ["attendance", "roster", "day", companyId, date, {}] as const
}

export function rosterEmployeesQueryKey(companyId: string, month: string) {
  return ["attendance", "roster", "employees", companyId, month, {}] as const
}

export function rosterMonthQueryKey(companyId: string, month: string) {
  return ["attendance", "roster", "month", companyId, month, {}] as const
}

export function rosterSyncPreviewQueryKey(companyId: string, month: string) {
  return ["attendance", "roster", "sync-preview", companyId, month] as const
}

export function rosterEntriesQueryKey(
  companyId: string,
  filters: { month?: string; employeeId?: string; source?: string },
) {
  return ["attendance", "roster-entries", "list", companyId, filters] as const
}

/** A roster write invalidates roster views, month state, and results. */
export function invalidateRosterQueries(queryClient: QueryClient): void {
  void queryClient.invalidateQueries({ queryKey: ["attendance", "roster"] })
  // The entry list uses its own ``roster-entries`` prefix, which the
  // ``roster`` prefix does not match.
  void queryClient.invalidateQueries({
    queryKey: ["attendance", "roster-entries"],
  })
  void queryClient.invalidateQueries({ queryKey: ["attendance", "months"] })
  void queryClient.invalidateQueries({ queryKey: ["attendance", "results"] })
}

/** Read every manual exception of a month across pages (limit is 500). */
export async function fetchAllManualEntries(
  companyId: string,
  month: string,
): Promise<RosterEntryPublic[]> {
  const limit = 500
  const entries: RosterEntryPublic[] = []
  for (let skip = 0; ; skip += limit) {
    const response = await AttendanceRosterService.readRosterEntries({
      query: {
        company_id: companyId,
        month,
        source: "manual",
        skip,
        limit,
      },
    })
    const page = response.data.data
    entries.push(...page)
    if (page.length < limit || entries.length >= response.data.count) {
      return entries
    }
  }
}
