import { expect, type Page, test } from "@playwright/test"
import { randomCompanyCode, randomCompanyName } from "./utils/random"

const COMPANY_STORAGE_KEY = "basic-management.company_id"

async function createCompanyViaUi(
  page: Page,
  options: { code: string; name: string; note?: string },
) {
  await page.getByRole("button", { name: "新增公司" }).first().click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("公司编码").fill(options.code)
  await dialog.getByLabel("公司名称").fill(options.name)
  if (options.note) {
    await dialog.getByLabel("备注").fill(options.note)
  }
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("公司创建成功").first()).toBeVisible()
  await expect(page.getByRole("dialog")).not.toBeVisible()
}

function companyRow(page: Page, code: string) {
  return page.getByRole("row").filter({ hasText: code })
}

async function searchCompany(page: Page, code: string) {
  await page.getByLabel("搜索公司").fill(code)
  await expect(companyRow(page, code)).toBeVisible()
}

test("sidebar shows the Basic Management group with the Companies entry", async ({
  page,
}) => {
  await page.goto("/companies")

  await expect(page.getByRole("heading", { name: "公司" })).toBeVisible()
  await expect(page.getByText("基础管理")).toBeVisible()
  await expect(page.getByRole("link", { name: "公司" })).toBeVisible()
  await expect(page.getByRole("combobox", { name: "切换公司" })).toBeVisible()
})

test("create a company", async ({ page }) => {
  const code = randomCompanyCode()
  const name = randomCompanyName()

  await page.goto("/companies")
  await createCompanyViaUi(page, { code, name, note: "E2E 创建" })

  await searchCompany(page, code)
  const row = companyRow(page, code)
  await expect(row).toContainText(name)
  await expect(row).toContainText("启用")
})

test("edit a company", async ({ page }) => {
  const code = randomCompanyCode()
  const originalName = randomCompanyName()
  const updatedName = randomCompanyName()

  await page.goto("/companies")
  await createCompanyViaUi(page, { code, name: originalName })
  await searchCompany(page, code)

  await companyRow(page, code).getByRole("button", { name: "编辑" }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("公司名称").fill(updatedName)
  await dialog.getByRole("button", { name: "保存" }).click()

  await expect(page.getByText("公司更新成功")).toBeVisible()
  await expect(page.getByRole("dialog")).not.toBeVisible()
  await expect(companyRow(page, code)).toContainText(updatedName)
})

test("deactivate a company with the status switch", async ({ page }) => {
  const code = randomCompanyCode()

  await page.goto("/companies")
  await createCompanyViaUi(page, { code, name: randomCompanyName() })
  await searchCompany(page, code)

  await companyRow(page, code).getByRole("button", { name: "编辑" }).click()
  const dialog = page.getByRole("dialog")
  const statusSwitch = dialog.getByRole("switch", { name: "状态" })
  await expect(statusSwitch).toHaveAttribute("aria-checked", "true")
  await statusSwitch.click()
  await expect(statusSwitch).toHaveAttribute("aria-checked", "false")
  await dialog.getByRole("button", { name: "保存" }).click()

  await expect(page.getByText("公司更新成功")).toBeVisible()
  await expect(companyRow(page, code)).toContainText("停用")
})

test("delete an unreferenced company", async ({ page }) => {
  const code = randomCompanyCode()

  await page.goto("/companies")
  await createCompanyViaUi(page, { code, name: randomCompanyName() })
  await searchCompany(page, code)

  await companyRow(page, code).getByRole("button", { name: "删除" }).click()
  const confirmDialog = page.getByRole("dialog")
  await expect(confirmDialog).toContainText("删除公司")
  await confirmDialog.getByRole("button", { name: "删除" }).click()

  await expect(page.getByText("公司删除成功")).toBeVisible()
  await expect(companyRow(page, code)).toHaveCount(0)
})

test("switch the active company from the top bar and the table", async ({
  page,
}) => {
  const firstCode = randomCompanyCode()
  const firstName = randomCompanyName()
  const secondCode = randomCompanyCode()
  const secondName = randomCompanyName()

  await page.goto("/companies")
  await createCompanyViaUi(page, { code: firstCode, name: firstName })
  await createCompanyViaUi(page, { code: secondCode, name: secondName })

  const switcher = page.getByRole("combobox", { name: "切换公司" })

  await switcher.click()
  await page.getByRole("option", { name: firstName }).click()
  await expect(switcher).toContainText(firstName)
  const firstId = await page.evaluate(
    (key) => localStorage.getItem(key),
    COMPANY_STORAGE_KEY,
  )
  expect(firstId).toBeTruthy()
  await searchCompany(page, firstCode)
  await expect(companyRow(page, firstCode)).toContainText("当前公司")

  await searchCompany(page, secondCode)
  await companyRow(page, secondCode)
    .getByRole("button", { name: "切换" })
    .click()
  await expect(switcher).toContainText(secondName)
  const secondId = await page.evaluate(
    (key) => localStorage.getItem(key),
    COMPANY_STORAGE_KEY,
  )
  expect(secondId).toBeTruthy()
  expect(secondId).not.toBe(firstId)
  await expect(companyRow(page, secondCode)).toContainText("当前公司")

  await page.reload()
  await expect(page.getByRole("combobox", { name: "切换公司" })).toContainText(
    secondName,
  )
})
