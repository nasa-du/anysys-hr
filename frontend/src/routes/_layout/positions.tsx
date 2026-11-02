import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Plus, Search } from "lucide-react"
import { useEffect, useState } from "react"

import {
  type DepartmentPublic,
  DepartmentsService,
  type PositionPublic,
  PositionsService,
} from "@/client"
import { DeletePositionDialog } from "@/components/BasicManagement/positions/DeletePositionDialog"
import { PositionForm } from "@/components/BasicManagement/positions/PositionForm"
import { PositionTable } from "@/components/BasicManagement/positions/PositionTable"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/BasicManagement/shared/StateViews"
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
import { getErrorMessage } from "@/lib/api-error"

type StatusFilter = "all" | "active" | "inactive"

const ALL_DEPARTMENTS = "__all__"

const STATUS_OPTIONS: Array<{ value: StatusFilter; label: string }> = [
  { value: "all", label: "全部状态" },
  { value: "active", label: "启用" },
  { value: "inactive", label: "停用" },
]

export const Route = createFileRoute("/_layout/positions")({
  component: PositionsPage,
  head: () => ({
    meta: [
      {
        title: "岗位 - AnySys",
      },
    ],
  }),
})

function PositionsPage() {
  const { selectedCompanyId, isLoading } = useCompany()

  if (isLoading) {
    return <LoadingState rows={4} />
  }

  if (!selectedCompanyId) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">岗位</h1>
          <p className="text-muted-foreground">
            维护当前公司的岗位档案；公司归属由顶部公司切换器决定。
          </p>
        </div>
        <EmptyState
          title="尚未选择公司"
          message="请先在「公司」页面创建并启用公司，再从顶部切换器选择公司。"
          action={
            <Button asChild variant="outline">
              <Link to="/companies">前往公司页面</Link>
            </Button>
          }
        />
      </div>
    )
  }

  // Keying on the company resets filters, dialogs, and the drawer when the
  // global switcher changes.
  return (
    <PositionWorkspace key={selectedCompanyId} companyId={selectedCompanyId} />
  )
}

function PositionWorkspace({ companyId }: { companyId: string }) {
  const { selectedCompany } = useCompany()
  const [keyword, setKeyword] = useState("")
  const [debouncedKeyword, setDebouncedKeyword] = useState("")
  const [status, setStatus] = useState<StatusFilter>("all")
  const [departmentId, setDepartmentId] = useState(ALL_DEPARTMENTS)
  const [formOpen, setFormOpen] = useState(false)
  const [editingPosition, setEditingPosition] = useState<PositionPublic | null>(
    null,
  )
  const [deletingPosition, setDeletingPosition] =
    useState<PositionPublic | null>(null)

  useEffect(() => {
    const timer = window.setTimeout(
      () => setDebouncedKeyword(keyword.trim()),
      300,
    )
    return () => window.clearTimeout(timer)
  }, [keyword])

  const departmentsQuery = useQuery({
    queryKey: ["basic", "departments", "list", companyId, { limit: 500 }],
    queryFn: async () => {
      const response = await DepartmentsService.readDepartments({
        query: { company_id: companyId, skip: 0, limit: 500 },
      })
      return response.data.data
    },
  })

  const positionsQuery = useQuery({
    queryKey: [
      "basic",
      "positions",
      "list",
      companyId,
      { keyword: debouncedKeyword, status, departmentId },
    ],
    queryFn: async () => {
      const response = await PositionsService.readPositions({
        query: {
          company_id: companyId,
          skip: 0,
          limit: 500,
          keyword: debouncedKeyword || undefined,
          is_active: status === "all" ? undefined : status === "active",
          dept_id: departmentId === ALL_DEPARTMENTS ? undefined : departmentId,
        },
      })
      return response.data
    },
  })

  const departments: DepartmentPublic[] = departmentsQuery.data ?? []
  const inactiveDepartmentIds = new Set(
    departments
      .filter((department) => !department.is_active)
      .map((department) => department.id),
  )
  const positions = positionsQuery.data?.data ?? []
  const count = positionsQuery.data?.count ?? 0
  const hasFilters =
    debouncedKeyword !== "" ||
    status !== "all" ||
    departmentId !== ALL_DEPARTMENTS

  const openCreate = () => {
    setEditingPosition(null)
    setFormOpen(true)
  }

  const openEdit = (position: PositionPublic) => {
    setEditingPosition(position)
    setFormOpen(true)
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">岗位</h1>
          <p className="text-muted-foreground">
            当前公司：{selectedCompany?.company_name ?? "—"}
            。岗位为公司级可复用档案；编码在公司内唯一且创建后不可修改。
          </p>
        </div>
        <Button className="shrink-0" onClick={openCreate}>
          <Plus className="mr-2 size-4" />
          新增岗位
        </Button>
      </div>

      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="relative lg:w-72">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="搜索岗位名称或编码"
            aria-label="搜索岗位"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
          />
        </div>
        <Select value={departmentId} onValueChange={setDepartmentId}>
          <SelectTrigger
            className="w-full lg:w-[200px]"
            aria-label="默认部门筛选"
            disabled={departmentsQuery.isLoading}
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_DEPARTMENTS}>全部部门</SelectItem>
            {departments.map((department) => (
              <SelectItem key={department.id} value={department.id}>
                {department.dept_name}（{department.dept_code}）
                {!department.is_active ? " 停用" : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={status}
          onValueChange={(value) => setStatus(value as StatusFilter)}
        >
          <SelectTrigger className="w-full lg:w-[140px]" aria-label="状态筛选">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {!positionsQuery.isLoading && !positionsQuery.isError && (
          <p className="text-sm text-muted-foreground lg:ml-auto">
            共 <span className="font-medium text-foreground">{count}</span>{" "}
            个岗位
          </p>
        )}
      </div>

      {departmentsQuery.isError && (
        <div className="flex flex-col gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive sm:flex-row sm:items-center sm:justify-between">
          <span>
            默认部门加载失败：{getErrorMessage(departmentsQuery.error)}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              void departmentsQuery.refetch()
            }}
          >
            重试
          </Button>
        </div>
      )}

      {positionsQuery.isLoading ? (
        <LoadingState />
      ) : positionsQuery.isError ? (
        <ErrorState
          message={getErrorMessage(positionsQuery.error)}
          onRetry={() => {
            void positionsQuery.refetch()
          }}
        />
      ) : positions.length === 0 ? (
        <EmptyState
          title={hasFilters ? "没有匹配的岗位" : "还没有岗位"}
          message={
            hasFilters
              ? "尝试调整搜索关键词、默认部门或状态筛选。"
              : "创建第一个岗位后，员工建档时就可以选择它。"
          }
          action={
            hasFilters ? (
              <Button
                variant="outline"
                onClick={() => {
                  setKeyword("")
                  setStatus("all")
                  setDepartmentId(ALL_DEPARTMENTS)
                }}
              >
                清除筛选
              </Button>
            ) : (
              <Button onClick={openCreate}>
                <Plus className="mr-2 size-4" />
                新增岗位
              </Button>
            )
          }
        />
      ) : (
        <PositionTable
          positions={positions}
          inactiveDepartmentIds={inactiveDepartmentIds}
          onEdit={openEdit}
          onDelete={setDeletingPosition}
        />
      )}

      <PositionForm
        open={formOpen}
        onOpenChange={setFormOpen}
        companyId={companyId}
        position={editingPosition}
        departments={departments}
      />
      <DeletePositionDialog
        position={deletingPosition}
        onOpenChange={(open) => {
          if (!open) setDeletingPosition(null)
        }}
        onDeleted={() => {
          setDeletingPosition(null)
        }}
      />
    </div>
  )
}
