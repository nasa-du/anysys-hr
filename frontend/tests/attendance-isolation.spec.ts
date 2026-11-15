import { expect, type Page, test } from "@playwright/test"

import {
  type AttendanceBootstrap,
  bootstrapAttendanceCompany,
  createHoliday,
  createSchedulePlan,
} from "./utils/api"
import {
  expectHeading,
  openAttendanceMonth,
  switchCompany,
} from "./utils/attendance-page"

test.setTimeout(120_000)

const MONTH = "2026-09"

async function expectShiftIsolation(
  page: Page,
  visible: AttendanceBootstrap,
  hidden: AttendanceBootstrap,
): Promise<void> {
  await page.goto("/attendance/shifts")
  await expectHeading(page, "班次")
  await expect(page.getByTestId("shift-table")).toContainText(
    visible.shift.shift_name,
  )
  await expect(page.getByTestId("shift-table")).not.toContainText(
    hidden.shift.shift_name,
  )
}

async function expectHolidayIsolation(
  page: Page,
  visibleName: string,
  hiddenName: string,
): Promise<void> {
  await page.goto("/attendance/rules")
  await expectHeading(page, "规则与节假日")
  await expect(page.getByTestId("holiday-calendar")).toContainText(visibleName)
  await expect(page.getByTestId("holiday-calendar")).not.toContainText(
    hiddenName,
  )
}

async function expectPlanIsolation(
  page: Page,
  visibleName: string,
  hiddenName: string,
): Promise<void> {
  await page.goto("/attendance/schedule")
  await expectHeading(page, "排班工作台")
  await expect(page.getByTestId("plan-list")).toContainText(visibleName)
  await expect(page.getByTestId("plan-list")).not.toContainText(hiddenName)
}

async function expectBatchIsolation(
  page: Page,
  visible: boolean,
): Promise<void> {
  await page.goto("/attendance/imports")
  await expectHeading(page, "导入中心")
  const punchBatch = page.getByTestId("current-batch-punch")
  await expect(
    punchBatch.getByText(visible ? "生效" : "未生效", { exact: true }),
  ).toBeVisible()
}

async function expectResultIsolation(
  page: Page,
  visibleNo: string,
  hiddenNo: string,
): Promise<void> {
  await page.goto("/attendance/results")
  await expectHeading(page, "考勤结果")
  await expect(page.getByTestId("day-results-table")).toContainText(visibleNo)
  await expect(page.getByTestId("day-results-table")).not.toContainText(
    hiddenNo,
  )
}

test("two companies never see each other's attendance data", async ({
  page,
}) => {
  const companyA = await bootstrapAttendanceCompany({
    employeeName: "甲公司员工",
    workDates: ["2026-09-07"],
    month: MONTH,
  })
  const companyB = await bootstrapAttendanceCompany({
    employeeName: "乙公司员工",
  })
  await createHoliday({
    company_id: companyA.company.id,
    date: "2026-09-25",
    name: "甲公司节日",
  })
  await createHoliday({
    company_id: companyB.company.id,
    date: "2026-09-25",
    name: "乙公司节日",
  })
  await createSchedulePlan({
    company_id: companyA.company.id,
    month: MONTH,
    plan_name: "甲公司方案",
  })
  await createSchedulePlan({
    company_id: companyB.company.id,
    month: MONTH,
    plan_name: "乙公司方案",
  })

  await openAttendanceMonth(page, companyA.company.id, MONTH)

  await expectShiftIsolation(page, companyA, companyB)
  await expectHolidayIsolation(page, "甲公司节日", "乙公司节日")
  await expectPlanIsolation(page, "甲公司方案", "乙公司方案")
  await expectBatchIsolation(page, true)
  await expectResultIsolation(page, companyA.employeeNo, companyB.employeeNo)

  await switchCompany(page, companyB.company)

  await expectShiftIsolation(page, companyB, companyA)
  await expectHolidayIsolation(page, "乙公司节日", "甲公司节日")
  await expectPlanIsolation(page, "乙公司方案", "甲公司方案")
  await expectBatchIsolation(page, false)
  await page.goto("/attendance/results")
  await expectHeading(page, "考勤结果")
  await expect(page.getByTestId("empty-state")).toContainText(
    `${MONTH} 还没有日结果`,
  )
})

test("switching companies discards the previous company's filters", async ({
  page,
}) => {
  const companyA = await bootstrapAttendanceCompany()
  const companyB = await bootstrapAttendanceCompany()
  await openAttendanceMonth(page, companyA.company.id, MONTH)

  await page.goto("/attendance/shifts")
  await page.getByLabel("搜索班次").fill(companyA.shift.shift_code)
  await expect(page.getByTestId("shift-table")).toContainText(
    companyA.shift.shift_name,
  )
  await expect(page.getByTestId("shift-table")).not.toContainText(
    companyB.shift.shift_name,
  )

  await switchCompany(page, companyB.company)

  // The workspace remounts per company: the search filter is empty and the
  // other company's shifts are visible.
  await expect(page.getByLabel("搜索班次")).toHaveValue("")
  await expect(page.getByTestId("shift-table")).toContainText(
    companyB.shift.shift_name,
  )
  await expect(page.getByTestId("shift-table")).not.toContainText(
    companyA.shift.shift_name,
  )

  await page.goto("/attendance/results")
  await expectHeading(page, "考勤结果")
  await expect(page.getByTestId("empty-state")).toContainText(
    `${MONTH} 还没有日结果`,
  )
})
