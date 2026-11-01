export interface TreeNodeLike<T> {
  id: string
  children?: T[]
}

export interface FlattenedTreeNode<T> {
  node: T
  depth: number
}

export function findTreeNode<T extends TreeNodeLike<T>>(
  nodes: T[],
  nodeId: string,
): T | null {
  for (const node of nodes) {
    if (node.id === nodeId) return node
    const found = findTreeNode(node.children ?? [], nodeId)
    if (found) return found
  }
  return null
}

/** Depth-first traversal in display order, carrying each node's depth. */
export function flattenTree<T extends TreeNodeLike<T>>(
  nodes: T[],
  depth = 0,
): FlattenedTreeNode<T>[] {
  return nodes.flatMap((node) => [
    { node, depth },
    ...flattenTree(node.children ?? [], depth + 1),
  ])
}

/** All descendants of ``nodeId``, excluding the node itself. */
export function collectDescendantIds<T extends TreeNodeLike<T>>(
  nodes: T[],
  nodeId: string,
): Set<string> {
  const ids = new Set<string>()
  const root = findTreeNode(nodes, nodeId)
  const visit = (current: T) => {
    for (const child of current.children ?? []) {
      ids.add(child.id)
      visit(child)
    }
  }
  if (root) visit(root)
  return ids
}
