import { expect, type Page, test } from "@playwright/test"
import {
  randomCompanyCode,
  randomCompanyName,
  randomDepartmentCode,
  randomDepartmentName,
} from "./utils/random"

async function createCompany(page: Page, code: string, name: string) {
  await page.goto("/companies")
  await page.getByRole("button", { name: "新增公司" }).first().click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("公司编码").fill(code)
  await dialog.getByLabel("公司名称").fill(name)
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("公司创建成功").first()).toBeVisible()
  await expect(page.getByRole("dialog")).not.toBeVisible()
}

async function switchCompany(page: Page, name: string) {
  const switcher = page.getByRole("combobox", { name: "切换公司" })
  await switcher.click()
  await page.getByRole("option", { name }).click()
  await expect(switcher).toContainText(name)
}

/** Creates an isolated company and makes it the active company. */
async function prepareCompany(page: Page) {
  const code = randomCompanyCode()
  const name = randomCompanyName()
  await createCompany(page, code, name)
  await switchCompany(page, name)
  await page.goto("/departments")
  return { code, name }
}

function treeNode(page: Page, name: string) {
  return page
    .getByTestId("department-tree")
    .getByRole("button", { name: new RegExp(name) })
}

async function selectDepartment(page: Page, name: string) {
  await treeNode(page, name).click()
  await expect(page.getByTestId("department-detail")).toContainText(name)
}

async function submitDepartment(
  page: Page,
  {
    code,
    name,
    parentName,
  }: { code: string; name: string; parentName?: string },
) {
  if (parentName) {
    await selectDepartment(page, parentName)
    await page.getByRole("button", { name: "新增下级" }).click()
  } else {
    await page.getByRole("button", { name: "新增根部门" }).first().click()
  }

  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("部门编码").fill(code)
  await dialog.getByLabel("部门名称").fill(name)
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("部门创建成功").first()).toBeVisible()
  await expect(page.getByRole("dialog")).not.toBeVisible()
}

test("sidebar shows the Departments entry and the page follows the company switcher", async ({
  page,
}) => {
  const company = await prepareCompany(page)

  await expect(
    page.getByRole("heading", { name: "部门", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: "部门", exact: true }),
  ).toBeVisible()
  await expect(page.getByText(`当前公司：${company.name}`)).toBeVisible()
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "还没有部门",
  )
})

test("create, edit, and delete a department tree", async ({ page }) => {
  await prepareCompany(page)
  const rootCode = randomDepartmentCode()
  const rootName = randomDepartmentName()
  const childCode = randomDepartmentCode()
  const childName = randomDepartmentName()

  await submitDepartment(page, { code: rootCode, name: rootName })
  await expect(treeNode(page, rootName)).toBeVisible()

  await submitDepartment(page, {
    code: childCode,
    name: childName,
    parentName: rootName,
  })
  await expect(treeNode(page, childName)).toBeVisible()

  await selectDepartment(page, childName)
  await page.getByRole("button", { name: "编辑" }).click()
  let dialog = page.getByRole("dialog")
  await expect(dialog.getByLabel("部门编码")).toBeDisabled()
  const updatedName = randomDepartmentName()
  await dialog.getByLabel("部门名称").fill(updatedName)
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("部门更新成功").first()).toBeVisible()
  await expect(treeNode(page, updatedName)).toBeVisible()

  await selectDepartment(page, updatedName)
  await page.getByRole("button", { name: "删除" }).click()
  dialog = page.getByRole("dialog")
  await expect(dialog).toContainText("删除部门")
  await dialog.getByRole("button", { name: "删除" }).click()
  await expect(page.getByText("部门删除成功").first()).toBeVisible()
  await expect(treeNode(page, updatedName)).toHaveCount(0)
  await expect(treeNode(page, rootName)).toBeVisible()
})

test("move a department to another parent", async ({ page }) => {
  await prepareCompany(page)
  const firstParent = randomDepartmentName()
  const secondParent = randomDepartmentName()
  const childName = randomDepartmentName()

  await submitDepartment(page, {
    code: randomDepartmentCode(),
    name: firstParent,
  })
  await submitDepartment(page, {
    code: randomDepartmentCode(),
    name: secondParent,
  })
  await submitDepartment(page, {
    code: randomDepartmentCode(),
    name: childName,
    parentName: firstParent,
  })

  await selectDepartment(page, childName)
  await page.getByRole("button", { name: "编辑" }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByRole("combobox", { name: "上级部门" }).click()
  await page.getByRole("option", { name: new RegExp(secondParent) }).click()
  await dialog.getByRole("button", { name: "保存" }).click()
  await expect(page.getByText("部门更新成功").first()).toBeVisible()

  await selectDepartment(page, childName)
  const detail = page.getByTestId("department-detail")
  await expect(detail.locator("dd").first()).toHaveText(secondParent)

  await selectDepartment(page, firstParent)
  await expect(page.getByTestId("department-detail")).toContainText(
    "暂无下级部门。",
  )
})

test("the parent selector disables the department and its descendants", async ({
  page,
}) => {
  await prepareCompany(page)
  const rootName = randomDepartmentName()
  const childName = randomDepartmentName()
  const grandchildName = randomDepartmentName()
  const otherRootName = randomDepartmentName()

  await submitDepartment(page, { code: randomDepartmentCode(), name: rootName })
  await submitDepartment(page, {
    code: randomDepartmentCode(),
    name: childName,
    parentName: rootName,
  })
  await submitDepartment(page, {
    code: randomDepartmentCode(),
    name: grandchildName,
    parentName: childName,
  })
  await submitDepartment(page, {
    code: randomDepartmentCode(),
    name: otherRootName,
  })

  await selectDepartment(page, rootName)
  await page.getByRole("button", { name: "编辑" }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByRole("combobox", { name: "上级部门" }).click()

  await expect(
    page.getByRole("option", { name: new RegExp(rootName) }),
  ).toBeDisabled()
  await expect(
    page.getByRole("option", { name: new RegExp(childName) }),
  ).toBeDisabled()
  await expect(
    page.getByRole("option", { name: new RegExp(grandchildName) }),
  ).toBeDisabled()
  await expect(
    page.getByRole("option", { name: new RegExp(otherRootName) }),
  ).toBeEnabled()

  await page.keyboard.press("Escape")
  await dialog.getByRole("button", { name: "取消" }).click()
  await expect(page.getByRole("dialog")).not.toBeVisible()
})

test("deleting a department with children is blocked", async ({ page }) => {
  await prepareCompany(page)
  const parentName = randomDepartmentName()
  const childCode = randomDepartmentCode()
  const childName = randomDepartmentName()

  await submitDepartment(page, {
    code: randomDepartmentCode(),
    name: parentName,
  })
  await submitDepartment(page, {
    code: childCode,
    name: childName,
    parentName,
  })

  await selectDepartment(page, parentName)
  await page.getByRole("button", { name: "删除" }).click()
  const confirmDialog = page.getByRole("dialog")
  await confirmDialog.getByRole("button", { name: "删除" }).click()

  const blockedDialog = page.getByTestId("blocked-dialog")
  await expect(blockedDialog).toBeVisible()
  await expect(blockedDialog).toContainText("无法删除部门")
  await expect(blockedDialog).toContainText(childCode)
  await expect(blockedDialog).toContainText(childName)
  await blockedDialog.getByRole("button", { name: "知道了" }).click()

  await expect(treeNode(page, parentName)).toBeVisible()
})

test("deactivating a department with active children is blocked", async ({
  page,
}) => {
  await prepareCompany(page)
  const parentName = randomDepartmentName()
  const childName = randomDepartmentName()

  await submitDepartment(page, {
    code: randomDepartmentCode(),
    name: parentName,
  })
  await submitDepartment(page, {
    code: randomDepartmentCode(),
    name: childName,
    parentName,
  })

  await selectDepartment(page, parentName)
  await page.getByRole("button", { name: "编辑" }).click()
  const dialog = page.getByRole("dialog")
  const statusSwitch = dialog.getByRole("switch", { name: "状态" })
  await expect(statusSwitch).toHaveAttribute("aria-checked", "true")
  await statusSwitch.click()
  await expect(statusSwitch).toHaveAttribute("aria-checked", "false")
  await dialog.getByRole("button", { name: "保存" }).click()

  const blockedDialog = page.getByTestId("blocked-dialog")
  await expect(blockedDialog).toBeVisible()
  await expect(blockedDialog).toContainText("无法停用部门")
  await expect(blockedDialog).toContainText(childName)
  await blockedDialog.getByRole("button", { name: "知道了" }).click()

  await expect(statusSwitch).toHaveAttribute("aria-checked", "true")
  await dialog.getByRole("button", { name: "取消" }).click()
  await expect(page.getByRole("dialog")).not.toBeVisible()
})

test("departments are scoped to the selected company", async ({ page }) => {
  const firstCompanyName = randomCompanyName()
  const secondCompanyName = randomCompanyName()
  await createCompany(page, randomCompanyCode(), firstCompanyName)
  await createCompany(page, randomCompanyCode(), secondCompanyName)

  await switchCompany(page, firstCompanyName)
  await page.goto("/departments")
  const departmentName = randomDepartmentName()
  await submitDepartment(page, {
    code: randomDepartmentCode(),
    name: departmentName,
  })
  await expect(treeNode(page, departmentName)).toBeVisible()

  await switchCompany(page, secondCompanyName)
  await expect(page.getByText(`当前公司：${secondCompanyName}`)).toBeVisible()
  await expect(page.getByTestId("empty-state").first()).toContainText(
    "还没有部门",
  )
  await expect(treeNode(page, departmentName)).toHaveCount(0)
  // The detail pane must not keep showing the previous company's department.
  await expect(page.getByTestId("department-detail")).toHaveCount(0)

  await switchCompany(page, firstCompanyName)
  await expect(treeNode(page, departmentName)).toBeVisible()
  await expect(page.getByTestId("department-detail")).toContainText(
    departmentName,
  )
})
