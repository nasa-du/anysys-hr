import { expect, type Page, test } from "@playwright/test"

import { createCompany } from "./utils/api"
import { randomCompanyCode, randomCompanyName } from "./utils/random"

const MONTHLY_MODULES = [
  { link: "工资列表", path: "/payroll/results", heading: "工资列表" },
  { link: "月度导入", path: "/payroll/imports", heading: "月度导入" },
  { link: "核算与确认", path: "/payroll/calc", heading: "核算与确认" },
  { link: "工资条", path: "/payroll/payslips", heading: "工资条" },
  { link: "成本统计", path: "/payroll/cost-stats", heading: "成本统计" },
] as const

const CONFIG_MODULES = [
  {
    link: "薪资构成",
    path: "/payroll/config/compositions",
    heading: "薪资构成",
  },
  {
    link: "计算方案",
    path: "/payroll/config/calc-schemes",
    heading: "计算方案",
  },
  {
    link: "工作日参数",
    path: "/payroll/config/workday-params",
    heading: "工作日参数",
  },
  { link: "岗位装配", path: "/payroll/config/positions", heading: "岗位装配" },
  { link: "字段与公式", path: "/payroll/config/fields", heading: "字段与公式" },
  { link: "全局参数", path: "/payroll/config/globals", heading: "全局参数" },
] as const

const PAYROLL_MONTH_STORAGE_KEY = "payroll.month"
const PAYROLL_MONTH_COMPANY_STORAGE_KEY = "payroll.month.company_id"

function currentShanghaiMonth(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
  }).format(new Date())
}

async function switchCompany(page: Page, name: string) {
  const switcher = page.getByRole("combobox", { name: "切换公司" })
  await switcher.click()
  await page.getByRole("option", { name, exact: true }).click()
  await expect(switcher).toContainText(name)
}

async function expectMonthlyShell(page: Page) {
  await expect(page.getByTestId("payroll-month-bar")).toBeVisible()
  await expect(page.getByLabel("薪资月份")).toBeVisible()
  await expect(page.getByTestId("payroll-status-badge")).toBeVisible()
  await expect(page.getByTestId("payroll-input-version")).toContainText("v0")
  await expect(page.getByTestId("payroll-latest-run")).toContainText("暂无")
  await expect(page.getByTestId("payroll-attendance-lock")).toContainText(
    "未锁定",
  )
  for (const action of ["导入", "重算", "确认", "发工资条", "解锁"]) {
    await expect(
      page.getByRole("button", { name: action, exact: true }),
    ).toBeVisible()
  }
}

async function expectNoMonthContext(page: Page) {
  await expect(page.getByTestId("payroll-month-bar")).toHaveCount(0)
  await expect(page.getByLabel("薪资月份")).toHaveCount(0)
}

test("the sidebar shows the five monthly and six configuration payroll groups", async ({
  page,
}) => {
  await page.goto("/")

  const monthlyGroup = page
    .locator('[data-sidebar="group"]')
    .filter({ hasText: "薪资月度" })
  await expect(monthlyGroup.getByRole("link")).toHaveText(
    MONTHLY_MODULES.map((module) => module.link),
  )

  const configGroup = page
    .locator('[data-sidebar="group"]')
    .filter({ hasText: "薪资配置" })
  await expect(configGroup.getByRole("link")).toHaveText(
    CONFIG_MODULES.map((module) => module.link),
  )
})

test("every payroll module resolves with the correct month context", async ({
  page,
}) => {
  await page.goto("/payroll/results")

  for (const { link, path, heading } of MONTHLY_MODULES) {
    await page.getByRole("link", { name: link, exact: true }).click()
    await expect(page).toHaveURL(new RegExp(`${path}\\?month=`))
    await expect(
      page.getByRole("heading", { name: heading, exact: true }),
    ).toBeVisible()
    await expectMonthlyShell(page)
  }

  for (const { link, path, heading } of CONFIG_MODULES) {
    await page.getByRole("link", { name: link, exact: true }).click()
    await expect(page).toHaveURL(new RegExp(`${path}(\\?|$)`))
    await expect(
      page.getByRole("heading", { name: heading, exact: true }),
    ).toBeVisible()
    await expectNoMonthContext(page)
  }

  await page.goto("/payroll/payslips/E4001")
  await expect(
    page.getByRole("heading", { name: "工资条详情", exact: true }),
  ).toBeVisible()
  await expectMonthlyShell(page)
})

test("the bare payroll path redirects to the payroll list", async ({
  page,
}) => {
  await page.goto("/payroll")

  await expect(page).toHaveURL(/\/payroll\/results\?month=/)
  await expect(
    page.getByRole("heading", { name: "工资列表", exact: true }),
  ).toBeVisible()
})

test("the payroll month defaults to the current Shanghai month", async ({
  page,
}) => {
  await page.goto("/payroll/results")

  await expect(page.getByLabel("薪资月份")).toHaveValue(currentShanghaiMonth())
})

test("the payroll month persists across monthly pages and reloads", async ({
  page,
}) => {
  await page.goto("/payroll/results")

  await page.getByLabel("薪资月份").fill("2026-09")
  await expect(page).toHaveURL(/[?&]month=2026-09/)
  await page.reload()
  await expect(page.getByLabel("薪资月份")).toHaveValue("2026-09")

  await page.getByRole("link", { name: "月度导入", exact: true }).click()
  await expect(page.getByLabel("薪资月份")).toHaveValue("2026-09")
  await expect(page).toHaveURL(/[?&]month=2026-09/)

  expect(
    await page.evaluate(
      (key) => window.localStorage.getItem(key),
      PAYROLL_MONTH_STORAGE_KEY,
    ),
  ).toBe("2026-09")
  const selectedCompanyId = await page.evaluate(() =>
    window.localStorage.getItem("basic-management.company_id"),
  )
  expect(
    await page.evaluate(
      (key) => window.localStorage.getItem(key),
      PAYROLL_MONTH_COMPANY_STORAGE_KEY,
    ),
  ).toBe(selectedCompanyId)
})

test("configuration pages never mount month context", async ({ page }) => {
  for (const { path } of CONFIG_MODULES) {
    await page.goto(path)
    await expectNoMonthContext(page)
  }
})

test("switching company resets the payroll month to the current month", async ({
  page,
}) => {
  const first = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  const second = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })

  await page.goto("/payroll/results")
  await switchCompany(page, first.company_name)
  await page.getByLabel("薪资月份").fill("2025-01")
  await expect(page.getByLabel("薪资月份")).toHaveValue("2025-01")

  await switchCompany(page, second.company_name)

  await expect(page.getByLabel("薪资月份")).toHaveValue(currentShanghaiMonth())
  await expect(page).toHaveURL(
    new RegExp(`[?&]month=${currentShanghaiMonth()}`),
  )
})

test("switching company on a configuration page resets the next monthly month", async ({
  page,
}) => {
  const first = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  const second = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })

  await page.goto("/payroll/results")
  await switchCompany(page, first.company_name)
  await page.getByLabel("薪资月份").fill("2025-01")
  await expect(page.getByLabel("薪资月份")).toHaveValue("2025-01")

  await page.goto("/payroll/config/compositions")
  await switchCompany(page, second.company_name)
  await page.getByRole("link", { name: "工资列表", exact: true }).click()

  await expect(page.getByLabel("薪资月份")).toHaveValue(currentShanghaiMonth())
})
