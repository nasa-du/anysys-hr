import { expect, type Page, test } from "@playwright/test"
import { BASIC_MANAGEMENT_MODULES } from "./utils/modules"

async function expectSidebar(page: Page) {
  await expect(
    page.getByRole("link", { name: "仪表盘", exact: true }),
  ).toBeVisible()
  await expect(page.getByText("基础管理")).toBeVisible()
  for (const { link } of BASIC_MANAGEMENT_MODULES) {
    await expect(
      page.getByRole("link", { name: link, exact: true }),
    ).toBeVisible()
  }
  await expect(page.getByText("系统")).toBeVisible()
  await expect(
    page.getByRole("link", { name: "管理后台", exact: true }),
  ).toBeVisible()
}

test("the sidebar shows five Basic Management modules and keeps Admin", async ({
  page,
}) => {
  await page.goto("/")

  await expectSidebar(page)
  await expect(page.getByRole("combobox", { name: "切换公司" })).toBeVisible()
})

test("the Items demo entry is gone from the navigation", async ({ page }) => {
  await page.goto("/companies")

  await expect(page.getByRole("link", { name: /条目|Items/i })).toHaveCount(0)
  await expect(page.locator('a[href="/items"]')).toHaveCount(0)
  await expect(
    page.getByRole("heading", { name: "公司", exact: true }),
  ).toBeVisible()
})

test("every Basic Management module is reachable from the sidebar", async ({
  page,
}) => {
  await page.goto("/companies")

  for (const { link, path, heading } of BASIC_MANAGEMENT_MODULES) {
    await page.getByRole("link", { name: link, exact: true }).click()
    await expect(page).toHaveURL(new RegExp(`${path}$`))
    await expect(
      page.getByRole("heading", { name: heading, exact: true }),
    ).toBeVisible()
    await expect(page.getByRole("combobox", { name: "切换公司" })).toBeVisible()
  }
})
