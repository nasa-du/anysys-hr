import { expect, type Page, test } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"
import { randomPassword } from "./utils/random.ts"

test.use({ storageState: { cookies: [], origins: [] } })

const fillForm = async (page: Page, email: string, password: string) => {
  await page.getByTestId("email-input").fill(email)
  await page.getByTestId("password-input").fill(password)
}

const verifyInput = async (page: Page, testId: string) => {
  const input = page.getByTestId(testId)
  await expect(input).toBeVisible()
  await expect(input).toHaveText("")
  await expect(input).toBeEditable()
}

test("Inputs are visible, empty and editable", async ({ page }) => {
  await page.goto("/login")

  await verifyInput(page, "email-input")
  await verifyInput(page, "password-input")
})

test("Log In button is visible", async ({ page }) => {
  await page.goto("/login")

  await expect(page.getByRole("button", { name: "登录" })).toBeVisible()
})

test("Forgot Password link is visible", async ({ page }) => {
  await page.goto("/login")

  await expect(page.getByRole("link", { name: "忘记密码？" })).toBeVisible()
})

test("Page title is localized", async ({ page }) => {
  await page.goto("/login")

  await expect(page).toHaveTitle("登录 - AnySys")
})

test("Shows AnySys branding in the auth layout", async ({ page }) => {
  await page.goto("/login")

  await expect(page.getByRole("img", { name: "AnySys" })).toBeVisible()
  await expect(
    page.getByText(`© ${new Date().getFullYear()} AnySys。保留所有权利。`),
  ).toBeVisible()
  await expect(page.locator("body")).not.toContainText("FastAPI")
  await expect(page.locator('a[href*="fastapi"]')).toHaveCount(0)
})

test("Serves the AnySys favicon suite", async ({ page, request }) => {
  await page.goto("/login")

  const iconHrefs = await page
    .locator('link[rel="icon"]')
    .evaluateAll((links) => links.map((link) => link.getAttribute("href")))
  expect(iconHrefs).toEqual([
    "/favicon-light.ico",
    "/favicon-light-32x32.png",
    "/icon-light-192.png",
    "/icon-light-512.png",
  ])
  await expect(page.locator('link[rel="apple-touch-icon"]')).toHaveAttribute(
    "href",
    "/apple-touch-icon-light.png",
  )

  for (const href of [...iconHrefs, "/apple-touch-icon-light.png"]) {
    const response = await request.get(href as string)
    expect(response.ok(), `${href} should be served`).toBe(true)

    const contentType = response.headers()["content-type"] ?? ""
    if (href?.endsWith(".ico")) {
      expect(contentType).toMatch(/^image\/(x-icon|vnd\.microsoft\.icon)/)
    } else {
      expect(contentType).toContain("image/png")
    }
  }
})

test("Unknown route uses a localized page", async ({ page }) => {
  await page.goto("/this-route-does-not-exist")

  await expect(page).toHaveTitle("页面不存在 - AnySys")
  await expect(page.getByTestId("not-found")).toContainText("404")
  await expect(page.getByText("你访问的页面不存在。")).toBeVisible()
  await expect(page.getByRole("button", { name: "返回首页" })).toBeVisible()
})

test("Log in with valid email and password ", async ({ page }) => {
  await page.goto("/login")

  await fillForm(page, firstSuperuser, firstSuperuserPassword)
  await page.getByRole("button", { name: "登录" }).click()

  await page.waitForURL("/")

  await expect(page).toHaveTitle("仪表盘 - AnySys")
  await expect(page.getByText("欢迎回来，很高兴再次见到你。")).toBeVisible()
})

test("App shell is localized", async ({ page }) => {
  await page.goto("/login")

  await fillForm(page, firstSuperuser, firstSuperuserPassword)
  await page.getByRole("button", { name: "登录" }).click()
  await page.waitForURL("/")

  await expect(page.getByText("你好，")).toBeVisible()
  await expect(page.getByRole("link", { name: "仪表盘" })).toBeVisible()
  await expect(page.getByRole("link", { name: "条目" })).toBeVisible()
  await expect(page.getByRole("link", { name: "管理后台" })).toBeVisible()

  await page.getByTestId("user-menu").click()
  await expect(page.getByRole("menuitem", { name: "设置" })).toBeVisible()
  await expect(page.getByRole("menuitem", { name: "退出登录" })).toBeVisible()

  await expect(page.locator("body")).not.toContainText("FastAPI")
  await expect(page.locator('a[href*="fastapi"]')).toHaveCount(0)
})

test("Log in with invalid email", async ({ page }) => {
  await page.goto("/login")

  await fillForm(page, "invalidemail", firstSuperuserPassword)
  await page.getByRole("button", { name: "登录" }).click()

  await expect(page.getByText("请输入有效的邮箱地址")).toBeVisible()
})

test("Log in with invalid password", async ({ page }) => {
  const password = randomPassword()

  await page.goto("/login")
  await fillForm(page, firstSuperuser, password)
  await page.getByRole("button", { name: "登录" }).click()

  await expect(page.getByText("邮箱或密码不正确")).toBeVisible()
  await expect(page.getByRole("region", { name: /通知/ })).toBeAttached()
  await expect(page.getByRole("button", { name: "关闭通知" })).toBeVisible()
})

test("Successful log out", async ({ page }) => {
  await page.goto("/login")

  await fillForm(page, firstSuperuser, firstSuperuserPassword)
  await page.getByRole("button", { name: "登录" }).click()

  await page.waitForURL("/")

  await expect(page.getByText("欢迎回来，很高兴再次见到你。")).toBeVisible()

  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "退出登录" }).click()
  await page.waitForURL("/login")
})

test("Logged-out user cannot access protected routes", async ({ page }) => {
  await page.goto("/login")

  await fillForm(page, firstSuperuser, firstSuperuserPassword)
  await page.getByRole("button", { name: "登录" }).click()

  await page.waitForURL("/")

  await expect(page.getByText("欢迎回来，很高兴再次见到你。")).toBeVisible()

  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "退出登录" }).click()
  await page.waitForURL("/login")

  await page.goto("/settings")
  await page.waitForURL("/login")
})

test("Redirects to /login when token is wrong", async ({ page }) => {
  await page.goto("/settings")
  await page.evaluate(() => {
    localStorage.setItem("access_token", "invalid_token")
  })
  await page.goto("/settings")
  await page.waitForURL("/login")
  await expect(page).toHaveURL("/login")
})
