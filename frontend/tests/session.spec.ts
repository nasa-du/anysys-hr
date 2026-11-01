import { expect, test } from "@playwright/test"

const staleUserResponse = {
  status: 404,
  contentType: "application/json",
  body: JSON.stringify({ detail: "用户不存在" }),
}

async function setStaleToken(page: import("@playwright/test").Page) {
  await page.goto("/login")
  await page.evaluate(() => localStorage.setItem("access_token", "stale-token"))
}

test.use({ storageState: { cookies: [], origins: [] } })

test("clears a stale session and returns to login from items", async ({
  page,
}) => {
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill(staleUserResponse),
  )
  await page.route("**/api/v1/items**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [], count: 0 }),
    }),
  )

  await setStaleToken(page)
  await page.goto("/items")

  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByTestId("email-input")).toBeVisible()
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("access_token")))
    .toBeNull()
})

test("clears a stale session and returns to login from admin", async ({
  page,
}) => {
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill(staleUserResponse),
  )

  await setStaleToken(page)
  await page.goto("/admin")

  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByTestId("email-input")).toBeVisible()
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("access_token")))
    .toBeNull()
})
