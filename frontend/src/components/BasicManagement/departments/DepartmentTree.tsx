import type { DepartmentTreeNode } from "@/client"
import {
  TreePanel,
  type TreePanelNode,
} from "@/components/BasicManagement/shared/TreePanel"

function toTreeNodes(nodes: DepartmentTreeNode[]): TreePanelNode[] {
  return nodes.map((node) => ({
    id: node.id,
    label: node.dept_name,
    code: node.dept_code,
    isActive: node.is_active,
    children: toTreeNodes(node.children ?? []),
  }))
}

interface DepartmentTreeProps {
  departments: DepartmentTreeNode[]
  selectedId: string | null
  onSelect: (departmentId: string) => void
}

export function DepartmentTree({
  departments,
  selectedId,
  onSelect,
}: DepartmentTreeProps) {
  return (
    <TreePanel
      nodes={toTreeNodes(departments)}
      selectedId={selectedId}
      onSelect={onSelect}
      testId="department-tree"
    />
  )
}
