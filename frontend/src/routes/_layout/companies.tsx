import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Plus, Search } from "lucide-react"
import { useEffect, useState } from "react"

import {
  type CompaniesPublic,
  CompaniesService,
  type CompanyPublic,
} from "@/client"
import { CompanyForm } from "@/components/BasicManagement/companies/CompanyForm"
import { CompanyTable } from "@/components/BasicManagement/companies/CompanyTable"
import { DeleteCompanyDialog } from "@/components/BasicManagement/companies/DeleteCompanyDialog"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/BasicManagement/shared/StateViews"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useCompany } from "@/contexts/CompanyContext"
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorMessage } from "@/lib/api-error"

type StatusFilter = "all" | "active" | "inactive"

const STATUS_OPTIONS: Array<{ value: StatusFilter; label: string }> = [
  { value: "all", label: "全部状态" },
  { value: "active", label: "启用" },
  { value: "inactive", label: "停用" },
]

export const Route = createFileRoute("/_layout/companies")({
  component: CompaniesPage,
  head: () => ({
    meta: [
      {
        title: "公司 - AnySys",
      },
    ],
  }),
})

async function fetchCompanies(
  keyword: string,
  status: StatusFilter,
): Promise<CompaniesPublic> {
  const response = await CompaniesService.readCompanies({
    query: {
      skip: 0,
      limit: 500,
      keyword: keyword || undefined,
      is_active: status === "all" ? undefined : status === "active",
    },
  })
  return response.data
}

function CompaniesPage() {
  const { selectedCompanyId, selectCompany } = useCompany()
  const { showSuccessToast } = useCustomToast()
  const [keyword, setKeyword] = useState("")
  const [debouncedKeyword, setDebouncedKeyword] = useState("")
  const [status, setStatus] = useState<StatusFilter>("all")
  const [formOpen, setFormOpen] = useState(false)
  const [editingCompany, setEditingCompany] = useState<CompanyPublic | null>(
    null,
  )
  const [deletingCompany, setDeletingCompany] = useState<CompanyPublic | null>(
    null,
  )

  useEffect(() => {
    const timer = window.setTimeout(
      () => setDebouncedKeyword(keyword.trim()),
      300,
    )
    return () => window.clearTimeout(timer)
  }, [keyword])

  const companiesQuery = useQuery({
    queryKey: ["basic", "companies", { keyword: debouncedKeyword, status }],
    queryFn: () => fetchCompanies(debouncedKeyword, status),
  })

  const openCreate = () => {
    setEditingCompany(null)
    setFormOpen(true)
  }

  const openEdit = (company: CompanyPublic) => {
    setEditingCompany(company)
    setFormOpen(true)
  }

  const handleSwitch = (company: CompanyPublic) => {
    selectCompany(company.id)
    showSuccessToast(`已切换至 ${company.company_name}`)
  }

  const hasFilters = debouncedKeyword !== "" || status !== "all"
  const companies = companiesQuery.data?.data ?? []
  const count = companiesQuery.data?.count ?? 0

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">公司</h1>
          <p className="text-muted-foreground">
            管理所有公司档案；公司之间扁平，不设上下级。删除公司前必须先清空其部门、岗位、成本中心与员工。
          </p>
        </div>
        <Button className="shrink-0" onClick={openCreate}>
          <Plus className="mr-2 size-4" />
          新增公司
        </Button>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative sm:w-72">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="搜索公司名称或编码"
            aria-label="搜索公司"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
          />
        </div>
        <Select
          value={status}
          onValueChange={(value) => setStatus(value as StatusFilter)}
        >
          <SelectTrigger className="w-[140px]" aria-label="状态筛选">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {!companiesQuery.isLoading && !companiesQuery.isError && (
          <p className="text-sm text-muted-foreground sm:ml-auto">
            共 <span className="font-medium text-foreground">{count}</span>{" "}
            家公司
          </p>
        )}
      </div>

      {companiesQuery.isLoading ? (
        <LoadingState />
      ) : companiesQuery.isError ? (
        <ErrorState
          message={getErrorMessage(companiesQuery.error)}
          onRetry={() => {
            void companiesQuery.refetch()
          }}
        />
      ) : companies.length === 0 ? (
        <EmptyState
          title={hasFilters ? "没有匹配的公司" : "还没有公司"}
          message={
            hasFilters
              ? "尝试调整搜索关键词或状态筛选。"
              : "创建第一家公司后，才能维护部门、岗位、员工与成本中心。"
          }
          action={
            hasFilters ? (
              <Button
                variant="outline"
                onClick={() => {
                  setKeyword("")
                  setStatus("all")
                }}
              >
                清除筛选
              </Button>
            ) : (
              <Button onClick={openCreate}>
                <Plus className="mr-2 size-4" />
                新增公司
              </Button>
            )
          }
        />
      ) : (
        <CompanyTable
          companies={companies}
          selectedCompanyId={selectedCompanyId}
          onEdit={openEdit}
          onDelete={setDeletingCompany}
          onSwitch={handleSwitch}
        />
      )}

      <CompanyForm
        open={formOpen}
        onOpenChange={setFormOpen}
        company={editingCompany}
      />
      <DeleteCompanyDialog
        company={deletingCompany}
        onOpenChange={(open) => {
          if (!open) setDeletingCompany(null)
        }}
      />
    </div>
  )
}
