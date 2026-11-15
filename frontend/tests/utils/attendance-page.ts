import { expect, type Page } from "@playwright/test"

import type { AttendanceBootstrap } from "./api"
import { setActiveCompany } from "./company"

/** Pin the active company and attendance month before navigating. */
export async function openAttendanceMonth(
  page: Page,
  companyId: string,
  month: string,
): Promise<void> {
  await setActiveCompany(page, companyId)
  await page.addInitScript((value: string) => {
    window.localStorage.setItem("attendance.month", value)
  }, month)
}

export async function expectHeading(page: Page, name: string) {
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible()
}

/**
 * Switch the company through the shared switcher and keep the choice for the
 * rest of the test; the company init script registered earlier still points at
 * the previous company, so re-register this one.
 */
export async function switchCompany(
  page: Page,
  company: AttendanceBootstrap["company"],
): Promise<void> {
  const switcher = page.getByRole("combobox", { name: "切换公司" })
  await switcher.click()
  await page
    .getByRole("option", { name: company.company_name, exact: true })
    .click()
  await expect(switcher).toContainText(company.company_name)
  await setActiveCompany(page, company.id)
}
