import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Plus, Search } from "lucide-react"
import { useEffect, useState } from "react"

import {
  AttendanceShiftsService,
  type ErrorDetail,
  type ShiftPublic,
} from "@/client"
import { AttendancePage } from "@/components/Attendance/shared/AttendancePage"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { DeleteShiftDialog } from "@/components/Attendance/shifts/DeleteShiftDialog"
import { invalidateShiftQueries } from "@/components/Attendance/shifts/queries"
import { ReferenceBlockedDialog } from "@/components/Attendance/shifts/ReferenceBlockedDialog"
import { ShiftForm } from "@/components/Attendance/shifts/ShiftForm"
import { ShiftTable } from "@/components/Attendance/shifts/ShiftTable"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useCompany } from "@/contexts/CompanyContext"
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorDetail, getErrorMessage } from "@/lib/api-error"
import {
  type AttendanceShiftStatusFilter,
  SHIFT_STATUS_FILTER_OPTIONS,
} from "@/lib/enums"

export const Route = createFileRoute("/_layout/attendance/shifts")({
  component: ShiftsPage,
  head: () => ({
    meta: [{ title: "班次 - AnySys" }],
  }),
})

const PAGE_DESCRIPTION =
  "班次是公司级可复用模板，定义上下班时间、跨天与休息扣减；编码在公司内唯一且创建后不可修改。"

function ShiftsPage() {
  const { selectedCompanyId, isLoading } = useCompany()

  if (isLoading) {
    return (
      <AttendancePage title="班次" description={PAGE_DESCRIPTION}>
        <LoadingState rows={4} />
      </AttendancePage>
    )
  }

  if (!selectedCompanyId) {
    return (
      <AttendancePage title="班次" description={PAGE_DESCRIPTION}>
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

  // Keying on the company resets filters, dialogs, and the drawer when the
  // global switcher changes.
  return (
    <ShiftWorkspace key={selectedCompanyId} companyId={selectedCompanyId} />
  )
}

function ShiftWorkspace({ companyId }: { companyId: string }) {
  const { selectedCompany } = useCompany()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [keyword, setKeyword] = useState("")
  const [debouncedKeyword, setDebouncedKeyword] = useState("")
  const [status, setStatus] = useState<AttendanceShiftStatusFilter>("all")
  const [formOpen, setFormOpen] = useState(false)
  const [editingShift, setEditingShift] = useState<ShiftPublic | null>(null)
  const [deletingShift, setDeletingShift] = useState<ShiftPublic | null>(null)
  const [blocked, setBlocked] = useState<ErrorDetail | null>(null)

  useEffect(() => {
    const timer = window.setTimeout(
      () => setDebouncedKeyword(keyword.trim()),
      300,
    )
    return () => window.clearTimeout(timer)
  }, [keyword])

  const shiftsQuery = useQuery({
    queryKey: [
      "attendance",
      "shifts",
      "list",
      companyId,
      { keyword: debouncedKeyword, status },
    ],
    queryFn: async () => {
      const response = await AttendanceShiftsService.readShifts({
        query: {
          company_id: companyId,
          skip: 0,
          limit: 500,
          keyword: debouncedKeyword || undefined,
          is_active: status === "all" ? undefined : status === "active",
        },
      })
      return response.data
    },
  })

  const toggleMutation = useMutation({
    mutationFn: async ({
      shiftId,
      isActive,
    }: {
      shiftId: string
      isActive: boolean
    }) =>
      AttendanceShiftsService.updateShift({
        path: { shift_id: shiftId },
        body: { is_active: isActive },
      }),
    onSuccess: (_data, variables) => {
      showSuccessToast(variables.isActive ? "班次已启用" : "班次已停用")
    },
    onError: (error) => {
      const detail = getErrorDetail(error)
      if (detail?.code === "deactivate_blocked") {
        setBlocked(detail)
        return
      }
      showErrorToast(getErrorMessage(error))
    },
    onSettled: () => {
      invalidateShiftQueries(queryClient)
    },
  })

  const shifts = shiftsQuery.data?.data ?? []
  const count = shiftsQuery.data?.count ?? 0
  const hasFilters = debouncedKeyword !== "" || status !== "all"
  const pendingShiftId = toggleMutation.isPending
    ? (toggleMutation.variables?.shiftId ?? null)
    : null

  const openCreate = () => {
    setEditingShift(null)
    setFormOpen(true)
  }

  const openEdit = (shift: ShiftPublic) => {
    setEditingShift(shift)
    setFormOpen(true)
  }

  return (
    <AttendancePage
      title="班次"
      description={`当前公司：${
        selectedCompany?.company_name ?? "—"
      }。${PAGE_DESCRIPTION}`}
      actions={
        <Button className="shrink-0" onClick={openCreate}>
          <Plus className="mr-2 size-4" />
          新增班次
        </Button>
      }
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="relative lg:w-72">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="搜索班次名称或编码"
            aria-label="搜索班次"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
          />
        </div>
        <Select
          value={status}
          onValueChange={(value) =>
            setStatus(value as AttendanceShiftStatusFilter)
          }
        >
          <SelectTrigger className="w-full lg:w-[140px]" aria-label="状态筛选">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SHIFT_STATUS_FILTER_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {!shiftsQuery.isLoading && !shiftsQuery.isError && (
          <p className="text-sm text-muted-foreground lg:ml-auto">
            共 <span className="font-medium text-foreground">{count}</span>{" "}
            个班次
          </p>
        )}
      </div>

      {shiftsQuery.isLoading ? (
        <LoadingState />
      ) : shiftsQuery.isError ? (
        <ErrorState
          message={getErrorMessage(shiftsQuery.error)}
          onRetry={() => {
            void shiftsQuery.refetch()
          }}
        />
      ) : shifts.length === 0 ? (
        <EmptyState
          title={hasFilters ? "没有匹配的班次" : "还没有班次"}
          message={
            hasFilters
              ? "尝试调整搜索关键词或状态筛选。"
              : "创建第一个班次后，排班方案就可以复用它。"
          }
          action={
            hasFilters ? (
              <Button
                variant="outline"
                onClick={() => {
                  setKeyword("")
                  setStatus("all")
                }}
              >
                清除筛选
              </Button>
            ) : (
              <Button onClick={openCreate}>
                <Plus className="mr-2 size-4" />
                新增班次
              </Button>
            )
          }
        />
      ) : (
        <ShiftTable
          shifts={shifts}
          pendingShiftId={pendingShiftId}
          onEdit={openEdit}
          onDelete={setDeletingShift}
          onToggleActive={(shift, isActive) => {
            toggleMutation.mutate({ shiftId: shift.id, isActive })
          }}
        />
      )}

      <ShiftForm
        open={formOpen}
        onOpenChange={setFormOpen}
        companyId={companyId}
        shift={editingShift}
      />
      <DeleteShiftDialog
        shift={deletingShift}
        onOpenChange={(open) => {
          if (!open) setDeletingShift(null)
        }}
        onDeleted={() => {
          setDeletingShift(null)
        }}
      />
      <ReferenceBlockedDialog
        detail={blocked}
        action="deactivate"
        onDismiss={() => setBlocked(null)}
      />
    </AttendancePage>
  )
}
