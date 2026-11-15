import { expect, type Page, test } from "@playwright/test"

import {
  bootstrapAttendanceCompany,
  confirmMonth,
  createCompany,
  lockMonth,
  unlockMonth,
  updateAttendanceRule,
} from "./utils/api"
import { expectHeading, openAttendanceMonth } from "./utils/attendance-page"
import { randomCompanyCode, randomCompanyName } from "./utils/random"

test.setTimeout(120_000)

const MONTH = "2026-09"
const WORK_DAYS = ["2026-09-07", "2026-09-08"]

type MonthSetup = {
  companyId: string
  employeeId: string
}

async function openResults(page: Page): Promise<void> {
  await page.goto("/attendance/results")
  await expectHeading(page, "考勤结果")
  await expect(page.getByTestId("month-state-bar")).toBeVisible()
}

async function openSchedule(page: Page): Promise<void> {
  await page.goto("/attendance/schedule")
  await expectHeading(page, "排班工作台")
}

async function openImports(page: Page): Promise<void> {
  await page.goto("/attendance/imports")
  await expectHeading(page, "导入中心")
}

async function expectCalculated(page: Page): Promise<void> {
  await expect(page.getByTestId("month-state-step-calculated")).toHaveAttribute(
    "data-current",
    "true",
  )
}

/** A company with one employee, two rostered days, punches, and results. */
async function setupCalculatedMonth(page: Page): Promise<MonthSetup> {
  const boot = await bootstrapAttendanceCompany({
    workDates: WORK_DAYS,
    month: MONTH,
  })
  await openAttendanceMonth(page, boot.company.id, MONTH)
  return { companyId: boot.company.id, employeeId: boot.employee.id }
}

test("an absent month is a synthetic draft and calculates on demand", async ({
  page,
}) => {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  await openAttendanceMonth(page, company.id, MONTH)
  await openResults(page)

  // No attendance_month row exists yet, but the state bar still shows a draft.
  await expect(page.getByTestId("month-state-step-draft")).toHaveAttribute(
    "data-current",
    "true",
  )
  await expect(page.getByTestId("month-state-bar")).toContainText("尚未计算")
  await expect(page.getByTestId("confirm-month-button")).toBeDisabled()
  await expect(page.getByTestId("month-action-hint")).toContainText(
    "请先计算本月结果",
  )
  await expect(page.getByTestId("recalculate-button")).toBeEnabled()
  await expect(page.getByTestId("empty-state")).toContainText(
    `${MONTH} 还没有日结果`,
  )

  await page.getByTestId("recalculate-button").click()
  await expect(page.getByText(/重新计算完成/)).toBeVisible()
  await expectCalculated(page)
  await expect(page.getByTestId("confirm-month-button")).toBeEnabled()
  await expect(page.getByTestId("empty-state")).toContainText(
    `${MONTH} 还没有日结果`,
  )
})

test("stale results block confirmation until recalculation", async ({
  page,
}) => {
  const setup = await setupCalculatedMonth(page)
  await openResults(page)
  await expectCalculated(page)
  await expect(page.getByTestId("confirm-month-button")).toBeEnabled()

  await updateAttendanceRule(setup.companyId, { late_grace_min: 8 })
  await page.reload()

  await expect(page.getByTestId("month-stale-banner")).toBeVisible()
  await expect(page.getByTestId("confirm-month-button")).toBeDisabled()
  await expect(page.getByTestId("month-action-hint")).toContainText(
    "结果已过期，请先重新计算后再确认",
  )

  await page.getByTestId("recalculate-button").click()
  await expect(page.getByText(/重新计算完成/)).toBeVisible()
  await expect(page.getByTestId("month-stale-banner")).toHaveCount(0)
  await expect(page.getByTestId("confirm-month-button")).toBeEnabled()
})

test("confirmed and locked months read as closed on every attendance page", async ({
  page,
}) => {
  const setup = await setupCalculatedMonth(page)
  await openResults(page)

  await page.getByTestId("confirm-month-button").click()
  await expect(page.getByText(/考勤结果已确认/)).toBeVisible()
  await expect(page.getByTestId("month-confirmed-banner")).toBeVisible()
  await expect(page.getByTestId("recalculate-button")).toBeDisabled()
  await expect(page.getByTestId("unconfirm-month-button")).toBeVisible()

  await openSchedule(page)
  await expect(page.getByTestId("month-confirmed-banner")).toBeVisible()
  await expect(
    page.getByRole("button", { name: "新建方案" }).first(),
  ).toBeDisabled()

  await openImports(page)
  await expect(page.getByTestId("import-month-status")).toHaveText("已确认")
  await expect(page.getByTestId("import-month-closed")).toBeVisible()

  // Unconfirm returns to calculated without a reason and re-enables editing.
  await openResults(page)
  await page.getByTestId("unconfirm-month-button").click()
  await expect(page.getByText(/已取消确认/)).toBeVisible()
  await expectCalculated(page)
  await expect(page.getByTestId("month-confirmed-banner")).toHaveCount(0)
  await expect(page.getByTestId("confirm-month-button")).toBeEnabled()

  await openSchedule(page)
  await expect(page.getByTestId("month-confirmed-banner")).toHaveCount(0)
  await expect(
    page.getByRole("button", { name: "新建方案" }).first(),
  ).toBeEnabled()

  await openResults(page)
  await page.getByTestId("confirm-month-button").click()
  await expect(page.getByTestId("month-confirmed-banner")).toBeVisible()
  await page.getByTestId("lock-month-button").click()
  await page.getByTestId("lock-submit").click()
  await expect(page.getByText(/已锁定，并生成不可变快照/)).toBeVisible()
  await expect(page.getByTestId("month-locked-banner")).toBeVisible()
  await expect(page.getByTestId("recalculate-button")).toBeDisabled()

  await openSchedule(page)
  await expect(page.getByTestId("month-locked-banner")).toBeVisible()
  await expect(
    page.getByRole("button", { name: "新建方案" }).first(),
  ).toBeDisabled()

  await openImports(page)
  await expect(page.getByTestId("import-month-status")).toHaveText("已锁定")
  await expect(page.getByTestId("import-month-closed")).toBeVisible()

  // A reason is mandatory; unlocking always returns the month as stale.
  const unlocked = await unlockMonth(setup.companyId, MONTH, "复核后重新打开")
  expect(unlocked.status).toBe("calculated")
  expect(unlocked.is_stale).toBe(true)

  await openResults(page)
  await expect(page.getByTestId("month-locked-banner")).toHaveCount(0)
  await expect(page.getByTestId("month-stale-banner")).toBeVisible()
  await expect(page.getByTestId("confirm-month-button")).toBeDisabled()
  await expect(page.getByTestId("recalculate-button")).toBeEnabled()

  await openSchedule(page)
  await expect(page.getByTestId("month-stale-banner")).toBeVisible()

  await openImports(page)
  await expect(page.getByTestId("import-month-stale")).toBeVisible()
})

test("a confirmed month must be recalculated after unlock before it can close again", async ({
  page,
}) => {
  const setup = await setupCalculatedMonth(page)
  await openResults(page)
  await confirmMonth(setup.companyId, MONTH)
  await lockMonth(setup.companyId, MONTH)
  await page.reload()
  await expect(page.getByTestId("month-locked-banner")).toBeVisible()

  await unlockMonth(setup.companyId, MONTH, "修正导入数据")
  await page.reload()
  await expect(page.getByTestId("month-stale-banner")).toBeVisible()
  await expect(page.getByTestId("confirm-month-button")).toBeDisabled()
  await expect(page.getByTestId("month-action-hint")).toContainText(
    "结果已过期",
  )

  await page.getByTestId("recalculate-button").click()
  await expect(page.getByText(/重新计算完成/)).toBeVisible()
  await expect(page.getByTestId("month-stale-banner")).toHaveCount(0)
  await expect(page.getByTestId("confirm-month-button")).toBeEnabled()
})
