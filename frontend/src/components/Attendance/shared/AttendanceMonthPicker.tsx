import { Input } from "@/components/ui/input"
import { useAttendanceMonth } from "@/contexts/AttendanceMonthContext"

/** The one attendance-month control shared by every attendance page. */
export function AttendanceMonthPicker() {
  const { month, setMonth } = useAttendanceMonth()

  return (
    <div className="flex items-center gap-2">
      <label
        className="text-sm font-medium text-muted-foreground"
        htmlFor="attendance-month"
      >
        考勤月份
      </label>
      <Input
        id="attendance-month"
        aria-label="考勤月份"
        className="w-[160px]"
        type="month"
        value={month}
        onChange={(event) => setMonth(event.target.value)}
      />
    </div>
  )
}
