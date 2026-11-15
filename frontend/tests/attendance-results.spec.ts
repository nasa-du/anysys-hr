import { readFile } from "node:fs/promises"

import { expect, type Page, test } from "@playwright/test"

import {
  calculateMonth,
  createAdjustment,
  createCompany,
  createDepartment,
  createEmployee,
  createManualRosterEntry,
  createPosition,
  createShift,
  importPunchText,
  updateAttendanceRule,
} from "./utils/api"
import { setActiveCompany } from "./utils/company"
import {
  randomCompanyCode,
  randomCompanyName,
  randomDepartmentCode,
  randomEmployeeName,
  randomEmployeeNo,
  randomPositionCode,
  randomShiftCode,
  randomShiftName,
} from "./utils/random"

test.setTimeout(120_000)

const MONTH = "2026-09"
const LATE_DAY = "2026-09-07"
const NORMAL_DAY = "2026-09-08"
const ABSENT_DAY = "2026-09-09"

type ResultSetup = {
  companyId: string
  departmentId: string
  employeeId: string
  employeeNo: string
  employeeName: string
}

async function setupResults(page: Page): Promise<ResultSetup> {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  const department = await createDepartment({
    company_id: company.id,
    dept_code: randomDepartmentCode(),
    dept_name: "生产部",
  })
  const position = await createPosition({
    company_id: company.id,
    position_code: randomPositionCode(),
    position_name: "操作工",
    dept_id: department.id,
  })
  const employeeNo = randomEmployeeNo()
  const employeeName = randomEmployeeName()
  const employee = await createEmployee({
    employee_no: employeeNo,
    name: employeeName,
    dept_id: department.id,
    position_id: position.id,
    hire_date: "2026-01-01",
  })
  const shift = await createShift({
    company_id: company.id,
    shift_code: randomShiftCode(),
    shift_name: randomShiftName(),
    start_time: "08:30:00",
    end_time: "17:30:00",
    rest_minutes: 60,
  })
  for (const workDate of [LATE_DAY, NORMAL_DAY, ABSENT_DAY]) {
    await createManualRosterEntry({
      employee_id: employee.id,
      work_date: workDate,
      state: "work",
      shifts: [{ seq: 0, shift_id: shift.id }],
    })
  }
  await importPunchText({
    company_id: company.id,
    month: MONTH,
    text: [
      "工号,考勤日期,打卡时间,打卡结果",
      `${employeeNo},${LATE_DAY},${LATE_DAY} 08:42,正常`,
      `${employeeNo},${LATE_DAY},${LATE_DAY} 17:30,正常`,
      `${employeeNo},${NORMAL_DAY},${NORMAL_DAY} 08:20,正常`,
      `${employeeNo},${NORMAL_DAY},${NORMAL_DAY} 17:35,正常`,
    ].join("\n"),
  })
  await calculateMonth(company.id, MONTH)

  await setActiveCompany(page, company.id)
  await page.addInitScript((month: string) => {
    window.localStorage.setItem("attendance.month", month)
  }, MONTH)
  return {
    companyId: company.id,
    departmentId: department.id,
    employeeId: employee.id,
    employeeNo,
    employeeName,
  }
}

async function openResults(page: Page): Promise<void> {
  await page.goto("/attendance/results")
  await expect(
    page.getByRole("heading", { name: "考勤结果", exact: true }),
  ).toBeVisible()
  await expect(page.getByTestId("month-state-bar")).toBeVisible()
}

function dayRow(page: Page, setup: ResultSetup, workDate: string) {
  return page.getByTestId(`day-result-row-${setup.employeeId}-${workDate}`)
}

test("shows all day results and focuses anomalies with one click", async ({
  page,
}) => {
  const setup = await setupResults(page)
  await openResults(page)

  await expect(dayRow(page, setup, LATE_DAY)).toBeVisible()
  await expect(dayRow(page, setup, NORMAL_DAY)).toBeVisible()
  await expect(dayRow(page, setup, ABSENT_DAY)).toBeVisible()
  await expect(page.getByTestId("day-result-count")).toContainText("共 3 条")

  await page.getByTestId("anomaly-only").click()
  await expect(dayRow(page, setup, LATE_DAY)).toBeVisible()
  await expect(dayRow(page, setup, ABSENT_DAY)).toBeVisible()
  await expect(dayRow(page, setup, NORMAL_DAY)).toHaveCount(0)
  await expect(page.getByTestId("day-result-count")).toContainText("共 2 条")

  await page.getByTestId("anomaly-only").click()
  await expect(dayRow(page, setup, NORMAL_DAY)).toBeVisible()
})

test("filters day results by status, date, and employee keyword", async ({
  page,
}) => {
  const setup = await setupResults(page)
  await openResults(page)

  await page.getByTestId("filter-day-status").click()
  await page.getByRole("option", { name: "迟到", exact: true }).click()
  await expect(dayRow(page, setup, LATE_DAY)).toBeVisible()
  await expect(dayRow(page, setup, ABSENT_DAY)).toHaveCount(0)
  await expect(dayRow(page, setup, NORMAL_DAY)).toHaveCount(0)

  await page.getByTestId("reset-filters").click()
  await page.getByTestId("filter-date-from").fill(LATE_DAY)
  await page.getByTestId("filter-date-to").fill(LATE_DAY)
  await expect(dayRow(page, setup, LATE_DAY)).toBeVisible()
  await expect(dayRow(page, setup, ABSENT_DAY)).toHaveCount(0)

  await page.getByTestId("reset-filters").click()
  await page.getByTestId("filter-keyword").fill(setup.employeeName)
  await expect(dayRow(page, setup, LATE_DAY)).toBeVisible()
  await expect(page.getByTestId("day-result-count")).toContainText("共 3 条")

  await page.getByTestId("filter-keyword").fill("不存在的员工")
  await expect(page.getByTestId("empty-state")).toBeVisible()
})

test("opens the day drawer with the four-way comparison and timeline", async ({
  page,
}) => {
  const setup = await setupResults(page)
  await openResults(page)

  await dayRow(page, setup, LATE_DAY).click()
  const drawer = page.getByTestId("day-detail-drawer")
  await expect(drawer).toBeVisible()
  await expect(drawer).toContainText(setup.employeeName)
  await expect(page.getByTestId("four-way-comparison")).toBeVisible()
  await expect(page.getByTestId("four-card-roster")).toContainText("上班")
  await expect(page.getByTestId("four-card-punch")).toContainText("08:42")
  await expect(page.getByTestId("four-card-oa")).toContainText("无 OA 申请")
  await expect(page.getByTestId("four-card-result")).toContainText("出勤比例")
  await expect(page.getByTestId("four-way-timeline")).toBeVisible()
  await expect(page.getByTestId("timeline-track")).toBeVisible()
  await expect(page.getByTestId("timeline-shift-0")).toBeVisible()
  await expect(page.getByTestId("timeline-result-0")).toContainText("迟到")
  await expect(page.getByTestId("shift-result-table")).toContainText("迟到")
  await expect(page.getByTestId("shift-result-table")).toContainText("7 / 0 分")
})

test("recalculates explicitly and lists calculation runs", async ({ page }) => {
  const setup = await setupResults(page)
  await openResults(page)

  await expect(page.getByTestId("recalculate-button")).toBeEnabled()
  await page.getByTestId("recalculate-button").click()
  await expect(page.getByText(/重新计算完成/)).toBeVisible()

  await page.getByTestId("tab-runs").click()
  await expect(page.getByTestId("calc-run-list")).toBeVisible()
  await expect(
    page.getByTestId("calc-run-list").getByText("手动", { exact: true }),
  ).toBeVisible()
  await expect(
    page.getByTestId("calc-run-list").getByText("首次", { exact: true }),
  ).toBeVisible()

  await page.getByTestId("tab-days").click()
  await expect(dayRow(page, setup, LATE_DAY)).toBeVisible()
})

test("shows the stale banner after a rule change and clears it on recalculate", async ({
  page,
}) => {
  const setup = await setupResults(page)
  await openResults(page)
  await expect(page.getByTestId("month-stale-banner")).toHaveCount(0)

  await updateAttendanceRule(setup.companyId, { late_grace_min: 6 })
  await page.reload()
  await expect(page.getByTestId("month-stale-banner")).toBeVisible()

  await page.getByTestId("recalculate-button").click()
  await expect(page.getByText(/重新计算完成/)).toBeVisible()
  await expect(page.getByTestId("month-stale-banner")).toHaveCount(0)
})

test("renders locked months as read-only with a disabled explanation", async ({
  page,
}) => {
  await setupResults(page)
  await page.route(
    (url) => url.pathname.endsWith(`/attendance/months/${MONTH}`),
    async (route) => {
      const response = await route.fetch()
      const body = (await response.json()) as Record<string, unknown>
      body.status = "locked"
      body.is_stale = false
      body.locked_at = "2026-09-30T10:00:00Z"
      body.unlock_reason = "复核后重新打开"
      await route.fulfill({ response, json: body })
    },
  )
  await openResults(page)

  await expect(page.getByTestId("month-locked-banner")).toBeVisible()
  await expect(page.getByTestId("month-locked-banner")).toContainText(
    "复核后重新打开",
  )
  await expect(page.getByTestId("month-state-step-locked")).toHaveAttribute(
    "data-current",
    "true",
  )
  await expect(page.getByTestId("recalculate-button")).toBeDisabled()
  await expect(page.getByTestId("recalc-hint")).toContainText("已锁定")
})

async function openAdjustmentDialog(
  page: Page,
  setup: ResultSetup,
): Promise<void> {
  await dayRow(page, setup, LATE_DAY).click()
  const drawer = page.getByTestId("day-detail-drawer")
  await expect(drawer).toBeVisible()
  await drawer.getByTestId("open-adjustment-dialog").click()
  await expect(page.getByTestId("adjustment-dialog")).toBeVisible()
}

test("adjusts a day, keeps version history, re-applies, and undoes", async ({
  page,
}) => {
  const setup = await setupResults(page)
  await openResults(page)
  await openAdjustmentDialog(page, setup)

  const dialog = page.getByTestId("adjustment-dialog")
  const drawer = page.getByTestId("day-detail-drawer")
  await expect(
    dialog.getByTestId("adjustment-original-day_status"),
  ).toContainText("迟到")
  await expect(
    dialog.getByTestId("adjustment-original-late_minutes"),
  ).toContainText("7")

  await dialog.getByTestId("adjustment-input-day_status").click()
  await page.getByRole("option", { name: "正常", exact: true }).click()
  await dialog.getByTestId("adjustment-input-late_minutes").fill("0")
  await dialog.getByTestId("adjustment-reason").fill("核实后不计迟到")
  await dialog.getByTestId("adjustment-submit").click()

  await expect(page.getByText("人工调整已保存")).toBeVisible()
  await expect(dialog).toHaveCount(0)
  const history = drawer.getByTestId("adjustment-history")
  await expect(history).toContainText("版本 1 · 生效")
  await expect(history).toContainText("核实后不计迟到")
  await expect(drawer.getByTestId("day-result-status")).toHaveText("正常")
  await expect(dayRow(page, setup, LATE_DAY)).toContainText("已调整")

  await page.keyboard.press("Escape")
  await expect(drawer).toHaveCount(0)
  await page.getByTestId("recalculate-button").click()
  await expect(page.getByText(/重新计算完成/)).toBeVisible()
  await expect(dayRow(page, setup, LATE_DAY)).toContainText("已调整")

  await dayRow(page, setup, LATE_DAY).click()
  await expect(drawer).toBeVisible()
  await expect(drawer.getByTestId("day-result-status")).toHaveText("正常")
  await expect(drawer.getByTestId("adjustment-history")).toContainText(
    "版本 1 · 生效",
  )

  await drawer.getByTestId("undo-adjustment-1").click()
  await page.getByRole("button", { name: "确认撤销" }).click()
  await expect(page.getByText("已撤销调整", { exact: false })).toBeVisible()
  const restored = drawer.getByTestId("adjustment-history")
  await expect(restored).toContainText("版本 2 · 生效")
  await expect(restored).toContainText("版本 1 · 已替代")
  await expect(drawer.getByTestId("day-result-status")).toHaveText("迟到")
})

test("surfaces a conflict when another version was submitted first", async ({
  page,
}) => {
  const setup = await setupResults(page)
  await openResults(page)
  await openAdjustmentDialog(page, setup)

  const dialog = page.getByTestId("adjustment-dialog")
  const drawer = page.getByTestId("day-detail-drawer")
  await dialog.getByTestId("adjustment-input-late_minutes").fill("0")
  await dialog.getByTestId("adjustment-reason").fill("并发提交")

  await createAdjustment({
    company_id: setup.companyId,
    employee_id: setup.employeeId,
    work_date: LATE_DAY,
    base_version: 0,
    adjusted_values: { day_status: "normal" },
    reason: "他人先提交",
  })

  await dialog.getByTestId("adjustment-submit").click()
  await expect(dialog.getByTestId("adjustment-conflict")).toBeVisible()
  await expect(dialog.getByTestId("adjustment-conflict")).toContainText(
    "调整版本已变化",
  )

  await dialog.getByTestId("adjustment-refresh").click()
  await expect(dialog).toHaveCount(0)
  await expect(drawer.getByTestId("adjustment-history")).toContainText(
    "版本 1 · 生效",
  )
  await expect(drawer.getByTestId("adjustment-history")).toContainText(
    "他人先提交",
  )
  await expect(drawer.getByTestId("day-result-status")).toHaveText("正常")
})

test("confirms, locks, views snapshots, exports, and requires recalculation after unlock", async ({
  page,
}) => {
  const setup = await setupResults(page)
  await openResults(page)

  const confirmButton = page.getByTestId("confirm-month-button")
  await expect(confirmButton).toBeEnabled()
  await confirmButton.click()
  await expect(page.getByText(/考勤结果已确认/)).toBeVisible()
  await expect(page.getByTestId("month-confirmed-banner")).toBeVisible()
  await expect(page.getByTestId("recalculate-button")).toBeDisabled()

  await page.getByTestId("lock-month-button").click()
  await expect(page.getByTestId("lock-month-dialog")).toBeVisible()
  await page.getByTestId("lock-submit").click()
  await expect(page.getByText(/已锁定，并生成不可变快照/)).toBeVisible()
  await expect(page.getByTestId("month-locked-banner")).toBeVisible()
  await expect(page.getByTestId("month-state-step-locked")).toHaveAttribute(
    "data-current",
    "true",
  )
  await expect(page.getByTestId("month-action-hint")).toContainText("已锁定")

  await dayRow(page, setup, LATE_DAY).click()
  const drawer = page.getByTestId("day-detail-drawer")
  await expect(drawer).toBeVisible()
  await expect(drawer.getByTestId("open-adjustment-dialog")).toBeDisabled()
  await expect(drawer.getByTestId("adjustment-readonly")).toBeVisible()
  await page.keyboard.press("Escape")
  await expect(drawer).toHaveCount(0)

  await page.getByTestId("view-snapshots-button").click()
  const viewer = page.getByTestId("snapshot-viewer")
  await expect(viewer).toBeVisible()
  await expect(page.getByTestId("snapshot-row-1")).toBeVisible()
  await page.getByTestId("snapshot-toggle-1").click()
  await expect(page.getByTestId("snapshot-payload-1")).toContainText(
    "schema_version",
  )
  await page.keyboard.press("Escape")
  await expect(viewer).toHaveCount(0)

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("export-payroll-button").click(),
  ])
  expect(download.suggestedFilename()).toBe("attendance-payroll-2026-09.csv")
  const downloadPath = await download.path()
  expect(downloadPath).not.toBeNull()
  const csv = await readFile(downloadPath as string, "utf8")
  expect(csv.startsWith("\ufeff")).toBe(true)
  expect(csv).toContain(
    "attendance_month,company_name,employee_no,employee_name,department_name,weekday_full,weekend_full,weekday_attended,weekend_attended,paid_leave_days,ot_weekday_hours,ot_weekend_hours,ot_holiday_hours,attendance_deduct",
  )
  expect(csv).toContain(setup.employeeNo)

  await page.getByTestId("unlock-month-button").click()
  const unlockDialog = page.getByTestId("unlock-month-dialog")
  await expect(unlockDialog).toBeVisible()
  await unlockDialog.getByTestId("unlock-submit").click()
  await expect(unlockDialog.getByText("请填写解锁理由")).toBeVisible()
  await unlockDialog.getByTestId("unlock-reason-input").fill("复核后重新打开")
  await unlockDialog.getByTestId("unlock-submit").click()
  await expect(page.getByText(/已解锁，结果已标记为过期/)).toBeVisible()
  await expect(page.getByTestId("month-locked-banner")).toHaveCount(0)
  await expect(page.getByTestId("month-stale-banner")).toBeVisible()
  await expect(page.getByTestId("confirm-month-button")).toBeDisabled()
  await expect(page.getByTestId("month-action-hint")).toContainText("已过期")
  await expect(page.getByTestId("recalculate-button")).toBeEnabled()

  await page.getByTestId("recalculate-button").click()
  await expect(page.getByText(/重新计算完成/)).toBeVisible()
  await expect(page.getByTestId("month-stale-banner")).toHaveCount(0)
  await expect(page.getByTestId("confirm-month-button")).toBeEnabled()
})
