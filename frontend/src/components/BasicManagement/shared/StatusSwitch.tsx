import type { ComponentProps } from "react"

import { cn } from "@/lib/utils"

type StatusSwitchProps = Omit<
  ComponentProps<"button">,
  "onChange" | "value"
> & {
  checked: boolean
  onCheckedChange: (checked: boolean) => void
}

/** Accessible enable/disable switch; the Chinese state text sits beside it. */
export function StatusSwitch({
  checked,
  onCheckedChange,
  className,
  ...props
}: StatusSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      data-state={checked ? "checked" : "unchecked"}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        "inline-flex h-5 w-9 shrink-0 items-center rounded-full border border-transparent transition-colors focus-visible:ring-ring/50 focus-visible:ring-[3px] focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50",
        checked ? "bg-primary" : "bg-input dark:bg-input/60",
        className,
      )}
      {...props}
    >
      <span
        className={cn(
          "block size-4 rounded-full bg-background shadow-sm transition-transform",
          checked ? "translate-x-4" : "translate-x-0.5",
        )}
      />
    </button>
  )
}
