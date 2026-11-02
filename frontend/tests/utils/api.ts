import {
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
