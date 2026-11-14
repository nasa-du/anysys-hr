import type {
  EmployeePublic,
  HolidayPublic,
  SchedulePlanPublic,
} from "@/client"
import {
  dayKind,
  dayKindLabel,
  mergedDaySummary,
  monthDays,
  planCoverage,
  planShiftsForDay,
  WEEKDAY_LABELS,
  weekdayIndex,
} from "./plan-utils"

export function PlanCalendar({
  month,
  plans,
  employees,
  holidays,
  selectedPlan,
  selectedDay,
  onSelectDay,
}: {
  month: string
  plans: SchedulePlanPublic[]
  employees: EmployeePublic[]
  holidays: HolidayPublic[]
  selectedPlan: SchedulePlanPublic | null
  selectedDay: number | null
  onSelectDay: (day: number) => void
}) {
  const coverage = selectedPlan
    ? planCoverage(selectedPlan, employees).length
    : 0

  return (
    <div className="rounded-lg border" data-testid="plan-calendar">
      <div className="grid grid-cols-7 border-b bg-muted/40 text-center text-xs text-muted-foreground">
        {WEEKDAY_LABELS.map((label) => (
          <div key={label} className="py-2">
            周{label}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7">
        {Array.from({ length: weekdayIndex(`${month}-01`) }).map((_, index) => (
          <div key={`lead-${index}`} className="min-h-24 border-b border-r" />
        ))}
        {monthDays(month).map((date) => {
          const day = Number(date.slice(8, 10))
          const kind = dayKind(date, holidays)
          const isSelected = selectedDay === day
          return (
            <button
              key={date}
              type="button"
              data-testid={`calendar-day-${day}`}
              aria-label={`${date} ${dayKindLabel(kind)}`}
              onClick={() => onSelectDay(day)}
              className={`min-h-24 border-b border-r p-1.5 text-left transition hover:bg-muted/40 ${
                kind === "holiday"
                  ? "bg-destructive/5"
                  : kind === "adjusted_workday"
                    ? "bg-primary/5"
                    : kind === "weekend"
                      ? "bg-muted/20"
                      : ""
              } ${isSelected ? "ring-2 ring-inset ring-primary/40" : ""}`}
            >
              <div className="flex items-center justify-between gap-1">
                <span className="text-sm font-medium">{day}</span>
                <span
                  className={`text-[10px] ${
                    kind === "holiday"
                      ? "text-destructive"
                      : kind === "adjusted_workday"
                        ? "text-primary"
                        : "text-muted-foreground"
                  }`}
                >
                  {dayKindLabel(kind)}
                </span>
              </div>
              {selectedPlan ? (
                <PlanDayCell
                  plan={selectedPlan}
                  day={day}
                  coverage={coverage}
                />
              ) : (
                <MergedDayCell
                  plans={plans}
                  employees={employees}
                  date={date}
                />
              )}
            </button>
          )
        })}
        {Array.from({
          length:
            (7 -
              ((weekdayIndex(`${month}-01`) + monthDays(month).length) % 7)) %
            7,
        }).map((_, index) => (
          <div key={`tail-${index}`} className="min-h-24 border-b border-r" />
        ))}
      </div>
      <div className="flex flex-wrap gap-3 border-t px-3 py-2 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <span className="size-2 rounded-full bg-destructive/60" />
          法定节假日
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="size-2 rounded-full bg-primary/60" />
          调休上班
        </span>
        <span>点击日期查看当天明细</span>
      </div>
    </div>
  )
}

function MergedDayCell({
  plans,
  employees,
  date,
}: {
  plans: SchedulePlanPublic[]
  employees: EmployeePublic[]
  date: string
}) {
  const summary = mergedDaySummary(plans, employees, date)
  const hidden = summary.shiftCounts.slice(0, 3)
  return (
    <div className="mt-1 space-y-1">
      {hidden.map((shift) => (
        <div
          key={shift.shiftCode}
          className="flex items-center justify-between gap-1 rounded px-1 text-[11px]"
          style={{
            backgroundColor: shift.color ? `${shift.color}22` : undefined,
          }}
        >
          <span className="truncate">{shift.shiftName}</span>
          <span className="text-muted-foreground">{shift.count}人</span>
        </div>
      ))}
      {summary.shiftCounts.length > 3 && (
        <div className="text-[10px] text-muted-foreground">
          +{summary.shiftCounts.length - 3} 个班次
        </div>
      )}
      {summary.workCount === 0 && (
        <div className="text-[11px] text-muted-foreground">
          {summary.restCount ? "休息" : "无人排班"}
        </div>
      )}
      <div className="flex flex-wrap gap-x-2 text-[10px] text-muted-foreground">
        {summary.restCount > 0 && <span>休 {summary.restCount}</span>}
        {summary.unscheduledCount > 0 && (
          <span className="text-amber-700 dark:text-amber-300">
            未排班 {summary.unscheduledCount}
          </span>
        )}
      </div>
    </div>
  )
}

function PlanDayCell({
  plan,
  day,
  coverage,
}: {
  plan: SchedulePlanPublic
  day: number
  coverage: number
}) {
  const shifts = planShiftsForDay(plan, day)
  return (
    <div className="mt-1 space-y-1">
      {shifts.length === 0 ? (
        <div className="text-[11px] text-muted-foreground">方案休息</div>
      ) : (
        shifts.map((shift) => (
          <div
            key={`${shift.id}-${shift.seq}`}
            className="truncate rounded px-1 text-[11px]"
            style={{
              backgroundColor: shift.shift_color
                ? `${shift.shift_color}22`
                : undefined,
            }}
          >
            {shift.shift_name ?? shift.shift_code}
          </div>
        ))
      )}
      <div className="text-[10px] text-muted-foreground">{coverage} 人范围</div>
    </div>
  )
}
