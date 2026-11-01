import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Plus } from "lucide-react"
import { useEffect, useState } from "react"

import type { DepartmentPublic } from "@/client"
import { DepartmentsService } from "@/client"
import { DeleteDepartmentDialog } from "@/components/BasicManagement/departments/DeleteDepartmentDialog"
import { DepartmentDetail } from "@/components/BasicManagement/departments/DepartmentDetail"
import { DepartmentForm } from "@/components/BasicManagement/departments/DepartmentForm"
import { DepartmentTree } from "@/components/BasicManagement/departments/DepartmentTree"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/BasicManagement/shared/StateViews"
import { findTreeNode } from "@/components/BasicManagement/shared/tree-utils"
import { Button } from "@/components/ui/button"
import { useCompany } from "@/contexts/CompanyContext"
import { getErrorMessage } from "@/lib/api-error"

export const Route = createFileRoute("/_layout/departments")({
  component: DepartmentsPage,
  head: () => ({
    meta: [
      {
        title: "部门 - AnySys",
      },
    ],
  }),
})

function DepartmentsPage() {
  const { selectedCompanyId, isLoading } = useCompany()

  if (isLoading) {
    return <LoadingState rows={4} />
  }

  if (!selectedCompanyId) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">部门</h1>
          <p className="text-muted-foreground">
            维护公司内部的部门树；部门归属由顶部公司切换器决定。
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

  // Keying on the company resets every selection and dialog when the global
  // switcher changes, so the detail pane can never show the previous
  // company's department.
  return (
    <DepartmentWorkspace
      key={selectedCompanyId}
      companyId={selectedCompanyId}
    />
  )
}

function DepartmentWorkspace({ companyId }: { companyId: string }) {
  const { selectedCompany } = useCompany()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editingDepartment, setEditingDepartment] =
    useState<DepartmentPublic | null>(null)
  const [defaultParentId, setDefaultParentId] = useState<string | null>(null)
  const [deletingDepartment, setDeletingDepartment] =
    useState<DepartmentPublic | null>(null)

  const treeQuery = useQuery({
    queryKey: ["basic", "departments", "tree", companyId, null],
    queryFn: async () => {
      const response = await DepartmentsService.readDepartmentTree({
        query: { company_id: companyId },
      })
      return response.data
    },
  })

  const treeData = treeQuery.data?.data
  const roots = treeData ?? []

  useEffect(() => {
    if (!treeData || treeData.length === 0 || selectedId !== null) return
    setSelectedId(treeData[0].id)
  }, [selectedId, treeData])

  const detailQuery = useQuery({
    queryKey: ["basic", "departments", "detail", selectedId],
    queryFn: async () => {
      if (!selectedId) throw new Error("未选择部门")
      const response = await DepartmentsService.readDepartment({
        path: { department_id: selectedId },
      })
      return response.data
    },
    enabled: selectedId !== null,
  })

  const selectDepartment = (departmentId: string) => {
    setSelectedId(departmentId)
  }

  const openCreateRoot = () => {
    setEditingDepartment(null)
    setDefaultParentId(null)
    setFormOpen(true)
  }

  const openCreateChild = () => {
    setEditingDepartment(null)
    setDefaultParentId(selectedId)
    setFormOpen(true)
  }

  const openEdit = (department: DepartmentPublic) => {
    setEditingDepartment(department)
    setDefaultParentId(null)
    setFormOpen(true)
  }

  const closeForm = (open: boolean) => {
    setFormOpen(open)
    if (!open) setEditingDepartment(null)
  }

  const selectedNode =
    selectedId !== null ? findTreeNode(roots, selectedId) : null
  const childDepartments = selectedNode?.children ?? []

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">部门</h1>
          <p className="text-muted-foreground">
            当前公司：{selectedCompany?.company_name ?? "—"}
            。部门支持任意层级；编码在公司内唯一且创建后不可修改。
          </p>
        </div>
        <Button className="shrink-0" onClick={openCreateRoot}>
          <Plus className="mr-2 size-4" />
          新增根部门
        </Button>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,320px)_1fr]">
        <aside className="rounded-lg border bg-card">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <h2 className="text-sm font-medium">部门树</h2>
            <span className="text-xs text-muted-foreground">
              {selectedCompany?.company_name}
            </span>
          </div>
          <div className="p-3">
            {treeQuery.isLoading ? (
              <LoadingState rows={4} />
            ) : treeQuery.isError ? (
              <ErrorState
                message={getErrorMessage(treeQuery.error)}
                onRetry={() => {
                  void treeQuery.refetch()
                }}
              />
            ) : roots.length === 0 ? (
              <EmptyState
                title="还没有部门"
                message="创建第一个根部门，就可以继续添加下级部门。"
                action={
                  <Button size="sm" onClick={openCreateRoot}>
                    <Plus className="mr-2 size-4" />
                    新增根部门
                  </Button>
                }
              />
            ) : (
              <DepartmentTree
                departments={roots}
                selectedId={selectedId}
                onSelect={selectDepartment}
              />
            )}
          </div>
        </aside>

        <section className="min-w-0">
          {selectedId === null ? (
            <EmptyState
              title="请选择部门"
              message="在左侧部门树中选择一个部门查看详情。"
            />
          ) : detailQuery.isLoading ? (
            <LoadingState rows={4} />
          ) : detailQuery.isError ? (
            <ErrorState
              message={getErrorMessage(detailQuery.error)}
              onRetry={() => {
                void detailQuery.refetch()
              }}
            />
          ) : detailQuery.data ? (
            <DepartmentDetail
              department={detailQuery.data}
              childDepartments={childDepartments}
              onCreateChild={openCreateChild}
              onEdit={() => openEdit(detailQuery.data)}
              onDelete={() => setDeletingDepartment(detailQuery.data)}
            />
          ) : null}
        </section>
      </div>

      <DepartmentForm
        open={formOpen}
        onOpenChange={closeForm}
        companyId={companyId}
        tree={roots}
        department={editingDepartment}
        defaultParentId={defaultParentId}
      />
      <DeleteDepartmentDialog
        department={deletingDepartment}
        onOpenChange={(open) => {
          if (!open) setDeletingDepartment(null)
        }}
        onDeleted={(departmentId) => {
          if (selectedId === departmentId) setSelectedId(null)
        }}
      />
    </div>
  )
}
