import { expect, type Page, test } from "@playwright/test"
import {
  type ApiCompany,
  type ApiCostCenter,
  type ApiDepartment,
  type ApiPosition,
  createCompany,
  createCostCenter,
  createDepartment,
  createEmployee,
  createPosition,
  resignEmployee,
} from "./utils/api"
import { todayShanghai } from "./utils/date"
import {
  randomCompanyCode,
  randomCompanyName,
  randomCostCenterCode,
  randomCostCenterName,
  randomDepartmentCode,
  randomDepartmentName,
  randomEmployeeName,
  randomEmployeeNo,
  randomPositionCode,
  randomPositionName,
} from "./utils/random"

test.setTimeout(120_000)

const COMPANY_STORAGE_KEY = "basic-management.company_id"

interface Organization {
  company: ApiCompany
  rootDept: ApiDepartment
  childDept: ApiDepartment | null
  position: ApiPosition
  costCenter: ApiCostCenter | null
}

interface SetupOptions {
  withChildDepartment?: boolean
  withCostCenter?: boolean
}

/** Creates an isolated company via the API and scopes the page to it. */
async function setupOrganization(
  page: Page,
  { withChildDepartment = false, withCostCenter = true }: SetupOptions = {},
): Promise<Organization> {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  const rootDept = await createDepartment({
    company_id: company.id,
    dept_code: randomDepartmentCode(),
    dept_name: randomDepartmentName(),
  })
  let childDept: ApiDepartment | null = null
  if (withChildDepartment) {
    childDept = await createDepartment({
      company_id: company.id,
      dept_code: randomDepartmentCode(),
      dept_name: randomDepartmentName(),
      parent_id: rootDept.id,
    })
  }
  const position = await createPosition({
    company_id: company.id,
    position_code: randomPositionCode(),
    position_name: randomPositionName(),
    dept_id: rootDept.id,
  })
  const costCenter = withCostCenter
    ? await createCostCenter({
        company_id: company.id,
        cost_org_code: randomCostCenterCode(),
        cost_org_name: randomCostCenterName(),
      })
    : null

  await page.addInitScript(
    ([key, companyId]: [string, string]) => {
      window.localStorage.setItem(key, companyId)
    },
    [COMPANY_STORAGE_KEY, company.id],
  )
  await page.goto("/employees")
  await expect(
    page.getByRole("heading", { name: "员工", exact: true }),
  ).toBeVisible()
  return { company, rootDept, childDept, position, costCenter }
}

interface EmployeeInput {
  employeeNo: string
  name: string
  departmentName: string
  positionName: string
  costCenterName?: string
  managerName?: string
  status?: "在职" | "试用期"
}

async function submitEmployee(page: Page, input: EmployeeInput) {
  await page.getByRole("button", { name: "新增员工" }).first().click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("工号").fill(input.employeeNo)
  await dialog.getByLabel("姓名").fill(input.name)
  await dialog.getByLabel("入职日期").fill(todayShanghai())
  if (input.status === "试用期") {
    await dialog.getByRole("combobox", { name: "状态" }).click()
    await page.getByRole("option", { name: "试用期" }).click()
  }

  await dialog.getByRole("combobox", { name: "部门" }).click()
  await page
    .getByRole("option", { name: new RegExp(input.departmentName) })
    .click()
  await dialog.getByRole("combobox", { name: "岗位" }).click()
  await page
    .getByRole("option", { name: new RegExp(input.positionName) })
    .click()
  if (input.managerName) {
    await dialog.getByRole("combobox", { name: "直属上级" }).click()
    await page
      .getByRole("option", { name: new RegExp(input.managerName) })
      .click()
  }
  if (input.costCenterName) {
    await dialog.getByRole("combobox", { name: "成本中心" }).click()
    await page
      .getByRole("option", { name: new RegExp(input.costCenterName) })
      .click()
  }

  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("员工创建成功").first()).toBeVisible()
  await expect(employeeRow(page, input.employeeNo)).toBeVisible()
}

function employeeRow(page: Page, employeeNo: string) {
  return page
    .getByTestId("employee-table")
    .getByRole("row")
    .filter({ hasText: employeeNo })
}

async function selectStatusFilter(page: Page, label: string) {
  await page.getByRole("combobox", { name: "状态筛选" }).click()
  await page.getByRole("option", { name: label, exact: true }).click()
}

test("sidebar shows the Employees entry and the page follows the company switcher", async ({
  page,
}) => {
  const organization = await setupOrganization(page)

  await expect(
    page.getByRole("link", { name: "员工", exact: true }),
  ).toBeVisible()
  await expect(page.getByRole("combobox", { name: "切换公司" })).toContainText(
    organization.company.company_name,
  )
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "还没有员工",
  )
})

test("create employees with the department tree, a manager, and a cost center", async ({
  page,
}) => {
  const organization = await setupOrganization(page, {
    withChildDepartment: true,
  })
  const managerNo = randomEmployeeNo()
  const managerName = randomEmployeeName()
  const reportNo = randomEmployeeNo()
  const reportName = randomEmployeeName()

  await submitEmployee(page, {
    employeeNo: managerNo,
    name: managerName,
    departmentName: organization.rootDept.dept_name,
    positionName: organization.position.position_name,
  })
  await expect(employeeRow(page, managerNo)).toContainText(managerName)

  await submitEmployee(page, {
    employeeNo: reportNo,
    name: reportName,
    departmentName: organization.childDept?.dept_name ?? "",
    positionName: organization.position.position_name,
    costCenterName: organization.costCenter?.cost_org_name,
    managerName,
    status: "试用期",
  })

  const row = employeeRow(page, reportNo)
  await expect(row).toContainText(reportName)
  await expect(row).toContainText(organization.childDept?.dept_name ?? "")
  await expect(row).toContainText(organization.position.position_name)
  await expect(row).toContainText(organization.costCenter?.cost_org_name ?? "")
  await expect(row).toContainText("试用期")
  await expect(row).toContainText(`上级 ${managerName}`)

  await row.click()
  const detail = page.getByTestId("employee-detail")
  await expect(detail).toBeVisible()
  await expect(detail).toContainText("基本信息")
  await expect(detail).toContainText("行政归属")
  await expect(detail).toContainText("成本归属")
  await expect(detail).toContainText("汇报关系")
  await expect(detail).toContainText(organization.childDept?.dept_name ?? "")
  await expect(detail).toContainText(
    organization.costCenter?.cost_org_name ?? "",
  )
  await expect(detail).toContainText(managerName)
  await expect(detail).toContainText("试用期")
})

test("filters by keyword, status, position, cost center, and department subtree", async ({
  page,
}) => {
  const organization = await setupOrganization(page, {
    withChildDepartment: true,
  })
  const firstPosition = await createPosition({
    company_id: organization.company.id,
    position_code: randomPositionCode(),
    position_name: randomPositionName(),
  })

  const rootNo = randomEmployeeNo()
  const rootName = randomEmployeeName()
  const childNo = randomEmployeeNo()
  const childName = randomEmployeeName()
  const leftNo = randomEmployeeNo()
  const leftName = randomEmployeeName()

  await createEmployee({
    employee_no: rootNo,
    name: rootName,
    dept_id: organization.rootDept.id,
    position_id: firstPosition.id,
    cost_org_id: organization.costCenter?.id,
  })
  await createEmployee({
    employee_no: childNo,
    name: childName,
    dept_id: organization.childDept?.id ?? organization.rootDept.id,
    position_id: organization.position.id,
    status: "probation",
  })
  await createEmployee({
    employee_no: leftNo,
    name: leftName,
    dept_id: organization.rootDept.id,
    position_id: firstPosition.id,
    cost_org_id: organization.costCenter?.id,
  })
  await page.reload()
  await expect(employeeRow(page, rootNo)).toBeVisible()

  await employeeRow(page, leftNo).getByRole("button", { name: "离职" }).click()
  const leaveDialog = page.getByRole("dialog")
  await leaveDialog.getByLabel("离职日期").fill(todayShanghai())
  await leaveDialog.getByRole("button", { name: "确认离职" }).click()
  await expect(page.getByText("员工已办理离职").first()).toBeVisible()

  // The default filter is active + probation, so the resigned row is hidden.
  await expect(employeeRow(page, leftNo)).toHaveCount(0)

  await page.getByLabel("搜索员工").fill(rootNo)
  await expect(employeeRow(page, rootNo)).toBeVisible()
  await expect(employeeRow(page, childNo)).toHaveCount(0)
  await page.getByLabel("搜索员工").fill("")
  await expect(employeeRow(page, childNo)).toBeVisible()

  await page.getByRole("combobox", { name: "岗位筛选" }).click()
  await page
    .getByRole("option", {
      name: new RegExp(organization.position.position_name),
    })
    .click()
  await expect(employeeRow(page, childNo)).toBeVisible()
  await expect(employeeRow(page, rootNo)).toHaveCount(0)
  await page.getByRole("combobox", { name: "岗位筛选" }).click()
  await page.getByRole("option", { name: "全部岗位" }).click()

  await page.getByRole("combobox", { name: "成本中心筛选" }).click()
  await page
    .getByRole("option", {
      name: new RegExp(organization.costCenter?.cost_org_name ?? ""),
    })
    .click()
  await expect(employeeRow(page, rootNo)).toBeVisible()
  await expect(employeeRow(page, childNo)).toHaveCount(0)

  await page.getByRole("combobox", { name: "成本中心筛选" }).click()
  await page.getByRole("option", { name: "未分配", exact: true }).click()
  await expect(page.getByTestId("unassigned-banner")).toBeVisible()
  await expect(employeeRow(page, childNo)).toBeVisible()
  await expect(employeeRow(page, rootNo)).toHaveCount(0)

  await page.getByRole("combobox", { name: "成本中心筛选" }).click()
  await page.getByRole("option", { name: "全部成本中心" }).click()
  await page.getByRole("button", { name: "全部部门" }).click()
  await expect(employeeRow(page, rootNo)).toBeVisible()
  await expect(employeeRow(page, childNo)).toBeVisible()

  await selectStatusFilter(page, "离职")
  await expect(employeeRow(page, leftNo)).toBeVisible()
  await expect(employeeRow(page, rootNo)).toHaveCount(0)

  await selectStatusFilter(page, "在职 + 试用期")
  await page
    .getByTestId("department-tree")
    .getByRole("button", {
      name: new RegExp(organization.rootDept.dept_name),
    })
    .click()
  await expect(employeeRow(page, rootNo)).toBeVisible()
  await expect(employeeRow(page, childNo)).toBeVisible()

  await page
    .getByTestId("department-tree")
    .getByRole("button", {
      name: new RegExp(organization.childDept?.dept_name ?? ""),
    })
    .click()
  await expect(employeeRow(page, childNo)).toBeVisible()
  await expect(employeeRow(page, rootNo)).toHaveCount(0)
})

test("leave an employee and lock the resigned record", async ({ page }) => {
  const organization = await setupOrganization(page)
  const employeeNo = randomEmployeeNo()
  await createEmployee({
    employee_no: employeeNo,
    name: randomEmployeeName(),
    dept_id: organization.rootDept.id,
    position_id: organization.position.id,
    cost_org_id: organization.costCenter?.id,
  })
  await page.reload()
  await expect(employeeRow(page, employeeNo)).toBeVisible()

  await employeeRow(page, employeeNo)
    .getByRole("button", { name: "离职" })
    .click()
  const leaveDialog = page.getByRole("dialog")
  await leaveDialog.getByLabel("离职日期").fill(todayShanghai())
  await leaveDialog.getByLabel("备注").fill("首次离职备注")
  await leaveDialog.getByRole("button", { name: "确认离职" }).click()
  await expect(page.getByText("员工已办理离职").first()).toBeVisible()

  await expect(employeeRow(page, employeeNo)).toHaveCount(0)

  await selectStatusFilter(page, "离职")
  await employeeRow(page, employeeNo).click()
  const detail = page.getByTestId("employee-detail")
  await expect(detail).toBeVisible()
  await expect(detail).toContainText("离职")
  await expect(detail).toContainText("首次离职备注")
  await expect(detail).toContainText("离职为终态")
  // The sheet footer sits under the dev-only TanStack devtools toggle, so open
  // the correction form from the table action instead.
  await expect(detail.getByRole("button", { name: "修正" })).toBeVisible()
  await detail.getByRole("button", { name: "关闭" }).click()
  await expect(detail).not.toBeVisible()
  await employeeRow(page, employeeNo)
    .getByRole("button", { name: "编辑" })
    .click()
  const correction = page.getByRole("dialog")
  await expect(correction).toContainText("修正离职信息")
  await expect(correction.getByLabel("姓名")).toHaveCount(0)
  await expect(correction.getByLabel("部门")).toHaveCount(0)
  await expect(correction.getByLabel("离职日期")).toBeVisible()
  await correction.getByLabel("备注").fill("修正后的备注")
  await correction.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("员工信息已更新").first()).toBeVisible()

  await employeeRow(page, employeeNo).click()
  await expect(detail).toContainText("修正后的备注")
  await expect(detail).toContainText("离职")
})

test("the cost center Unassigned entry opens the unassigned employee list", async ({
  page,
}) => {
  const organization = await setupOrganization(page)
  const unassignedNo = randomEmployeeNo()
  const assignedNo = randomEmployeeNo()

  await createEmployee({
    employee_no: unassignedNo,
    name: randomEmployeeName(),
    dept_id: organization.rootDept.id,
    position_id: organization.position.id,
  })
  await createEmployee({
    employee_no: assignedNo,
    name: randomEmployeeName(),
    dept_id: organization.rootDept.id,
    position_id: organization.position.id,
    cost_org_id: organization.costCenter?.id,
  })

  await page.goto("/cost-centers")
  await page.getByTestId("cost-center-unassigned").click()
  await page.waitForURL(/unassigned_cost_org=true/)
  await expect(
    page.getByRole("heading", { name: "员工", exact: true }),
  ).toBeVisible()
  await expect(page.getByTestId("unassigned-banner")).toBeVisible()
  await expect(employeeRow(page, unassignedNo)).toBeVisible()
  await expect(employeeRow(page, assignedNo)).toHaveCount(0)
})

test("department and cost center manager selectors offer active company employees", async ({
  page,
}) => {
  const organization = await setupOrganization(page)
  const managerNo = randomEmployeeNo()
  const managerName = randomEmployeeName()
  const resignedNo = randomEmployeeNo()
  const resignedName = randomEmployeeName()
  await createEmployee({
    employee_no: managerNo,
    name: managerName,
    dept_id: organization.rootDept.id,
    position_id: organization.position.id,
  })
  const resigned = await createEmployee({
    employee_no: resignedNo,
    name: resignedName,
    dept_id: organization.rootDept.id,
    position_id: organization.position.id,
  })
  await resignEmployee(resigned.id)

  await page.goto("/departments")
  await page
    .getByTestId("department-tree")
    .getByRole("button", {
      name: new RegExp(organization.rootDept.dept_name),
    })
    .click()
  await page.getByRole("button", { name: "编辑" }).click()
  let dialog = page.getByRole("dialog")
  await dialog.getByRole("combobox", { name: "直属上级" }).click()
  await expect(
    page.getByRole("option", { name: new RegExp(managerName) }),
  ).toBeEnabled()
  const resignedOption = page.getByRole("option", {
    name: new RegExp(resignedName),
  })
  await expect(resignedOption).toBeVisible()
  await expect(resignedOption).toBeDisabled()
  await expect(resignedOption).toContainText("已离职")
  await page.getByRole("option", { name: new RegExp(managerName) }).click()
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("部门更新成功").first()).toBeVisible()
  await expect(page.getByTestId("department-detail")).toContainText(managerName)

  await page.goto("/cost-centers")
  await page
    .getByTestId("cost-center-tree")
    .getByRole("button", {
      name: new RegExp(organization.costCenter?.cost_org_name ?? ""),
    })
    .click()
  await page.getByRole("button", { name: "编辑" }).click()
  dialog = page.getByRole("dialog")
  await dialog.getByRole("combobox", { name: "直属上级" }).click()
  await expect(
    page.getByRole("option", { name: new RegExp(managerName) }),
  ).toBeEnabled()
  await page.getByRole("option", { name: new RegExp(managerName) }).click()
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("成本中心更新成功").first()).toBeVisible()
  await expect(page.getByTestId("cost-center-detail")).toContainText(
    managerName,
  )
})

test("employee references block deleting departments, positions, and cost centers", async ({
  page,
}) => {
  const organization = await setupOrganization(page)
  const employeeNo = randomEmployeeNo()
  const name = randomEmployeeName()
  await createEmployee({
    employee_no: employeeNo,
    name,
    dept_id: organization.rootDept.id,
    position_id: organization.position.id,
    cost_org_id: organization.costCenter?.id,
  })

  await page.goto("/departments")
  await page
    .getByTestId("department-tree")
    .getByRole("button", {
      name: new RegExp(organization.rootDept.dept_name),
    })
    .click()
  await page.getByRole("button", { name: "删除" }).click()
  await page.getByRole("dialog").getByRole("button", { name: "删除" }).click()
  let blocked = page.getByTestId("blocked-dialog")
  await expect(blocked).toContainText("无法删除部门")
  await expect(blocked).toContainText(employeeNo)
  await expect(blocked).toContainText(name)
  await blocked.getByRole("button", { name: "知道了" }).click()

  await page.goto("/positions")
  const positionRow = page
    .getByTestId("position-table")
    .getByRole("row")
    .filter({ hasText: organization.position.position_name })
  await positionRow.getByRole("button", { name: "删除" }).click()
  await page.getByRole("dialog").getByRole("button", { name: "删除" }).click()
  blocked = page.getByTestId("blocked-dialog")
  await expect(blocked).toContainText("无法删除岗位")
  await expect(blocked).toContainText(employeeNo)
  await blocked.getByRole("button", { name: "知道了" }).click()

  await page.goto("/cost-centers")
  await page
    .getByTestId("cost-center-tree")
    .getByRole("button", {
      name: new RegExp(organization.costCenter?.cost_org_name ?? ""),
    })
    .click()
  await page.getByRole("button", { name: "删除" }).click()
  await page.getByRole("dialog").getByRole("button", { name: "删除" }).click()
  blocked = page.getByTestId("blocked-dialog")
  await expect(blocked).toContainText("无法删除成本中心")
  await expect(blocked).toContainText(employeeNo)
  await blocked.getByRole("button", { name: "知道了" }).click()
})

test("employee references block deleting and deactivating the company", async ({
  page,
}) => {
  const organization = await setupOrganization(page)
  const employeeNo = randomEmployeeNo()
  await createEmployee({
    employee_no: employeeNo,
    name: randomEmployeeName(),
    dept_id: organization.rootDept.id,
    position_id: organization.position.id,
    cost_org_id: organization.costCenter?.id,
  })

  await page.goto("/companies")
  const search = page.getByLabel("搜索公司")
  await search.fill(organization.company.company_code)
  const companyRow = page
    .getByRole("row")
    .filter({ hasText: organization.company.company_code })
  await expect(companyRow).toBeVisible()

  await companyRow.getByRole("button", { name: "删除" }).click()
  await page.getByRole("dialog").getByRole("button", { name: "删除" }).click()
  let blocked = page.getByTestId("blocked-dialog")
  await expect(blocked).toContainText("无法删除公司")
  await expect(blocked).toContainText(employeeNo)
  await blocked.getByRole("button", { name: "知道了" }).click()

  await companyRow.getByRole("button", { name: "编辑" }).click()
  const form = page.getByRole("dialog")
  const statusSwitch = form.getByRole("switch", { name: "状态" })
  await expect(statusSwitch).toHaveAttribute("aria-checked", "true")
  await statusSwitch.click()
  await form.getByRole("button", { name: "保存" }).click()
  blocked = page.getByTestId("blocked-dialog")
  await expect(blocked).toContainText("无法停用公司")
  await expect(blocked).toContainText(employeeNo)
  await blocked.getByRole("button", { name: "知道了" }).click()
  await expect(statusSwitch).toHaveAttribute("aria-checked", "true")
  await form.getByRole("button", { name: "取消" }).click()
})

test("employee references block deactivating departments, positions, and cost centers", async ({
  page,
}) => {
  const organization = await setupOrganization(page)
  const employeeNo = randomEmployeeNo()
  await createEmployee({
    employee_no: employeeNo,
    name: randomEmployeeName(),
    dept_id: organization.rootDept.id,
    position_id: organization.position.id,
    cost_org_id: organization.costCenter?.id,
  })

  await page.goto("/departments")
  await page
    .getByTestId("department-tree")
    .getByRole("button", {
      name: new RegExp(organization.rootDept.dept_name),
    })
    .click()
  await page.getByRole("button", { name: "编辑" }).click()
  let dialog = page.getByRole("dialog")
  await dialog.getByRole("switch", { name: "状态" }).click()
  await dialog.getByRole("button", { name: "保存" }).click()
  let blocked = page.getByTestId("blocked-dialog")
  await expect(blocked).toContainText("无法停用部门")
  await expect(blocked).toContainText(employeeNo)
  await blocked.getByRole("button", { name: "知道了" }).click()
  await dialog.getByRole("button", { name: "取消" }).click()

  await page.goto("/positions")
  const positionRow = page
    .getByTestId("position-table")
    .getByRole("row")
    .filter({ hasText: organization.position.position_name })
  await positionRow.getByRole("button", { name: "编辑" }).click()
  dialog = page.getByRole("dialog")
  await dialog.getByRole("switch", { name: "状态" }).click()
  await dialog.getByRole("button", { name: "保存" }).click()
  blocked = page.getByTestId("blocked-dialog")
  await expect(blocked).toContainText("无法停用岗位")
  await expect(blocked).toContainText(employeeNo)
  await blocked.getByRole("button", { name: "知道了" }).click()
  await dialog.getByRole("button", { name: "取消" }).click()

  await page.goto("/cost-centers")
  await page
    .getByTestId("cost-center-tree")
    .getByRole("button", {
      name: new RegExp(organization.costCenter?.cost_org_name ?? ""),
    })
    .click()
  await page.getByRole("button", { name: "编辑" }).click()
  dialog = page.getByRole("dialog")
  await dialog.getByRole("switch", { name: "状态" }).click()
  await dialog.getByRole("button", { name: "保存" }).click()
  blocked = page.getByTestId("blocked-dialog")
  await expect(blocked).toContainText("无法停用成本中心")
  await expect(blocked).toContainText(employeeNo)
  await blocked.getByRole("button", { name: "知道了" }).click()
  await dialog.getByRole("button", { name: "取消" }).click()
})
