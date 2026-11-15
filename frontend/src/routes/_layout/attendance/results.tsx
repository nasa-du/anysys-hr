import { createFileRoute, Link } from "@tanstack/react-router"
import { useState } from "react"

import { CalcRunList } from "@/components/Attendance/results/CalcRunList"
import { DayDetailDrawer } from "@/components/Attendance/results/DayDetailDrawer"
import { DayResultTable } from "@/components/Attendance/results/DayResultTable"
import { EmployeeResultCalendarDialog } from "@/components/Attendance/results/EmployeeResultCalendarDialog"
import { MonthStateBar } from "@/components/Attendance/results/MonthStateBar"
import { MonthSummaryTable } from "@/components/Attendance/results/MonthSummaryTable"
import {
  useMonthState,
  useResultDepartments,
  useResultEmployees,
} from "@/components/Attendance/results/queries"
import { AttendancePage } from "@/components/Attendance/shared/AttendancePage"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Button } from "@/components/ui/button"
import { useAttendanceMonth } from "@/contexts/AttendanceMonthContext"
import { useCompany } from "@/contexts/CompanyContext"
import { getErrorMessage } from "@/lib/api-error"

export const Route = createFileRoute("/_layout/attendance/results")({
  component: ResultsPage,
  head: () => ({
    meta: [{ title: "考勤结果 - AnySys" }],
  }),
})

const PAGE_DESCRIPTION =
  "默认查看全量日结果，一键聚焦异常；日详情抽屉对照排班、打卡、OA 与结果。计算只在此处显式触发。"

type ResultTab = "days" | "summary" | "runs"

const TABS: Array<{ key: ResultTab; label: string }> = [
  { key: "days", label: "日结果" },
  { key: "summary", label: "员工月汇总" },
  { key: "runs", label: "计算记录" },
]

function ResultsPage() {
  const { selectedCompanyId, isLoading } = useCompany()
  const { month } = useAttendanceMonth()

  if (isLoading) {
    return (
      <AttendancePage title="考勤结果" description={PAGE_DESCRIPTION}>
        <LoadingState rows={4} />
      </AttendancePage>
    )
  }

  if (!selectedCompanyId) {
    return (
      <AttendancePage title="考勤结果" description={PAGE_DESCRIPTION}>
        <EmptyState
          title="尚未选择公司"
          message="请先在「公司」页面创建并启用公司，再从顶部切换器选择公司。"
          action={
            <Button asChild variant="outline">
              <Link to="/companies">前往公司页面</Link>
            </Button>
          }
        />
      </AttendancePage>
    )
  }

  return (
    <ResultsWorkspace
      key={`${selectedCompanyId}-${month}`}
      companyId={selectedCompanyId}
    />
  )
}

function ResultsWorkspace({ companyId }: { companyId: string }) {
  const { month } = useAttendanceMonth()
  const { selectedCompany } = useCompany()
  const [tab, setTab] = useState<ResultTab>("days")
  const [selectedDay, setSelectedDay] = useState<{
    employeeId: string
    workDate: string
  } | null>(null)
  const [calendarEmployeeId, setCalendarEmployeeId] = useState<string | null>(
    null,
  )

  const monthStateQuery = useMonthState(companyId, month)
  const departmentsQuery = useResultDepartments(companyId)
  const employeesQuery = useResultEmployees(companyId)

  const departments = departmentsQuery.data ?? []
  const employees = employeesQuery.data ?? []
  const referenceError = departmentsQuery.error ?? employeesQuery.error
  const referenceLoading =
    departmentsQuery.isLoading || employeesQuery.isLoading

  return (
    <AttendancePage
      title="考勤结果"
      description={`当前公司：${
        selectedCompany?.company_name ?? "—"
      }。${PAGE_DESCRIPTION}`}
    >
      <MonthStateBar
        companyId={companyId}
        month={month}
        state={monthStateQuery.data}
        isLoading={monthStateQuery.isLoading}
        isError={monthStateQuery.isError}
        onRetry={() => void monthStateQuery.refetch()}
        onViewHistory={() => setTab("runs")}
      />

      <div className="flex w-fit gap-1 rounded-md border p-1">
        {TABS.map((item) => (
          <Button
            key={item.key}
            type="button"
            size="sm"
            variant={tab === item.key ? "default" : "ghost"}
            data-testid={`tab-${item.key}`}
            onClick={() => setTab(item.key)}
          >
            {item.label}
          </Button>
        ))}
      </div>

      {tab === "runs" ? (
        <CalcRunList companyId={companyId} month={month} />
      ) : referenceLoading ? (
        <LoadingState rows={5} />
      ) : referenceError ? (
        <ErrorState
          message={getErrorMessage(referenceError)}
          onRetry={() => {
            void departmentsQuery.refetch()
            void employeesQuery.refetch()
          }}
        />
      ) : tab === "days" ? (
        <DayResultTable
          companyId={companyId}
          month={month}
          departments={departments}
          employees={employees}
          onOpenDay={(employeeId, workDate) =>
            setSelectedDay({ employeeId, workDate })
          }
        />
      ) : (
        <MonthSummaryTable
          companyId={companyId}
          month={month}
          departments={departments}
          employees={employees}
          onOpenCalendar={setCalendarEmployeeId}
        />
      )}

      <DayDetailDrawer
        companyId={companyId}
        employeeId={selectedDay?.employeeId ?? null}
        workDate={selectedDay?.workDate ?? null}
        onClose={() => setSelectedDay(null)}
      />
      <EmployeeResultCalendarDialog
        companyId={companyId}
        month={month}
        employeeId={calendarEmployeeId}
        onOpenDay={(employeeId, workDate) => {
          setCalendarEmployeeId(null)
          setSelectedDay({ employeeId, workDate })
        }}
        onClose={() => setCalendarEmployeeId(null)}
      />
    </AttendancePage>
  )
}
