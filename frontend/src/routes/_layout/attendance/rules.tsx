import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"

import { type AttendanceMonthPublic, AttendanceMonthsService } from "@/client"
import { CompanyRuleForm } from "@/components/Attendance/rules/CompanyRuleForm"
import { HolidayCalendar } from "@/components/Attendance/rules/HolidayCalendar"
import { ImpactHint } from "@/components/Attendance/rules/ImpactHint"
import { PlanOverrideSection } from "@/components/Attendance/rules/PlanOverrideSection"
import { monthsQueryKey } from "@/components/Attendance/rules/queries"
import { AttendancePage } from "@/components/Attendance/shared/AttendancePage"
import {
  EmptyState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Button } from "@/components/ui/button"
import { useAttendanceMonth } from "@/contexts/AttendanceMonthContext"
import { useCompany } from "@/contexts/CompanyContext"

export const Route = createFileRoute("/_layout/attendance/rules")({
  component: RulesPage,
  head: () => ({
    meta: [{ title: "规则与节假日 - AnySys" }],
  }),
})

const PAGE_DESCRIPTION =
  "公司默认规则 + 方案覆盖；节假日日历决定工作日 / 周末 / 法定节假日 / 调休上班。修改只影响草稿与已计算月份。"

function RulesPage() {
  const { selectedCompanyId, isLoading } = useCompany()

  if (isLoading) {
    return (
      <AttendancePage title="规则与节假日" description={PAGE_DESCRIPTION}>
        <LoadingState rows={4} />
      </AttendancePage>
    )
  }

  if (!selectedCompanyId) {
    return (
      <AttendancePage title="规则与节假日" description={PAGE_DESCRIPTION}>
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
    <RulesWorkspace key={selectedCompanyId} companyId={selectedCompanyId} />
  )
}

function RulesWorkspace({ companyId }: { companyId: string }) {
  const { selectedCompany } = useCompany()
  const { month } = useAttendanceMonth()

  // Company rule and holiday changes affect every editable month, not just
  // the selected year, so the impact hint reads the full company list.
  const monthsQuery = useQuery({
    queryKey: monthsQueryKey(companyId, null),
    queryFn: async () => {
      const response = await AttendanceMonthsService.readMonths({
        query: { company_id: companyId },
      })
      return response.data
    },
  })
  const months: AttendanceMonthPublic[] = monthsQuery.data?.data ?? []
  const currentMonth = months.find((item) => item.month === month) ?? null

  return (
    <AttendancePage
      title="规则与节假日"
      description={`当前公司：${
        selectedCompany?.company_name ?? "—"
      }。${PAGE_DESCRIPTION}`}
    >
      <ImpactHint months={months} isLoading={monthsQuery.isLoading} />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <CompanyRuleForm companyId={companyId} />
        <HolidayCalendar companyId={companyId} month={month} />
      </div>

      <PlanOverrideSection
        companyId={companyId}
        month={month}
        monthState={currentMonth}
      />
    </AttendancePage>
  )
}
