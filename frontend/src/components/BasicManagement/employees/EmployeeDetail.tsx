import { LogOut, Pencil } from "lucide-react"
import type { ReactNode } from "react"

import type { EmployeePublic } from "@/client"
import {
  ErrorState,
  LoadingState,
} from "@/components/BasicManagement/shared/StateViews"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { formatDateShanghai, formatDateTimeShanghai } from "@/lib/datetime"
import {
  CONTRACT_TYPE_LABELS,
  EMPLOYEE_STATUS_LABELS,
  GENDER_LABELS,
  GENDER_NOT_PROVIDED_LABEL,
  MANAGER_STATUS_LABELS,
} from "@/lib/enums"

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

function DetailGroup({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <section className="space-y-3">
      <h3 className="text-sm font-medium">{title}</h3>
      <dl className="grid gap-4 rounded-md border p-4 sm:grid-cols-2">
        {children}
      </dl>
    </section>
  )
}

interface EmployeeDetailProps {
  employee: EmployeePublic | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onEdit: (employee: EmployeePublic) => void
  onLeave: (employee: EmployeePublic) => void
  isLoading?: boolean
  errorMessage?: string
  onRetry?: () => void
}

/** Read-only employee record; resigned records only allow note/date corrections. */
export function EmployeeDetail({
  employee,
  open,
  onOpenChange,
  onEdit,
  onLeave,
  isLoading = false,
  errorMessage,
  onRetry,
}: EmployeeDetailProps) {
  const isResigned = employee?.status === "resigned"

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        className="flex w-full flex-col gap-0 overflow-y-auto sm:max-w-xl"
        data-testid="employee-detail"
      >
        {employee ? (
          <>
            <SheetHeader>
              <SheetTitle className="flex flex-wrap items-center gap-2">
                {employee.name}
                <span className="font-mono text-sm font-normal text-muted-foreground">
                  {employee.employee_no}
                </span>
                <Badge
                  variant={isResigned ? "outline" : "default"}
                  data-testid="employee-detail-status"
                >
                  {EMPLOYEE_STATUS_LABELS[employee.status]}
                </Badge>
              </SheetTitle>
              <SheetDescription>
                {employee.company_name} · {employee.dept_name} ·{" "}
                {employee.position_name}
              </SheetDescription>
            </SheetHeader>

            <div className="space-y-6 px-4 pb-6">
              <DetailGroup title="基本信息">
                <DetailField label="姓名">{employee.name}</DetailField>
                <DetailField label="性别">
                  {employee.gender
                    ? GENDER_LABELS[employee.gender]
                    : GENDER_NOT_PROVIDED_LABEL}
                </DetailField>
                <DetailField label="合同类型">
                  {CONTRACT_TYPE_LABELS[employee.contract_type]}
                </DetailField>
                <DetailField label="状态">
                  {EMPLOYEE_STATUS_LABELS[employee.status]}
                </DetailField>
                <DetailField label="入职日期">
                  {formatDateShanghai(employee.hire_date)}
                </DetailField>
                <DetailField label="离职日期">
                  {employee.resign_date
                    ? formatDateShanghai(employee.resign_date)
                    : "—"}
                </DetailField>
              </DetailGroup>

              <DetailGroup title="行政归属">
                <DetailField label="公司">{employee.company_name}</DetailField>
                <DetailField label="部门">{employee.dept_name}</DetailField>
                <DetailField label="岗位">{employee.position_name}</DetailField>
              </DetailGroup>

              <DetailGroup title="成本归属">
                <DetailField label="成本中心">
                  {employee.cost_org_name ?? (
                    <Badge variant="secondary">未分配</Badge>
                  )}
                </DetailField>
              </DetailGroup>

              <DetailGroup title="汇报关系">
                <DetailField label="直属上级">
                  {employee.manager_name ? (
                    <span className="flex flex-wrap items-center gap-2">
                      {employee.manager_name}
                      {employee.manager_status === "resigned" && (
                        <Badge variant="secondary" className="text-xs">
                          {MANAGER_STATUS_LABELS.resigned}
                        </Badge>
                      )}
                    </span>
                  ) : (
                    "无"
                  )}
                </DetailField>
              </DetailGroup>

              <DetailGroup title="更多档案字段">
                <DetailField label="每日工时">
                  {employee.daily_hours ?? "—"}
                </DetailField>
                <DetailField label="月休天数">
                  {employee.monthly_rest ?? "—"}
                </DetailField>
                <DetailField label="保密等级">
                  {employee.confidentiality_level ?? "—"}
                </DetailField>
                <DetailField label="备注">
                  {employee.note ? (
                    <span className="whitespace-pre-wrap">{employee.note}</span>
                  ) : (
                    "—"
                  )}
                </DetailField>
                <DetailField label="创建时间">
                  {formatDateTimeShanghai(employee.created_at)}
                </DetailField>
                <DetailField label="更新时间">
                  {formatDateTimeShanghai(employee.updated_at)}
                </DetailField>
              </DetailGroup>

              {isResigned && (
                <p className="rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">
                  离职为终态，档案只读；仅可修正备注与离职日期。
                </p>
              )}
            </div>

            <SheetFooter className="mt-auto flex-row justify-end gap-2 border-t px-4 py-3">
              <Button
                variant="outline"
                onClick={() => {
                  onOpenChange(false)
                  onEdit(employee)
                }}
              >
                <Pencil className="mr-2 size-4" />
                {isResigned ? "修正" : "编辑"}
              </Button>
              {!isResigned && (
                <Button
                  variant="destructive"
                  onClick={() => {
                    onOpenChange(false)
                    onLeave(employee)
                  }}
                >
                  <LogOut className="mr-2 size-4" />
                  办理离职
                </Button>
              )}
            </SheetFooter>
          </>
        ) : (
          <>
            <SheetHeader>
              <SheetTitle>员工详情</SheetTitle>
              <SheetDescription>查看员工档案与归属信息。</SheetDescription>
            </SheetHeader>
            <div className="px-4 pb-6">
              {isLoading || !errorMessage ? (
                <LoadingState rows={3} />
              ) : (
                <ErrorState message={errorMessage} onRetry={onRetry} />
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
