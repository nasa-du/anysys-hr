import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"

import {
  AttendanceRosterService,
  type EmployeePublic,
  type RosterEmployeeSummaryPublic,
  type RosterEntryPublic,
  type ShiftPublic,
} from "@/client"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { getErrorMessage } from "@/lib/api-error"
import { DAY_TYPE_LABELS, ROSTER_SOURCE_LABELS } from "@/lib/enums"
import { ManualExceptionDialog } from "./ManualExceptionDialog"
import { monthDays, WEEKDAY_LABELS, weekdayIndex } from "./plan-utils"
import { DAY_TYPE_STYLES } from "./roster-day-styles"
import {
  rosterCalendarQueryKey,
  rosterEmployeesQueryKey,
  rosterEntriesQueryKey,
  rosterMonthQueryKey,
} from "./roster-queries"

const UNSCHEDULED_LABEL = "未排班"

export function EmployeeCalendarView({
  companyId,
  month,
  editable,
  employees,
  shifts,
}: {
  companyId: string
  month: string
  editable: boolean
  employees: EmployeePublic[]
  shifts: ShiftPublic[]
}) {
  const queryClient = useQueryClient()
  const [keyword, setKeyword] = useState("")
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string | null>(
    null,
  )
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogDate, setDialogDate] = useState<string | null>(null)
  const [dialogEntry, setDialogEntry] = useState<RosterEntryPublic | null>(null)

  const summariesQuery = useQuery({
    queryKey: rosterEmployeesQueryKey(companyId, month),
    queryFn: async () => {
      const response = await AttendanceRosterService.readRosterEmployees({
        query: { company_id: companyId, month, limit: 500 },
      })
      return response.data
    },
  })

  const monthQuery = useQuery({
    queryKey: rosterMonthQueryKey(companyId, month),
    queryFn: async () => {
      const response = await AttendanceRosterService.readRosterMonth({
        query: { company_id: companyId, month },
      })
      return response.data
    },
  })

  const overview = useMemo(() => {
    const days = monthQuery.data?.days ?? []
    const shifts = new Map<
      string,
      {
        shift_code: string
        shift_name: string
        color: string | null
        count: number
      }
    >()
    for (const day of days) {
      for (const shift of day.shift_counts ?? []) {
        const existing = shifts.get(shift.shift_code)
        if (existing) {
          existing.count += shift.count
        } else {
          shifts.set(shift.shift_code, {
            shift_code: shift.shift_code,
            shift_name: shift.shift_name,
            color: shift.color ?? null,
            count: shift.count,
          })
        }
      }
    }
    return {
      work: days.reduce((sum, day) => sum + day.work_count, 0),
      rest: days.reduce((sum, day) => sum + day.rest_count, 0),
      unscheduled: days.reduce((sum, day) => sum + day.unscheduled_count, 0),
      manual: days.reduce((sum, day) => sum + day.manual_count, 0),
      shifts: [...shifts.values()].sort((left, right) =>
        left.shift_code.localeCompare(right.shift_code),
      ),
      plans: monthQuery.data?.plans.length ?? 0,
    }
  }, [monthQuery.data])

  const summaries: RosterEmployeeSummaryPublic[] =
    summariesQuery.data?.data ?? []
  const filteredSummaries = useMemo(() => {
    const normalized = keyword.trim().toLowerCase()
    if (!normalized) return summaries
    return summaries.filter(
      (summary) =>
        summary.employee_name.toLowerCase().includes(normalized) ||
        summary.employee_no.toLowerCase().includes(normalized),
    )
  }, [summaries, keyword])

  useEffect(() => {
    if (summaries.length === 0) {
      setSelectedEmployeeId(null)
      return
    }
    if (
      selectedEmployeeId === null ||
      !summaries.some((summary) => summary.employee_id === selectedEmployeeId)
    ) {
      setSelectedEmployeeId(summaries[0].employee_id)
    }
  }, [summaries, selectedEmployeeId])

  const selectedSummary = summaries.find(
    (summary) => summary.employee_id === selectedEmployeeId,
  )

  const calendarQuery = useQuery({
    queryKey: rosterCalendarQueryKey(
      companyId,
      month,
      selectedEmployeeId ?? "",
    ),
    enabled: selectedEmployeeId !== null,
    queryFn: async () => {
      const response = await AttendanceRosterService.readEmployeeCalendar({
        query: {
          company_id: companyId,
          month,
          employee_id: selectedEmployeeId ?? "",
        },
      })
      return response.data
    },
  })

  const entriesQuery = useQuery({
    queryKey: rosterEntriesQueryKey(companyId, {
      month,
      employeeId: selectedEmployeeId ?? undefined,
    }),
    enabled: selectedEmployeeId !== null,
    queryFn: async () => {
      const response = await AttendanceRosterService.readRosterEntries({
        query: {
          company_id: companyId,
          month,
          employee_id: selectedEmployeeId ?? undefined,
          limit: 500,
        },
      })
      return response.data.data
    },
  })

  const manualEntryByDate = useMemo(() => {
    const map = new Map<string, RosterEntryPublic>()
    for (const entry of entriesQuery.data ?? []) {
      if (entry.source === "manual") map.set(entry.work_date, entry)
    }
    return map
  }, [entriesQuery.data])

  const openDay = async (date: string, source: string | null | undefined) => {
    if (!editable || !selectedEmployeeId) return
    let manual = manualEntryByDate.get(date)
    if (source === "manual" && manual === undefined) {
      // The calendar response intentionally has no entry id; fetch the row
      // when the entries query has not caught up with the latest write yet.
      const response = await AttendanceRosterService.readRosterEntries({
        query: {
          company_id: companyId,
          month,
          employee_id: selectedEmployeeId,
          source: "manual",
          limit: 500,
        },
      })
      manual = response.data.data.find((entry) => entry.work_date === date)
      queryClient.setQueryData(
        rosterEntriesQueryKey(companyId, {
          month,
          employeeId: selectedEmployeeId,
        }),
        response.data.data,
      )
    }
    setDialogEntry(manual ?? null)
    setDialogDate(date)
    setDialogOpen(true)
  }

  const openCreate = () => {
    if (!editable || !selectedEmployeeId) return
    setDialogEntry(null)
    setDialogDate(null)
    setDialogOpen(true)
  }

  const closeDialog = () => {
    setDialogOpen(false)
    setDialogEntry(null)
    setDialogDate(null)
  }

  const loading = summariesQuery.isLoading || calendarQuery.isLoading
  const queryError = summariesQuery.error ?? calendarQuery.error

  if (loading) {
    return <LoadingState rows={5} />
  }
  if (queryError) {
    return (
      <ErrorState
        message={getErrorMessage(queryError)}
        onRetry={() => {
          void summariesQuery.refetch()
          void calendarQuery.refetch()
        }}
      />
    )
  }
  if (summaries.length === 0) {
    return (
      <EmptyState
        title={`${month} 没有可排班的员工`}
        message="本月没有处于任职期间的员工。请先在「员工」页面维护入职与离职日期。"
      />
    )
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
      <div className="space-y-3 rounded-lg border p-3">
        <div>
          <div className="text-sm font-medium">员工明细</div>
          <p className="text-xs text-muted-foreground">
            选中员工查看月历，点击日期新增或编辑人工例外。
          </p>
        </div>
        <Input
          placeholder="搜索工号或姓名"
          value={keyword}
          maxLength={100}
          onChange={(event) => setKeyword(event.target.value)}
        />
        <div
          className="max-h-[520px] space-y-1 overflow-y-auto"
          data-testid="roster-employee-list"
        >
          {filteredSummaries.map((summary) => (
            <button
              key={summary.employee_id}
              type="button"
              data-testid={`roster-employee-${summary.employee_no}`}
              onClick={() => setSelectedEmployeeId(summary.employee_id)}
              className={`w-full rounded-md border px-2 py-2 text-left text-sm transition hover:bg-muted/60 ${
                summary.employee_id === selectedEmployeeId
                  ? "border-primary/50 bg-primary/5"
                  : ""
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{summary.employee_name}</span>
                <span className="text-xs text-muted-foreground">
                  {summary.employee_no}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap gap-x-2 text-xs text-muted-foreground">
                <span>上班 {summary.work_days}</span>
                <span>休息 {summary.rest_days}</span>
                <span
                  className={
                    summary.unscheduled_days
                      ? "text-amber-700 dark:text-amber-300"
                      : undefined
                  }
                >
                  未排班 {summary.unscheduled_days}
                </span>
                {summary.manual_exception_count > 0 && (
                  <span className="text-primary">
                    人工 {summary.manual_exception_count}
                  </span>
                )}
              </div>
            </button>
          ))}
          {filteredSummaries.length === 0 && (
            <p className="px-2 py-4 text-sm text-muted-foreground">
              没有匹配的员工。
            </p>
          )}
        </div>
      </div>

      <div className="space-y-3">
        <div
          className="rounded-lg border px-3 py-2"
          data-testid="roster-month-overview"
        >
          <div className="mb-2 flex flex-wrap items-center justify-between gap-1">
            <span className="text-sm font-medium">本月概览</span>
            <span className="text-xs text-muted-foreground">
              {monthQuery.isLoading
                ? "加载中…"
                : monthQuery.error
                  ? "本月概览加载失败"
                  : `${overview.plans} 个方案`}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <OverviewTile label="上班人日" value={overview.work} />
            <OverviewTile label="休息人日" value={overview.rest} />
            <OverviewTile
              label="未排班人日"
              value={overview.unscheduled}
              tone="warn"
            />
            <OverviewTile
              label="人工例外"
              value={overview.manual}
              tone="manual"
            />
          </div>
          {overview.shifts.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {overview.shifts.map((shift) => (
                <Badge key={shift.shift_code} variant="secondary">
                  {shift.shift_name} × {shift.count}
                </Badge>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2 rounded-lg border px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium">
              {selectedSummary
                ? `${selectedSummary.employee_name} · ${selectedSummary.department_name ?? "—"}`
                : "员工日历"}
            </span>
            {selectedSummary && (
              <>
                <Badge variant="secondary">
                  上班 {selectedSummary.work_days}
                </Badge>
                <Badge variant="outline">
                  休息 {selectedSummary.rest_days}
                </Badge>
                <Badge variant="outline">
                  未排班 {selectedSummary.unscheduled_days}
                </Badge>
                <Badge variant="secondary">
                  人工 {selectedSummary.manual_exception_count}
                </Badge>
              </>
            )}
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={!editable || !selectedEmployeeId}
            onClick={openCreate}
          >
            新建人工例外
          </Button>
        </div>

        {!editable && (
          <div
            role="status"
            className="rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground"
          >
            本月已确认或锁定，员工日历只读。
          </div>
        )}

        <div className="rounded-lg border" data-testid="employee-calendar">
          <div className="grid grid-cols-7 border-b bg-muted/40 text-center text-xs text-muted-foreground">
            {WEEKDAY_LABELS.map((label) => (
              <div key={label} className="py-2">
                周{label}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {Array.from({ length: weekdayIndex(`${month}-01`) }).map(
              (_, index) => (
                <div
                  key={`lead-${index}`}
                  className="min-h-24 border-b border-r"
                />
              ),
            )}
            {(calendarQuery.data?.days ?? []).map((day) => {
              const dayNumber = Number(day.work_date.slice(8, 10))
              const manual = day.source === "manual"
              const shiftLabel = (day.shifts ?? [])
                .map((shift) => shift.shift_name)
                .join(" + ")
              return (
                <button
                  key={day.work_date}
                  type="button"
                  data-testid={`roster-day-${dayNumber}`}
                  aria-label={`${day.work_date} ${DAY_TYPE_LABELS[day.day_type]} ${
                    day.state === "unscheduled"
                      ? UNSCHEDULED_LABEL
                      : day.state === "rest"
                        ? "休息"
                        : "上班"
                  }`}
                  disabled={!editable}
                  onClick={() => void openDay(day.work_date, day.source)}
                  className={`min-h-24 border-b border-r p-1.5 text-left transition hover:bg-muted/40 ${
                    DAY_TYPE_STYLES[day.day_type]
                  } ${manual ? "ring-1 ring-inset ring-primary/40" : ""} ${
                    editable ? "" : "cursor-default"
                  }`}
                >
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-sm font-medium">{dayNumber}</span>
                    <span className="text-[10px] text-muted-foreground">
                      {DAY_TYPE_LABELS[day.day_type]}
                    </span>
                  </div>
                  <div className="mt-1 space-y-1">
                    {day.state === "work" && (
                      <div className="truncate rounded bg-emerald-500/10 px-1 text-[11px] text-emerald-800 dark:text-emerald-200">
                        {shiftLabel || "上班"}
                      </div>
                    )}
                    {day.state === "rest" && (
                      <div className="rounded bg-muted px-1 text-[11px] text-muted-foreground">
                        休息
                      </div>
                    )}
                    {day.state === "unscheduled" && (
                      <div className="rounded px-1 text-[11px] text-amber-700 dark:text-amber-300">
                        {UNSCHEDULED_LABEL}
                      </div>
                    )}
                    <div className="flex flex-wrap items-center gap-1">
                      {day.source && (
                        <span
                          className={`text-[10px] ${
                            manual
                              ? "font-medium text-primary"
                              : "text-muted-foreground"
                          }`}
                        >
                          {ROSTER_SOURCE_LABELS[day.source]}
                        </span>
                      )}
                      {day.note && (
                        <span className="truncate text-[10px] text-muted-foreground">
                          {day.note}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              )
            })}
            {Array.from({
              length:
                (7 -
                  ((weekdayIndex(`${month}-01`) + monthDays(month).length) %
                    7)) %
                7,
            }).map((_, index) => (
              <div
                key={`tail-${index}`}
                className="min-h-24 border-b border-r"
              />
            ))}
          </div>
          <div className="flex flex-wrap gap-3 border-t px-3 py-2 text-xs text-muted-foreground">
            <span>上班 / 休息为已生成明细</span>
            <span className="text-amber-700 dark:text-amber-300">
              未排班 = 无明细（不是休息）
            </span>
            <span>人工 = 人工例外，优先于方案</span>
          </div>
        </div>
      </div>

      <ManualExceptionDialog
        open={dialogOpen}
        month={month}
        employees={employees}
        shifts={shifts}
        initialEmployeeId={selectedEmployeeId}
        initialDate={dialogDate}
        entry={dialogEntry}
        onClose={closeDialog}
        onSaved={closeDialog}
      />
    </div>
  )
}

function OverviewTile({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone?: "warn" | "manual"
}) {
  const toneClass =
    tone === "warn"
      ? "text-amber-700 dark:text-amber-300"
      : tone === "manual"
        ? "text-primary"
        : ""
  return (
    <div className="rounded-md border px-2 py-1.5">
      <div className="text-[10px] text-muted-foreground">{label}</div>
      <div className={`text-lg font-semibold ${toneClass}`}>{value}</div>
    </div>
  )
}
