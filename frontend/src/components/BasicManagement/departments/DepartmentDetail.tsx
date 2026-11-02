import { Pencil, Plus, Trash2 } from "lucide-react"
import type { ReactNode } from "react"

import type { DepartmentPublic, DepartmentTreeNode } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { formatDateTimeShanghai } from "@/lib/datetime"
import { MANAGER_STATUS_LABELS } from "@/lib/enums"
import { DepartmentPositions } from "./DepartmentPositions"

interface DepartmentDetailProps {
  department: DepartmentPublic
  childDepartments: DepartmentTreeNode[]
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

export function DepartmentDetail({
  department,
  childDepartments,
  onCreateChild,
  onEdit,
  onDelete,
}: DepartmentDetailProps) {
  return (
    <div className="rounded-lg border p-6" data-testid="department-detail">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-semibold tracking-tight">
              {department.dept_name}
            </h2>
            <span className="font-mono text-sm text-muted-foreground">
              {department.dept_code}
            </span>
            <Badge variant={department.is_active ? "default" : "secondary"}>
              {department.is_active ? "启用" : "停用"}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            {department.company_name}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onCreateChild}
            disabled={!department.is_active}
            title={
              department.is_active
                ? undefined
                : "停用部门不能新增下级部门，请先启用该部门"
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
        <DetailField label="上级部门">
          {department.parent_name ?? "无（根部门）"}
        </DetailField>
        <DetailField label="直属上级">
          {department.manager_name ? (
            <span className="flex flex-wrap items-center gap-2">
              {department.manager_name}
              {department.manager_status === "resigned" && (
                <Badge variant="secondary" className="text-xs">
                  {MANAGER_STATUS_LABELS.resigned}
                </Badge>
              )}
            </span>
          ) : (
            "未设置"
          )}
        </DetailField>
        <DetailField label="排序号">{department.order_no}</DetailField>
        <DetailField label="备注">
          {department.note ? (
            <span className="whitespace-pre-wrap">{department.note}</span>
          ) : (
            "—"
          )}
        </DetailField>
        <DetailField label="创建时间">
          {formatDateTimeShanghai(department.created_at)}
        </DetailField>
        <DetailField label="更新时间">
          {formatDateTimeShanghai(department.updated_at)}
        </DetailField>
      </dl>

      <Separator className="my-6" />

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">下级部门</h3>
          <span className="text-xs text-muted-foreground">
            共 {childDepartments.length} 个
          </span>
        </div>
        {childDepartments.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无下级部门。</p>
        ) : (
          <ul
            className="divide-y rounded-md border"
            data-testid="child-departments"
          >
            {childDepartments.map((child) => (
              <li
                key={child.id}
                className="flex flex-wrap items-center gap-2 px-3 py-2 text-sm"
              >
                <span className="font-mono text-xs text-muted-foreground">
                  {child.dept_code}
                </span>
                <span>{child.dept_name}</span>
                {!child.is_active && (
                  <Badge variant="secondary" className="text-xs">
                    停用
                  </Badge>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <Separator className="my-6" />

      <DepartmentPositions department={department} />
    </div>
  )
}
