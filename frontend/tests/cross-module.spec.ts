import { expect, type Page, test } from "@playwright/test"
import {
  createCompany,
  createDepartment,
  createEmployee,
  createPosition,
} from "./utils/api"
import { setActiveCompany } from "./utils/company"
import {
  randomCompanyCode,
  randomCompanyName,
  randomDepartmentCode,
  randomDepartmentName,
  randomEmployeeName,
  randomEmployeeNo,
  randomPositionCode,
  randomPositionName,
} from "./utils/random"

/** Creates an isolated company and makes it the active company. */
async function setupCompany(page: Page) {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  await setActiveCompany(page, company.id)
  return company
}

test("deleting a department clears the default department on its positions", async ({
  page,
}) => {
  const company = await setupCompany(page)
  const department = await createDepartment({
    company_id: company.id,
    dept_code: randomDepartmentCode(),
    dept_name: randomDepartmentName(),
  })
  const position = await createPosition({
    company_id: company.id,
    position_code: randomPositionCode(),
    position_name: randomPositionName(),
    dept_id: department.id,
  })

  await page.goto("/departments")
  await page
    .getByTestId("department-tree")
    .getByRole("button", { name: new RegExp(department.dept_name) })
    .click()
  await page.getByRole("button", { name: "删除" }).click()
  await page.getByRole("dialog").getByRole("button", { name: "删除" }).click()
  await expect(page.getByText("部门删除成功").first()).toBeVisible()

  await page.goto("/positions")
  const row = page
    .getByTestId("position-table")
    .getByRole("row")
    .filter({ hasText: position.position_code })
  await expect(row).toBeVisible()
  await expect(row).toContainText("未设置")
  await expect(row).not.toContainText(department.dept_name)
})

test("the employee manager selector rejects self and reporting cycles", async ({
  page,
}) => {
  const company = await setupCompany(page)
  const department = await createDepartment({
    company_id: company.id,
    dept_code: randomDepartmentCode(),
    dept_name: randomDepartmentName(),
  })
  const position = await createPosition({
    company_id: company.id,
    position_code: randomPositionCode(),
    position_name: randomPositionName(),
  })
  const managerNo = randomEmployeeNo()
  const managerName = randomEmployeeName()
  const reportNo = randomEmployeeNo()
  const reportName = randomEmployeeName()

  const manager = await createEmployee({
    employee_no: managerNo,
    name: managerName,
    dept_id: department.id,
    position_id: position.id,
  })
  await createEmployee({
    employee_no: reportNo,
    name: reportName,
    dept_id: department.id,
    position_id: position.id,
    manager_id: manager.id,
  })

  await page.goto("/employees")
  const managerRow = page
    .getByTestId("employee-table")
    .getByRole("row")
    .filter({ hasText: managerNo })
  await managerRow.getByRole("button", { name: "编辑" }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByRole("combobox", { name: "直属上级" }).click()

  const selfOption = page.getByRole("option", { name: new RegExp(managerName) })
  await expect(selfOption).toBeDisabled()
  const reportOption = page.getByRole("option", {
    name: new RegExp(reportName),
  })
  await expect(reportOption).toBeVisible()
  await expect(reportOption).toBeDisabled()
})

test("selectors never offer references from another company", async ({
  page,
}) => {
  const companyA = await setupCompany(page)
  const companyB = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  const departmentA = await createDepartment({
    company_id: companyA.id,
    dept_code: randomDepartmentCode(),
    dept_name: randomDepartmentName(),
  })
  const departmentB = await createDepartment({
    company_id: companyB.id,
    dept_code: randomDepartmentCode(),
    dept_name: randomDepartmentName(),
  })

  await page.goto("/departments")
  await page
    .getByTestId("department-tree")
    .getByRole("button", { name: new RegExp(departmentA.dept_name) })
    .click()
  await page.getByRole("button", { name: "编辑" }).click()
  const departmentDialog = page.getByRole("dialog")
  await departmentDialog.getByRole("combobox", { name: "上级部门" }).click()
  await expect(
    page.getByRole("option", { name: new RegExp(departmentB.dept_name) }),
  ).toHaveCount(0)
  await page.keyboard.press("Escape")

  await page.goto("/employees")
  await page.getByRole("button", { name: "新增员工" }).first().click()
  const employeeDialog = page.getByRole("dialog")
  await employeeDialog.getByRole("combobox", { name: "部门" }).click()
  await expect(
    page.getByRole("option", { name: new RegExp(departmentA.dept_name) }),
  ).toBeVisible()
  await expect(
    page.getByRole("option", { name: new RegExp(departmentB.dept_name) }),
  ).toHaveCount(0)
})
