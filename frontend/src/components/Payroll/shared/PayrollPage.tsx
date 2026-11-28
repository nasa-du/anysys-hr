import { Link } from "@tanstack/react-router"
import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"
import { useCompany } from "@/contexts/CompanyContext"
import {
  PayrollMonthProvider,
  usePayrollMonth,
} from "@/contexts/PayrollMonthContext"
import { PayrollMonthBar } from "./MonthBar"
import { EmptyState, ErrorState, LoadingState } from "./StateViews"

interface PayrollPageProps {
  title: string
  description: string
  children?: ReactNode
  actions?: ReactNode
}

interface PayrollPageBodyProps extends PayrollPageProps {
  monthly: boolean
}

function NoCompanyState() {
  return (
    <EmptyState
      title="尚未选择公司"
      message="请先在「公司」页面创建并启用公司，再从顶部切换器选择公司。"
      action={
        <Button asChild variant="outline">
          <Link to="/companies">前往公司页面</Link>
        </Button>
      }
    />
  )
}

function PayrollPageBody({
  title,
  description,
  children,
  actions,
  monthly,
}: PayrollPageBodyProps) {
  const { selectedCompanyId, isLoading, isError, refetch } = useCompany()

  let content: ReactNode
  if (isLoading) {
    content = <LoadingState rows={4} />
  } else if (isError) {
    content = <ErrorState onRetry={refetch} />
  } else if (!selectedCompanyId) {
    content = <NoCompanyState />
  } else {
    content = children
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="text-muted-foreground">{description}</p>
        </div>
        {actions && (
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {actions}
          </div>
        )}
      </div>
      {monthly && <PayrollMonthBar />}
      {content}
    </div>
  )
}

function MonthlyPageContent({
  title,
  description,
  children,
  actions,
}: PayrollPageProps) {
  const { month } = usePayrollMonth()

  return (
    <PayrollPageBody
      monthly
      title={title}
      description={description}
      actions={actions}
    >
      {children ?? (
        <EmptyState
          title={`${title}功能建设中`}
          message={`当前薪资月份为 ${month}。该模块将在后续切片中实现。`}
        />
      )}
    </PayrollPageBody>
  )
}

/** Monthly payroll page: mounts the shared month context and month bar. */
export function PayrollMonthlyPage(props: PayrollPageProps) {
  return (
    <PayrollMonthProvider>
      <MonthlyPageContent {...props} />
    </PayrollMonthProvider>
  )
}

/** Configuration payroll page: explicitly has no month context or month bar. */
export function PayrollConfigPage({
  title,
  description,
  children,
  actions,
}: PayrollPageProps) {
  return (
    <PayrollPageBody
      monthly={false}
      title={title}
      description={description}
      actions={actions}
    >
      {children ?? (
        <EmptyState
          title={`${title}功能建设中`}
          message="该配置模块将在后续切片中实现。"
        />
      )}
    </PayrollPageBody>
  )
}
