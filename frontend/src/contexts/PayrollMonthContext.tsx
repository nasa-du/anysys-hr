import { useNavigate, useRouterState } from "@tanstack/react-router"
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import type { CompanyPublic } from "@/client"
import { useCompany } from "@/contexts/CompanyContext"
import {
  currentShanghaiMonth,
  isMonthString,
  readStoredMonth,
  writeStoredMonth,
} from "@/lib/month"
import type {
  PayrollAttendanceLockState,
  PayrollCalcRunStatus,
  PayrollCalcRunTrigger,
  PayrollMonthStatus,
  PayrollStaleBadge,
} from "@/lib/payroll-enums"

export type { PayrollAttendanceLockState } from "@/lib/payroll-enums"

export const PAYROLL_MONTH_STORAGE_KEY = "payroll.month"
export const PAYROLL_MONTH_COMPANY_STORAGE_KEY = "payroll.month.company_id"
export const PAYROLL_MONTH_SEARCH_PARAM = "month"

export type PayrollLatestRun = {
  status: PayrollCalcRunStatus
  trigger: PayrollCalcRunTrigger
  finishedAt: string | null
}

export type PayrollAttendanceLock = {
  status: PayrollAttendanceLockState
  lockedAt: string | null
}

/** Month-level state shown by the shared month bar. */
export type PayrollMonthState = {
  status: PayrollMonthStatus
  inputVersion: number
  latestRun: PayrollLatestRun | null
  attendanceLock: PayrollAttendanceLock
  staleBadges: PayrollStaleBadge[]
}

/**
 * Month actions. Phase 0 routes to the page that owns the real control; the
 * monthly slices replace each entry with the corresponding API action.
 */
export type PayrollMonthActions = {
  importMonth: () => void
  recalculate: () => void
  confirmMonth: () => void
  issuePayslips: () => void
  unlockMonth: () => void
}

export type PayrollMonthContextValue = PayrollMonthState & {
  company: CompanyPublic | null
  companyId: string | null
  month: string
  setMonth: (month: string) => void
  actions: PayrollMonthActions
}

/** A month exists lazily: absent state is a synthetic draft. */
const DRAFT_MONTH_STATE: PayrollMonthState = {
  status: "draft",
  inputVersion: 0,
  latestRun: null,
  attendanceLock: { status: "unlocked", lockedAt: null },
  staleBadges: [],
}

const PayrollMonthContext = createContext<PayrollMonthContextValue | null>(null)

function initialMonth(): string {
  return readStoredMonth(PAYROLL_MONTH_STORAGE_KEY) ?? currentShanghaiMonth()
}

function writeStoredSelection(month: string, companyId: string | null): void {
  writeStoredMonth(PAYROLL_MONTH_STORAGE_KEY, month)
  if (!companyId) return
  try {
    localStorage.setItem(PAYROLL_MONTH_COMPANY_STORAGE_KEY, companyId)
  } catch {
    // Selection still works for the current page when storage is unavailable.
  }
}

function readStoredCompanyId(): string | null {
  try {
    return localStorage.getItem(PAYROLL_MONTH_COMPANY_STORAGE_KEY)
  } catch {
    return null
  }
}

function readMonthFromUrl(): string | null {
  if (typeof window === "undefined") return null
  const value = new URLSearchParams(window.location.search).get(
    PAYROLL_MONTH_SEARCH_PARAM,
  )
  return isMonthString(value) ? value : null
}

export function PayrollMonthProvider({ children }: { children: ReactNode }) {
  const { selectedCompany, selectedCompanyId } = useCompany()
  const navigate = useNavigate()
  const searchStr = useRouterState({
    select: (state) => state.location.searchStr,
  })
  const urlMonth = new URLSearchParams(searchStr).get(
    PAYROLL_MONTH_SEARCH_PARAM,
  )
  const urlMonthAtMount = useRef(readMonthFromUrl())
  const storedCompanyIdAtMount = useRef(readStoredCompanyId())
  const hasResolvedCompany = useRef(false)
  const [month, setMonthState] = useState<string>(
    () => urlMonthAtMount.current ?? initialMonth(),
  )
  const previousCompanyId = useRef(selectedCompanyId)

  useEffect(() => {
    writeStoredSelection(month, selectedCompanyId)
    if (urlMonth === month) return
    // Navigate rather than touching history directly so the router's search
    // state stays in sync with the deep-link URL. Plain link clicks may drop
    // the query, and this restores it for the new monthly page.
    navigate({
      to: ".",
      search: (prev) => ({ ...prev, [PAYROLL_MONTH_SEARCH_PARAM]: month }),
      replace: true,
    })
  }, [month, navigate, selectedCompanyId, urlMonth])

  // Switching company is a new data scope: start that scope on the current
  // Shanghai month rather than reusing the previous company's selection. The
  // stored company also covers a switch made while a configuration page was
  // open (those pages do not mount this provider); the next monthly page then
  // sees the mismatch and starts clean.
  useEffect(() => {
    if (selectedCompanyId === null) {
      previousCompanyId.current = null
      return
    }

    const firstResolution = !hasResolvedCompany.current
    hasResolvedCompany.current = true
    const companyChanged =
      previousCompanyId.current !== null &&
      previousCompanyId.current !== selectedCompanyId
    const storedSelectionBelongsToAnotherCompany =
      firstResolution &&
      urlMonthAtMount.current === null &&
      storedCompanyIdAtMount.current !== null &&
      storedCompanyIdAtMount.current !== selectedCompanyId

    if (companyChanged || storedSelectionBelongsToAnotherCompany) {
      setMonthState(currentShanghaiMonth())
    }
    previousCompanyId.current = selectedCompanyId
  }, [selectedCompanyId])

  const setMonth = useCallback((nextMonth: string) => {
    if (!isMonthString(nextMonth)) return
    setMonthState(nextMonth)
  }, [])

  const actions = useMemo<PayrollMonthActions>(
    () => ({
      importMonth: () => navigate({ to: "/payroll/imports" }),
      recalculate: () => navigate({ to: "/payroll/calc" }),
      confirmMonth: () => navigate({ to: "/payroll/calc" }),
      issuePayslips: () => navigate({ to: "/payroll/payslips" }),
      unlockMonth: () => navigate({ to: "/payroll/calc" }),
    }),
    [navigate],
  )

  const value = useMemo<PayrollMonthContextValue>(
    () => ({
      ...DRAFT_MONTH_STATE,
      company: selectedCompany,
      companyId: selectedCompanyId,
      month,
      setMonth,
      actions,
    }),
    [actions, month, selectedCompany, selectedCompanyId, setMonth],
  )

  return (
    <PayrollMonthContext.Provider value={value}>
      {children}
    </PayrollMonthContext.Provider>
  )
}

export function usePayrollMonth(): PayrollMonthContextValue {
  const context = useContext(PayrollMonthContext)
  if (context === null) {
    throw new Error(
      "usePayrollMonth must be used within a PayrollMonthProvider; " +
        "configuration pages do not mount month context.",
    )
  }
  return context
}
