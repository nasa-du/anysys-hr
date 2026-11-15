import { useState } from "react"

import type { DepartmentPublic, EmployeePublic } from "@/client"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { getErrorMessage } from "@/lib/api-error"

import { PaginationFooter } from "./PaginationFooter"
import {
  EMPTY_SUMMARY_FILTERS,
  type SummaryFilters,
  useMonthSummaries,
} from "./queries"
import {
  formatAmount,
  formatDecimal,
  formatFraction,
  formatHours,
} from "./result-format"

const PAGE_SIZE = 25

type MonthSummaryTableProps = {
  companyId: string
  month: string
  departments: DepartmentPublic[]
  employees: EmployeePublic[]
  onOpenCalendar: (employeeId: string) => void
}

/** Employee month summaries with employee/department/keyword filters. */
export function MonthSummaryTable({
  companyId,
  month,
  departments,
  employees,
  onOpenCalendar,
}: MonthSummaryTableProps) {
  const [filters, setFilters] = useState<SummaryFilters>(EMPTY_SUMMARY_FILTERS)
  const [skip, setSkip] = useState(0)
  const query = useMonthSummaries(companyId, month, filters, skip, PAGE_SIZE)
  const rows = query.data?.data ?? []
  const count = query.data?.count ?? 0
  const filtered =
    filters.deptId !== "all" ||
    filters.employeeId !== "all" ||
    filters.keyword.trim() !== ""

  const update = (patch: Partial<SummaryFilters>) => {
    setFilters((current) => ({ ...current, ...patch }))
    setSkip(0)
  }

  return (
    <div className="space-y-3" data-testid="month-summary-panel">
      <div className="flex flex-wrap items-center gap-2 rounded-lg border p-3">
        <Select
          value={filters.deptId}
          onValueChange={(value) => update({ deptId: value })}
        >
          <SelectTrigger className="w-40" aria-label="汇总部门筛选">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部部门</SelectItem>
            {departments.map((department) => (
              <SelectItem key={department.id} value={department.id}>
                {department.dept_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={filters.employeeId}
          onValueChange={(value) => update({ employeeId: value })}
        >
          <SelectTrigger className="w-48" aria-label="汇总员工筛选">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部员工</SelectItem>
            {employees.map((employee) => (
              <SelectItem key={employee.id} value={employee.id}>
                {employee.employee_no} {employee.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          aria-label="汇总员工关键词"
          className="w-44"
          placeholder="姓名 / 工号"
          value={filters.keyword}
          onChange={(event) => update({ keyword: event.target.value })}
        />
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => {
            setFilters(EMPTY_SUMMARY_FILTERS)
            setSkip(0)
          }}
        >
          重置筛选
        </Button>
        <span className="ml-auto text-sm text-muted-foreground">
          共 {count} 名员工
        </span>
      </div>

      {query.isLoading ? (
        <LoadingState rows={5} />
      ) : query.isError ? (
        <ErrorState
          message={getErrorMessage(query.error)}
          onRetry={() => void query.refetch()}
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title={filtered ? "没有匹配的月汇总" : `${month} 还没有月汇总`}
          message={
            filtered
              ? "试试重置筛选或切换月份。"
              : "重新计算后生成每名员工的月汇总。"
          }
        />
      ) : (
        <div className="space-y-3">
          <div className="overflow-x-auto rounded-lg border">
            <Table data-testid="month-summary-table">
              <TableHeader>
                <TableRow>
                  <TableHead>员工</TableHead>
                  <TableHead>部门</TableHead>
                  <TableHead>应出勤</TableHead>
                  <TableHead>实际出勤</TableHead>
                  <TableHead>请假</TableHead>
                  <TableHead className="text-right">出差</TableHead>
                  <TableHead>加班</TableHead>
                  <TableHead>迟到 / 早退</TableHead>
                  <TableHead>缺卡 / 旷工</TableHead>
                  <TableHead className="text-right">工时</TableHead>
                  <TableHead className="text-right">扣款建议</TableHead>
                  <TableHead>调整</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((summary) => {
                  const otTotal =
                    Number(summary.ot_weekday_hours) +
                    Number(summary.ot_weekend_hours) +
                    Number(summary.ot_holiday_hours)
                  return (
                    <TableRow
                      key={summary.id}
                      data-testid={`summary-row-${summary.employee_id}`}
                      tabIndex={0}
                      className="cursor-pointer"
                      onClick={() => onOpenCalendar(summary.employee_id)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault()
                          onOpenCalendar(summary.employee_id)
                        }
                      }}
                    >
                      <TableCell>
                        <div className="font-medium">
                          {summary.employee_name ?? summary.employee_id}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {summary.employee_no ?? ""}
                        </div>
                      </TableCell>
                      <TableCell>{summary.department_name ?? "—"}</TableCell>
                      <TableCell>
                        <div>
                          {formatFraction(
                            Number(summary.weekday_full) +
                              Number(summary.weekend_full),
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          工作 {summary.weekday_full} · 周末{" "}
                          {summary.weekend_full}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div>
                          {formatFraction(
                            Number(summary.weekday_attended) +
                              Number(summary.weekend_attended),
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          工作 {summary.weekday_attended} · 周末{" "}
                          {summary.weekend_attended}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div>
                          {formatFraction(
                            Number(summary.paid_leave_days) +
                              Number(summary.unpaid_leave_days) +
                              Number(summary.comp_leave_days),
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          带薪 {summary.paid_leave_days} · 事假{" "}
                          {summary.unpaid_leave_days} · 补休{" "}
                          {summary.comp_leave_days}
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {summary.trip_days}
                      </TableCell>
                      <TableCell>
                        <div>{formatDecimal(otTotal)} h</div>
                        <div className="text-xs text-muted-foreground">
                          工 {summary.ot_weekday_hours} · 周{" "}
                          {summary.ot_weekend_hours} · 节{" "}
                          {summary.ot_holiday_hours}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div>
                          {summary.late_count} / {summary.early_count}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {summary.late_minutes} / {summary.early_minutes} 分钟
                        </div>
                      </TableCell>
                      <TableCell>
                        {summary.missing_punch_count} / {summary.absent_days}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatHours(summary.worked_minutes)} h
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatAmount(summary.attendance_deduct)}
                      </TableCell>
                      <TableCell>
                        {summary.is_adjusted ? (
                          <Badge variant="secondary">有调整</Badge>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
          <PaginationFooter
            count={count}
            skip={skip}
            pageSize={PAGE_SIZE}
            onSkipChange={setSkip}
          />
        </div>
      )}
    </div>
  )
}
