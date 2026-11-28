import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useState,
} from "react"

import {
  currentShanghaiMonth,
  isMonthString,
  readStoredMonth,
  writeStoredMonth,
} from "@/lib/month"

export const ATTENDANCE_MONTH_STORAGE_KEY = "attendance.month"

function initialMonth(): string {
  return readStoredMonth(ATTENDANCE_MONTH_STORAGE_KEY) ?? currentShanghaiMonth()
}

type AttendanceMonthContextValue = {
  month: string
  setMonth: (month: string) => void
}

const AttendanceMonthContext =
  createContext<AttendanceMonthContextValue | null>(null)

export function AttendanceMonthProvider({ children }: { children: ReactNode }) {
  const [month, setMonthState] = useState<string>(initialMonth)

  useEffect(() => {
    // Persist the initial fallback as well as later user selections.
    writeStoredMonth(ATTENDANCE_MONTH_STORAGE_KEY, month)
  }, [month])

  const setMonth = (nextMonth: string) => {
    if (!isMonthString(nextMonth)) return
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
