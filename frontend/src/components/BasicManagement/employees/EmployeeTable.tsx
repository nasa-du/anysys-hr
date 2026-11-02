import type { ColumnDef } from "@tanstack/react-table"
import { useMemo } from "react"

import type { EmployeePublic, EmployeeStatus } from "@/client"
import {
  DataTable,
  type DataTableFeatures,
} from "@/components/Common/DataTable"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { formatDateShanghai } from "@/lib/datetime"
import {
  EMPLOYEE_STATUS_LABELS,
  GENDER_LABELS,
  GENDER_NOT_PROVIDED_LABEL,
  MANAGER_STATUS_LABELS,
} from "@/lib/enums"

function statusVariant(
  status: EmployeeStatus,
): "default" | "secondary" | "outline" {
  if (status === "active") return "default"
  if (status === "probation") return "secondary"
  return "outline"
}

interface EmployeeTableProps {
  employees: EmployeePublic[]
  onOpen: (employee: EmployeePublic) => void
  onEdit: (employee: EmployeePublic) => void
  onLeave: (employee: EmployeePublic) => void
}

export function EmployeeTable({
  employees,
  onOpen,
  onEdit,
  onLeave,
}: EmployeeTableProps) {
  const columns = useMemo<ColumnDef<DataTableFeatures, EmployeePublic>[]>(
    () => [
      {
        accessorKey: "employee_no",
        header: "工号",
        cell: ({ row }) => (
          <span className="font-mono text-xs">{row.original.employee_no}</span>
        ),
      },
      {
        accessorKey: "name",
        header: "姓名",
        cell: ({ row }) => {
          const employee = row.original
          return (
            <div className="flex flex-col">
              <span className="font-medium">{employee.name}</span>
              <span className="text-xs text-muted-foreground">
                {employee.gender
                  ? GENDER_LABELS[employee.gender]
                  : GENDER_NOT_PROVIDED_LABEL}
                {employee.manager_name
                  ? ` · 上级 ${employee.manager_name}`
                  : ""}
                {employee.manager_status === "resigned" && (
                  <Badge variant="secondary" className="ml-1 text-[10px]">
                    {MANAGER_STATUS_LABELS.resigned}
                  </Badge>
                )}
              </span>
            </div>
          )
        },
      },
      {
        accessorKey: "dept_name",
        header: "部门",
        cell: ({ row }) => row.original.dept_name,
      },
      {
        accessorKey: "position_name",
        header: "岗位",
        cell: ({ row }) => row.original.position_name,
      },
      {
        accessorKey: "cost_org_name",
        header: "成本中心",
        cell: ({ row }) =>
          row.original.cost_org_name ?? (
            <Badge variant="secondary">未分配</Badge>
          ),
      },
      {
        accessorKey: "status",
        header: "状态",
        cell: ({ row }) => (
          <Badge variant={statusVariant(row.original.status)}>
            {EMPLOYEE_STATUS_LABELS[row.original.status]}
          </Badge>
        ),
      },
      {
        accessorKey: "hire_date",
        header: "入职日期",
        cell: ({ row }) => (
          <span className="whitespace-nowrap text-muted-foreground">
            {formatDateShanghai(row.original.hire_date)}
          </span>
        ),
      },
      {
        id: "actions",
        header: () => <span className="sr-only">操作</span>,
        cell: ({ row }) => {
          const employee = row.original
          return (
            <div className="flex justify-end gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={(event) => {
                  event.stopPropagation()
                  onEdit(employee)
                }}
              >
                编辑
              </Button>
              {employee.status !== "resigned" && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={(event) => {
                    event.stopPropagation()
                    onLeave(employee)
                  }}
                >
                  离职
                </Button>
              )}
            </div>
          )
        },
      },
    ],
    [onEdit, onLeave],
  )

  return (
    <div data-testid="employee-table">
      <DataTable
        columns={columns}
        data={employees}
        onRowClick={onOpen}
        showPagination={false}
      />
    </div>
  )
}
