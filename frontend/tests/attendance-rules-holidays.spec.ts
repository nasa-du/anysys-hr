import { expect, type Page, test } from "@playwright/test"

import { createCompany, createHoliday, readHolidays } from "./utils/api"
import { setActiveCompany } from "./utils/company"
import { randomCompanyCode, randomCompanyName } from "./utils/random"

test.setTimeout(60_000)

const PLAN_ID = "019a0000-0000-7000-8000-00000000a001"

const RULE_DEFAULTS = {
  punch_window_min: 120,
  late_cap_min: 240,
  early_cap_min: 240,
  ot_max_min: 600,
  late_grace_min: 5,
  early_grace_min: 5,
  ot_threshold_min: 30,
  absent_if_no_punch: true,
  break_punch_required: true,
  break_punch_tolerance_min: 60,
  absent_deduct_per_day: "0.00",
  late_deduct_per_occurrence: "0.00",
  early_deduct_per_occurrence: "0.00",
  missing_punch_deduct_per_occurrence: "0.00",
}

const NULL_OVERRIDES = Object.fromEntries(
  Object.keys(RULE_DEFAULTS).map((key) => [key, null]),
)

async function setupCompany(page: Page, navigate = true) {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  await setActiveCompany(page, company.id)
  if (navigate) {
    await page.goto("/attendance/rules")
  }
  return company
}

function mockedOverridesResponse(overrides: Record<string, unknown>) {
  const clean = Object.fromEntries(
    Object.entries(overrides).filter(
      ([, value]) => value !== null && value !== undefined,
    ),
  )
  return {
    overrides: { ...NULL_OVERRIDES, ...overrides },
    effective: { ...RULE_DEFAULTS, ...clean },
    company_default: RULE_DEFAULTS,
  }
}

async function mockPlanOverrides(page: Page, planMonth = "2026-09") {
  const plan = {
    id: PLAN_ID,
    company_id: "019a0000-0000-7000-8000-000000000001",
    month: planMonth,
    plan_name: "行政班方案",
    scope_type: "all",
    status: "enabled",
    copied_from_plan_id: null,
    note: null,
    scopes: [],
    days: [],
    created_at: "2026-09-01T00:00:00Z",
    updated_at: "2026-09-01T00:00:00Z",
  }

  await page.route(
    /\/api\/v1\/attendance\/schedule-plans\/\?.*/,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: [plan], count: 1 }),
      })
    },
  )

  let initialOverrides = { ...NULL_OVERRIDES, late_grace_min: 12 }
  let lastPutBody: Record<string, unknown> | null = null

  await page.route(
    /\/api\/v1\/attendance\/schedule-plans\/[^/]+\/rule-overrides$/,
    async (route) => {
      if (route.request().method() === "PUT") {
        lastPutBody = route.request().postDataJSON() as Record<string, unknown>
        const body = lastPutBody as {
          overrides: Record<string, unknown>
        }
        initialOverrides = { ...initialOverrides, ...body.overrides }
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockedOverridesResponse(initialOverrides)),
        })
        return
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockedOverridesResponse(initialOverrides)),
      })
    },
  )

  return {
    getLastPutBody: () => lastPutBody,
  }
}

function currentShanghaiMonth(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
  }).format(new Date())
}

function monthState(companyId: string, month: string, status: string) {
  return {
    id: "019a0000-0000-7000-8000-0000000000aa",
    exists: true,
    company_id: companyId,
    month,
    status,
    is_stale: false,
    calculated_at: null,
    confirmed_at: null,
    locked_at: null,
    unlock_reason: null,
    latest_calc_run: null,
    active_batches: { punch: null, trip: null, ot: null, leave: null },
    counts: {
      employee_count: 0,
      day_result_count: 0,
      abnormal_day_count: 0,
      month_summary_count: 0,
    },
  }
}

test("plan overrides are read-only in a confirmed month", async ({ page }) => {
  const company = await setupCompany(page, false)
  const month = currentShanghaiMonth()
  await mockPlanOverrides(page, month)
  await page.route(/\/api\/v1\/attendance\/months\/\?.*/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: [monthState(company.id, month, "confirmed")],
        count: 1,
      }),
    })
  })
  await page.goto("/attendance/rules")

  await expect(page.getByText(/该考勤月份已确认/)).toBeVisible()
  await expect(page.getByTestId("impact-hint")).toContainText("结果保持不变")
  await expect(page.getByTestId("impact-hint")).toContainText(month)
  await expect(page.getByRole("button", { name: "保存覆盖" })).toBeDisabled()
})

test("company rules show system defaults, save, persist, and explain stale impact", async ({
  page,
}) => {
  await setupCompany(page)

  await expect(
    page.getByRole("heading", { name: "规则与节假日", exact: true }),
  ).toBeVisible()
  await expect(page.getByTestId("impact-hint")).toContainText("结果过期")
  await expect(page.getByText("系统默认", { exact: true })).toBeVisible()
  await expect(page.getByText("当前月份没有可配置的排班方案")).toBeVisible()

  const lateGrace = page.getByLabel("迟到宽限（分钟）")
  await expect(lateGrace).toHaveValue("5")
  await lateGrace.fill("10")
  await page.getByRole("button", { name: "保存规则" }).click()

  await expect(page.getByText(/规则已保存/).first()).toBeVisible()
  await expect(page.getByText("公司已配置")).toBeVisible()

  await page.reload()
  await expect(page.getByLabel("迟到宽限（分钟）")).toHaveValue("10")
  await expect(page.getByText("公司已配置")).toBeVisible()
})

test("plan overrides keep null inheritance and replace the supplied fields", async ({
  page,
}) => {
  await setupCompany(page, false)
  const mock = await mockPlanOverrides(page)
  await page.goto("/attendance/rules")

  await expect(page.getByLabel("选择需要覆盖规则的排班方案")).toContainText(
    "行政班方案",
  )

  const lateGraceMode = page.getByLabel("迟到宽限（分钟） 继承方式")
  await expect(lateGraceMode).toContainText("覆盖")
  await expect(page.getByText("12 分钟", { exact: true })).toBeVisible()

  const earlyGraceMode = page.getByLabel("早退宽限（分钟） 继承方式")
  await expect(earlyGraceMode).toContainText("继承")
  await earlyGraceMode.click()
  await page.getByRole("option", { name: "覆盖" }).click()
  await page.getByLabel("早退宽限（分钟） 覆盖值").fill("9")

  await page.getByRole("button", { name: "保存覆盖" }).click()
  await expect(page.getByText(/方案覆盖已保存/).first()).toBeVisible()

  await expect.poll(() => mock.getLastPutBody()).not.toBeNull()

  const body = mock.getLastPutBody() as {
    overrides: Record<string, unknown>
  }
  expect(body.overrides.late_grace_min).toBe(12)
  expect(body.overrides.early_grace_min).toBe(9)
  expect(body.overrides.punch_window_min).toBeNull()
  expect(body.overrides.absent_if_no_punch).toBeNull()
  expect(body.overrides.absent_deduct_per_day).toBeNull()

  await expect(page.getByText("9 分钟", { exact: true })).toBeVisible()
})

test("holiday calendar supports create, edit, and delete", async ({ page }) => {
  await setupCompany(page)

  await page.getByLabel("考勤月份").fill("2026-09")
  await expect(page.getByText("2026 年 9 月", { exact: true })).toBeVisible()
  await expect(page.getByTestId("holiday-empty")).toBeVisible()

  await page.getByRole("button", { name: "添加节假日", exact: true }).click()
  const form = page.getByRole("dialog")
  await expect(form.getByRole("heading", { name: "添加节假日" })).toBeVisible()
  await form.getByLabel("节假日日期").fill("2026-09-25")
  await form.getByLabel("节假日名称").fill("中秋节")
  await form.getByLabel("节假日备注").fill("三倍工资")
  await form.getByRole("button", { name: "保存" }).click()

  await expect(page.getByText("节假日已添加").first()).toBeVisible()
  await expect(
    page.getByRole("button", { name: "2026-09-25 中秋节" }),
  ).toBeVisible()

  await page.getByRole("button", { name: "编辑 中秋节" }).click()
  const edit = page.getByRole("dialog")
  await expect(edit.getByLabel("节假日日期")).toBeDisabled()
  await edit.getByLabel("节假日名称").fill("中秋节（改）")
  await edit.getByRole("button", { name: "保存" }).click()

  await expect(page.getByText("节假日已更新").first()).toBeVisible()

  await page.getByRole("button", { name: "删除 中秋节（改）" }).click()
  const confirm = page.getByRole("dialog")
  await expect(
    confirm.getByRole("heading", { name: "删除节假日" }),
  ).toBeVisible()
  await confirm.getByRole("button", { name: "删除" }).click()

  await expect(page.getByText("节假日删除成功").first()).toBeVisible()
  await expect(page.getByTestId("holiday-empty")).toBeVisible()
})

test("copy previous year shows conflicts and requires explicit overwrite", async ({
  page,
}) => {
  const company = await setupCompany(page)
  await createHoliday({
    company_id: company.id,
    date: "2025-09-25",
    name: "中秋节",
  })
  await createHoliday({
    company_id: company.id,
    date: "2025-10-01",
    name: "国庆节",
  })
  await createHoliday({
    company_id: company.id,
    date: "2026-10-01",
    name: "已有国庆安排",
  })

  await page.getByLabel("考勤月份").fill("2026-09")
  await expect(page.getByText("2026 年 9 月", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "复制上一年" }).click()

  const dialog = page.getByRole("dialog")
  await expect(
    dialog.getByRole("heading", { name: "复制上一年节假日" }),
  ).toBeVisible()
  const preview = page.getByTestId("copy-preview")
  await expect(preview).toContainText(/将新增\s*1\s*条/)
  await expect(preview).toContainText(/1\s*条冲突日期/)
  await expect(preview).toContainText("2026-09-25 · 中秋节")
  await expect(preview).toContainText("已有国庆安排")

  await dialog.getByRole("button", { name: "复制", exact: true }).click()
  await expect(page.getByTestId("copy-conflict")).toBeVisible()
  await expect(page.getByTestId("copy-conflict")).toContainText(
    "目标年份存在冲突的节假日",
  )

  await dialog.getByLabel("覆盖目标年份中的冲突日期").check()
  await dialog.getByRole("button", { name: "覆盖并复制" }).click()

  await expect(
    page.getByText(/复制完成：新增 1，更新 1，跳过 0/).first(),
  ).toBeVisible()

  const holidays = await readHolidays(company.id, 2026)
  expect(holidays.map((holiday) => holiday.date)).toEqual([
    "2026-09-25",
    "2026-10-01",
  ])
  expect(holidays.find((holiday) => holiday.date === "2026-10-01")?.name).toBe(
    "国庆节",
  )
})
