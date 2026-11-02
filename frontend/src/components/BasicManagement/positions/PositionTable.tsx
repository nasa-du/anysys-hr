import type { ColumnDef } from "@tanstack/react-table"
import { useMemo } from "react"

import type { PositionPublic } from "@/client"
import {
  DataTable,
  type DataTableFeatures,
} from "@/components/Common/DataTable"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { formatDateTimeShanghai } from "@/lib/datetime"

interface PositionTableProps {
  positions: PositionPublic[]
  inactiveDepartmentIds: Set<string>
  onEdit: (position: PositionPublic) => void
  onDelete: (position: PositionPublic) => void
}

export function PositionTable({
  positions,
  inactiveDepartmentIds,
  onEdit,
  onDelete,
}: PositionTableProps) {
  const columns = useMemo<ColumnDef<DataTableFeatures, PositionPublic>[]>(
    () => [
      {
        accessorKey: "position_code",
        header: "编码",
        cell: ({ row }) => (
          <span className="font-mono text-sm">
            {row.original.position_code}
          </span>
        ),
      },
      {
        accessorKey: "position_name",
        header: "岗位名称",
        cell: ({ row }) => (
          <div className="flex flex-col gap-1">
            <span className="font-medium">{row.original.position_name}</span>
            {row.original.note && (
              <span className="text-xs text-muted-foreground">
                {row.original.note}
              </span>
            )}
          </div>
        ),
      },
      {
        accessorKey: "dept_name",
        header: "默认部门",
        cell: ({ row }) =>
          row.original.dept_name ? (
            <span className="flex flex-wrap items-center gap-2">
              {row.original.dept_name}
              {row.original.dept_id &&
                inactiveDepartmentIds.has(row.original.dept_id) && (
                  <Badge variant="secondary" className="text-xs">
                    已停用
                  </Badge>
                )}
            </span>
          ) : (
            <span className="text-muted-foreground">未设置</span>
          ),
      },
      {
        accessorKey: "is_active",
        header: "状态",
        cell: ({ row }) => (
          <Badge variant={row.original.is_active ? "default" : "secondary"}>
            {row.original.is_active ? "启用" : "停用"}
          </Badge>
        ),
      },
      {
        accessorKey: "created_at",
        header: "创建时间",
        cell: ({ row }) => (
          <span className="whitespace-nowrap text-muted-foreground">
            {formatDateTimeShanghai(row.original.created_at)}
          </span>
        ),
      },
      {
        id: "actions",
        header: () => <span className="sr-only">操作</span>,
        cell: ({ row }) => {
          const position = row.original
          return (
            <div className="flex justify-end gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onEdit(position)}
              >
                编辑
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={() => onDelete(position)}
              >
                删除
              </Button>
            </div>
          )
        },
      },
    ],
    [inactiveDepartmentIds, onDelete, onEdit],
  )

  return (
    <div data-testid="position-table">
      <DataTable columns={columns} data={positions} />
    </div>
  )
}
