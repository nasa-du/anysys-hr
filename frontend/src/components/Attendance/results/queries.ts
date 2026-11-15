import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  type AttendanceAdjustmentCreate,
  type AttendanceAdjustmentPublic,
  AttendanceAdjustmentsService,
  type AttendanceDayDetailPublic,
  type AttendanceDayResultsPublic,
  type AttendanceMonthPublic,
  type AttendanceMonthSummariesPublic,
  AttendanceMonthsService,
  AttendanceResultsService,
  type CalcRunsPublic,
  type DayStatus,
  type DayType,
  DepartmentsService,
  type EmployeeResultCalendarPublic,
  EmployeesService,
  type ResultRosterState,
} from "@/client"
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorMessage } from "@/lib/api-error"

export type DayResultFilters = {
  isAbnormalOnly: boolean
  adjustedOnly: boolean
  deptId: string
  employeeId: string
  dateFrom: string
  dateTo: string
  dayType: DayType | "all"
  rosterState: ResultRosterState | "all"
  dayStatus: DayStatus | "all"
  flag: string | "all"
  keyword: string
}

export const EMPTY_DAY_RESULT_FILTERS: DayResultFilters = {
  isAbnormalOnly: false,
  adjustedOnly: false,
  deptId: "all",
  employeeId: "all",
  dateFrom: "",
  dateTo: "",
  dayType: "all",
  rosterState: "all",
  dayStatus: "all",
  flag: "all",
  keyword: "",
}

export type SummaryFilters = {
  deptId: string
  employeeId: string
  keyword: string
}

export const EMPTY_SUMMARY_FILTERS: SummaryFilters = {
  deptId: "all",
  employeeId: "all",
  keyword: "",
}

export function dayResultsQueryKey(
  companyId: string,
  month: string,
  filters: DayResultFilters,
  skip: number,
  limit: number,
) {
  return [
    "attendance",
    "results",
    "days",
    companyId,
    month,
    { ...filters, skip, limit },
  ] as const
}

export function monthSummariesQueryKey(
  companyId: string,
  month: string,
  filters: SummaryFilters,
  skip: number,
  limit: number,
) {
  return [
    "attendance",
    "results",
    "summary",
    companyId,
    month,
    { ...filters, skip, limit },
  ] as const
}

export function resultCalendarQueryKey(
  companyId: string,
  month: string,
  employeeId: string,
) {
  return [
    "attendance",
    "results",
    "calendar",
    companyId,
    month,
    employeeId,
  ] as const
}

export function monthStateQueryKey(companyId: string, month: string) {
  return ["attendance", "months", "detail", companyId, month] as const
}

export function calcRunsQueryKey(
  companyId: string,
  month: string,
  skip: number,
  limit: number,
) {
  return [
    "attendance",
    "months",
    "calc-runs",
    companyId,
    month,
    { skip, limit },
  ] as const
}

/** Calculation and import changes invalidate results and month state (spec 8.9). */
export function invalidateResultQueries(
  queryClient: ReturnType<typeof useQueryClient>,
): void {
  void queryClient.invalidateQueries({ queryKey: ["attendance", "results"] })
  void queryClient.invalidateQueries({ queryKey: ["attendance", "months"] })
}

export function useResultDepartments(companyId: string) {
  return useQuery({
    queryKey: ["attendance", "reference", "departments", companyId],
    queryFn: async () => {
      const response = await DepartmentsService.readDepartments({
        query: { company_id: companyId, limit: 500 },
      })
      return response.data.data
    },
    enabled: Boolean(companyId),
  })
}

export function useResultEmployees(companyId: string) {
  return useQuery({
    queryKey: ["attendance", "reference", "employees", companyId],
    queryFn: async () => {
      const response = await EmployeesService.readEmployees({
        query: { company_id: companyId, limit: 500 },
      })
      return response.data.data
    },
    enabled: Boolean(companyId),
  })
}

export function useMonthState(companyId: string, month: string) {
  return useQuery({
    queryKey: monthStateQueryKey(companyId, month),
    queryFn: async (): Promise<AttendanceMonthPublic> => {
      const response = await AttendanceMonthsService.readMonth({
        path: { month },
        query: { company_id: companyId },
      })
      return response.data
    },
    enabled: Boolean(companyId && month),
  })
}

export function useDayResults(
  companyId: string,
  month: string,
  filters: DayResultFilters,
  skip: number,
  limit: number,
) {
  return useQuery({
    queryKey: dayResultsQueryKey(companyId, month, filters, skip, limit),
    queryFn: async (): Promise<AttendanceDayResultsPublic> => {
      const keyword = filters.keyword.trim()
      const response = await AttendanceResultsService.readDayResults({
        query: {
          company_id: companyId,
          month,
          skip,
          limit,
          ...(filters.isAbnormalOnly ? { is_abnormal: true } : {}),
          ...(filters.adjustedOnly ? { has_adjustment: true } : {}),
          ...(filters.deptId !== "all" ? { dept_id: filters.deptId } : {}),
          ...(filters.employeeId !== "all"
            ? { employee_id: filters.employeeId }
            : {}),
          ...(filters.dateFrom ? { date_from: filters.dateFrom } : {}),
          ...(filters.dateTo ? { date_to: filters.dateTo } : {}),
          ...(filters.dayType !== "all" ? { day_type: filters.dayType } : {}),
          ...(filters.rosterState !== "all"
            ? { roster_state: filters.rosterState }
            : {}),
          ...(filters.dayStatus !== "all"
            ? { day_status: [filters.dayStatus] }
            : {}),
          ...(filters.flag !== "all" ? { flag: [filters.flag] } : {}),
          ...(keyword ? { keyword } : {}),
        },
      })
      return response.data
    },
    enabled: Boolean(companyId && month),
  })
}

export function useMonthSummaries(
  companyId: string,
  month: string,
  filters: SummaryFilters,
  skip: number,
  limit: number,
) {
  return useQuery({
    queryKey: monthSummariesQueryKey(companyId, month, filters, skip, limit),
    queryFn: async (): Promise<AttendanceMonthSummariesPublic> => {
      const keyword = filters.keyword.trim()
      const response = await AttendanceResultsService.readMonthSummaries({
        query: {
          company_id: companyId,
          month,
          skip,
          limit,
          ...(filters.deptId !== "all" ? { dept_id: filters.deptId } : {}),
          ...(filters.employeeId !== "all"
            ? { employee_id: filters.employeeId }
            : {}),
          ...(keyword ? { keyword } : {}),
        },
      })
      return response.data
    },
    enabled: Boolean(companyId && month),
  })
}

export function useDayDetail(
  companyId: string,
  employeeId: string | null,
  workDate: string | null,
) {
  return useQuery({
    queryKey: [
      "attendance",
      "results",
      "detail",
      companyId,
      employeeId,
      workDate,
    ],
    queryFn: async (): Promise<AttendanceDayDetailPublic> => {
      const response = await AttendanceResultsService.readDayDetail({
        path: {
          employee_id: employeeId as string,
          work_date: workDate as string,
        },
        query: { company_id: companyId },
      })
      return response.data
    },
    enabled: Boolean(companyId && employeeId && workDate),
  })
}

export function useResultCalendar(
  companyId: string,
  month: string,
  employeeId: string | null,
) {
  return useQuery({
    queryKey: resultCalendarQueryKey(companyId, month, employeeId ?? ""),
    queryFn: async (): Promise<EmployeeResultCalendarPublic> => {
      const response = await AttendanceResultsService.readResultCalendar({
        query: {
          company_id: companyId,
          month,
          employee_id: employeeId as string,
        },
      })
      return response.data
    },
    enabled: Boolean(companyId && month && employeeId),
  })
}

export function useCalcRuns(
  companyId: string,
  month: string,
  skip: number,
  limit: number,
) {
  return useQuery({
    queryKey: calcRunsQueryKey(companyId, month, skip, limit),
    queryFn: async (): Promise<CalcRunsPublic> => {
      const response = await AttendanceMonthsService.readCalcRuns({
        path: { month },
        query: { company_id: companyId, skip, limit },
      })
      return response.data
    },
    enabled: Boolean(companyId && month),
  })
}

/** Explicit recalculation; the API never recalculates automatically. */
export function useRecalculateMonth(companyId: string, month: string) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: async () => {
      const response = await AttendanceMonthsService.calculateMonth({
        path: { month },
        query: { company_id: companyId },
      })
      return response.data
    },
    onSuccess: (data) => {
      showSuccessToast(
        `重新计算完成：${data.summary?.employees_calculated ?? 0} 人、${
          data.summary?.days_total ?? 0
        } 天`,
      )
      invalidateResultQueries(queryClient)
    },
    onError: (error) => showErrorToast(getErrorMessage(error)),
  })
}

/** Creating a version refreshes results, adjustment history, and month state. */
export function useCreateAdjustment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (
      body: AttendanceAdjustmentCreate,
    ): Promise<AttendanceAdjustmentPublic> => {
      const response = await AttendanceAdjustmentsService.createAdjustment({
        body,
      })
      return response.data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["attendance", "results", "adjustments"],
      })
      invalidateResultQueries(queryClient)
    },
  })
}
