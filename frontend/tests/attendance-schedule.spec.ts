import { expect, type Page, test } from "@playwright/test"
import {
  createCompany,
  createDepartment,
  createEmployee,
  createManualRosterEntry,
  createPosition,
  createSchedulePlan,
  createShift,
  readRosterEntries,
  readSchedulePlans,
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

test.setTimeout(90_000)

const MONTH = "2026-09"
const NEXT_MONTH = "2026-10"

type Setup = {
  companyId: string
  departmentId: string
  positionId: string
  employeeId: string
  employeeNo: string
  employeeName: string
  shiftId: string
  shiftName: string
  secondShiftId: string
  secondShiftName: string
}

async function setup(page: Page): Promise<Setup> {
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
  const employeeName = randomEmployeeName()
  const employeeNo = randomEmployeeNo()
  const employee = await createEmployee({
    employee_no: employeeNo,
    name: employeeName,
    dept_id: department.id,
    position_id: position.id,
    hire_date: "2026-01-01",
  })
  const shiftName = randomShiftName()
  const shift = await createShift({
    company_id: company.id,
    shift_code: randomShiftCode(),
    shift_name: shiftName,
  })
  const secondShiftName = randomShiftName()
  const secondShift = await createShift({
    company_id: company.id,
    shift_code: randomShiftCode(),
    shift_name: secondShiftName,
    start_time: "18:00:00",
    end_time: "22:00:00",
  })
  await setActiveCompany(page, company.id)
  await page.addInitScript((month: string) => {
    window.localStorage.setItem("attendance.month", month)
  }, MONTH)
  return {
    companyId: company.id,
    departmentId: department.id,
    positionId: position.id,
    employeeId: employee.id,
    employeeNo,
    employeeName,
    shiftId: shift.id,
    shiftName,
    secondShiftId: secondShift.id,
    secondShiftName,
  }
}

async function openWorkbench(page: Page) {
  await page.goto("/attendance/schedule")
  await expect(
    page.getByRole("heading", { name: "排班工作台", exact: true }),
  ).toBeVisible()
}

async function startPlanThroughUi(page: Page, name: string, shiftName: string) {
  await page.getByRole("button", { name: "新建方案" }).first().click()
  const editor = page.getByTestId("plan-editor")
  await expect(
    editor.getByRole("heading", { name: "新建排班方案" }),
  ).toBeVisible()
  await editor.getByLabel("方案名称").fill(name)
  await editor.getByTestId("plan-day-1").click()
  await editor.getByLabel(`第 1 天 ${shiftName}`).check()
  await editor.getByRole("button", { name: "预览并保存" }).click()
  await expect(page.getByText("影响员工")).toBeVisible()
}

test("creates a plan, previews the expansion, and shows who works that day", async ({
  page,
}) => {
  const setupData = await setup(page)
  await openWorkbench(page)

  await startPlanThroughUi(page, "行政班方案", setupData.shiftName)
  await page.getByRole("button", { name: "保存并展开" }).click()
  await expect(page.getByText(/排班方案已创建/).first()).toBeVisible()
  await expect(
    page.getByTestId("plan-list").getByText("行政班方案", { exact: true }),
  ).toBeVisible()

  // Saving expanded the month: the merged day sheet resolves the employee.
  await page.getByTestId("plan-card-all").click()
  await page.getByTestId("calendar-day-1").click()
  const sheet = page.getByTestId("day-sheet")
  await expect(sheet.getByRole("heading", { name: /这天谁上班/ })).toBeVisible()
  await expect(sheet.getByText(setupData.employeeName)).toBeVisible()
  await expect(sheet.getByText(/上班 1 人/)).toBeVisible()
  await sheet.getByRole("button", { name: "关闭", exact: true }).first().click()
})

test("same-precision conflict preview blocks saving a second plan", async ({
  page,
}) => {
  const setupData = await setup(page)
  await createSchedulePlan({
    company_id: setupData.companyId,
    month: MONTH,
    plan_name: "全公司标准班",
  })
  await openWorkbench(page)

  await startPlanThroughUi(page, "冲突方案", setupData.shiftName)
  await expect(page.getByTestId("preview-conflicts")).toBeVisible()
  await expect(page.getByTestId("preview-conflicts")).toContainText(
    "全公司标准班",
  )
  await expect(page.getByRole("button", { name: "保存并展开" })).toBeDisabled()

  await page.getByRole("button", { name: "返回修改" }).click()
  await page.getByRole("button", { name: "取消" }).click()
  await expect(
    page.getByTestId("plan-list").getByText("冲突方案", { exact: true }),
  ).toHaveCount(0)
})

test("re-expand preview applies and reports roster counts", async ({
  page,
}) => {
  const setupData = await setup(page)
  await createSchedulePlan({
    company_id: setupData.companyId,
    month: MONTH,
    plan_name: "全公司标准班",
    days: [{ day_of_month: 1, seq: 0, shift_id: setupData.shiftId }],
  })
  await openWorkbench(page)

  await page
    .getByTestId("plan-list")
    .getByRole("button")
    .filter({ hasText: "全公司标准班" })
    .click()
  await page.getByRole("button", { name: "重新展开" }).click()

  const dialog = page.getByRole("dialog")
  await expect(
    dialog.getByRole("heading", { name: "重新展开预览" }),
  ).toBeVisible()
  await expect(dialog.getByText("影响员工")).toBeVisible()
  await dialog.getByRole("button", { name: "确认重新展开" }).click()
  await expect(page.getByText(/已重新展开/).first()).toBeVisible()
})

test("copies the plan to the next natural month", async ({ page }) => {
  const setupData = await setup(page)
  await createSchedulePlan({
    company_id: setupData.companyId,
    month: MONTH,
    plan_name: "九月行政班",
    days: [{ day_of_month: 1, seq: 0, shift_id: setupData.shiftId }],
  })
  await openWorkbench(page)

  await page
    .getByTestId("plan-list")
    .getByRole("button")
    .filter({ hasText: "九月行政班" })
    .click()
  await page.getByRole("button", { name: "复制下月" }).click()

  const dialog = page.getByTestId("copy-month-dialog")
  await expect(dialog.getByText(`${MONTH} → ${NEXT_MONTH}`)).toBeVisible()
  await dialog.getByRole("button", { name: "预览复制" }).click()
  // September has 30 days and October 31: the preview warns about the gap.
  await expect(dialog.getByText(/目标月份比源月份多 1 天/)).toBeVisible()
  await dialog.getByRole("button", { name: "确认复制并展开" }).click()
  await expect(
    page.getByText(new RegExp(`已复制到 ${NEXT_MONTH}`)).first(),
  ).toBeVisible()

  const copied = await readSchedulePlans(setupData.companyId, NEXT_MONTH)
  expect(copied).toHaveLength(1)
  expect(copied[0].copied_from_plan_id).not.toBeNull()
  expect(copied[0].days.map((day) => day.day_of_month)).toEqual([1])

  await page.getByLabel("考勤月份").fill(NEXT_MONTH)
  await expect(
    page.getByTestId("plan-list").getByText("九月行政班", { exact: true }),
  ).toBeVisible()
})

test("archives a plan and keeps it visible as archived", async ({ page }) => {
  const setupData = await setup(page)
  await createSchedulePlan({
    company_id: setupData.companyId,
    month: MONTH,
    plan_name: "待归档方案",
    days: [{ day_of_month: 1, seq: 0, shift_id: setupData.shiftId }],
  })
  await openWorkbench(page)

  await page
    .getByTestId("plan-list")
    .getByRole("button")
    .filter({ hasText: "待归档方案" })
    .click()
  await page.getByRole("button", { name: "归档", exact: true }).click()

  const dialog = page.getByRole("dialog")
  await expect(
    dialog.getByRole("heading", { name: "归档排班方案" }),
  ).toBeVisible()
  await dialog.getByRole("button", { name: "确认归档" }).click()
  await expect(page.getByText(/排班方案已归档/).first()).toBeVisible()
  await expect(
    page.getByTestId("plan-list").getByText("已归档", { exact: true }),
  ).toBeVisible()

  const [archived] = await readSchedulePlans(setupData.companyId, MONTH)
  expect(archived.status).toBe("archived")
})

test("creates, edits, and deletes a multi-shift manual exception", async ({
  page,
}) => {
  const setupData = await setup(page)
  await openWorkbench(page)
  await page.getByTestId("view-employee").click()
  await expect(page.getByTestId("employee-calendar")).toBeVisible()
  await expect(page.getByTestId("roster-month-overview")).toContainText(
    "上班人日",
  )
  await page.getByTestId(`roster-employee-${setupData.employeeNo}`).click()
  await expect(page.getByTestId("roster-day-1")).toContainText("未排班")

  await page.getByTestId("roster-day-1").click()
  const dialog = page.getByTestId("manual-exception-dialog")
  await expect(
    dialog.getByRole("heading", { name: "新建人工例外" }),
  ).toBeVisible()
  await dialog.getByRole("button", { name: "休息", exact: true }).click()
  await dialog.getByRole("button", { name: "保存例外" }).click()
  await expect(page.getByText(/人工例外已保存/).first()).toBeVisible()
  await expect(dialog).toBeHidden()
  await expect(page.getByTestId("roster-day-1")).toContainText("休息")
  await expect(page.getByTestId("roster-day-1")).toContainText("人工")

  await page.getByTestId("roster-day-1").click()
  await expect(
    dialog.getByRole("heading", { name: "编辑人工例外" }),
  ).toBeVisible()
  await dialog.getByRole("button", { name: "上班", exact: true }).click()
  await dialog.getByLabel(`班次 ${setupData.shiftName}`).check()
  await dialog.getByLabel(`班次 ${setupData.secondShiftName}`).check()
  await dialog.getByRole("button", { name: "保存例外" }).click()
  await expect(page.getByText(/人工例外已更新/).first()).toBeVisible()
  await expect(dialog).toBeHidden()
  await expect(page.getByTestId("roster-day-1")).toContainText(
    setupData.shiftName,
  )
  await expect(page.getByTestId("roster-day-1")).toContainText(
    setupData.secondShiftName,
  )
  await expect(page.getByTestId("roster-month-overview")).toContainText(
    setupData.shiftName,
  )
  await expect(page.getByTestId("roster-month-overview")).toContainText(
    setupData.secondShiftName,
  )

  await page.getByTestId("roster-day-1").click()
  await dialog.getByRole("button", { name: "删除例外" }).click()
  await page.getByRole("button", { name: "确认删除" }).click()
  await expect(page.getByText(/人工例外已删除/).first()).toBeVisible()
  await expect(page.getByTestId("roster-day-1")).toContainText("未排班")
})

test("batch fill applies workdays and clearing restores the plan", async ({
  page,
}) => {
  const setupData = await setup(page)
  await createSchedulePlan({
    company_id: setupData.companyId,
    month: MONTH,
    plan_name: "标准班",
    days: [{ day_of_month: 1, seq: 0, shift_id: setupData.shiftId }],
  })
  await openWorkbench(page)
  await page.getByTestId("view-employee").click()
  await page.getByTestId(`roster-employee-${setupData.employeeNo}`).click()
  await expect(page.getByTestId("roster-day-1")).toContainText("方案")

  await page.getByTestId("open-batch-fill").click()
  const dialog = page.getByTestId("batch-fill-dialog")
  await expect(dialog.getByRole("heading", { name: "批量填充" })).toBeVisible()
  await dialog.getByLabel(`班次 ${setupData.shiftName}`).check()
  await expect(dialog.getByText("预计人日")).toBeVisible()
  await dialog.getByRole("button", { name: "应用批量调整" }).click()
  await expect(page.getByText(/已批量调整/).first()).toBeVisible()
  await expect(dialog).toBeHidden()
  await expect(page.getByTestId("roster-day-1")).toContainText("人工")

  await page.getByTestId("open-batch-fill").click()
  await dialog.getByRole("button", { name: "清除人工例外" }).click()
  await dialog.getByRole("button", { name: "应用批量调整" }).click()
  await expect(page.getByText(/已清除/).first()).toBeVisible()
  await expect(page.getByTestId("roster-day-1")).toContainText("方案")
  await expect(page.getByTestId("roster-day-1")).toContainText(
    setupData.shiftName,
  )
})

test("sync personnel previews hires and preserves manual exceptions", async ({
  page,
}) => {
  const setupData = await setup(page)
  await createSchedulePlan({
    company_id: setupData.companyId,
    month: MONTH,
    plan_name: "标准班",
    days: [{ day_of_month: 1, seq: 0, shift_id: setupData.shiftId }],
  })
  await createManualRosterEntry({
    employee_id: setupData.employeeId,
    work_date: `${MONTH}-02`,
    state: "rest",
    note: "手动休息",
  })
  const newHire = await createEmployee({
    employee_no: randomEmployeeNo(),
    name: randomEmployeeName(),
    dept_id: setupData.departmentId,
    position_id: setupData.positionId,
    hire_date: `${MONTH}-03`,
  })

  await openWorkbench(page)
  await page.getByTestId("open-sync-personnel").click()
  const dialog = page.getByTestId("sync-personnel-dialog")
  await expect(dialog.getByText("员工变化")).toBeVisible()
  await expect(dialog.getByTestId("sync-added")).toContainText("1")
  await expect(dialog.getByTestId("sync-manual-preserved")).toContainText("1")
  await dialog.getByRole("button", { name: "确认同步" }).click()
  await expect(page.getByText(/人员已同步/).first()).toBeVisible()

  const newEntries = await readRosterEntries(
    setupData.companyId,
    MONTH,
    newHire.id,
  )
  expect(newEntries.length).toBe(28)
  expect(newEntries[0].work_date).toBe(`${MONTH}-03`)
  const manual = (
    await readRosterEntries(setupData.companyId, MONTH, setupData.employeeId)
  ).find((entry) => entry.work_date === `${MONTH}-02`)
  expect(manual?.source).toBe("manual")
})
