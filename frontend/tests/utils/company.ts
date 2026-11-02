import type { Page } from "@playwright/test"

export const COMPANY_STORAGE_KEY = "basic-management.company_id"

/** Preselect a company for the basic-management company switcher. */
export async function setActiveCompany(
  page: Page,
  companyId: string,
): Promise<void> {
  await page.addInitScript(
    ([key, value]: [string, string]) => {
      window.localStorage.setItem(key, value)
    },
    [COMPANY_STORAGE_KEY, companyId],
  )
}
