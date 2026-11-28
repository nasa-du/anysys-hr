import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  type PayrollAttendanceLock,
  usePayrollMonth,
} from "@/contexts/PayrollMonthContext"
import { formatDateTimeShanghai } from "@/lib/datetime"
import {
  PAYROLL_ATTENDANCE_LOCK_LABELS,
  PAYROLL_CALC_RUN_STATUS_LABELS,
  PAYROLL_CALC_RUN_TRIGGER_LABELS,
} from "@/lib/payroll-enums"
import { PayrollStaleBadgeView } from "./StaleBadge"
import { PayrollMonthStatusBadge } from "./StatusBadge"

function attendanceLockLabel(status: PayrollAttendanceLock["status"]): string {
  return PAYROLL_ATTENDANCE_LOCK_LABELS[status]
}

/**
 * The one month control shared by every monthly payroll page. Configuration
 * pages never mount the provider, so they never render this bar.
 */
export function PayrollMonthBar() {
  const {
    month,
    setMonth,
    status,
    inputVersion,
    latestRun,
    attendanceLock,
    staleBadges,
    actions,
  } = usePayrollMonth()

  return (
    <section
      className="flex flex-col gap-4 rounded-lg border bg-card p-4"
      data-testid="payroll-month-bar"
    >
      <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
        <div className="flex items-center gap-2">
          <label
            className="text-sm font-medium text-muted-foreground"
            htmlFor="payroll-month"
          >
            薪资月份
          </label>
          <Input
            id="payroll-month"
            aria-label="薪资月份"
            className="w-[160px]"
            type="month"
            value={month}
            onChange={(event) => setMonth(event.target.value)}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PayrollMonthStatusBadge status={status} />
          {staleBadges.map((badge) => (
            <PayrollStaleBadgeView key={badge} badge={badge} />
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <span
          className="text-muted-foreground"
          data-testid="payroll-input-version"
        >
          输入版本 <span className="text-foreground">v{inputVersion}</span>
        </span>
        <span
          className="text-muted-foreground"
          data-testid="payroll-latest-run"
        >
          最近成功核算{" "}
          <span className="text-foreground">
            {latestRun
              ? `${PAYROLL_CALC_RUN_STATUS_LABELS[latestRun.status]} · ${
                  PAYROLL_CALC_RUN_TRIGGER_LABELS[latestRun.trigger]
                } · ${formatDateTimeShanghai(latestRun.finishedAt)}`
              : "暂无"}
          </span>
        </span>
        <span
          className="text-muted-foreground"
          data-testid="payroll-attendance-lock"
        >
          考勤{" "}
          <span className="text-foreground">
            {attendanceLockLabel(attendanceLock.status)}
            {attendanceLock.status === "locked" && attendanceLock.lockedAt
              ? ` · ${formatDateTimeShanghai(attendanceLock.lockedAt)}`
              : ""}
          </span>
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="outline" onClick={actions.importMonth}>
          导入
        </Button>
        <Button size="sm" onClick={actions.recalculate}>
          重算
        </Button>
        <Button size="sm" variant="outline" onClick={actions.confirmMonth}>
          确认
        </Button>
        <Button size="sm" variant="outline" onClick={actions.issuePayslips}>
          发工资条
        </Button>
        <Button size="sm" variant="ghost" onClick={actions.unlockMonth}>
          解锁
        </Button>
      </div>
    </section>
  )
}
