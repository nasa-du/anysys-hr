import type { DayType } from "@/client"

/** Shared calendar tinting for the server-resolved day type. */
export const DAY_TYPE_STYLES: Record<DayType, string> = {
  workday: "",
  weekend: "bg-muted/20",
  holiday: "bg-destructive/5",
}
