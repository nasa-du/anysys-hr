import { CalendarDays, Clock3, MapPin, UserRoundCheck } from "lucide-react"

import {
  type AttendanceImportDataType,
  IMPORT_DATA_TYPE_DESCRIPTIONS,
  IMPORT_DATA_TYPE_LABELS,
  IMPORT_DATA_TYPE_OPTIONS,
} from "@/lib/enums"
import { cn } from "@/lib/utils"

const DATA_TYPE_ICONS = {
  punch: Clock3,
  trip: MapPin,
  ot: UserRoundCheck,
  leave: CalendarDays,
} as const

interface DataTypeCardsProps {
  value: AttendanceImportDataType
  month: string
  onChange: (dataType: AttendanceImportDataType) => void
}

/** The four import entries from the Import Center layout (spec §9.2). */
export function DataTypeCards({ value, month, onChange }: DataTypeCardsProps) {
  return (
    <fieldset
      className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
      aria-label="导入数据类型"
    >
      {IMPORT_DATA_TYPE_OPTIONS.map((option) => {
        const Icon = DATA_TYPE_ICONS[option.value]
        const selected = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={selected}
            data-testid={`import-type-${option.value}`}
            onClick={() => onChange(option.value)}
            className={cn(
              "rounded-lg border bg-card p-4 text-left transition hover:border-primary/60 hover:bg-accent/40",
              selected && "border-primary bg-primary/5 ring-1 ring-primary/30",
            )}
          >
            <span className="flex items-center gap-2 font-medium">
              <Icon className="size-4 text-muted-foreground" aria-hidden />
              {IMPORT_DATA_TYPE_LABELS[option.value]}
            </span>
            <span className="mt-1 block text-sm text-muted-foreground">
              {IMPORT_DATA_TYPE_DESCRIPTIONS[option.value]}
            </span>
            <span className="mt-2 block text-xs text-muted-foreground">
              目标月份 {month}
            </span>
          </button>
        )
      })}
    </fieldset>
  )
}
