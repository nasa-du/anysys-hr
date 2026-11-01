import { expect, test } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"
import { DATE_TIME_PATTERN, toShanghaiDateTime } from "./utils/date"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test("Admin page is accessible and shows correct title", async ({ page }) => {
  await page.goto("/admin")
  await expect(page).toHaveTitle("管理后台 - AnySys")
  await expect(page.getByRole("heading", { name: "用户管理" })).toBeVisible()
  await expect(page.getByText("管理用户账号与权限")).toBeVisible()
})

test("Add User button is visible", async ({ page }) => {
  await page.goto("/admin")
  await expect(page.getByRole("button", { name: "新建用户" })).toBeVisible()
})

test.describe("Admin user management", () => {
  test("Create a new user successfully", async ({ page }) => {
    await page.goto("/admin")

    const email = randomEmail()
    const password = randomPassword()
    const fullName = "Test User Admin"

    await page.getByRole("button", { name: "新建用户" }).click()

    await page.getByLabel("邮箱").fill(email)
    await page.getByLabel("姓名").fill(fullName)
    await page.getByLabel("设置密码").fill(password)
    await page.getByLabel("确认密码").fill(password)

    await page.getByRole("button", { name: "保存" }).click()

    await expect(page.getByText("用户创建成功")).toBeVisible()

    await expect(page.getByRole("dialog")).not.toBeVisible()

    const userRow = page.getByRole("row").filter({ hasText: email })
    await expect(userRow).toBeVisible()
  })

  test("Create a superuser", async ({ page }) => {
    await page.goto("/admin")

    const email = randomEmail()
    const password = randomPassword()

    await page.getByRole("button", { name: "新建用户" }).click()

    await page.getByLabel("邮箱").fill(email)
    await page.getByLabel("设置密码").fill(password)
    await page.getByLabel("确认密码").fill(password)
    await page.getByLabel("是否为超级管理员？").check()
    await page.getByLabel("是否启用？").check()

    await page.getByRole("button", { name: "保存" }).click()

    await expect(page.getByText("用户创建成功")).toBeVisible()

    await expect(page.getByRole("dialog")).not.toBeVisible()

    const userRow = page.getByRole("row").filter({ hasText: email })
    await expect(userRow.getByText("超级管理员")).toBeVisible()
  })

  test("Edit a user successfully", async ({ page }) => {
    await page.goto("/admin")

    const email = randomEmail()
    const password = randomPassword()
    const originalName = "Original Name"
    const updatedName = "Updated Name"

    await page.getByRole("button", { name: "新建用户" }).click()
    await page.getByLabel("邮箱").fill(email)
    await page.getByLabel("姓名").fill(originalName)
    await page.getByLabel("设置密码").fill(password)
    await page.getByLabel("确认密码").fill(password)
    await page.getByRole("button", { name: "保存" }).click()

    await expect(page.getByText("用户创建成功")).toBeVisible()
    await expect(page.getByRole("dialog")).not.toBeVisible()

    const userRow = page.getByRole("row").filter({ hasText: email })
    await userRow.getByRole("button").click()

    await page.getByRole("menuitem", { name: "编辑用户" }).click()

    await page.getByLabel("姓名").fill(updatedName)
    await page.getByRole("button", { name: "保存" }).click()

    await expect(page.getByText("用户更新成功")).toBeVisible()
    await expect(page.getByText(updatedName)).toBeVisible()
  })

  test("Delete a user successfully", async ({ page }) => {
    await page.goto("/admin")

    const email = randomEmail()
    const password = randomPassword()

    await page.getByRole("button", { name: "新建用户" }).click()
    await page.getByLabel("邮箱").fill(email)
    await page.getByLabel("设置密码").fill(password)
    await page.getByLabel("确认密码").fill(password)
    await page.getByRole("button", { name: "保存" }).click()

    await expect(page.getByText("用户创建成功")).toBeVisible()

    await expect(page.getByRole("dialog")).not.toBeVisible()

    const userRow = page.getByRole("row").filter({ hasText: email })
    await userRow.getByRole("button").click()

    await page.getByRole("menuitem", { name: "删除用户" }).click()

    await page.getByRole("button", { name: "删除" }).click()

    await expect(page.getByText("用户删除成功")).toBeVisible()

    await expect(
      page.getByRole("row").filter({ hasText: email }),
    ).not.toBeVisible()
  })

  test("Cancel user creation", async ({ page }) => {
    await page.goto("/admin")

    await page.getByRole("button", { name: "新建用户" }).click()
    await page.getByLabel("邮箱").fill("test@example.com")

    await page.getByRole("button", { name: "取消" }).click()

    await expect(page.getByRole("dialog")).not.toBeVisible()
  })

  test("Email is required and must be valid", async ({ page }) => {
    await page.goto("/admin")

    await page.getByRole("button", { name: "新建用户" }).click()

    await page.getByLabel("邮箱").fill("invalid-email")
    await page.getByLabel("邮箱").blur()

    await expect(page.getByText("请输入有效的邮箱地址")).toBeVisible()
  })

  test("Password must be at least 8 characters", async ({ page }) => {
    await page.goto("/admin")

    await page.getByRole("button", { name: "新建用户" }).click()

    await page.getByLabel("邮箱").fill(randomEmail())
    await page.getByLabel("设置密码").fill("short")
    await page.getByLabel("确认密码").fill("short")
    await page.getByRole("button", { name: "保存" }).click()

    await expect(page.getByText("密码至少需要 8 个字符")).toBeVisible()
  })

  test("Passwords must match", async ({ page }) => {
    await page.goto("/admin")

    await page.getByRole("button", { name: "新建用户" }).click()

    await page.getByLabel("邮箱").fill(randomEmail())
    await page.getByLabel("设置密码").fill(randomPassword())
    await page.getByLabel("确认密码").fill("different12345")
    await page.getByLabel("确认密码").blur()

    await expect(page.getByText("两次输入的密码不一致")).toBeVisible()
  })

  test.describe("Created time", () => {
    test.use({ timezoneId: "America/New_York" })

    test("Shows the creation time in Asia/Shanghai as YYYY-MM-DD HH:mm", async ({
      page,
    }) => {
      await page.goto("/admin")

      const email = randomEmail()
      const password = randomPassword()

      await page.getByRole("button", { name: "新建用户" }).click()
      await page.getByLabel("邮箱").fill(email)
      await page.getByLabel("设置密码").fill(password)
      await page.getByLabel("确认密码").fill(password)

      const createResponse = page.waitForResponse(
        (response) =>
          response.url().includes("/api/v1/users/") &&
          response.request().method() === "POST",
      )
      await page.getByRole("button", { name: "保存" }).click()
      const createdUser = await (await createResponse).json()

      await expect(page.getByText("用户创建成功")).toBeVisible()
      await expect(
        page.getByRole("columnheader", { name: "创建时间" }),
      ).toBeVisible()

      const createdTime = page
        .getByRole("row")
        .filter({ hasText: email })
        .getByTestId("created-at")

      await expect(createdTime).toHaveText(DATE_TIME_PATTERN)
      await expect(createdTime).toHaveText(
        toShanghaiDateTime(createdUser.created_at),
      )
    })
  })
})

test.describe("Admin page access control", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Non-superuser cannot access admin page", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()

    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto("/admin")

    await expect(
      page.getByRole("heading", { name: "用户管理" }),
    ).not.toBeVisible()
    await expect(page).not.toHaveURL(/\/admin/)
  })

  test("Superuser can access admin page", async ({ page }) => {
    await logInUser(page, firstSuperuser, firstSuperuserPassword)

    await page.goto("/admin")

    await expect(page.getByRole("heading", { name: "用户管理" })).toBeVisible()
  })
})
