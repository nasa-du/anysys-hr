import { createFileRoute, Link } from "@tanstack/react-router"

import { BatchHistory } from "@/components/Attendance/imports/BatchHistory"
import { CurrentBatches } from "@/components/Attendance/imports/CurrentBatches"
import { ImportWizard } from "@/components/Attendance/imports/ImportWizard"
import { AttendancePage } from "@/components/Attendance/shared/AttendancePage"
import {
  EmptyState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Button } from "@/components/ui/button"
import { useAttendanceMonth } from "@/contexts/AttendanceMonthContext"
import { useCompany } from "@/contexts/CompanyContext"

export const Route = createFileRoute("/_layout/attendance/imports")({
  component: ImportsPage,
  head: () => ({
    meta: [{ title: "导入中心 - AnySys" }],
  }),
})

const PAGE_DESCRIPTION =
  "上传或粘贴打卡与 OA 申请数据，核对列映射和预览统计后提交。覆盖式刷新以公司 + 月份 + 数据类型为一个批次。"

function ImportsPage() {
  const { selectedCompanyId, selectedCompany, isLoading } = useCompany()
  const { month } = useAttendanceMonth()

  if (isLoading) {
    return (
      <AttendancePage title="导入中心" description={PAGE_DESCRIPTION}>
        <LoadingState rows={4} />
      </AttendancePage>
    )
  }

  if (!selectedCompanyId) {
    return (
      <AttendancePage title="导入中心" description={PAGE_DESCRIPTION}>
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
    <AttendancePage
      title="导入中心"
      description={`当前公司：${
        selectedCompany?.company_name ?? "—"
      }。${PAGE_DESCRIPTION}`}
    >
      <ImportWizard
        key={`${selectedCompanyId}-${month}`}
        companyId={selectedCompanyId}
        month={month}
      />
      <CurrentBatches
        key={`current-${selectedCompanyId}-${month}`}
        companyId={selectedCompanyId}
        month={month}
      />
      <BatchHistory
        key={`history-${selectedCompanyId}-${month}`}
        companyId={selectedCompanyId}
        month={month}
      />
    </AttendancePage>
  )
}
