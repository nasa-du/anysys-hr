import { expect, type Page, test } from "@playwright/test"
import {
  randomCompanyCode,
  randomCompanyName,
  randomCostCenterCode,
  randomCostCenterName,
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
  await page.goto("/cost-centers")
  return { code, name }
}

function treeNode(page: Page, name: string) {
  return page
    .getByTestId("cost-center-tree")
    .getByRole("button", { name: new RegExp(name) })
}

async function selectCostCenter(page: Page, name: string) {
  await treeNode(page, name).click()
  await expect(page.getByTestId("cost-center-detail")).toContainText(name)
}

async function submitCostCenter(
  page: Page,
  {
    code,
    name,
    parentName,
    budget,
    warnPct,
  }: {
    code: string
    name: string
    parentName?: string
    budget?: string
    warnPct?: string
  },
) {
  if (parentName) {
    await selectCostCenter(page, parentName)
    await page.getByRole("button", { name: "新增下级" }).click()
  } else {
    await page.getByRole("button", { name: "新增根成本中心" }).first().click()
  }

  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("成本中心编码").fill(code)
  await dialog.getByLabel("成本中心名称").fill(name)
  if (budget !== undefined) {
    await dialog.getByLabel("预算（元）").fill(budget)
  }
  if (warnPct !== undefined) {
    await dialog.getByLabel("预警比例（%）").fill(warnPct)
  }
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("成本中心创建成功").first()).toBeVisible()
  await expect(page.getByRole("dialog")).not.toBeVisible()
}

test("sidebar shows the Cost Centers entry and the page follows the company switcher", async ({
  page,
}) => {
  const company = await prepareCompany(page)

  await expect(
    page.getByRole("heading", { name: "成本中心", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: "成本中心", exact: true }),
  ).toBeVisible()
  await expect(page.getByText(`当前公司：${company.name}`)).toBeVisible()
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "还没有成本中心",
  )
})

test("create, edit, and delete a cost center tree", async ({ page }) => {
  await prepareCompany(page)
  const rootCode = randomCostCenterCode()
  const rootName = randomCostCenterName()
  const childCode = randomCostCenterCode()
  const childName = randomCostCenterName()

  await submitCostCenter(page, {
    code: rootCode,
    name: rootName,
    budget: "1000.00",
  })
  await expect(treeNode(page, rootName)).toBeVisible()

  await submitCostCenter(page, {
    code: childCode,
    name: childName,
    parentName: rootName,
    budget: "250.50",
    warnPct: "90",
  })
  await expect(treeNode(page, childName)).toBeVisible()

  await selectCostCenter(page, childName)
  await page.getByRole("button", { name: "编辑" }).click()
  let dialog = page.getByRole("dialog")
  await expect(dialog.getByLabel("成本中心编码")).toBeDisabled()
  const updatedName = randomCostCenterName()
  await dialog.getByLabel("成本中心名称").fill(updatedName)
  await dialog.getByLabel("预算（元）").fill("1234.50")
  await dialog.getByLabel("预警比例（%）").fill("75")
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("成本中心更新成功").first()).toBeVisible()
  await expect(treeNode(page, updatedName)).toBeVisible()

  await selectCostCenter(page, updatedName)
  await expect(page.getByTestId("cost-center-budget")).toContainText("1234.50")
  await expect(page.getByTestId("cost-center-detail")).toContainText("75%")

  await page.getByRole("button", { name: "删除" }).click()
  dialog = page.getByRole("dialog")
  await expect(dialog).toContainText("删除成本中心")
  await dialog.getByRole("button", { name: "删除" }).click()
  await expect(page.getByText("成本中心删除成功").first()).toBeVisible()
  await expect(treeNode(page, updatedName)).toHaveCount(0)
  await expect(treeNode(page, rootName)).toBeVisible()

  await selectCostCenter(page, rootName)
  await page.getByRole("button", { name: "删除" }).click()
  dialog = page.getByRole("dialog")
  await dialog.getByRole("button", { name: "删除" }).click()
  await expect(page.getByText("成本中心删除成功").first()).toBeVisible()
  await expect(treeNode(page, rootName)).toHaveCount(0)
})

test("budget and warn percentage validation rejects invalid values", async ({
  page,
}) => {
  await prepareCompany(page)
  const code = randomCostCenterCode()
  const name = randomCostCenterName()

  await page.getByRole("button", { name: "新增根成本中心" }).first().click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("成本中心编码").fill(code)
  await dialog.getByLabel("成本中心名称").fill(name)

  const budgetInput = dialog.getByLabel("预算（元）")
  const warnInput = dialog.getByLabel("预警比例（%）")

  await budgetInput.fill("-1")
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(
    dialog.getByText("请输入不小于 0、最多两位小数的金额"),
  ).toBeVisible()

  await budgetInput.fill("12.345")
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(
    dialog.getByText("请输入不小于 0、最多两位小数的金额"),
  ).toBeVisible()

  await budgetInput.fill("1500.50")
  await warnInput.fill("101")
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(dialog.getByText("预警比例不能大于 100")).toBeVisible()

  await warnInput.fill("0")
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(dialog.getByText("预警比例不能小于 1")).toBeVisible()

  await warnInput.fill("80")
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("成本中心创建成功").first()).toBeVisible()
  await expect(page.getByRole("dialog")).not.toBeVisible()

  await selectCostCenter(page, name)
  await expect(page.getByTestId("cost-center-budget")).toContainText("1500.50")
  await expect(page.getByTestId("cost-center-detail")).toContainText("80%")
})

test("move a cost center to another parent", async ({ page }) => {
  await prepareCompany(page)
  const firstParent = randomCostCenterName()
  const secondParent = randomCostCenterName()
  const childName = randomCostCenterName()

  await submitCostCenter(page, {
    code: randomCostCenterCode(),
    name: firstParent,
  })
  await submitCostCenter(page, {
    code: randomCostCenterCode(),
    name: secondParent,
  })
  await submitCostCenter(page, {
    code: randomCostCenterCode(),
    name: childName,
    parentName: firstParent,
  })

  await selectCostCenter(page, childName)
  await page.getByRole("button", { name: "编辑" }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByRole("combobox", { name: "上级成本中心" }).click()
  await page.getByRole("option", { name: new RegExp(secondParent) }).click()
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("成本中心更新成功").first()).toBeVisible()

  await selectCostCenter(page, childName)
  const detail = page.getByTestId("cost-center-detail")
  await expect(detail.locator("dd").first()).toHaveText(secondParent)

  await selectCostCenter(page, firstParent)
  await expect(page.getByTestId("cost-center-detail")).toContainText(
    "暂无下级成本中心。",
  )
})

test("the parent selector disables the cost center and its descendants", async ({
  page,
}) => {
  await prepareCompany(page)
  const rootName = randomCostCenterName()
  const childName = randomCostCenterName()
  const grandchildName = randomCostCenterName()
  const otherRootName = randomCostCenterName()

  await submitCostCenter(page, {
    code: randomCostCenterCode(),
    name: rootName,
  })
  await submitCostCenter(page, {
    code: randomCostCenterCode(),
    name: childName,
    parentName: rootName,
  })
  await submitCostCenter(page, {
    code: randomCostCenterCode(),
    name: grandchildName,
    parentName: childName,
  })
  await submitCostCenter(page, {
    code: randomCostCenterCode(),
    name: otherRootName,
  })

  await selectCostCenter(page, rootName)
  await page.getByRole("button", { name: "编辑" }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByRole("combobox", { name: "上级成本中心" }).click()

  await expect(
    page.getByRole("option", { name: new RegExp(rootName) }),
  ).toBeDisabled()
  await expect(
    page.getByRole("option", { name: new RegExp(childName) }),
  ).toBeDisabled()
  await expect(
    page.getByRole("option", { name: new RegExp(grandchildName) }),
  ).toBeDisabled()
  await expect(
    page.getByRole("option", { name: new RegExp(otherRootName) }),
  ).toBeEnabled()

  await page.keyboard.press("Escape")
  await dialog.getByRole("button", { name: "取消" }).click()
  await expect(page.getByRole("dialog")).not.toBeVisible()
})

test("deleting a cost center with children is blocked", async ({ page }) => {
  await prepareCompany(page)
  const parentName = randomCostCenterName()
  const childCode = randomCostCenterCode()
  const childName = randomCostCenterName()

  await submitCostCenter(page, {
    code: randomCostCenterCode(),
    name: parentName,
  })
  await submitCostCenter(page, {
    code: childCode,
    name: childName,
    parentName,
  })

  await selectCostCenter(page, parentName)
  await page.getByRole("button", { name: "删除" }).click()
  const confirmDialog = page.getByRole("dialog")
  await confirmDialog.getByRole("button", { name: "删除" }).click()

  const blockedDialog = page.getByTestId("blocked-dialog")
  await expect(blockedDialog).toBeVisible()
  await expect(blockedDialog).toContainText("无法删除成本中心")
  await expect(blockedDialog).toContainText(childCode)
  await expect(blockedDialog).toContainText(childName)
  await blockedDialog.getByRole("button", { name: "知道了" }).click()

  await expect(treeNode(page, parentName)).toBeVisible()
})

test("deactivating a cost center with active children is blocked", async ({
  page,
}) => {
  await prepareCompany(page)
  const parentName = randomCostCenterName()
  const childName = randomCostCenterName()

  await submitCostCenter(page, {
    code: randomCostCenterCode(),
    name: parentName,
  })
  await submitCostCenter(page, {
    code: randomCostCenterCode(),
    name: childName,
    parentName,
  })

  await selectCostCenter(page, parentName)
  await page.getByRole("button", { name: "编辑" }).click()
  const dialog = page.getByRole("dialog")
  const statusSwitch = dialog.getByRole("switch", { name: "状态" })
  await expect(statusSwitch).toHaveAttribute("aria-checked", "true")
  await statusSwitch.click()
  await expect(statusSwitch).toHaveAttribute("aria-checked", "false")
  await dialog.getByRole("button", { name: "保存" }).click()

  const blockedDialog = page.getByTestId("blocked-dialog")
  await expect(blockedDialog).toBeVisible()
  await expect(blockedDialog).toContainText("无法停用成本中心")
  await expect(blockedDialog).toContainText(childName)
  await blockedDialog.getByRole("button", { name: "知道了" }).click()

  await expect(statusSwitch).toHaveAttribute("aria-checked", "true")
  await dialog.getByRole("button", { name: "取消" }).click()
  await expect(page.getByRole("dialog")).not.toBeVisible()
})

test("deleting a company with a cost center is blocked", async ({ page }) => {
  const company = await prepareCompany(page)
  const code = randomCostCenterCode()
  const name = randomCostCenterName()
  await submitCostCenter(page, { code, name })

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

test("cost centers are scoped to the selected company", async ({ page }) => {
  const firstCompanyName = randomCompanyName()
  const secondCompanyName = randomCompanyName()
  await createCompany(page, randomCompanyCode(), firstCompanyName)
  await createCompany(page, randomCompanyCode(), secondCompanyName)

  await switchCompany(page, firstCompanyName)
  await page.goto("/cost-centers")
  const costCenterName = randomCostCenterName()
  await submitCostCenter(page, {
    code: randomCostCenterCode(),
    name: costCenterName,
  })
  await expect(treeNode(page, costCenterName)).toBeVisible()

  await switchCompany(page, secondCompanyName)
  await expect(page.getByText(`当前公司：${secondCompanyName}`)).toBeVisible()
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "还没有成本中心",
  )
  await expect(treeNode(page, costCenterName)).toHaveCount(0)
  // The detail pane must not keep showing the previous company's cost center.
  await expect(page.getByTestId("cost-center-detail")).toHaveCount(0)

  await switchCompany(page, firstCompanyName)
  await expect(treeNode(page, costCenterName)).toBeVisible()
  await expect(page.getByTestId("cost-center-detail")).toContainText(
    costCenterName,
  )
})
