import { useQuery } from "@tanstack/react-query"
import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react"

import { CompaniesService, type CompanyPublic } from "@/client"

export const COMPANY_STORAGE_KEY = "basic-management.company_id"

export const companiesQueryKey = ["basic", "companies", "all"] as const

type CompanyContextValue = {
  companies: CompanyPublic[]
  activeCompanies: CompanyPublic[]
  selectedCompany: CompanyPublic | null
  selectedCompanyId: string | null
  selectCompany: (companyId: string) => void
  isLoading: boolean
  isError: boolean
  refetch: () => void
}

const CompanyContext = createContext<CompanyContextValue | null>(null)

async function fetchCompanies(): Promise<CompanyPublic[]> {
  const response = await CompaniesService.readCompanies({
    query: { skip: 0, limit: 100 },
  })
  return response.data.data
}

function readStoredCompanyId(): string | null {
  try {
    return localStorage.getItem(COMPANY_STORAGE_KEY)
  } catch {
    return null
  }
}

function writeStoredCompanyId(companyId: string | null): void {
  try {
    if (companyId) {
      localStorage.setItem(COMPANY_STORAGE_KEY, companyId)
    } else {
      localStorage.removeItem(COMPANY_STORAGE_KEY)
    }
  } catch {
    // Storage can be unavailable in private browsing; selection still works.
  }
}

export function CompanyProvider({ children }: { children: ReactNode }) {
  const query = useQuery({
    queryKey: companiesQueryKey,
    queryFn: fetchCompanies,
  })
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(
    readStoredCompanyId,
  )

  const companies = useMemo(() => query.data ?? [], [query.data])
  const activeCompanies = useMemo(
    () => companies.filter((company) => company.is_active),
    [companies],
  )

  useEffect(() => {
    if (!query.data) return

    const stored = companies.find((company) => company.id === selectedCompanyId)
    if (stored?.is_active) {
      return
    }

    const fallback = activeCompanies[0] ?? null
    const fallbackId = fallback?.id ?? null
    if (fallbackId !== selectedCompanyId) {
      setSelectedCompanyId(fallbackId)
      writeStoredCompanyId(fallbackId)
    }
  }, [activeCompanies, companies, query.data, selectedCompanyId])

  const selectedCompany =
    companies.find((company) => company.id === selectedCompanyId) ?? null

  const selectCompany = (companyId: string) => {
    const company = companies.find((item) => item.id === companyId)
    if (!company?.is_active) {
      return
    }
    setSelectedCompanyId(companyId)
    writeStoredCompanyId(companyId)
  }

  const value: CompanyContextValue = {
    companies,
    activeCompanies,
    selectedCompany,
    selectedCompanyId: selectedCompany?.id ?? null,
    selectCompany,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: () => {
      void query.refetch()
    },
  }

  return (
    <CompanyContext.Provider value={value}>{children}</CompanyContext.Provider>
  )
}

export function useCompany(): CompanyContextValue {
  const context = useContext(CompanyContext)
  if (context === null) {
    throw new Error("useCompany must be used within a CompanyProvider")
  }
  return context
}
