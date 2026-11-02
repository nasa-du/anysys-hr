import type { ColumnDef } from "@tanstack/react-table"
import { useMemo } from "react"

import type { CompanyPublic } from "@/client"
import {
  DataTable,
  type DataTableFeatures,
} from "@/components/Common/DataTable"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { formatDateTimeShanghai } from "@/lib/datetime"

interface CompanyTableProps {
  companies: CompanyPublic[]
  selectedCompanyId: string | null
  onEdit: (company: CompanyPublic) => void
  onDelete: (company: CompanyPublic) => void
  onSwitch: (company: CompanyPublic) => void
}

export function CompanyTable({
  companies,
  selectedCompanyId,
  onEdit,
  onDelete,
  onSwitch,
}: CompanyTableProps) {
  const columns = useMemo<ColumnDef<DataTableFeatures, CompanyPublic>[]>(
    () => [
      {
        accessorKey: "company_code",
        header: "编码",
        cell: ({ row }) => (
          <span className="font-mono text-sm">{row.original.company_code}</span>
        ),
      },
      {
        accessorKey: "company_name",
        header: "公司名称",
        cell: ({ row }) => (
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className="font-medium">{row.original.company_name}</span>
              {row.original.id === selectedCompanyId && (
                <Badge variant="outline" className="text-xs">
                  当前公司
                </Badge>
              )}
            </div>
            {row.original.note && (
              <span className="text-xs text-muted-foreground">
                {row.original.note}
              </span>
            )}
          </div>
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
          const company = row.original
          return (
            <div className="flex justify-end gap-1">
              {company.is_active && company.id !== selectedCompanyId && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onSwitch(company)}
                >
                  切换
                </Button>
              )}
              <Button variant="ghost" size="sm" onClick={() => onEdit(company)}>
                编辑
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={() => onDelete(company)}
              >
                删除
              </Button>
            </div>
          )
        },
      },
    ],
    [onDelete, onEdit, onSwitch, selectedCompanyId],
  )

  return (
    <div data-testid="company-table">
      <DataTable columns={columns} data={companies} />
    </div>
  )
}
