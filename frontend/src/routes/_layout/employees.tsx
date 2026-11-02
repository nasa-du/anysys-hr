import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Plus } from "lucide-react"
import { useEffect, useState } from "react"

import {
  CostCentersService,
  DepartmentsService,
  type EmployeePublic,
  EmployeesService,
  PositionsService,
} from "@/client"
import { DepartmentTree } from "@/components/BasicManagement/departments/DepartmentTree"
import { EmployeeDetail } from "@/components/BasicManagement/employees/EmployeeDetail"
import {
  ALL_COST_CENTERS,
  ALL_POSITIONS,
  EmployeeFilters,
  UNASSIGNED_COST_CENTER,
} from "@/components/BasicManagement/employees/EmployeeFilters"
import { EmployeeForm } from "@/components/BasicManagement/employees/EmployeeForm"
import { EmployeeTable } from "@/components/BasicManagement/employees/EmployeeTable"
import { LeaveDialog } from "@/components/BasicManagement/employees/LeaveDialog"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/BasicManagement/shared/StateViews"
import { Button } from "@/components/ui/button"
import { useCompany } from "@/contexts/CompanyContext"
import { getErrorMessage } from "@/lib/api-error"
import type { EmployeeStatusFilter } from "@/lib/enums"

const PAGE_SIZE = 50

interface EmployeeSearch {
  unassigned_cost_org?: boolean
}

export const Route = createFileRoute("/_layout/employees")({
  component: EmployeesPage,
  validateSearch: (search: Record<string, unknown>): EmployeeSearch => ({
    unassigned_cost_org:
      search.unassigned_cost_org === true ||
      search.unassigned_cost_org === "true"
        ? true
        : undefined,
  }),
  head: () => ({
    meta: [
      {
        title: "员工 - AnySys",
      },
    ],
  }),
})

function EmployeesPage() {
  const { selectedCompanyId, isLoading } = useCompany()
  const search = Route.useSearch()

  if (isLoading) {
    return <LoadingState rows={4} />
  }

  if (!selectedCompanyId) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">员工</h1>
          <p className="text-muted-foreground">
            维护当前公司的员工档案；公司归属由顶部公司切换器决定。
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

  // Keying on the company resets filters, drawers, and pagination when the
  // global switcher changes.
  return (
    <EmployeeWorkspace
      key={selectedCompanyId}
      companyId={selectedCompanyId}
      initialUnassigned={search.unassigned_cost_org === true}
    />
  )
}

interface EmployeeWorkspaceProps {
  companyId: string
  initialUnassigned: boolean
}

function EmployeeWorkspace({
  companyId,
  initialUnassigned,
}: EmployeeWorkspaceProps) {
  const { selectedCompany } = useCompany()
  const [deptId, setDeptId] = useState<string | null>(null)
  const [keyword, setKeyword] = useState("")
  const [debouncedKeyword, setDebouncedKeyword] = useState("")
  const [status, setStatus] = useState<EmployeeStatusFilter>("current")
  const [positionId, setPositionId] = useState(ALL_POSITIONS)
  const [costCenterValue, setCostCenterValue] = useState(
    initialUnassigned ? UNASSIGNED_COST_CENTER : ALL_COST_CENTERS,
  )
  const [page, setPage] = useState(0)
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string | null>(
    null,
  )
  const [formOpen, setFormOpen] = useState(false)
  const [formCorrection, setFormCorrection] = useState(false)
  const [editingEmployee, setEditingEmployee] = useState<EmployeePublic | null>(
    null,
  )
  const [leavingEmployee, setLeavingEmployee] = useState<EmployeePublic | null>(
    null,
  )

  useEffect(() => {
    const timer = window.setTimeout(
      () => setDebouncedKeyword(keyword.trim()),
      300,
    )
    return () => window.clearTimeout(timer)
  }, [keyword])

  const departmentsQuery = useQuery({
    queryKey: ["basic", "departments", "tree", companyId, null],
    queryFn: async () => {
      const response = await DepartmentsService.readDepartmentTree({
        query: { company_id: companyId },
      })
      return response.data
    },
  })

  const positionsQuery = useQuery({
    queryKey: ["basic", "positions", "list", companyId, { limit: 500 }],
    queryFn: async () => {
      const response = await PositionsService.readPositions({
        query: { company_id: companyId, skip: 0, limit: 500 },
      })
      return response.data.data
    },
  })

  const costCentersQuery = useQuery({
    queryKey: ["basic", "cost-centers", "list", companyId, { limit: 500 }],
    queryFn: async () => {
      const response = await CostCentersService.readCostCenters({
        query: { company_id: companyId, skip: 0, limit: 500 },
      })
      return response.data.data
    },
  })

  const statuses =
    status === "current"
      ? undefined
      : status === "all"
        ? (["active", "probation", "resigned"] as const)
        : ([status] as const)

  const employeesQuery = useQuery({
    queryKey: [
      "basic",
      "employees",
      "list",
      companyId,
      {
        deptId,
        keyword: debouncedKeyword,
        status,
        positionId,
        costCenterValue,
        page,
      },
    ],
    queryFn: async () => {
      const response = await EmployeesService.readEmployees({
        query: {
          company_id: companyId,
          dept_id: deptId ?? undefined,
          position_id: positionId === ALL_POSITIONS ? undefined : positionId,
          cost_org_id:
            costCenterValue === ALL_COST_CENTERS ||
            costCenterValue === UNASSIGNED_COST_CENTER
              ? undefined
              : costCenterValue,
          unassigned_cost_org:
            costCenterValue === UNASSIGNED_COST_CENTER ? true : undefined,
          status: statuses ? [...statuses] : undefined,
          keyword: debouncedKeyword || undefined,
          skip: page * PAGE_SIZE,
          limit: PAGE_SIZE,
        },
      })
      return response.data
    },
  })

  const detailQuery = useQuery({
    queryKey: ["basic", "employees", "detail", selectedEmployeeId],
    queryFn: async () => {
      if (!selectedEmployeeId) throw new Error("未选择员工")
      const response = await EmployeesService.readEmployee({
        path: { employee_id: selectedEmployeeId },
      })
      return response.data
    },
    enabled: selectedEmployeeId !== null,
  })

  const departments = departmentsQuery.data?.data ?? []
  const positions = positionsQuery.data ?? []
  const costCenters = costCentersQuery.data ?? []
  const employees = employeesQuery.data?.data ?? []
  const count = employeesQuery.data?.count ?? 0
  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE))
  const hasFilters =
    deptId !== null ||
    debouncedKeyword !== "" ||
    status !== "current" ||
    positionId !== ALL_POSITIONS ||
    costCenterValue !== ALL_COST_CENTERS

  const openCreate = () => {
    setEditingEmployee(null)
    setFormCorrection(false)
    setFormOpen(true)
  }

  const openEdit = (employee: EmployeePublic) => {
    setEditingEmployee(employee)
    setFormCorrection(employee.status === "resigned")
    setFormOpen(true)
  }

  const openLeave = (employee: EmployeePublic) => {
    setLeavingEmployee(employee)
  }

  const selectDepartment = (departmentId: string | null) => {
    setDeptId(departmentId)
    setPage(0)
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">员工</h1>
          <p className="text-muted-foreground">
            当前公司：{selectedCompany?.company_name ?? "—"}
            。列表默认显示在职与试用期；离职员工保留档案但不物理删除。
          </p>
        </div>
        <Button className="shrink-0" onClick={openCreate}>
          <Plus className="mr-2 size-4" />
          新增员工
        </Button>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,280px)_1fr]">
        <aside className="rounded-lg border bg-card">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <h2 className="text-sm font-medium">按部门筛选</h2>
            <span className="text-xs text-muted-foreground">
              {selectedCompany?.company_name}
            </span>
          </div>
          <div className="space-y-2 p-3">
            <button
              type="button"
              onClick={() => selectDepartment(null)}
              className={`w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted ${
                deptId === null ? "bg-muted font-medium" : ""
              }`}
            >
              全部部门
            </button>
            {departmentsQuery.isLoading ? (
              <LoadingState rows={3} />
            ) : departmentsQuery.isError ? (
              <ErrorState
                message={getErrorMessage(departmentsQuery.error)}
                onRetry={() => {
                  void departmentsQuery.refetch()
                }}
              />
            ) : departments.length === 0 ? (
              <p className="px-2 py-3 text-sm text-muted-foreground">
                还没有部门。请先在「部门」页面维护部门树。
              </p>
            ) : (
              <DepartmentTree
                departments={departments}
                selectedId={deptId}
                onSelect={selectDepartment}
              />
            )}
            <p className="border-t px-2 pt-2 text-xs text-muted-foreground">
              部门筛选包含全部下级部门。
            </p>
          </div>
        </aside>

        <section className="min-w-0 space-y-4">
          <EmployeeFilters
            keyword={keyword}
            onKeywordChange={(value) => {
              setKeyword(value)
              setPage(0)
            }}
            status={status}
            onStatusChange={(value) => {
              setStatus(value)
              setPage(0)
            }}
            positionId={positionId}
            onPositionIdChange={(value) => {
              setPositionId(value)
              setPage(0)
            }}
            positions={positions}
            costCenterValue={costCenterValue}
            onCostCenterChange={(value) => {
              setCostCenterValue(value)
              setPage(0)
            }}
            costCenters={costCenters}
          />

          {costCenterValue === UNASSIGNED_COST_CENTER && (
            <div
              className="rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground"
              data-testid="unassigned-banner"
            >
              当前仅显示成本中心为「未分配」的员工。
            </div>
          )}

          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              共 <span className="font-medium text-foreground">{count}</span>{" "}
              名员工
            </p>
          </div>

          {employeesQuery.isLoading ? (
            <LoadingState />
          ) : employeesQuery.isError ? (
            <ErrorState
              message={getErrorMessage(employeesQuery.error)}
              onRetry={() => {
                void employeesQuery.refetch()
              }}
            />
          ) : employees.length === 0 ? (
            <EmptyState
              title={hasFilters ? "没有匹配的员工" : "还没有员工"}
              message={
                hasFilters
                  ? "尝试调整部门、状态、岗位、成本中心或搜索关键词。"
                  : "新增第一位员工后，就可以按部门、状态和成本中心筛选。"
              }
              action={
                hasFilters ? (
                  <Button
                    variant="outline"
                    onClick={() => {
                      selectDepartment(null)
                      setKeyword("")
                      setStatus("current")
                      setPositionId(ALL_POSITIONS)
                      setCostCenterValue(ALL_COST_CENTERS)
                    }}
                  >
                    清除筛选
                  </Button>
                ) : (
                  <Button onClick={openCreate}>
                    <Plus className="mr-2 size-4" />
                    新增员工
                  </Button>
                )
              }
            />
          ) : (
            <EmployeeTable
              employees={employees}
              onOpen={(employee) => setSelectedEmployeeId(employee.id)}
              onEdit={openEdit}
              onLeave={openLeave}
            />
          )}

          {count > PAGE_SIZE && (
            <div className="flex items-center justify-end gap-3">
              <span className="text-sm text-muted-foreground">
                第 {page + 1} / {totalPages} 页
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((value) => Math.max(0, value - 1))}
              >
                上一页
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page + 1 >= totalPages}
                onClick={() => setPage((value) => value + 1)}
              >
                下一页
              </Button>
            </div>
          )}
        </section>
      </div>

      <EmployeeDetail
        employee={detailQuery.data ?? null}
        open={selectedEmployeeId !== null}
        isLoading={detailQuery.isLoading}
        errorMessage={
          detailQuery.isError ? getErrorMessage(detailQuery.error) : undefined
        }
        onRetry={() => {
          void detailQuery.refetch()
        }}
        onOpenChange={(open) => {
          if (!open) setSelectedEmployeeId(null)
        }}
        onEdit={openEdit}
        onLeave={openLeave}
      />

      <EmployeeForm
        open={formOpen}
        onOpenChange={(open) => {
          setFormOpen(open)
          if (!open) {
            setEditingEmployee(null)
            setFormCorrection(false)
          }
        }}
        companyId={companyId}
        departments={departments}
        positions={positions}
        costCenters={costCenters}
        employee={editingEmployee}
        correction={formCorrection}
      />

      <LeaveDialog
        employee={leavingEmployee}
        onOpenChange={(open) => {
          if (!open) setLeavingEmployee(null)
        }}
      />
    </div>
  )
}
