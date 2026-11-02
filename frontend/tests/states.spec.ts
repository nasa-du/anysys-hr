import { expect, type Page, type Route, test } from "@playwright/test"
import {
  createCompany,
  createCostCenter,
  createDepartment,
  createEmployee,
  createPosition,
} from "./utils/api"
import { setActiveCompany } from "./utils/company"
import { BASIC_MANAGEMENT_MODULES } from "./utils/modules"
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

const COMPANIES_PATH = /\/api\/v1\/companies\/\?/
const DEPARTMENT_TREE_PATH = /\/api\/v1\/departments\/tree\?/
const REQUEST_DELAY_MS = 1_500
const SLOW_REQUEST_TIMEOUT_MS = 20_000

function failWithInternalError(route: Route) {
  return route.fulfill({
    status: 500,
    contentType: "application/json",
    body: JSON.stringify({
      detail: { code: "internal_error", message: "服务器内部错误" },
    }),
  })
}

async function expectHeading(page: Page, name: string) {
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible()
}

test("the company list shows a loading state while the request is in flight", async ({
  page,
}) => {
  await page.route(COMPANIES_PATH, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, REQUEST_DELAY_MS))
    await route.continue()
  })

  await page.goto("/companies")

  await expectHeading(page, "公司")
  await expect(page.getByTestId("loading-state").first()).toBeVisible()
  await expect(page.getByTestId("loading-state")).toHaveCount(0, {
    timeout: SLOW_REQUEST_TIMEOUT_MS,
  })
})

test("the department tree shows a loading state while the tree request is in flight", async ({
  page,
}) => {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  await setActiveCompany(page, company.id)
  await page.route(DEPARTMENT_TREE_PATH, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, REQUEST_DELAY_MS))
    await route.continue()
  })

  await page.goto("/departments")

  await expectHeading(page, "部门")
  await expect(page.getByTestId("loading-state").first()).toBeVisible()
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "还没有部门",
    { timeout: SLOW_REQUEST_TIMEOUT_MS },
  )
})

test("a company with no data shows an empty state in every module", async ({
  page,
}) => {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  await setActiveCompany(page, company.id)

  await page.goto("/departments")
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "还没有部门",
  )

  await page.goto("/positions")
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "还没有岗位",
  )

  await page.goto("/cost-centers")
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "还没有成本中心",
  )

  await page.goto("/employees")
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "还没有员工",
  )

  await page.goto("/companies")
  await page.getByLabel("搜索公司").fill("不存在的公司关键词")
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "没有匹配的公司",
  )
})

test("modules explain how to choose a company when none is available", async ({
  page,
}) => {
  // An account with no active company sees the same empty states a fresh
  // installation shows; the pages must never render a half-built workspace.
  await page.route(COMPANIES_PATH, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [], count: 0 }),
    }),
  )

  await page.goto("/departments")
  await expectHeading(page, "部门")
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "尚未选择公司",
  )

  await page.goto("/employees")
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "尚未选择公司",
  )

  await page.goto("/companies")
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "还没有公司",
  )
})

test("a failed company list shows an error state and recovers on retry", async ({
  page,
}) => {
  // The retry must recover into a populated table, so this test owns a company
  // instead of relying on whatever happens to be in the database.
  await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  await page.route(COMPANIES_PATH, failWithInternalError)

  await page.goto("/companies")

  // TanStack Query retries failed requests a few times before surfacing the
  // error, so allow more than the default assertion timeout.
  await expect(page.getByTestId("error-state")).toBeVisible({
    timeout: SLOW_REQUEST_TIMEOUT_MS,
  })
  await expect(page.getByRole("button", { name: "重试" })).toBeVisible()

  await page.unroute(COMPANIES_PATH)
  await page.getByRole("button", { name: "重试" }).click()

  await expect(page.getByTestId("error-state")).toHaveCount(0)
  await expect(page.getByTestId("company-table")).toBeVisible()
})

test("a failed department tree shows an error state and recovers on retry", async ({
  page,
}) => {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  await createDepartment({
    company_id: company.id,
    dept_code: randomDepartmentCode(),
    dept_name: randomDepartmentName(),
  })
  await setActiveCompany(page, company.id)
  await page.route(DEPARTMENT_TREE_PATH, failWithInternalError)

  await page.goto("/departments")

  await expect(page.getByTestId("error-state")).toBeVisible({
    timeout: SLOW_REQUEST_TIMEOUT_MS,
  })
  await page.unroute(DEPARTMENT_TREE_PATH)
  await page.getByRole("button", { name: "重试" }).click()

  await expect(page.getByTestId("error-state")).toHaveCount(0)
  await expect(page.getByTestId("department-tree")).toBeVisible()
})

test("the narrow-screen layout keeps every module usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
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
  await createCostCenter({
    company_id: company.id,
    cost_org_code: randomCostCenterCode(),
    cost_org_name: randomCostCenterName(),
  })
  await createEmployee({
    employee_no: randomEmployeeNo(),
    name: randomEmployeeName(),
    dept_id: department.id,
    position_id: position.id,
  })
  await setActiveCompany(page, company.id)

  for (const { path, heading } of BASIC_MANAGEMENT_MODULES) {
    await page.goto(path)
    await expectHeading(page, heading)
    await expect(page.getByRole("combobox", { name: "切换公司" })).toBeVisible()
  }

  await page.goto("/departments")
  await page.getByRole("button", { name: /侧边栏/ }).click()
  for (const { heading } of BASIC_MANAGEMENT_MODULES) {
    await expect(
      page.getByRole("link", { name: heading, exact: true }),
    ).toBeVisible()
  }
  await page.keyboard.press("Escape")
})
