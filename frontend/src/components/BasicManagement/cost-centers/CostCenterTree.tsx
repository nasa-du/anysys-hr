import type { CostCenterTreeNode } from "@/client"
import {
  TreePanel,
  type TreePanelNode,
} from "@/components/BasicManagement/shared/TreePanel"

function toTreeNodes(nodes: CostCenterTreeNode[]): TreePanelNode[] {
  return nodes.map((node) => ({
    id: node.id,
    label: node.cost_org_name,
    code: node.cost_org_code,
    isActive: node.is_active,
    children: toTreeNodes(node.children ?? []),
  }))
}

interface CostCenterTreeProps {
  costCenters: CostCenterTreeNode[]
  selectedId: string | null
  onSelect: (costCenterId: string) => void
}

export function CostCenterTree({
  costCenters,
  selectedId,
  onSelect,
}: CostCenterTreeProps) {
  return (
    <TreePanel
      nodes={toTreeNodes(costCenters)}
      selectedId={selectedId}
      onSelect={onSelect}
      testId="cost-center-tree"
      childLabel="下级成本中心"
      inactiveLabel="已停用"
    />
  )
}
