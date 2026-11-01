import { expect, test } from "@playwright/test"
import { DATE_TIME_PATTERN, toShanghaiDateTime } from "./utils/date"
import { createUser } from "./utils/privateApi"
import {
  randomEmail,
  randomItemDescription,
  randomItemTitle,
  randomPassword,
} from "./utils/random"
import { logInUser } from "./utils/user"

test("Items page is accessible and shows correct title", async ({ page }) => {
  await page.goto("/items")
  await expect(page).toHaveTitle("条目 - AnySys")
  await expect(page.getByRole("heading", { name: "条目" })).toBeVisible()
  await expect(page.getByText("创建和管理你的条目")).toBeVisible()
})

test("Add Item button is visible", async ({ page }) => {
  await page.goto("/items")
  await expect(page.getByRole("button", { name: "新建条目" })).toBeVisible()
})

test.describe("Items management", () => {
  test.use({ storageState: { cookies: [], origins: [] } })
  let email: string
  const password = randomPassword()

  test.beforeAll(async () => {
    email = randomEmail()
    await createUser({ email, password })
  })

  test.beforeEach(async ({ page }) => {
    await logInUser(page, email, password)
    await page.goto("/items")
  })

  test("Create a new item successfully", async ({ page }) => {
    const title = randomItemTitle()
    const description = randomItemDescription()

    await page.getByRole("button", { name: "新建条目" }).click()
    await page.getByLabel("标题").fill(title)
    await page.getByLabel("描述").fill(description)
    await page.getByRole("button", { name: "保存" }).click()

    await expect(page.getByText("条目创建成功")).toBeVisible()
    await expect(page.getByText(title)).toBeVisible()
  })

  test("Create item with only required fields", async ({ page }) => {
    const title = randomItemTitle()

    await page.getByRole("button", { name: "新建条目" }).click()
    await page.getByLabel("标题").fill(title)
    await page.getByRole("button", { name: "保存" }).click()

    await expect(page.getByText("条目创建成功")).toBeVisible()
    await expect(page.getByText(title)).toBeVisible()
  })

  test("Cancel item creation", async ({ page }) => {
    await page.getByRole("button", { name: "新建条目" }).click()
    await page.getByLabel("标题").fill("Test Item")
    await page.getByRole("button", { name: "取消" }).click()

    await expect(page.getByRole("dialog")).not.toBeVisible()
  })

  test("Title is required", async ({ page }) => {
    await page.getByRole("button", { name: "新建条目" }).click()
    await page.getByLabel("标题").fill("")
    await page.getByLabel("标题").blur()

    await expect(page.getByText("请输入标题")).toBeVisible()
  })

  test.describe("Created time", () => {
    test.use({ timezoneId: "America/New_York" })

    test("Shows the creation time in Asia/Shanghai as YYYY-MM-DD HH:mm", async ({
      page,
    }) => {
      const title = randomItemTitle()

      await page.getByRole("button", { name: "新建条目" }).click()
      await page.getByLabel("标题").fill(title)

      const createResponse = page.waitForResponse(
        (response) =>
          response.url().includes("/api/v1/items/") &&
          response.request().method() === "POST",
      )
      await page.getByRole("button", { name: "保存" }).click()
      const createdItem = await (await createResponse).json()

      await expect(page.getByText("条目创建成功")).toBeVisible()
      await expect(
        page.getByRole("columnheader", { name: "创建时间" }),
      ).toBeVisible()

      const createdTime = page
        .getByRole("row")
        .filter({ hasText: title })
        .getByTestId("created-at")

      await expect(createdTime).toHaveText(DATE_TIME_PATTERN)
      await expect(createdTime).toHaveText(
        toShanghaiDateTime(createdItem.created_at),
      )
    })
  })

  test.describe("Edit and Delete", () => {
    let itemTitle: string

    test.beforeEach(async ({ page }) => {
      itemTitle = randomItemTitle()

      await page.getByRole("button", { name: "新建条目" }).click()
      await page.getByLabel("标题").fill(itemTitle)
      await page.getByRole("button", { name: "保存" }).click()
      await expect(page.getByText("条目创建成功")).toBeVisible()
      await expect(page.getByRole("dialog")).not.toBeVisible()
    })

    test("Edit an item successfully", async ({ page }) => {
      const itemRow = page.getByRole("row").filter({ hasText: itemTitle })
      await itemRow.getByRole("button").last().click()
      await page.getByRole("menuitem", { name: "编辑条目" }).click()

      const updatedTitle = randomItemTitle()
      await page.getByLabel("标题").fill(updatedTitle)
      await page.getByRole("button", { name: "保存" }).click()

      await expect(page.getByText("条目更新成功")).toBeVisible()
      await expect(page.getByText(updatedTitle)).toBeVisible()
    })

    test("Delete an item successfully", async ({ page }) => {
      const itemRow = page.getByRole("row").filter({ hasText: itemTitle })
      await itemRow.getByRole("button").last().click()
      await page.getByRole("menuitem", { name: "删除条目" }).click()

      await page.getByRole("button", { name: "删除" }).click()

      await expect(page.getByText("条目删除成功")).toBeVisible()
      await expect(page.getByText(itemTitle)).not.toBeVisible()
    })
  })
})

test.describe("Items empty state", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Shows empty state message when no items exist", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto("/items")

    await expect(page.getByText("你还没有任何条目")).toBeVisible()
    await expect(page.getByText("新建一个条目开始使用")).toBeVisible()
  })
})
