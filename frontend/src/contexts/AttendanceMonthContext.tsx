import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useState,
} from "react"

export const ATTENDANCE_MONTH_STORAGE_KEY = "attendance.month"

const MONTH_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/

/** The current calendar month in Asia/Shanghai, formatted as YYYY-MM. */
export function currentShanghaiMonth(now: Date = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(now)
  const year = parts.find((part) => part.type === "year")?.value
  const month = parts.find((part) => part.type === "month")?.value
  return `${year}-${month}`
}

function readStoredMonth(): string {
  try {
    const stored = localStorage.getItem(ATTENDANCE_MONTH_STORAGE_KEY)
    if (stored && MONTH_PATTERN.test(stored)) {
      return stored
    }
  } catch {
    // Storage can be unavailable in private browsing; the fallback still works.
  }
  return currentShanghaiMonth()
}

function writeStoredMonth(month: string): void {
  try {
    localStorage.setItem(ATTENDANCE_MONTH_STORAGE_KEY, month)
  } catch {
    // Selection still works for the current page when storage is unavailable.
  }
}

type AttendanceMonthContextValue = {
  month: string
  setMonth: (month: string) => void
}

const AttendanceMonthContext =
  createContext<AttendanceMonthContextValue | null>(null)

export function AttendanceMonthProvider({ children }: { children: ReactNode }) {
  const [month, setMonthState] = useState<string>(readStoredMonth)

  useEffect(() => {
    // Persist the initial fallback as well as later user selections.
    writeStoredMonth(month)
  }, [month])

  const setMonth = (nextMonth: string) => {
    if (!MONTH_PATTERN.test(nextMonth)) return
    setMonthState(nextMonth)
  }

  return (
    <AttendanceMonthContext.Provider value={{ month, setMonth }}>
      {children}
    </AttendanceMonthContext.Provider>
  )
}

export function useAttendanceMonth(): AttendanceMonthContextValue {
  const context = useContext(AttendanceMonthContext)
  if (context === null) {
    throw new Error(
      "useAttendanceMonth must be used within an AttendanceMonthProvider",
    )
  }
  return context
}
