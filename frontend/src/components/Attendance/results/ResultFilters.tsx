import type { DepartmentPublic, EmployeePublic } from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  type AttendanceDayFlag,
  type AttendanceDayStatus,
  type AttendanceDayType,
  type AttendanceRosterStateWithUnscheduled,
  DAY_FLAG_LABELS,
  DAY_STATUS_LABELS,
  DAY_TYPE_LABELS,
  ROSTER_STATE_LABELS,
} from "@/lib/enums"

import type { DayResultFilters } from "./queries"

type Option = { value: string; label: string }

const ALL: Option = { value: "all", label: "全部" }

const DAY_TYPE_OPTIONS: Option[] = [
  ALL,
  ...(
    Object.entries(DAY_TYPE_LABELS) as Array<[AttendanceDayType, string]>
  ).map(([value, label]) => ({ value, label })),
]

const ROSTER_STATE_OPTIONS: Option[] = [
  ALL,
  ...(
    Object.entries(ROSTER_STATE_LABELS) as Array<
      [AttendanceRosterStateWithUnscheduled, string]
    >
  ).map(([value, label]) => ({ value, label })),
]

const DAY_STATUS_OPTIONS: Option[] = [
  ALL,
  ...(
    Object.entries(DAY_STATUS_LABELS) as Array<[AttendanceDayStatus, string]>
  ).map(([value, label]) => ({ value, label })),
]

const FLAG_OPTIONS: Option[] = [
  ALL,
  ...(
    Object.entries(DAY_FLAG_LABELS) as Array<[AttendanceDayFlag, string]>
  ).map(([value, label]) => ({ value, label })),
]

type ResultFiltersProps = {
  filters: DayResultFilters
  departments: DepartmentPublic[]
  employees: EmployeePublic[]
  onChange: (patch: Partial<DayResultFilters>) => void
  onReset: () => void
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
  testId,
  width = "w-36",
}: {
  label: string
  value: string
  options: Option[]
  onChange: (value: string) => void
  testId: string
  width?: string
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className={width} aria-label={label} data-testid={testId}>
        <SelectValue placeholder={label} />
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

/** The full day-result filter set, including one-click anomaly-only. */
export function ResultFilters({
  filters,
  departments,
  employees,
  onChange,
  onReset,
}: ResultFiltersProps) {
  return (
    <div className="flex flex-wrap items-end gap-2 rounded-lg border p-3">
      <div className="flex h-9 items-center gap-2 text-sm">
        <Checkbox
          id="result-anomaly-only"
          checked={filters.isAbnormalOnly}
          onCheckedChange={(checked) =>
            onChange({ isAbnormalOnly: checked === true })
          }
          data-testid="anomaly-only"
          aria-label="只看异常"
        />
        <Label htmlFor="result-anomaly-only" className="font-normal">
          只看异常
        </Label>
      </div>
      <div className="flex h-9 items-center gap-2 text-sm">
        <Checkbox
          id="result-adjusted-only"
          checked={filters.adjustedOnly}
          onCheckedChange={(checked) =>
            onChange({ adjustedOnly: checked === true })
          }
          data-testid="adjusted-only"
          aria-label="仅已调整"
        />
        <Label htmlFor="result-adjusted-only" className="font-normal">
          仅已调整
        </Label>
      </div>
      <FilterSelect
        label="部门筛选"
        testId="filter-dept"
        value={filters.deptId}
        onChange={(value) => onChange({ deptId: value })}
        options={[
          ALL,
          ...departments.map((department) => ({
            value: department.id,
            label: department.dept_name,
          })),
        ]}
      />
      <FilterSelect
        label="员工筛选"
        testId="filter-employee"
        value={filters.employeeId}
        onChange={(value) => onChange({ employeeId: value })}
        options={[
          ALL,
          ...employees.map((employee) => ({
            value: employee.id,
            label: `${employee.employee_no} ${employee.name}`,
          })),
        ]}
      />
      <div className="flex items-center gap-1">
        <Input
          aria-label="开始日期"
          data-testid="filter-date-from"
          type="date"
          className="w-36"
          value={filters.dateFrom}
          onChange={(event) => onChange({ dateFrom: event.target.value })}
        />
        <span className="text-muted-foreground">–</span>
        <Input
          aria-label="结束日期"
          data-testid="filter-date-to"
          type="date"
          className="w-36"
          value={filters.dateTo}
          onChange={(event) => onChange({ dateTo: event.target.value })}
        />
      </div>
      <FilterSelect
        label="日类型"
        testId="filter-day-type"
        value={filters.dayType}
        onChange={(value) =>
          onChange({ dayType: value as DayResultFilters["dayType"] })
        }
        options={DAY_TYPE_OPTIONS}
      />
      <FilterSelect
        label="排班状态"
        testId="filter-roster-state"
        value={filters.rosterState}
        onChange={(value) =>
          onChange({
            rosterState: value as DayResultFilters["rosterState"],
          })
        }
        options={ROSTER_STATE_OPTIONS}
      />
      <FilterSelect
        label="日状态"
        testId="filter-day-status"
        value={filters.dayStatus}
        onChange={(value) =>
          onChange({ dayStatus: value as DayResultFilters["dayStatus"] })
        }
        options={DAY_STATUS_OPTIONS}
      />
      <FilterSelect
        label="标记"
        testId="filter-flag"
        value={filters.flag}
        onChange={(value) => onChange({ flag: value })}
        options={FLAG_OPTIONS}
        width="w-44"
      />
      <div className="flex items-center gap-2">
        <Label htmlFor="result-keyword" className="sr-only">
          员工关键词
        </Label>
        <Input
          id="result-keyword"
          aria-label="员工关键词"
          data-testid="filter-keyword"
          className="w-40"
          placeholder="姓名 / 工号"
          value={filters.keyword}
          onChange={(event) => onChange({ keyword: event.target.value })}
        />
      </div>
      <Button
        type="button"
        size="sm"
        variant="ghost"
        onClick={onReset}
        data-testid="reset-filters"
      >
        重置筛选
      </Button>
    </div>
  )
}
