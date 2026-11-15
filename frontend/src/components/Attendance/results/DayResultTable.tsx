import { useState } from "react"

import type {
  AttendanceDayResultPublic,
  DepartmentPublic,
  EmployeePublic,
} from "@/client"
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Badge } from "@/components/ui/badge"
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
  type DayResultFilters,
  EMPTY_DAY_RESULT_FILTERS,
  useDayResults,
} from "./queries"
import { ResultFilters } from "./ResultFilters"
import {
  dayFlagLabel,
  dayStatusLabel,
  dayStatusVariant,
  dayTypeLabel,
  formatAmount,
  formatFraction,
  formatHours,
  formatWorkDate,
  leaveKindLabel,
  rosterStateLabel,
  totalOtMinutes,
  tripKindLabel,
} from "./result-format"

const PAGE_SIZE = 25

type DayResultTableProps = {
  companyId: string
  month: string
  departments: DepartmentPublic[]
  employees: EmployeePublic[]
  onOpenDay: (employeeId: string, workDate: string) => void
}

function LeaveTripCell({ result }: { result: AttendanceDayResultPublic }) {
  const parts: string[] = []
  if (Number(result.leave_days) > 0) {
    parts.push(
      `${
        result.leave_kind ? leaveKindLabel(result.leave_kind) : "请假"
      } ${formatFraction(result.leave_days)}`,
    )
  }
  if (result.trip_kind) {
    parts.push(
      `${tripKindLabel(result.trip_kind)} ${formatFraction(result.trip_fraction)}`,
    )
  }
  return parts.length > 0 ? (
    <span>{parts.join(" · ")}</span>
  ) : (
    <span className="text-muted-foreground">—</span>
  )
}

/** Full day-result table with the complete filter set and server pagination. */
export function DayResultTable({
  companyId,
  month,
  departments,
  employees,
  onOpenDay,
}: DayResultTableProps) {
  const [filters, setFilters] = useState<DayResultFilters>(
    EMPTY_DAY_RESULT_FILTERS,
  )
  const [skip, setSkip] = useState(0)
  const query = useDayResults(companyId, month, filters, skip, PAGE_SIZE)
  const rows = query.data?.data ?? []
  const count = query.data?.count ?? 0
  const filtered = Object.entries(filters).some(([key, value]) => {
    const emptyValue = EMPTY_DAY_RESULT_FILTERS[key as keyof DayResultFilters]
    return value !== emptyValue
  })

  const updateFilters = (patch: Partial<DayResultFilters>) => {
    setFilters((current) => ({ ...current, ...patch }))
    setSkip(0)
  }

  return (
    <div className="space-y-3" data-testid="day-results-panel">
      <ResultFilters
        filters={filters}
        departments={departments}
        employees={employees}
        onChange={updateFilters}
        onReset={() => {
          setFilters(EMPTY_DAY_RESULT_FILTERS)
          setSkip(0)
        }}
      />

      {query.isLoading ? (
        <LoadingState rows={6} />
      ) : query.isError ? (
        <ErrorState
          message={getErrorMessage(query.error)}
          onRetry={() => void query.refetch()}
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title={filtered ? "没有匹配的日结果" : `${month} 还没有日结果`}
          message={
            filtered
              ? "试试关闭「只看异常」或重置筛选。"
              : "导入打卡与 OA 数据后，点击「重新计算」生成日结果。"
          }
        />
      ) : (
        <div className="space-y-3">
          <div className="overflow-x-auto rounded-lg border">
            <Table data-testid="day-results-table">
              <TableHeader>
                <TableRow>
                  <TableHead>员工</TableHead>
                  <TableHead>部门</TableHead>
                  <TableHead>日期</TableHead>
                  <TableHead>日类型</TableHead>
                  <TableHead>排班</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>迟到 / 早退</TableHead>
                  <TableHead>请假 / 出差</TableHead>
                  <TableHead className="text-right">加班</TableHead>
                  <TableHead className="text-right">出勤</TableHead>
                  <TableHead className="text-right">工时</TableHead>
                  <TableHead className="text-right">扣款</TableHead>
                  <TableHead>标记</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => (
                  <TableRow
                    key={row.id}
                    data-testid={`day-result-row-${row.employee_id}-${row.work_date}`}
                    data-abnormal={row.is_abnormal}
                    tabIndex={0}
                    className={`cursor-pointer ${
                      row.is_abnormal ? "bg-destructive/5" : ""
                    }`}
                    onClick={() => onOpenDay(row.employee_id, row.work_date)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault()
                        onOpenDay(row.employee_id, row.work_date)
                      }
                    }}
                  >
                    <TableCell>
                      <div className="font-medium">
                        {row.employee_name ?? row.employee_id}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {row.employee_no ?? ""}
                      </div>
                    </TableCell>
                    <TableCell>{row.department_name ?? "—"}</TableCell>
                    <TableCell className="whitespace-nowrap">
                      {formatWorkDate(row.work_date)}
                    </TableCell>
                    <TableCell>{dayTypeLabel(row.day_type)}</TableCell>
                    <TableCell>{rosterStateLabel(row.roster_state)}</TableCell>
                    <TableCell>
                      <Badge variant={dayStatusVariant(row.day_status)}>
                        {dayStatusLabel(row.day_status)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {row.late_minutes || row.early_minutes ? (
                        <span>
                          迟 {row.late_minutes} / 早 {row.early_minutes} 分
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <LeaveTripCell result={row} />
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {totalOtMinutes(row) > 0
                        ? `${formatHours(totalOtMinutes(row))} h`
                        : "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatFraction(row.attendance_fraction)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatHours(row.worked_minutes)} h
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatAmount(row.deduction_total)}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {row.is_adjusted && (
                          <Badge variant="secondary">已调整</Badge>
                        )}
                        {(row.day_flags ?? []).slice(0, 2).map((flag) => (
                          <Badge key={flag} variant="outline">
                            {dayFlagLabel(flag)}
                          </Badge>
                        ))}
                        {!row.is_adjusted &&
                          (row.day_flags ?? []).length === 0 && (
                            <span className="text-muted-foreground">—</span>
                          )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <PaginationFooter
            count={count}
            skip={skip}
            pageSize={PAGE_SIZE}
            onSkipChange={setSkip}
            countTestId="day-result-count"
          />
        </div>
      )}
    </div>
  )
}
