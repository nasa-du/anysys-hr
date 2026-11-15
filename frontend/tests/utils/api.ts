import {
  type AttendanceAdjustmentPublic,
  AttendanceAdjustmentsService,
  type AttendanceAdjustmentValues,
  AttendanceHolidaysService,
  AttendanceImportsService,
  type AttendanceMonthPublic,
  AttendanceMonthsService,
  AttendanceRosterService,
  AttendanceRulesService,
  AttendanceSchedulePlansService,
  AttendanceShiftsService,
  type CalcRunPublic,
  CompaniesService,
  type CompanyPublic,
  type ContractType,
  type CostCenterPublic,
  CostCentersService,
  type DepartmentPublic,
  DepartmentsService,
  type EmployeePublic,
  type EmployeeStatus,
  EmployeesService,
  type HolidayDayType,
  type HolidayPublic,
  LoginService,
  type PlanDayInput,
  type PositionPublic,
  PositionsService,
  type RosterEntryPublic,
  type RosterState,
  type SchedulePlanPublic,
  type ScheduleScopeType,
  type ShiftPublic,
} from "../../src/client"
import { client } from "../../src/client/client.gen"
import { firstSuperuser, firstSuperuserPassword } from "../config"
import { todayShanghai } from "./date"
import {
  randomCompanyCode,
  randomCompanyName,
  randomDepartmentCode,
  randomEmployeeName,
  randomEmployeeNo,
  randomPositionCode,
  randomShiftCode,
  randomShiftName,
} from "./random"

const API_URL = process.env.VITE_API_URL ?? "http://localhost:8000"

export type ApiCompany = CompanyPublic
export type ApiDepartment = DepartmentPublic
export type ApiPosition = PositionPublic
export type ApiCostCenter = CostCenterPublic
export type ApiEmployee = EmployeePublic
export type ApiShift = ShiftPublic
export type ApiHoliday = HolidayPublic

let authentication: Promise<void> | null = null

/** Configure the generated client with the dev API and a superuser token. */
async function ensureAuthenticated(): Promise<void> {
  if (authentication === null) {
    authentication = (async () => {
      client.setConfig({ baseURL: API_URL })
      const response = await LoginService.loginAccessToken({
        body: {
          username: firstSuperuser,
          password: firstSuperuserPassword,
        },
      })
      const accessToken = response.data.access_token
      client.setConfig({ auth: () => accessToken })
    })()
  }
  return authentication
}

export async function createCompany(input: {
  company_code: string
  company_name: string
}): Promise<ApiCompany> {
  await ensureAuthenticated()
  const response = await CompaniesService.createCompany({
    body: { ...input, is_active: true },
  })
  return response.data
}

export async function createDepartment(input: {
  company_id: string
  dept_code: string
  dept_name: string
  parent_id?: string | null
}): Promise<ApiDepartment> {
  await ensureAuthenticated()
  const response = await DepartmentsService.createDepartment({ body: input })
  return response.data
}

export async function createPosition(input: {
  company_id: string
  position_code: string
  position_name: string
  dept_id?: string | null
}): Promise<ApiPosition> {
  await ensureAuthenticated()
  const response = await PositionsService.createPosition({ body: input })
  return response.data
}

export async function createCostCenter(input: {
  company_id: string
  cost_org_code: string
  cost_org_name: string
}): Promise<ApiCostCenter> {
  await ensureAuthenticated()
  const response = await CostCentersService.createCostCenter({ body: input })
  return response.data
}

export async function createShift(input: {
  company_id: string
  shift_code: string
  shift_name: string
  start_time?: string
  end_time?: string
  cross_day?: boolean
  break_start?: string | null
  break_end?: string | null
  rest_minutes?: number
  color?: string | null
  note?: string | null
  is_active?: boolean
}): Promise<ApiShift> {
  await ensureAuthenticated()
  const response = await AttendanceShiftsService.createShift({
    body: {
      company_id: input.company_id,
      shift_code: input.shift_code,
      shift_name: input.shift_name,
      start_time: input.start_time ?? "08:30:00",
      end_time: input.end_time ?? "17:30:00",
      cross_day: input.cross_day ?? false,
      break_start: input.break_start ?? null,
      break_end: input.break_end ?? null,
      rest_minutes: input.rest_minutes ?? 60,
      color: input.color ?? null,
      note: input.note ?? null,
      is_active: input.is_active ?? true,
    },
  })
  return response.data
}

export async function readShift(shiftId: string): Promise<ApiShift> {
  await ensureAuthenticated()
  const response = await AttendanceShiftsService.readShift({
    path: { shift_id: shiftId },
  })
  return response.data
}

export async function createHoliday(input: {
  company_id: string
  date: string
  name: string
  day_type?: HolidayDayType
  note?: string | null
}): Promise<ApiHoliday> {
  await ensureAuthenticated()
  const response = await AttendanceHolidaysService.createHoliday({
    body: {
      company_id: input.company_id,
      date: input.date,
      name: input.name,
      day_type: input.day_type ?? "holiday",
      note: input.note ?? null,
    },
  })
  return response.data
}

export async function readHolidays(
  companyId: string,
  year: number,
): Promise<ApiHoliday[]> {
  await ensureAuthenticated()
  const response = await AttendanceHolidaysService.readHolidays({
    query: { company_id: companyId, year, skip: 0, limit: 500 },
  })
  return response.data.data
}

export async function resignEmployee(
  employeeId: string,
  resignDate?: string,
): Promise<ApiEmployee> {
  await ensureAuthenticated()
  const response = await EmployeesService.updateEmployee({
    path: { employee_id: employeeId },
    body: {
      status: "resigned",
      resign_date: resignDate ?? todayShanghai(),
    },
  })
  return response.data
}

export async function createEmployee(input: {
  employee_no: string
  name: string
  dept_id: string
  position_id: string
  cost_org_id?: string | null
  manager_id?: string | null
  status?: EmployeeStatus
  hire_date?: string
  contract_type?: ContractType
}): Promise<ApiEmployee> {
  await ensureAuthenticated()
  const response = await EmployeesService.createEmployee({
    body: {
      ...input,
      hire_date: input.hire_date ?? todayShanghai(),
      contract_type: input.contract_type ?? "full_time",
      status: input.status ?? "active",
    },
  })
  return response.data
}

export async function createSchedulePlan(input: {
  company_id: string
  month: string
  plan_name: string
  scope_type?: ScheduleScopeType
  scope_ids?: string[]
  days?: PlanDayInput[]
  note?: string | null
}): Promise<SchedulePlanPublic> {
  await ensureAuthenticated()
  const response = await AttendanceSchedulePlansService.createSchedulePlan({
    body: {
      company_id: input.company_id,
      month: input.month,
      plan_name: input.plan_name,
      scope_type: input.scope_type ?? "all",
      scope_ids: input.scope_ids ?? [],
      days: input.days ?? [],
      note: input.note ?? null,
    },
  })
  return response.data
}

export async function readSchedulePlans(
  companyId: string,
  month: string,
): Promise<SchedulePlanPublic[]> {
  await ensureAuthenticated()
  const response = await AttendanceSchedulePlansService.readSchedulePlans({
    query: { company_id: companyId, month, limit: 500 },
  })
  return response.data.data
}

export async function createManualRosterEntry(input: {
  employee_id: string
  work_date: string
  state: RosterState
  shifts?: Array<{ seq: number; shift_id: string }>
  note?: string | null
}): Promise<RosterEntryPublic> {
  await ensureAuthenticated()
  const response = await AttendanceRosterService.createRosterEntry({
    body: {
      employee_id: input.employee_id,
      work_date: input.work_date,
      state: input.state,
      shifts: input.shifts ?? [],
      note: input.note ?? null,
    },
  })
  return response.data
}

export async function readRosterEntries(
  companyId: string,
  month: string,
  employeeId?: string,
): Promise<RosterEntryPublic[]> {
  await ensureAuthenticated()
  const response = await AttendanceRosterService.readRosterEntries({
    query: {
      company_id: companyId,
      month,
      employee_id: employeeId,
      limit: 500,
    },
  })
  return response.data.data
}

/** Upload one punch text through preview + commit; returns the committed batch id. */
export async function importPunchText(input: {
  company_id: string
  month: string
  text: string
}): Promise<string> {
  await ensureAuthenticated()
  const preview = await AttendanceImportsService.previewImports({
    body: {
      company_id: input.company_id,
      data_type: "punch",
      month: input.month,
      text: input.text,
    },
  })
  const batchId = preview.data.batch.id
  await AttendanceImportsService.commitImport({ path: { batch_id: batchId } })
  return batchId
}

export async function calculateMonth(
  companyId: string,
  month: string,
): Promise<CalcRunPublic> {
  await ensureAuthenticated()
  const response = await AttendanceMonthsService.calculateMonth({
    path: { month },
    query: { company_id: companyId },
  })
  return response.data
}

export async function confirmMonth(
  companyId: string,
  month: string,
): Promise<AttendanceMonthPublic> {
  await ensureAuthenticated()
  const response = await AttendanceMonthsService.confirmMonth({
    path: { month },
    query: { company_id: companyId },
  })
  return response.data
}

export async function lockMonth(
  companyId: string,
  month: string,
): Promise<AttendanceMonthPublic> {
  await ensureAuthenticated()
  const response = await AttendanceMonthsService.lockMonth({
    path: { month },
    query: { company_id: companyId },
  })
  return response.data
}

export async function unlockMonth(
  companyId: string,
  month: string,
  reason: string,
): Promise<AttendanceMonthPublic> {
  await ensureAuthenticated()
  const response = await AttendanceMonthsService.unlockMonth({
    path: { month },
    query: { company_id: companyId },
    body: { reason },
  })
  return response.data
}

/** Change one rule field so calculated months become stale. */
export async function updateAttendanceRule(
  companyId: string,
  input: { late_grace_min?: number },
): Promise<void> {
  await ensureAuthenticated()
  await AttendanceRulesService.updateCompanyRule({
    query: { company_id: companyId },
    body: input,
  })
}

/** Create one manual adjustment version through the public API. */
export async function createAdjustment(input: {
  company_id: string
  employee_id: string
  work_date: string
  base_version: number
  adjusted_values: AttendanceAdjustmentValues
  reason: string
}): Promise<AttendanceAdjustmentPublic> {
  await ensureAuthenticated()
  const response = await AttendanceAdjustmentsService.createAdjustment({
    body: input,
  })
  return response.data
}

export type AttendanceBootstrap = {
  company: ApiCompany
  department: ApiDepartment
  position: ApiPosition
  employee: ApiEmployee
  employeeNo: string
  shift: ApiShift
}

export type AttendanceBootstrapOptions = {
  employeeName?: string
  employeeNo?: string
  shiftName?: string
  /** When present, creates `work` roster rows and punches and calculates. */
  workDates?: string[]
  month?: string
}

/**
 * Create a minimal isolated attendance company used by one test.
 *
 * Every data-driven Playwright attendance test owns its company so shards
 * never share filters, states, or counts, and no test depends on the
 * development seed. Specs that need the full E101–E113 fixture roster build it
 * themselves (see attendance-imports.spec.ts).
 */
export async function bootstrapAttendanceCompany(
  options: AttendanceBootstrapOptions = {},
): Promise<AttendanceBootstrap> {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  const department = await createDepartment({
    company_id: company.id,
    dept_code: randomDepartmentCode(),
    dept_name: "生产部",
  })
  const position = await createPosition({
    company_id: company.id,
    position_code: randomPositionCode(),
    position_name: "操作工",
    dept_id: department.id,
  })
  const employeeNo = options.employeeNo ?? randomEmployeeNo()
  const employee = await createEmployee({
    employee_no: employeeNo,
    name: options.employeeName ?? randomEmployeeName(),
    dept_id: department.id,
    position_id: position.id,
    hire_date: "2026-01-01",
  })
  const shift = await createShift({
    company_id: company.id,
    shift_code: randomShiftCode(),
    shift_name: options.shiftName ?? randomShiftName(),
  })
  if (options.workDates && options.workDates.length > 0) {
    for (const workDate of options.workDates) {
      await createManualRosterEntry({
        employee_id: employee.id,
        work_date: workDate,
        state: "work",
        shifts: [{ seq: 0, shift_id: shift.id }],
      })
    }
    const month = options.month ?? options.workDates[0].slice(0, 7)
    await importPunchText({
      company_id: company.id,
      month,
      text: [
        "工号,考勤日期,打卡时间,打卡结果",
        ...options.workDates.flatMap((workDate) => [
          `${employeeNo},${workDate},${workDate} 08:20,正常`,
          `${employeeNo},${workDate},${workDate} 17:35,正常`,
        ]),
      ].join("\n"),
    })
    await calculateMonth(company.id, month)
  }
  return { company, department, position, employee, employeeNo, shift }
}
