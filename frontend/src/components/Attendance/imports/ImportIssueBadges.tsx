import { Badge } from "@/components/ui/badge"
import { IMPORT_ROW_CODE_LABELS } from "@/lib/enums"

/** Aggregate row-level skip/warning/error codes into labelled counts. */
export function ImportIssueBadges({
  counts,
}: {
  counts: Record<string, number> | undefined
}) {
  const entries = Object.entries(counts ?? {}).filter(([, count]) => count > 0)
  if (entries.length === 0) {
    return <span className="text-sm text-muted-foreground">无</span>
  }
  return (
    <div className="flex flex-wrap gap-2">
      {entries.map(([code, count]) => (
        <Badge key={code} variant="secondary">
          {IMPORT_ROW_CODE_LABELS[code] ?? code} × {count}
        </Badge>
      ))}
    </div>
  )
}
