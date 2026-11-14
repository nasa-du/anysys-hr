import { expect, type Page, test } from "@playwright/test"

const ATTENDANCE_MODULES = [
  { link: "排班工作台", path: "/attendance/schedule", heading: "排班工作台" },
  { link: "导入中心", path: "/attendance/imports", heading: "导入中心" },
  { link: "考勤结果", path: "/attendance/results", heading: "考勤结果" },
  {
    link: "规则与节假日",
    path: "/attendance/rules",
    heading: "规则与节假日",
  },
  { link: "班次", path: "/attendance/shifts", heading: "班次" },
]

const ATTENDANCE_MONTH_STORAGE_KEY = "attendance.month"

function currentShanghaiMonth(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
  }).format(new Date())
}

async function expectAttendanceShell(page: Page) {
  await expect(page.getByRole("combobox", { name: "切换公司" })).toBeVisible()
  await expect(page.getByLabel("考勤月份")).toBeVisible()
}

test("the sidebar shows the five attendance entries in Scheme A order", async ({
  page,
}) => {
  await page.goto("/")

  await expect(page.getByText("考勤管理")).toBeVisible()
  const attendanceLinks = page.locator('a[href^="/attendance/"]')
  await expect(attendanceLinks).toHaveText(
    ATTENDANCE_MODULES.map((module) => module.link),
  )
})

test("every attendance module is reachable with the shared month context", async ({
  page,
}) => {
  await page.goto("/attendance/schedule")

  for (const { link, path, heading } of ATTENDANCE_MODULES) {
    await page.getByRole("link", { name: link, exact: true }).click()
    await expect(page).toHaveURL(new RegExp(`${path}$`))
    await expect(
      page.getByRole("heading", { name: heading, exact: true }),
    ).toBeVisible()
    await expectAttendanceShell(page)
  }
})

test("the bare attendance path redirects to the schedule workbench", async ({
  page,
}) => {
  await page.goto("/attendance")

  await expect(page).toHaveURL(/\/attendance\/schedule$/)
  await expect(
    page.getByRole("heading", { name: "排班工作台", exact: true }),
  ).toBeVisible()
})

test("the attendance month defaults to the current Shanghai month", async ({
  page,
}) => {
  await page.goto("/attendance/results")

  await expect(page.getByLabel("考勤月份")).toHaveValue(currentShanghaiMonth())
})

test("the attendance month persists across pages and reloads", async ({
  page,
}) => {
  await page.goto("/attendance/schedule")

  await page.getByLabel("考勤月份").fill("2026-09")
  await page.reload()
  await expect(page.getByLabel("考勤月份")).toHaveValue("2026-09")

  await page.getByRole("link", { name: "考勤结果", exact: true }).click()
  await expect(page.getByLabel("考勤月份")).toHaveValue("2026-09")

  expect(
    await page.evaluate(
      (key) => window.localStorage.getItem(key),
      ATTENDANCE_MONTH_STORAGE_KEY,
    ),
  ).toBe("2026-09")
})
