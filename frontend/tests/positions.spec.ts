import { expect, type Page, test } from "@playwright/test"
import {
  randomCompanyCode,
  randomCompanyName,
  randomDepartmentCode,
  randomDepartmentName,
  randomPositionCode,
  randomPositionName,
} from "./utils/random"

async function createCompany(page: Page, code: string, name: string) {
  await page.goto("/companies")
  await page.getByRole("button", { name: "新增公司" }).first().click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("公司编码").fill(code)
  await dialog.getByLabel("公司名称").fill(name)
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("公司创建成功").first()).toBeVisible()
  await expect(page.getByRole("dialog")).not.toBeVisible()
}

async function switchCompany(page: Page, name: string) {
  const switcher = page.getByRole("combobox", { name: "切换公司" })
  await switcher.click()
  await page.getByRole("option", { name }).click()
  await expect(switcher).toContainText(name)
}

/** Creates an isolated company and makes it the active company. */
async function prepareCompany(page: Page) {
  const code = randomCompanyCode()
  const name = randomCompanyName()
  await createCompany(page, code, name)
  await switchCompany(page, name)
  await page.goto("/positions")
  return { code, name }
}

async function createDepartment(page: Page, code: string, name: string) {
  await page.goto("/departments")
  await page.getByRole("button", { name: "新增根部门" }).first().click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("部门编码").fill(code)
  await dialog.getByLabel("部门名称").fill(name)
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("部门创建成功").first()).toBeVisible()
  await expect(page.getByRole("dialog")).not.toBeVisible()
  await page.goto("/positions")
}

async function submitPosition(
  page: Page,
  {
    code,
    name,
    departmentName,
  }: { code: string; name: string; departmentName?: string },
) {
  await page.getByRole("button", { name: "新增岗位" }).first().click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("岗位编码").fill(code)
  await dialog.getByLabel("岗位名称").fill(name)
  if (departmentName) {
    await dialog.getByRole("combobox", { name: "默认部门" }).click()
    await page.getByRole("option", { name: new RegExp(departmentName) }).click()
  }
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("岗位创建成功").first()).toBeVisible()
  await expect(page.getByRole("dialog")).not.toBeVisible()
}

function positionRow(page: Page, code: string) {
  return page
    .getByTestId("position-table")
    .getByRole("row")
    .filter({ hasText: code })
}

test("sidebar shows the Positions entry and the page follows the company switcher", async ({
  page,
}) => {
  const company = await prepareCompany(page)

  await expect(
    page.getByRole("heading", { name: "岗位", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: "岗位", exact: true }),
  ).toBeVisible()
  await expect(page.getByText(`当前公司：${company.name}`)).toBeVisible()
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "还没有岗位",
  )
})

test("create and edit a position with a default department", async ({
  page,
}) => {
  await prepareCompany(page)
  const departmentName = randomDepartmentName()
  await createDepartment(page, randomDepartmentCode(), departmentName)

  const code = randomPositionCode()
  const name = randomPositionName()
  await submitPosition(page, {
    code,
    name,
    departmentName,
  })

  const row = positionRow(page, code)
  await expect(row).toContainText(name)
  await expect(row).toContainText(departmentName)
  await expect(row).toContainText("启用")

  await row.getByRole("button", { name: "编辑" }).click()
  const dialog = page.getByRole("dialog")
  await expect(dialog.getByLabel("岗位编码")).toBeDisabled()
  const updatedName = randomPositionName()
  await dialog.getByLabel("岗位名称").fill(updatedName)
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("岗位更新成功").first()).toBeVisible()
  await expect(positionRow(page, code)).toContainText(updatedName)
})

test("delete an unreferenced position", async ({ page }) => {
  await prepareCompany(page)
  const code = randomPositionCode()
  await submitPosition(page, { code, name: randomPositionName() })

  await positionRow(page, code).getByRole("button", { name: "删除" }).click()
  const confirmDialog = page.getByRole("dialog")
  await expect(confirmDialog).toContainText("删除岗位")
  await confirmDialog.getByRole("button", { name: "删除" }).click()

  await expect(page.getByText("岗位删除成功").first()).toBeVisible()
  await expect(positionRow(page, code)).toHaveCount(0)
})

test("deleting a company with a position is blocked", async ({ page }) => {
  const company = await prepareCompany(page)
  const code = randomPositionCode()
  const name = randomPositionName()
  await submitPosition(page, { code, name })

  await page.goto("/companies")
  const search = page.getByLabel("搜索公司")
  await search.fill(company.code)
  const companyRow = page.getByRole("row").filter({ hasText: company.code })
  await expect(companyRow).toBeVisible()
  await companyRow.getByRole("button", { name: "删除" }).click()
  const confirmDialog = page.getByRole("dialog")
  await confirmDialog.getByRole("button", { name: "删除" }).click()

  const blockedDialog = page.getByTestId("blocked-dialog")
  await expect(blockedDialog).toBeVisible()
  await expect(blockedDialog).toContainText("无法删除公司")
  await expect(blockedDialog).toContainText(code)
  await expect(blockedDialog).toContainText(name)
  await blockedDialog.getByRole("button", { name: "知道了" }).click()
  await expect(companyRow).toBeVisible()
})

test("department detail lists positions using it as the default department", async ({
  page,
}) => {
  await prepareCompany(page)
  const departmentName = randomDepartmentName()
  await createDepartment(page, randomDepartmentCode(), departmentName)
  const code = randomPositionCode()
  const name = randomPositionName()
  await submitPosition(page, { code, name, departmentName })

  await page.goto("/departments")
  await page
    .getByTestId("department-tree")
    .getByRole("button", { name: new RegExp(departmentName) })
    .click()
  const panel = page.getByTestId("department-positions")
  await expect(panel).toContainText(code)
  await expect(panel).toContainText(name)
  await expect(panel).toContainText("共 1 个")
})
