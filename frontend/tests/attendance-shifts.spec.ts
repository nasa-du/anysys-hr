import { expect, type Page, test } from "@playwright/test"
import { createCompany, createShift, readShift } from "./utils/api"
import { setActiveCompany } from "./utils/company"
import {
  randomCompanyCode,
  randomCompanyName,
  randomShiftCode,
  randomShiftName,
} from "./utils/random"

test.setTimeout(60_000)

const BLOCKED_DIALOG = "blocked-dialog"

async function setupCompany(page: Page) {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  await setActiveCompany(page, company.id)
  await page.goto("/attendance/shifts")
  return company
}

function shiftRow(page: Page, code: string) {
  return page
    .getByTestId("shift-table")
    .getByRole("row")
    .filter({ hasText: code })
}

async function openCreateDrawer(page: Page) {
  await page.getByRole("button", { name: "新增班次" }).first().click()
  return page.getByRole("dialog")
}

function blockedResponse(body: {
  code: string
  message: string
  type: "schedule_plan" | "roster_entry"
  label: string
  field_errors?: Record<string, string>
}) {
  return JSON.stringify({
    detail: {
      code: body.code,
      message: body.message,
      field_errors: body.field_errors ?? {},
      blockers: [
        {
          type: body.type,
          id: "019a0000-0000-7000-8000-000000000001",
          code: body.code === "referenced" ? "E101" : "2026-09",
          label: body.label,
        },
      ],
      blocker_count: 1,
    },
  })
}

test("the shifts page follows the company switcher with loading, empty, and month states", async ({
  page,
}) => {
  const company = await setupCompany(page)

  await expect(
    page.getByRole("heading", { name: "班次", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByText(`当前公司：${company.company_name}`),
  ).toBeVisible()
  await expect(page.getByLabel("考勤月份")).toBeVisible()
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "还没有班次",
  )
})

test("create and edit a shift with an immutable code", async ({ page }) => {
  await setupCompany(page)
  const code = randomShiftCode()
  const name = randomShiftName()

  let drawer = await openCreateDrawer(page)
  await drawer.getByLabel("班次编码").fill(code.toLowerCase())
  await drawer.getByLabel("班次名称").fill(name)
  await drawer.getByLabel("开始时间").fill("08:30")
  await drawer.getByLabel("结束时间").fill("17:30")
  await drawer.getByLabel("休息扣减（分钟）").fill("60")
  await drawer.getByRole("button", { name: "保存" }).click()

  await expect(page.getByText("班次创建成功").first()).toBeVisible()
  await expect(page.getByRole("dialog")).not.toBeVisible()

  const row = shiftRow(page, code)
  await expect(row).toContainText(name)
  await expect(row).toContainText("08:30–17:30")
  await expect(row).toContainText("启用")

  await row.getByRole("button", { name: "编辑" }).click()
  drawer = page.getByRole("dialog")
  await expect(drawer.getByLabel("班次编码")).toBeDisabled()
  const updatedName = randomShiftName()
  await drawer.getByLabel("班次名称").fill(updatedName)
  await drawer.getByLabel("结束时间").fill("18:00")
  await drawer.getByRole("button", { name: "保存" }).click()

  await expect(page.getByText("班次更新成功").first()).toBeVisible()
  await expect(shiftRow(page, code)).toContainText(updatedName)
  await expect(shiftRow(page, code)).toContainText("08:30–18:00")
})

test("editing other fields preserves existing second precision", async ({
  page,
}) => {
  const company = await setupCompany(page)
  const shift = await createShift({
    company_id: company.id,
    shift_code: randomShiftCode(),
    shift_name: randomShiftName(),
    start_time: "08:30:30",
    end_time: "17:30:00",
  })
  await page.goto("/attendance/shifts")
  const row = shiftRow(page, shift.shift_code)
  await expect(row).toContainText("08:30:30–17:30")

  await row.getByRole("button", { name: "编辑" }).click()
  const drawer = page.getByRole("dialog")
  await drawer.getByLabel("班次名称").fill(randomShiftName())
  await drawer.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("班次更新成功").first()).toBeVisible()

  const reloaded = await readShift(shift.id)
  expect(reloaded.start_time).toBe("08:30:30")
})

test("the drawer mirrors time, break, and rest-deduction validation", async ({
  page,
}) => {
  await setupCompany(page)
  const drawer = await openCreateDrawer(page)
  await drawer.getByLabel("班次编码").fill(randomShiftCode())
  await drawer.getByLabel("班次名称").fill(randomShiftName())
  await drawer.getByLabel("开始时间").fill("09:00")
  await drawer.getByLabel("结束时间").fill("08:00")
  await drawer.getByRole("button", { name: "保存" }).click()

  await expect(drawer.getByText("结束时间必须晚于开始时间")).toBeVisible()

  await drawer.getByRole("checkbox", { name: "跨天班次" }).check()
  await drawer.getByLabel("休息扣减（分钟）").fill("1441")
  await drawer.getByRole("button", { name: "保存" }).click()
  await expect(drawer.getByText(/休息扣减不能超过班次时长/)).toBeVisible()
  await expect(drawer.getByText("结束时间必须晚于开始时间")).toHaveCount(0)

  await drawer.getByLabel("休息扣减（分钟）").fill("60")
  await drawer.getByLabel("休息开始").fill("12:00")
  await drawer.getByRole("button", { name: "保存" }).click()
  await expect(drawer.getByText("休息开始与结束时间必须同时填写")).toBeVisible()

  await drawer.getByLabel("休息结束").fill("13:00")
  await drawer.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("班次创建成功").first()).toBeVisible()
})

test("deactivate and reactivate a shift with the row switch", async ({
  page,
}) => {
  const company = await setupCompany(page)
  const shift = await createShift({
    company_id: company.id,
    shift_code: randomShiftCode(),
    shift_name: randomShiftName(),
  })
  await page.goto("/attendance/shifts")

  const row = shiftRow(page, shift.shift_code)
  await expect(row).toBeVisible()
  await expect(row.getByRole("switch")).toHaveAttribute("aria-checked", "true")

  await row.getByRole("switch").click()
  await expect(page.getByText("班次已停用").first()).toBeVisible()
  await expect(row).toContainText("已停用")

  await row.getByRole("switch").click()
  await expect(page.getByText("班次已启用").first()).toBeVisible()
  await expect(row).toContainText("启用")
})

test("blocked deactivate and delete dialogs explain their references", async ({
  page,
}) => {
  const company = await setupCompany(page)
  const shift = await createShift({
    company_id: company.id,
    shift_code: randomShiftCode(),
    shift_name: randomShiftName(),
  })
  await page.goto("/attendance/shifts")
  const row = shiftRow(page, shift.shift_code)
  await expect(row).toBeVisible()

  // Plans and roster entries are built by later slices; mock the two domain
  // conflicts so the blocked dialogs are still exercised end to end. The real
  // blocker queries are covered by the backend API tests.
  await page.route(
    /\/api\/v1\/attendance\/shifts\/[0-9a-f-]+$/,
    async (route) => {
      const method = route.request().method()
      if (method === "PATCH") {
        await route.fulfill({
          status: 409,
          contentType: "application/json",
          body: blockedResponse({
            code: "deactivate_blocked",
            message: "无法停用：仍有启用中的排班方案引用该班次",
            type: "schedule_plan",
            label: "2026-09 行政班方案",
            field_errors: { is_active: "存在启用中的排班方案" },
          }),
        })
        return
      }
      if (method === "DELETE") {
        await route.fulfill({
          status: 409,
          contentType: "application/json",
          body: blockedResponse({
            code: "referenced",
            message: "无法删除：仍有排班方案或排班明细引用该班次",
            type: "roster_entry",
            label: "E101 张三 2026-09-01",
          }),
        })
        return
      }
      await route.continue()
    },
  )

  await row.getByRole("switch").click()
  let blocked = page.getByTestId(BLOCKED_DIALOG)
  await expect(blocked).toBeVisible()
  await expect(blocked).toContainText("无法停用班次")
  await expect(blocked).toContainText("2026-09 行政班方案")
  await expect(blocked.getByRole("button", { name: "无法停用" })).toBeVisible()
  await blocked.getByRole("button", { name: "知道了" }).click()
  await expect(row.getByRole("switch")).toHaveAttribute("aria-checked", "true")

  await row.getByRole("button", { name: "删除" }).click()
  const confirm = page.getByRole("dialog")
  await confirm.getByRole("button", { name: "删除" }).click()
  blocked = page.getByTestId(BLOCKED_DIALOG)
  await expect(blocked).toBeVisible()
  await expect(blocked).toContainText("无法删除班次")
  await expect(blocked).toContainText("E101 张三 2026-09-01")
  await expect(blocked.getByRole("button", { name: "无法删除" })).toBeVisible()
  await blocked.getByRole("button", { name: "知道了" }).click()
  await expect(row).toBeVisible()
})

test("search and status filters narrow the shift list", async ({ page }) => {
  const company = await setupCompany(page)
  const activeCode = randomShiftCode()
  const otherCode = randomShiftCode()
  const inactiveCode = randomShiftCode()
  await createShift({
    company_id: company.id,
    shift_code: activeCode,
    shift_name: randomShiftName(),
  })
  await createShift({
    company_id: company.id,
    shift_code: otherCode,
    shift_name: randomShiftName(),
  })
  await createShift({
    company_id: company.id,
    shift_code: inactiveCode,
    shift_name: "停用班次",
    is_active: false,
  })
  await page.reload()

  await expect(shiftRow(page, activeCode)).toBeVisible()
  await expect(shiftRow(page, otherCode)).toBeVisible()
  await expect(shiftRow(page, inactiveCode)).toBeVisible()

  await page.getByLabel("搜索班次").fill("停用班次")
  await expect(shiftRow(page, inactiveCode)).toBeVisible()
  await expect(shiftRow(page, activeCode)).toHaveCount(0)

  await page.getByLabel("搜索班次").fill("")
  await page.getByRole("combobox", { name: "状态筛选" }).click()
  await page.getByRole("option", { name: "已停用" }).click()
  await expect(shiftRow(page, inactiveCode)).toBeVisible()
  await expect(shiftRow(page, activeCode)).toHaveCount(0)

  await page.getByRole("combobox", { name: "状态筛选" }).click()
  await page.getByRole("option", { name: "启用", exact: true }).click()
  await expect(shiftRow(page, activeCode)).toBeVisible()
  await expect(shiftRow(page, inactiveCode)).toHaveCount(0)
})
