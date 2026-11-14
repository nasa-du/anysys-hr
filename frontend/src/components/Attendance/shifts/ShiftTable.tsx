import type { ColumnDef } from "@tanstack/react-table"
import { useMemo } from "react"

import type { ShiftPublic } from "@/client"
import { StatusSwitch } from "@/components/BasicManagement/shared/StatusSwitch"
import {
  DataTable,
  type DataTableFeatures,
} from "@/components/Common/DataTable"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { SHIFT_STATUS_LABELS } from "@/lib/enums"
import { formatShiftRange, formatShiftTime } from "./shift-time"

interface ShiftTableProps {
  shifts: ShiftPublic[]
  pendingShiftId: string | null
  onEdit: (shift: ShiftPublic) => void
  onDelete: (shift: ShiftPublic) => void
  onToggleActive: (shift: ShiftPublic, isActive: boolean) => void
}

export function ShiftTable({
  shifts,
  pendingShiftId,
  onEdit,
  onDelete,
  onToggleActive,
}: ShiftTableProps) {
  const columns = useMemo<ColumnDef<DataTableFeatures, ShiftPublic>[]>(
    () => [
      {
        accessorKey: "shift_code",
        header: "编码",
        cell: ({ row }) => (
          <span className="font-mono text-sm">{row.original.shift_code}</span>
        ),
      },
      {
        accessorKey: "shift_name",
        header: "班次名称",
        cell: ({ row }) => (
          <div className="flex flex-col gap-1">
            <span className="font-medium">{row.original.shift_name}</span>
            {row.original.note && (
              <span className="text-xs text-muted-foreground">
                {row.original.note}
              </span>
            )}
          </div>
        ),
      },
      {
        id: "time_range",
        header: "时间",
        cell: ({ row }) => {
          const shift = row.original
          return (
            <div className="flex flex-col gap-1">
              <span className="flex flex-wrap items-center gap-2 whitespace-nowrap font-medium">
                {formatShiftRange(shift)}
                {shift.cross_day && (
                  <Badge variant="outline" className="text-xs">
                    跨天
                  </Badge>
                )}
              </span>
              {shift.break_start && shift.break_end && (
                <span className="text-xs text-muted-foreground">
                  休息 {formatShiftTime(shift.break_start)}–
                  {formatShiftTime(shift.break_end)}
                </span>
              )}
              <span className="text-xs text-muted-foreground">
                扣减 {shift.rest_minutes} 分钟
              </span>
            </div>
          )
        },
      },
      {
        accessorKey: "color",
        header: "颜色",
        cell: ({ row }) =>
          row.original.color ? (
            <span className="flex items-center gap-2 text-sm">
              <span
                className="size-4 rounded border"
                style={{ backgroundColor: row.original.color }}
                aria-hidden="true"
              />
              <span className="font-mono text-xs">{row.original.color}</span>
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        accessorKey: "is_active",
        header: "状态",
        cell: ({ row }) => {
          const shift = row.original
          return (
            <div className="flex items-center gap-2">
              <StatusSwitch
                checked={shift.is_active}
                aria-label={`${shift.shift_code} 启用状态`}
                disabled={pendingShiftId === shift.id}
                onCheckedChange={(checked) => onToggleActive(shift, checked)}
              />
              <Badge variant={shift.is_active ? "default" : "secondary"}>
                {SHIFT_STATUS_LABELS[shift.is_active ? "active" : "inactive"]}
              </Badge>
            </div>
          )
        },
      },
      {
        id: "actions",
        header: () => <span className="sr-only">操作</span>,
        cell: ({ row }) => {
          const shift = row.original
          return (
            <div className="flex justify-end gap-1">
              <Button variant="ghost" size="sm" onClick={() => onEdit(shift)}>
                编辑
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={() => onDelete(shift)}
              >
                删除
              </Button>
            </div>
          )
        },
      },
    ],
    [onDelete, onEdit, onToggleActive, pendingShiftId],
  )

  return (
    <div data-testid="shift-table">
      <DataTable columns={columns} data={shifts} />
    </div>
  )
}
