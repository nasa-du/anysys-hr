import { expect, type Page, type Route, test } from "@playwright/test"

import { createCompany } from "./utils/api"
import { setActiveCompany } from "./utils/company"
import { randomCompanyCode, randomCompanyName } from "./utils/random"

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

async function createActiveCompany(page: Page) {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  await setActiveCompany(page, company.id)
  return company
}

test("payroll pages show the shared loading state while companies load", async ({
  page,
}) => {
  await page.route(/\/api\/v1\/companies\/\?/, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, REQUEST_DELAY_MS))
    await route.continue()
  })

  await page.goto("/payroll/results")

  await expect(
    page.getByRole("heading", { name: "工资列表", exact: true }),
  ).toBeVisible()
  await expect(page.getByTestId("loading-state")).toBeVisible()
  await expect(page.getByTestId("loading-state")).toHaveCount(0, {
    timeout: SLOW_REQUEST_TIMEOUT_MS,
  })
})

test("a fresh company sees the payroll empty states without month context on configuration pages", async ({
  page,
}) => {
  await createActiveCompany(page)

  await page.goto("/payroll/results")
  await expect(page.getByTestId("payroll-month-bar")).toBeVisible()
  await expect(page.getByTestId("empty-state")).toContainText(
    "工资列表功能建设中",
  )
  await expect(page.getByTestId("empty-state")).toContainText("当前薪资月份为")

  await page.goto("/payroll/config/compositions")
  await expect(page.getByTestId("empty-state")).toContainText(
    "薪资构成功能建设中",
  )
  await expect(page.getByTestId("payroll-month-bar")).toHaveCount(0)
})

test("a failed company list shows the shared error state and recovers on retry", async ({
  page,
}) => {
  await page.route(/\/api\/v1\/companies\/\?/, failWithInternalError)

  await page.goto("/payroll/results")
  await expect(page.getByTestId("error-state")).toBeVisible({
    timeout: SLOW_REQUEST_TIMEOUT_MS,
  })

  await page.unroute(/\/api\/v1\/companies\/\?/)
  await page.getByRole("button", { name: "重试" }).click()

  await expect(page.getByTestId("error-state")).toHaveCount(0)
  await expect(
    page.getByRole("heading", { name: "工资列表", exact: true }),
  ).toBeVisible()
})

test("the payroll month bar stacks within a narrow viewport", async ({
  page,
}) => {
  await createActiveCompany(page)
  await page.setViewportSize({ width: 390, height: 844 })

  await page.goto("/payroll/results")

  await expect(page.getByTestId("payroll-month-bar")).toBeVisible()
  await expect(page.getByLabel("薪资月份")).toBeVisible()
  for (const action of ["导入", "重算", "确认", "发工资条", "解锁"]) {
    await expect(
      page.getByRole("button", { name: action, exact: true }),
    ).toBeVisible()
  }

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  )
  expect(overflow).toBeLessThanOrEqual(1)
})
