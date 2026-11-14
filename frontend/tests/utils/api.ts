import {
  AttendanceShiftsService,
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
  LoginService,
  type PositionPublic,
  PositionsService,
  type ShiftPublic,
} from "../../src/client"
import { client } from "../../src/client/client.gen"
import { firstSuperuser, firstSuperuserPassword } from "../config"
import { todayShanghai } from "./date"

const API_URL = process.env.VITE_API_URL ?? "http://localhost:8000"

export type ApiCompany = CompanyPublic
export type ApiDepartment = DepartmentPublic
export type ApiPosition = PositionPublic
export type ApiCostCenter = CostCenterPublic
export type ApiEmployee = EmployeePublic
export type ApiShift = ShiftPublic

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

export async function resignEmployee(employeeId: string): Promise<ApiEmployee> {
  await ensureAuthenticated()
  const response = await EmployeesService.updateEmployee({
    path: { employee_id: employeeId },
    body: {
      status: "resigned",
      resign_date: todayShanghai(),
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
