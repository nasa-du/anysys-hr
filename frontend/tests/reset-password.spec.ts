import { expect, test } from "@playwright/test"
import { waitForEmail } from "./utils/mailpit"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser, signUpNewUser } from "./utils/user"

test.use({ storageState: { cookies: [], origins: [] } })

const resetPath = "/reset-password?token="

test("Password Recovery title is visible", async ({ page }) => {
  await page.goto("/recover-password")

  await expect(page.getByRole("heading", { name: "忘记密码" })).toBeVisible()
})

test("Recovery page title is localized", async ({ page }) => {
  await page.goto("/recover-password")

  await expect(page).toHaveTitle("忘记密码 - AnySys")
})

test("Reset page title is localized", async ({ page }) => {
  await page.goto("/reset-password?token=test")

  await expect(page).toHaveTitle("重置密码 - AnySys")
})

test("Input is visible, empty and editable", async ({ page }) => {
  await page.goto("/recover-password")

  await expect(page.getByTestId("email-input")).toBeVisible()
  await expect(page.getByTestId("email-input")).toHaveText("")
  await expect(page.getByTestId("email-input")).toBeEditable()
})

test("Continue button is visible", async ({ page }) => {
  await page.goto("/recover-password")

  await expect(page.getByRole("button", { name: "继续" })).toBeVisible()
})

test("User can reset password successfully using the link", async ({
  page,
  request,
}) => {
  const fullName = "Test User"
  const email = randomEmail()
  const password = randomPassword()
  const newPassword = randomPassword()

  // Sign up a new user
  await signUpNewUser(page, fullName, email, password)

  await page.goto("/recover-password")
  await page.getByTestId("email-input").fill(email)

  await page.getByRole("button", { name: "继续" }).click()

  const message = await waitForEmail({
    request,
    query: `to:${email}`,
  })

  expect(message.subject).toBe("AnySys - 重置密码")
  expect(message.html).toContain('lang="zh-CN"')
  expect(message.html).toContain("重置密码")
  expect(message.html).toContain("你好")
  expect(message.html).toContain(resetPath)
  const resetUrl = message.html.match(/\/reset-password\?token=[^"]+/)?.[0]
  expect(resetUrl).toBeDefined()

  // Set the new password and confirm it
  await page.goto(resetUrl!)

  await page.getByTestId("new-password-input").fill(newPassword)
  await page.getByTestId("confirm-password-input").fill(newPassword)
  await page.getByRole("button", { name: "重置密码" }).click()
  await expect(page.getByText("密码更新成功")).toBeVisible()

  // Check if the user is able to login with the new password
  await logInUser(page, email, newPassword)
})

test("Expired or invalid reset link", async ({ page }) => {
  const password = randomPassword()
  const invalidUrl = "/reset-password?token=invalidtoken"

  await page.goto(invalidUrl)

  await page.getByTestId("new-password-input").fill(password)
  await page.getByTestId("confirm-password-input").fill(password)
  await page.getByRole("button", { name: "重置密码" }).click()

  await expect(page.getByText("重置链接无效")).toBeVisible()
})

test("Weak new password validation", async ({ page, request }) => {
  const fullName = "Test User"
  const email = randomEmail()
  const password = randomPassword()
  const weakPassword = "123"

  // Sign up a new user
  await signUpNewUser(page, fullName, email, password)

  await page.goto("/recover-password")
  await page.getByTestId("email-input").fill(email)
  await page.getByRole("button", { name: "继续" }).click()

  const message = await waitForEmail({
    request,
    query: `to:${email}`,
  })

  expect(message.html).toContain(resetPath)
  const resetUrl = message.html.match(/\/reset-password\?token=[^"]+/)?.[0]
  expect(resetUrl).toBeDefined()

  // Set a weak new password
  await page.goto(resetUrl!)
  await page.getByTestId("new-password-input").fill(weakPassword)
  await page.getByTestId("confirm-password-input").fill(weakPassword)
  await page.getByRole("button", { name: "重置密码" }).click()

  await expect(page.getByText("密码至少需要 8 个字符")).toBeVisible()
})
