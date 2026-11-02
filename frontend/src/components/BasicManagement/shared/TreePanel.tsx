import { ChevronDown, ChevronRight, FolderTree } from "lucide-react"
import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

export interface TreePanelNode {
  id: string
  label: string
  code?: string
  isActive?: boolean
  children?: TreePanelNode[]
}

interface TreePanelProps {
  nodes: TreePanelNode[]
  selectedId: string | null
  onSelect: (id: string) => void
  testId?: string
  childLabel?: string
  inactiveLabel?: string
}

interface TreeNodeItemProps {
  node: TreePanelNode
  depth: number
  selectedId: string | null
  onSelect: (id: string) => void
  childLabel: string
  inactiveLabel: string
}

function TreeNodeItem({
  node,
  depth,
  selectedId,
  onSelect,
  childLabel,
  inactiveLabel,
}: TreeNodeItemProps) {
  const [expanded, setExpanded] = useState(true)
  const children = node.children ?? []
  const hasChildren = children.length > 0
  const isSelected = selectedId === node.id

  return (
    <li>
      <div
        className="flex items-center gap-1"
        style={{ paddingLeft: depth * 16 }}
      >
        {hasChildren ? (
          <button
            type="button"
            className="flex size-5 shrink-0 items-center justify-center rounded text-muted-foreground hover:bg-muted"
            aria-label={expanded ? `收起${childLabel}` : `展开${childLabel}`}
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? (
              <ChevronDown className="size-4" />
            ) : (
              <ChevronRight className="size-4" />
            )}
          </button>
        ) : (
          <span className="size-5 shrink-0" aria-hidden="true" />
        )}
        <button
          type="button"
          aria-current={isSelected ? "true" : undefined}
          onClick={() => onSelect(node.id)}
          className={cn(
            "flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted",
            isSelected && "bg-muted font-medium",
          )}
        >
          <FolderTree className="size-4 shrink-0 text-muted-foreground" />
          <span className="truncate">{node.label}</span>
          {node.code && (
            <span className="shrink-0 font-mono text-xs text-muted-foreground">
              {node.code}
            </span>
          )}
          {node.isActive === false && (
            <Badge variant="secondary" className="ml-auto shrink-0 text-xs">
              {inactiveLabel}
            </Badge>
          )}
        </button>
      </div>
      {hasChildren && expanded && (
        <ul className="space-y-0.5">
          {children.map((child) => (
            <TreeNodeItem
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              childLabel={childLabel}
              inactiveLabel={inactiveLabel}
            />
          ))}
        </ul>
      )}
    </li>
  )
}

/** Recursive tree list with selection; children are always arrays. */
export function TreePanel({
  nodes,
  selectedId,
  onSelect,
  testId = "tree-panel",
  childLabel = "下级部门",
  inactiveLabel = "停用",
}: TreePanelProps) {
  return (
    <ul className="space-y-0.5" data-testid={testId}>
      {nodes.map((node) => (
        <TreeNodeItem
          key={node.id}
          node={node}
          depth={0}
          selectedId={selectedId}
          onSelect={onSelect}
          childLabel={childLabel}
          inactiveLabel={inactiveLabel}
        />
      ))}
    </ul>
  )
}
