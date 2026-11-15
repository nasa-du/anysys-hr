import { expect, type Route, test } from "@playwright/test"

import {
  bootstrapAttendanceCompany,
  confirmMonth,
  createCompany,
  createShift,
  lockMonth,
  unlockMonth,
} from "./utils/api"
import { expectHeading, openAttendanceMonth } from "./utils/attendance-page"
import { randomCompanyCode, randomCompanyName } from "./utils/random"

test.setTimeout(120_000)

const MONTH = "2026-09"
const REQUEST_DELAY_MS = 1_500
const SLOW_REQUEST_TIMEOUT_MS = 20_000

const ATTENDANCE_MODULES = [
  { path: "/attendance/schedule", heading: "排班工作台" },
  { path: "/attendance/imports", heading: "导入中心" },
  { path: "/attendance/results", heading: "考勤结果" },
  { path: "/attendance/rules", heading: "规则与节假日" },
  { path: "/attendance/shifts", heading: "班次" },
] as const

function failWithInternalError(route: Route) {
  return route.fulfill({
    status: 500,
    contentType: "application/json",
    body: JSON.stringify({
      detail: { code: "internal_error", message: "服务器内部错误" },
    }),
  })
}

test("attendance pages show a loading state while the company list is in flight", async ({
  page,
}) => {
  await page.route(/\/api\/v1\/companies\/\?/, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, REQUEST_DELAY_MS))
    await route.continue()
  })

  await page.goto("/attendance/results")

  await expectHeading(page, "考勤结果")
  await expect(page.getByTestId("loading-state").first()).toBeVisible()
  await expect(page.getByTestId("loading-state")).toHaveCount(0, {
    timeout: SLOW_REQUEST_TIMEOUT_MS,
  })
})

test("a fresh company shows the attendance empty states", async ({ page }) => {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  await openAttendanceMonth(page, company.id, MONTH)

  await page.goto("/attendance/shifts")
  await expect(page.getByTestId("empty-state")).toContainText("还没有班次")

  await page.goto("/attendance/schedule")
  await expect(page.getByTestId("empty-state")).toContainText(
    `${MONTH} 还没有排班方案`,
  )

  await page.goto("/attendance/imports")
  await expect(page.getByTestId("current-batch-punch")).toContainText("未生效")
  await expect(page.getByTestId("batch-history")).toContainText(
    "当前筛选下没有批次",
  )

  await page.goto("/attendance/results")
  await expect(page.getByTestId("empty-state")).toContainText(
    `${MONTH} 还没有日结果`,
  )

  await page.goto("/attendance/rules")
  await expect(page.getByTestId("holiday-empty")).toBeVisible()
  await expect(page.getByTestId("company-rule-form")).toBeVisible()
})

test("a failed shift list shows an error state and recovers on retry", async ({
  page,
}) => {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  await createShift({
    company_id: company.id,
    shift_code: "ERR",
    shift_name: "重试班次",
  })
  await openAttendanceMonth(page, company.id, MONTH)
  await page.route(/\/api\/v1\/attendance\/shifts\/\?/, failWithInternalError)

  await page.goto("/attendance/shifts")

  await expect(page.getByTestId("error-state")).toBeVisible({
    timeout: SLOW_REQUEST_TIMEOUT_MS,
  })
  await page.unroute(/\/api\/v1\/attendance\/shifts\/\?/)
  await page.getByRole("button", { name: "重试" }).click()

  await expect(page.getByTestId("error-state")).toHaveCount(0)
  await expect(page.getByTestId("shift-table")).toContainText("重试班次")
})

test("a failed result list shows an error state and recovers on retry", async ({
  page,
}) => {
  const boot = await bootstrapAttendanceCompany({
    workDates: ["2026-09-07"],
    month: MONTH,
  })
  await openAttendanceMonth(page, boot.company.id, MONTH)
  await page.route(
    /\/api\/v1\/attendance\/results\/days\/\?/,
    failWithInternalError,
  )

  await page.goto("/attendance/results")

  await expect(page.getByTestId("error-state")).toBeVisible({
    timeout: SLOW_REQUEST_TIMEOUT_MS,
  })
  await page.unroute(/\/api\/v1\/attendance\/results\/days\/\?/)
  await page.getByRole("button", { name: "重试" }).click()

  await expect(page.getByTestId("error-state")).toHaveCount(0)
  await expect(page.getByTestId("day-results-table")).toContainText(
    boot.employeeNo,
  )
})

test("locked and stale months stay visible across attendance pages", async ({
  page,
}) => {
  const boot = await bootstrapAttendanceCompany({
    workDates: ["2026-09-07"],
    month: MONTH,
  })
  await openAttendanceMonth(page, boot.company.id, MONTH)
  await confirmMonth(boot.company.id, MONTH)
  await lockMonth(boot.company.id, MONTH)

  await page.goto("/attendance/results")
  await expect(page.getByTestId("month-locked-banner")).toBeVisible()
  await expect(page.getByTestId("recalculate-button")).toBeDisabled()

  await page.goto("/attendance/schedule")
  await expect(page.getByTestId("month-locked-banner")).toBeVisible()
  await expect(
    page.getByRole("button", { name: "新建方案" }).first(),
  ).toBeDisabled()

  await page.goto("/attendance/imports")
  await expect(page.getByTestId("import-month-status")).toHaveText("已锁定")
  await expect(page.getByTestId("import-month-closed")).toBeVisible()

  await unlockMonth(boot.company.id, MONTH, "复核后重新打开")

  await page.goto("/attendance/results")
  await expect(page.getByTestId("month-stale-banner")).toBeVisible()
  await expect(page.getByTestId("confirm-month-button")).toBeDisabled()
  await expect(page.getByTestId("recalculate-button")).toBeEnabled()

  await page.goto("/attendance/schedule")
  await expect(page.getByTestId("month-stale-banner")).toBeVisible()

  await page.goto("/attendance/imports")
  await expect(page.getByTestId("import-month-stale")).toBeVisible()
})

test("dark theme keeps every attendance page readable", async ({ page }) => {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  await openAttendanceMonth(page, company.id, MONTH)

  await page.goto("/attendance/schedule")
  await page.getByTestId("theme-button").click()
  await page.getByTestId("dark-mode").click()
  await expect(page.locator("html")).toHaveClass(/dark/)

  for (const { path, heading } of ATTENDANCE_MODULES) {
    await page.goto(path)
    await expectHeading(page, heading)
    await expect(page.getByRole("combobox", { name: "切换公司" })).toBeVisible()
  }
})

test("narrow screens keep every attendance module usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  await openAttendanceMonth(page, company.id, MONTH)

  for (const { path, heading } of ATTENDANCE_MODULES) {
    await page.goto(path)
    await expectHeading(page, heading)
    await expect(page.getByRole("combobox", { name: "切换公司" })).toBeVisible()
  }

  await page.goto("/attendance/schedule")
  await page.getByRole("button", { name: /侧边栏/ }).click()
  for (const { heading } of ATTENDANCE_MODULES) {
    await expect(
      page.getByRole("link", { name: heading, exact: true }),
    ).toBeVisible()
  }
  await page.keyboard.press("Escape")
})
