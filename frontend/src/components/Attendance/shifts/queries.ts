import type { QueryClient } from "@tanstack/react-query"

/** Invalidate every shift view plus plan selectors that reuse the templates. */
export function invalidateShiftQueries(queryClient: QueryClient): void {
  void queryClient.invalidateQueries({ queryKey: ["attendance", "shifts"] })
  void queryClient.invalidateQueries({
    queryKey: ["attendance", "schedule-plans"],
  })
}
