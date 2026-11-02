import { Pencil, Plus, Trash2 } from "lucide-react"
import type { ReactNode } from "react"

import type { CostCenterPublic, CostCenterTreeNode } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { formatDateTimeShanghai } from "@/lib/datetime"
import { MANAGER_STATUS_LABELS } from "@/lib/enums"

interface CostCenterDetailProps {
  costCenter: CostCenterPublic
  childCostCenters: CostCenterTreeNode[]
  onCreateChild: () => void
  onEdit: () => void
  onDelete: () => void
}

function DetailField({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <div className="space-y-1">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  )
}

export function CostCenterDetail({
  costCenter,
  childCostCenters,
  onCreateChild,
  onEdit,
  onDelete,
}: CostCenterDetailProps) {
  return (
    <div className="rounded-lg border p-6" data-testid="cost-center-detail">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-semibold tracking-tight">
              {costCenter.cost_org_name}
            </h2>
            <span className="font-mono text-sm text-muted-foreground">
              {costCenter.cost_org_code}
            </span>
            <Badge variant={costCenter.is_active ? "default" : "secondary"}>
              {costCenter.is_active ? "启用" : "停用"}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            {costCenter.company_name}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onCreateChild}
            disabled={!costCenter.is_active}
            title={
              costCenter.is_active
                ? undefined
                : "停用成本中心不能新增下级成本中心，请先启用该成本中心"
            }
          >
            <Plus className="mr-2 size-4" />
            新增下级
          </Button>
          <Button variant="outline" size="sm" onClick={onEdit}>
            <Pencil className="mr-2 size-4" />
            编辑
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-destructive hover:text-destructive"
            onClick={onDelete}
          >
            <Trash2 className="mr-2 size-4" />
            删除
          </Button>
        </div>
      </div>

      <Separator className="my-6" />

      <dl className="grid gap-5 sm:grid-cols-2">
        <DetailField label="上级成本中心">
          {costCenter.parent_name ?? "无（根成本中心）"}
        </DetailField>
        <DetailField label="直属上级">
          {costCenter.manager_name ? (
            <span className="flex flex-wrap items-center gap-2">
              {costCenter.manager_name}
              {costCenter.manager_status === "resigned" && (
                <Badge variant="secondary" className="text-xs">
                  {MANAGER_STATUS_LABELS.resigned}
                </Badge>
              )}
            </span>
          ) : (
            "未设置"
          )}
        </DetailField>
        <DetailField label="预算">
          <span data-testid="cost-center-budget">¥ {costCenter.budget}</span>
        </DetailField>
        <DetailField label="预警比例">{costCenter.warn_pct}%</DetailField>
        <DetailField label="排序号">{costCenter.order_no}</DetailField>
        <DetailField label="备注">
          {costCenter.note ? (
            <span className="whitespace-pre-wrap">{costCenter.note}</span>
          ) : (
            "—"
          )}
        </DetailField>
        <DetailField label="创建时间">
          {formatDateTimeShanghai(costCenter.created_at)}
        </DetailField>
        <DetailField label="更新时间">
          {formatDateTimeShanghai(costCenter.updated_at)}
        </DetailField>
      </dl>

      <Separator className="my-6" />

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">下级成本中心</h3>
          <span className="text-xs text-muted-foreground">
            共 {childCostCenters.length} 个
          </span>
        </div>
        {childCostCenters.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无下级成本中心。</p>
        ) : (
          <ul
            className="divide-y rounded-md border"
            data-testid="child-cost-centers"
          >
            {childCostCenters.map((child) => (
              <li
                key={child.id}
                className="flex flex-wrap items-center gap-2 px-3 py-2 text-sm"
              >
                <span className="font-mono text-xs text-muted-foreground">
                  {child.cost_org_code}
                </span>
                <span>{child.cost_org_name}</span>
                {!child.is_active && (
                  <Badge variant="secondary" className="text-xs">
                    已停用
                  </Badge>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
