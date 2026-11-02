import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Plus } from "lucide-react"
import { useEffect, useState } from "react"

import type { CostCenterPublic } from "@/client"
import { CostCentersService } from "@/client"
import { CostCenterDetail } from "@/components/BasicManagement/cost-centers/CostCenterDetail"
import { CostCenterForm } from "@/components/BasicManagement/cost-centers/CostCenterForm"
import { CostCenterTree } from "@/components/BasicManagement/cost-centers/CostCenterTree"
import { DeleteCostCenterDialog } from "@/components/BasicManagement/cost-centers/DeleteCostCenterDialog"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/BasicManagement/shared/StateViews"
import { findTreeNode } from "@/components/BasicManagement/shared/tree-utils"
import { Button } from "@/components/ui/button"
import { useCompany } from "@/contexts/CompanyContext"
import { getErrorMessage } from "@/lib/api-error"

export const Route = createFileRoute("/_layout/cost-centers")({
  component: CostCentersPage,
  head: () => ({
    meta: [
      {
        title: "成本中心 - AnySys",
      },
    ],
  }),
})

function CostCentersPage() {
  const { selectedCompanyId, isLoading } = useCompany()

  if (isLoading) {
    return <LoadingState rows={4} />
  }

  if (!selectedCompanyId) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">成本中心</h1>
          <p className="text-muted-foreground">
            维护公司的成本中心树；公司归属由顶部公司切换器决定。
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
  // company's cost center.
  return (
    <CostCenterWorkspace
      key={selectedCompanyId}
      companyId={selectedCompanyId}
    />
  )
}

function CostCenterWorkspace({ companyId }: { companyId: string }) {
  const { selectedCompany } = useCompany()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editingCostCenter, setEditingCostCenter] =
    useState<CostCenterPublic | null>(null)
  const [defaultParentId, setDefaultParentId] = useState<string | null>(null)
  const [deletingCostCenter, setDeletingCostCenter] =
    useState<CostCenterPublic | null>(null)

  const treeQuery = useQuery({
    queryKey: ["basic", "cost-centers", "tree", companyId, null],
    queryFn: async () => {
      const response = await CostCentersService.readCostCenterTree({
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
    queryKey: ["basic", "cost-centers", "detail", selectedId],
    queryFn: async () => {
      if (!selectedId) throw new Error("未选择成本中心")
      const response = await CostCentersService.readCostCenter({
        path: { cost_center_id: selectedId },
      })
      return response.data
    },
    enabled: selectedId !== null,
  })

  const selectCostCenter = (costCenterId: string) => {
    setSelectedId(costCenterId)
  }

  const openCreateRoot = () => {
    setEditingCostCenter(null)
    setDefaultParentId(null)
    setFormOpen(true)
  }

  const openCreateChild = () => {
    setEditingCostCenter(null)
    setDefaultParentId(selectedId)
    setFormOpen(true)
  }

  const openEdit = (costCenter: CostCenterPublic) => {
    setEditingCostCenter(costCenter)
    setDefaultParentId(null)
    setFormOpen(true)
  }

  const closeForm = (open: boolean) => {
    setFormOpen(open)
    if (!open) setEditingCostCenter(null)
  }

  const selectedNode =
    selectedId !== null ? findTreeNode(roots, selectedId) : null
  const childCostCenters = selectedNode?.children ?? []

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">成本中心</h1>
          <p className="text-muted-foreground">
            当前公司：{selectedCompany?.company_name ?? "—"}
            。成本中心支持任意层级；编码在公司内唯一且创建后不可修改。
          </p>
        </div>
        <Button className="shrink-0" onClick={openCreateRoot}>
          <Plus className="mr-2 size-4" />
          新增根成本中心
        </Button>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,320px)_1fr]">
        <aside className="rounded-lg border bg-card">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <h2 className="text-sm font-medium">成本中心树</h2>
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
                title="还没有成本中心"
                message="创建第一个根成本中心，就可以继续添加下级成本中心。"
                action={
                  <Button size="sm" onClick={openCreateRoot}>
                    <Plus className="mr-2 size-4" />
                    新增根成本中心
                  </Button>
                }
              />
            ) : (
              <CostCenterTree
                costCenters={roots}
                selectedId={selectedId}
                onSelect={selectCostCenter}
              />
            )}
          </div>
        </aside>

        <section className="min-w-0">
          {selectedId === null ? (
            <EmptyState
              title="请选择成本中心"
              message="在左侧成本中心树中选择一个成本中心查看详情。"
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
            <CostCenterDetail
              costCenter={detailQuery.data}
              childCostCenters={childCostCenters}
              onCreateChild={openCreateChild}
              onEdit={() => openEdit(detailQuery.data)}
              onDelete={() => setDeletingCostCenter(detailQuery.data)}
            />
          ) : null}
        </section>
      </div>

      <CostCenterForm
        open={formOpen}
        onOpenChange={closeForm}
        companyId={companyId}
        tree={roots}
        costCenter={editingCostCenter}
        defaultParentId={defaultParentId}
      />
      <DeleteCostCenterDialog
        costCenter={deletingCostCenter}
        onOpenChange={(open) => {
          if (!open) setDeletingCostCenter(null)
        }}
        onDeleted={(costCenterId) => {
          if (selectedId === costCenterId) setSelectedId(null)
        }}
      />
    </div>
  )
}
