import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { useEffect, useState } from "react"

import {
  AttendanceHolidaysService,
  type AttendanceMonthPublic,
  AttendanceMonthsService,
  AttendanceSchedulePlansService,
  AttendanceShiftsService,
  DepartmentsService,
  EmployeesService,
  PositionsService,
  type SchedulePlanPreview,
  type SchedulePlanPublic,
} from "@/client"
import { BatchFillDialog } from "@/components/Attendance/schedule/BatchFillDialog"
import { CopyMonthDialog } from "@/components/Attendance/schedule/CopyMonthDialog"
import { DaySheetDialog } from "@/components/Attendance/schedule/DaySheetDialog"
import { EmployeeCalendarView } from "@/components/Attendance/schedule/EmployeeCalendarView"
import { PlanCalendar } from "@/components/Attendance/schedule/PlanCalendar"
import { PlanEditorDialog } from "@/components/Attendance/schedule/PlanEditorDialog"
import { PlanListPanel } from "@/components/Attendance/schedule/PlanListPanel"
import {
  ConfirmDialog,
  PreviewDialog,
} from "@/components/Attendance/schedule/PreviewDialog"
import {
  nextMonth as nextTargetMonth,
  scopeLabel,
} from "@/components/Attendance/schedule/plan-utils"
import {
  invalidatePlanQueries,
  planDepartmentsQueryKey,
  planEmployeesQueryKey,
  planHolidaysQueryKey,
  planListQueryKey,
  planMonthStateQueryKey,
  planPositionsQueryKey,
  planShiftsQueryKey,
} from "@/components/Attendance/schedule/queries"
import { SyncPersonnelDialog } from "@/components/Attendance/schedule/SyncPersonnelDialog"
import { AttendancePage } from "@/components/Attendance/shared/AttendancePage"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useAttendanceMonth } from "@/contexts/AttendanceMonthContext"
import { useCompany } from "@/contexts/CompanyContext"
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorMessage } from "@/lib/api-error"
import { PLAN_STATUS_LABELS } from "@/lib/enums"

export const Route = createFileRoute("/_layout/attendance/schedule")({
  component: SchedulePage,
  head: () => ({
    meta: [{ title: "排班工作台 - AnySys" }],
  }),
})

const PAGE_DESCRIPTION =
  "按方案视图看一张方案怎么排，或按合并视图看每天谁上班。方案保存即展开为员工日明细；人工例外永远优先。"

type ConfirmAction = "archive" | "unarchive" | "delete"

function SchedulePage() {
  const { selectedCompanyId, isLoading } = useCompany()

  if (isLoading) {
    return (
      <AttendancePage title="排班工作台" description={PAGE_DESCRIPTION}>
        <LoadingState rows={4} />
      </AttendancePage>
    )
  }

  if (!selectedCompanyId) {
    return (
      <AttendancePage title="排班工作台" description={PAGE_DESCRIPTION}>
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
    <ScheduleWorkspace key={selectedCompanyId} companyId={selectedCompanyId} />
  )
}

function ScheduleWorkspace({ companyId }: { companyId: string }) {
  const queryClient = useQueryClient()
  const { selectedCompany } = useCompany()
  const { month, setMonth } = useAttendanceMonth()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const year = Number(month.slice(0, 4))

  const [selectedPlanId, setSelectedPlanId] = useState<string>("all")
  const [selectedDay, setSelectedDay] = useState<number | null>(null)
  const [view, setView] = useState<"plan" | "employee">("plan")
  const [editorOpen, setEditorOpen] = useState(false)
  const [editorDay, setEditorDay] = useState(1)
  const [editingPlan, setEditingPlan] = useState<SchedulePlanPublic | null>(
    null,
  )
  const [daySheetOpen, setDaySheetOpen] = useState(false)
  const [copyOpen, setCopyOpen] = useState(false)
  const [batchOpen, setBatchOpen] = useState(false)
  const [syncOpen, setSyncOpen] = useState(false)
  const [confirmAction, setConfirmAction] = useState<ConfirmAction | null>(null)
  const [expandPreview, setExpandPreview] =
    useState<SchedulePlanPreview | null>(null)

  const plansQuery = useQuery({
    queryKey: planListQueryKey(companyId, month),
    queryFn: async () => {
      const response = await AttendanceSchedulePlansService.readSchedulePlans({
        query: { company_id: companyId, month, limit: 500 },
      })
      return response.data
    },
  })
  const employeesQuery = useQuery({
    queryKey: planEmployeesQueryKey(companyId),
    queryFn: async () => {
      const response = await EmployeesService.readEmployees({
        query: { company_id: companyId, limit: 500 },
      })
      return response.data
    },
  })
  const departmentsQuery = useQuery({
    queryKey: planDepartmentsQueryKey(companyId),
    queryFn: async () => {
      const response = await DepartmentsService.readDepartments({
        query: { company_id: companyId, limit: 500 },
      })
      return response.data
    },
  })
  const positionsQuery = useQuery({
    queryKey: planPositionsQueryKey(companyId),
    queryFn: async () => {
      const response = await PositionsService.readPositions({
        query: { company_id: companyId, limit: 500 },
      })
      return response.data
    },
  })
  const shiftsQuery = useQuery({
    queryKey: planShiftsQueryKey(companyId),
    queryFn: async () => {
      const response = await AttendanceShiftsService.readShifts({
        query: { company_id: companyId, is_active: true, limit: 500 },
      })
      return response.data
    },
  })
  const holidaysQuery = useQuery({
    queryKey: planHolidaysQueryKey(companyId, year),
    queryFn: async () => {
      const response = await AttendanceHolidaysService.readHolidays({
        query: { company_id: companyId, year, limit: 500 },
      })
      return response.data
    },
  })
  const monthsQuery = useQuery({
    queryKey: planMonthStateQueryKey(companyId),
    queryFn: async () => {
      const response = await AttendanceMonthsService.readMonths({
        query: { company_id: companyId },
      })
      return response.data
    },
  })

  useEffect(() => {
    setSelectedPlanId("all")
    setSelectedDay(null)
  }, [])

  const plans = plansQuery.data?.data ?? []
  const employees = employeesQuery.data?.data ?? []
  const departments = departmentsQuery.data?.data ?? []
  const positions = positionsQuery.data?.data ?? []
  const shifts = shiftsQuery.data?.data ?? []
  const holidays = holidaysQuery.data?.data ?? []
  const months: AttendanceMonthPublic[] = monthsQuery.data?.data ?? []
  const monthState = months.find((item) => item.month === month) ?? null
  const monthStatus = monthState?.status ?? "draft"
  const editable = monthStatus === "draft" || monthStatus === "calculated"

  const selectedPlan =
    selectedPlanId === "all"
      ? null
      : (plans.find((plan) => plan.id === selectedPlanId) ?? null)
  const enabledPlans = plans.filter((plan) => plan.status === "enabled")

  const loading =
    plansQuery.isLoading ||
    employeesQuery.isLoading ||
    departmentsQuery.isLoading ||
    positionsQuery.isLoading ||
    shiftsQuery.isLoading ||
    holidaysQuery.isLoading ||
    monthsQuery.isLoading
  const queryError =
    plansQuery.error ??
    employeesQuery.error ??
    departmentsQuery.error ??
    positionsQuery.error ??
    shiftsQuery.error ??
    holidaysQuery.error ??
    monthsQuery.error

  const retryAll = () => {
    void plansQuery.refetch()
    void employeesQuery.refetch()
    void departmentsQuery.refetch()
    void positionsQuery.refetch()
    void shiftsQuery.refetch()
    void holidaysQuery.refetch()
    void monthsQuery.refetch()
  }

  const expandMutation = useMutation({
    mutationFn: async (planId: string) =>
      (
        await AttendanceSchedulePlansService.expandSchedulePlan({
          path: { plan_id: planId },
        })
      ).data,
    onSuccess: (data) => {
      showSuccessToast(
        `已重新展开：新增 ${data.roster_change.added}、更新 ${data.roster_change.updated}、删除 ${data.roster_change.deleted}`,
      )
      setExpandPreview(null)
      invalidatePlanQueries(queryClient)
    },
    onError: (error) => showErrorToast(getErrorMessage(error)),
  })

  const expandPreviewMutation = useMutation({
    mutationFn: async (planId: string) =>
      (
        await AttendanceSchedulePlansService.expandPreview({
          path: { plan_id: planId },
        })
      ).data,
    onSuccess: setExpandPreview,
    onError: (error) => showErrorToast(getErrorMessage(error)),
  })

  const lifecycleMutation = useMutation({
    mutationFn: async ({
      action,
      planId,
    }: {
      action: ConfirmAction
      planId: string
    }) => {
      if (action === "archive") {
        return (
          await AttendanceSchedulePlansService.archiveSchedulePlan({
            path: { plan_id: planId },
          })
        ).data
      }
      if (action === "unarchive") {
        return (
          await AttendanceSchedulePlansService.unarchiveSchedulePlan({
            path: { plan_id: planId },
          })
        ).data
      }
      await AttendanceSchedulePlansService.deleteSchedulePlan({
        path: { plan_id: planId },
      })
      return null
    },
    onSuccess: (data, variables) => {
      const messages = {
        archive: "排班方案已归档，并已重新展开月度排班",
        unarchive: "排班方案已取消归档，并已重新展开月度排班",
        delete: "排班方案已删除",
      }
      showSuccessToast(messages[variables.action])
      if (variables.action === "delete" || variables.action === "archive") {
        setSelectedPlanId("all")
      }
      void data
      setConfirmAction(null)
      invalidatePlanQueries(queryClient)
    },
    onError: (error) => showErrorToast(getErrorMessage(error)),
  })

  const openCreate = () => {
    setEditingPlan(null)
    setEditorDay(1)
    setEditorOpen(true)
  }

  const openEdit = () => {
    if (!selectedPlan) return
    setEditingPlan(selectedPlan)
    setEditorDay(selectedDay ?? 1)
    setEditorOpen(true)
  }

  const onSelectDay = (day: number) => {
    setSelectedDay(day)
    if (!selectedPlan) {
      setDaySheetOpen(true)
    } else if (editable && selectedPlan.status === "enabled") {
      setEditingPlan(selectedPlan)
      setEditorDay(day)
      setEditorOpen(true)
    } else {
      setDaySheetOpen(true)
    }
  }

  return (
    <AttendancePage
      title="排班工作台"
      description={`当前公司：${
        selectedCompany?.company_name ?? "—"
      }。${PAGE_DESCRIPTION}`}
      actions={
        view === "plan" ? (
          <Button
            type="button"
            size="sm"
            disabled={!editable}
            title={
              editable ? undefined : "本月已确认或锁定，请先取消确认或解锁"
            }
            onClick={openCreate}
          >
            新建方案
          </Button>
        ) : null
      }
    >
      {monthStatus === "locked" && (
        <div
          role="status"
          data-testid="month-locked-banner"
          className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          本月已锁定，排班只读。解锁需在「考勤结果」填写理由并重新计算。
        </div>
      )}
      {monthStatus === "confirmed" && (
        <div
          role="status"
          data-testid="month-confirmed-banner"
          className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100"
        >
          本月已确认，排班只读。修改前请先在「考勤结果」取消确认。
        </div>
      )}
      {monthState?.is_stale && monthStatus !== "locked" && (
        <div
          role="status"
          data-testid="month-stale-banner"
          className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100"
        >
          当前结果已过期：排班数据在本月计算后发生变化，重算后生效。
        </div>
      )}

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex w-fit gap-1 rounded-md border p-1">
          <Button
            type="button"
            size="sm"
            variant={view === "plan" ? "default" : "ghost"}
            data-testid="view-plan"
            onClick={() => setView("plan")}
          >
            方案视图
          </Button>
          <Button
            type="button"
            size="sm"
            variant={view === "employee" ? "default" : "ghost"}
            data-testid="view-employee"
            onClick={() => setView("employee")}
          >
            员工明细
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            data-testid="open-batch-fill"
            disabled={!editable}
            onClick={() => setBatchOpen(true)}
          >
            批量填充
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            data-testid="open-sync-personnel"
            disabled={!editable}
            onClick={() => setSyncOpen(true)}
          >
            同步人员
          </Button>
        </div>
      </div>

      {loading ? (
        <LoadingState rows={5} />
      ) : queryError ? (
        <ErrorState message={getErrorMessage(queryError)} onRetry={retryAll} />
      ) : view === "employee" ? (
        <EmployeeCalendarView
          companyId={companyId}
          month={month}
          editable={editable}
          employees={employees}
          shifts={shifts}
        />
      ) : plans.length === 0 ? (
        <EmptyState
          title={`${month} 还没有排班方案`}
          message="方案按「公司 + 月份 + 范围」创建，保存时展开为员工日明细。可以先新建一张全公司方案。"
          action={
            <Button type="button" disabled={!editable} onClick={openCreate}>
              新建方案
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
          <PlanListPanel
            plans={plans}
            employees={employees}
            departments={departments}
            positions={positions}
            selectedPlanId={selectedPlanId}
            onSelect={(planId) => {
              setSelectedPlanId(planId)
              setSelectedDay(null)
            }}
            onCreate={openCreate}
            editable={editable}
          />

          <div className="space-y-3">
            <div className="flex flex-col gap-2 rounded-lg border px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium">
                  {selectedPlan
                    ? selectedPlan.plan_name
                    : "全部方案 · 合并视图"}
                </span>
                {selectedPlan && (
                  <>
                    <Badge
                      variant={
                        selectedPlan.status === "enabled"
                          ? "default"
                          : "secondary"
                      }
                    >
                      {PLAN_STATUS_LABELS[selectedPlan.status]}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {scopeLabel(selectedPlan, departments, positions)}
                    </span>
                  </>
                )}
              </div>
              {selectedPlan && (
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={!editable || selectedPlan.status === "archived"}
                    onClick={openEdit}
                  >
                    编辑
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={!editable || selectedPlan.status === "archived"}
                    onClick={() =>
                      expandPreviewMutation.mutate(selectedPlan.id)
                    }
                  >
                    重新展开
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={!editable}
                    onClick={() => setCopyOpen(true)}
                  >
                    复制下月
                  </Button>
                  {selectedPlan.status === "enabled" ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={!editable}
                      onClick={() => setConfirmAction("archive")}
                    >
                      归档
                    </Button>
                  ) : (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={!editable}
                      onClick={() => setConfirmAction("unarchive")}
                    >
                      取消归档
                    </Button>
                  )}
                  <Button
                    type="button"
                    size="sm"
                    variant="destructive"
                    disabled={!editable}
                    onClick={() => setConfirmAction("delete")}
                  >
                    删除
                  </Button>
                </div>
              )}
            </div>

            <PlanCalendar
              month={month}
              plans={enabledPlans}
              employees={employees}
              holidays={holidays}
              selectedPlan={selectedPlan}
              selectedDay={selectedDay}
              onSelectDay={onSelectDay}
            />
            <div className="rounded-lg border px-3 py-2 text-xs text-muted-foreground">
              {selectedPlan
                ? "点击日期可编辑该方案的当天班次；保存后整月重新展开。"
                : "合并视图按「员工 > 岗位 > 部门 > 全公司」解析；点击日期查看「这天谁上班」。"}
            </div>
          </div>
        </div>
      )}

      <PlanEditorDialog
        open={editorOpen}
        companyId={companyId}
        month={month}
        plan={editingPlan}
        initialDay={editorDay}
        departments={departments}
        positions={positions}
        employees={employees}
        shifts={shifts}
        onClose={() => setEditorOpen(false)}
        onSaved={() => {
          setEditorOpen(false)
          setEditingPlan(null)
        }}
      />

      <DaySheetDialog
        open={daySheetOpen}
        companyId={companyId}
        month={month}
        day={selectedDay}
        onClose={() => setDaySheetOpen(false)}
      />

      <BatchFillDialog
        open={batchOpen}
        companyId={companyId}
        month={month}
        employees={employees}
        departments={departments}
        shifts={shifts}
        onClose={() => setBatchOpen(false)}
        onApplied={() => {
          setBatchOpen(false)
          invalidatePlanQueries(queryClient)
        }}
      />

      <SyncPersonnelDialog
        open={syncOpen}
        companyId={companyId}
        month={month}
        editable={editable}
        onClose={() => setSyncOpen(false)}
        onSynced={() => {
          setSyncOpen(false)
          invalidatePlanQueries(queryClient)
        }}
      />

      <CopyMonthDialog
        open={copyOpen}
        month={month}
        plan={selectedPlan}
        onClose={() => setCopyOpen(false)}
        onCopied={() => {
          setCopyOpen(false)
          setMonth(nextTargetMonth(month))
        }}
      />

      {expandPreview && selectedPlan && (
        <PreviewDialog
          open
          title="重新展开预览"
          description="整月重新解析方案优先级；人工例外保持不变。"
          data={expandPreview}
          busy={expandMutation.isPending}
          confirmLabel="确认重新展开"
          onClose={() => setExpandPreview(null)}
          onConfirm={() => expandMutation.mutate(selectedPlan.id)}
        />
      )}

      <ConfirmDialog
        open={confirmAction !== null}
        title={
          confirmAction === "delete"
            ? "删除排班方案"
            : confirmAction === "archive"
              ? "归档排班方案"
              : "取消归档"
        }
        description={
          confirmAction === "delete"
            ? "删除是例外路径，仅当没有排班明细引用该方案时允许；正常退出请使用归档。"
            : confirmAction === "archive"
              ? "归档后整月重新展开；方案排班明细会被移除，人工例外保持不变。"
              : "取消归档前会校验同范围冲突与班次是否启用，然后整月重新展开。"
        }
        confirmLabel={
          confirmAction === "delete"
            ? "确认删除"
            : confirmAction === "archive"
              ? "确认归档"
              : "确认取消归档"
        }
        destructive={confirmAction === "delete"}
        busy={lifecycleMutation.isPending}
        onClose={() => setConfirmAction(null)}
        onConfirm={() => {
          if (!selectedPlan || !confirmAction) return
          lifecycleMutation.mutate({
            action: confirmAction,
            planId: selectedPlan.id,
          })
        }}
      />
    </AttendancePage>
  )
}
