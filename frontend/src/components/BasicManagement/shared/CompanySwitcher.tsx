import { Building2 } from "lucide-react"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useCompany } from "@/contexts/CompanyContext"

export function CompanySwitcher() {
  const { activeCompanies, selectedCompanyId, selectCompany, isLoading } =
    useCompany()

  return (
    <div className="flex items-center gap-2" data-testid="company-switcher">
      <Building2 className="size-4 text-muted-foreground" />
      <Select
        value={selectedCompanyId ?? undefined}
        onValueChange={selectCompany}
        disabled={isLoading || activeCompanies.length === 0}
      >
        <SelectTrigger size="sm" className="w-[190px]" aria-label="切换公司">
          <SelectValue placeholder={isLoading ? "加载中…" : "选择公司"} />
        </SelectTrigger>
        <SelectContent align="end">
          {activeCompanies.map((company) => (
            <SelectItem key={company.id} value={company.id}>
              {company.company_name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
