import { useQuery } from "@tanstack/react-query"

import { AttendanceRosterService, type RosterDayEmployee } from "@/client"
import {
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { getErrorMessage } from "@/lib/api-error"
import { ROSTER_SOURCE_LABELS, ROSTER_STATE_LABELS } from "@/lib/enums"
import { rosterDayQueryKey } from "./roster-queries"

export function DaySheetDialog({
  open,
  companyId,
  month,
  day,
  onClose,
}: {
  open: boolean
  companyId: string
  month: string
  day: number | null
  onClose: () => void
}) {
  const date = day === null ? "" : `${month}-${String(day).padStart(2, "0")}`
  const dayQuery = useQuery({
    queryKey: rosterDayQueryKey(companyId, date),
    enabled: open && day !== null,
    queryFn: async () => {
      const response = await AttendanceRosterService.readRosterDay({
        query: { company_id: companyId, date },
      })
      return response.data
    },
  })

  const workRows = (dayQuery.data?.employees ?? []).filter(
    (row) => row.state === "work",
  )
  const restRows = (dayQuery.data?.employees ?? []).filter(
    (row) => row.state === "rest",
  )

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent
        className="max-h-[88vh] overflow-y-auto sm:max-w-2xl"
        data-testid="day-sheet"
      >
        <DialogHeader>
          <DialogTitle>{date} 这天谁上班</DialogTitle>
          <DialogDescription>
            {dayQuery.data
              ? `上班 ${workRows.length} 人、休息 ${restRows.length} 人、未排班 ${dayQuery.data.unscheduled_count} 人。`
              : "按当前排班明细展示这一天的人员安排。"}
          </DialogDescription>
        </DialogHeader>

        {dayQuery.isLoading ? (
          <LoadingState rows={3} />
        ) : dayQuery.error ? (
          <ErrorState
            message={getErrorMessage(dayQuery.error)}
            onRetry={() => void dayQuery.refetch()}
          />
        ) : (
          <>
            {workRows.length > 0 && (
              <EmployeeGroup title="上班" rows={workRows} />
            )}
            {restRows.length > 0 && (
              <EmployeeGroup title="休息" rows={restRows} />
            )}
            {workRows.length === 0 && restRows.length === 0 && (
              <div className="rounded-md border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
                这一天没有任何已生成的排班明细。
              </div>
            )}
            {(dayQuery.data?.unscheduled_count ?? 0) > 0 && (
              <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100">
                {dayQuery.data?.unscheduled_count}{" "}
                名在职员工当天未排班（未排班不是休息）。
              </div>
            )}
          </>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            关闭
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function EmployeeGroup({
  title,
  rows,
}: {
  title: string
  rows: RosterDayEmployee[]
}) {
  return (
    <div className="space-y-1">
      <div className="text-sm font-medium">{title}</div>
      <div className="divide-y rounded-md border">
        {rows.map((row) => (
          <div
            key={row.employee.employee_id}
            className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm"
          >
            <div>
              <span className="font-medium">{row.employee.employee_name}</span>
              <span className="ml-2 text-xs text-muted-foreground">
                {row.employee.employee_no} ·{" "}
                {row.employee.department_name ?? "—"}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-1">
              {row.state === "work" ? (
                (row.shifts ?? []).map((shift) => (
                  <Badge key={`${shift.id}-${shift.seq}`} variant="secondary">
                    {shift.shift_name}
                  </Badge>
                ))
              ) : (
                <Badge variant="outline">{ROSTER_STATE_LABELS.rest}</Badge>
              )}
              <Badge variant={row.source === "manual" ? "default" : "outline"}>
                {ROSTER_SOURCE_LABELS[row.source]}
              </Badge>
              {row.note && (
                <span className="text-xs text-muted-foreground">
                  {row.note}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
