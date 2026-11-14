import type { ReactNode } from "react"

import { useAttendanceMonth } from "@/contexts/AttendanceMonthContext"
import { AttendanceMonthPicker } from "./AttendanceMonthPicker"
import { EmptyState } from "./StateViews"

interface AttendancePageProps {
  title: string
  description: string
  children?: ReactNode
  actions?: ReactNode
}

/** Scheme A page shell: title, month context, and an explicit empty state. */
export function AttendancePage({
  title,
  description,
  children,
  actions,
}: AttendancePageProps) {
  const { month } = useAttendanceMonth()

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="text-muted-foreground">{description}</p>
        </div>
        <div className="flex shrink-0 flex-col items-start gap-3 sm:items-end">
          <AttendanceMonthPicker />
          {actions}
        </div>
      </div>
      {children ?? (
        <EmptyState
          title={`${title}功能建设中`}
          message={`当前考勤月份为 ${month}。该模块将在后续切片中实现。`}
        />
      )}
    </div>
  )
}
