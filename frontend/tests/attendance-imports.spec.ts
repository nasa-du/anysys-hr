import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { expect, type Page, test } from "@playwright/test"

import {
  type ApiDepartment,
  createCompany,
  createDepartment,
  createEmployee,
  createPosition,
  resignEmployee,
} from "./utils/api"
import { setActiveCompany } from "./utils/company"
import {
  randomCompanyCode,
  randomCompanyName,
  randomDepartmentCode,
  randomEmployeeNo,
  randomPositionCode,
} from "./utils/random"

test.setTimeout(120_000)

const MONTH = "2026-09"
const FIXTURE_DIR = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../docs/specs/attendance-fixtures",
)

// Employee seed from docs/specs/attendance-fixtures/README.md section 1.
const FIXTURE_EMPLOYEES: Array<{
  employeeNo: string
  name: string
  department: string
  hireDate: string
  resignDate?: string
}> = [
  {
    employeeNo: "E101",
    name: "冯芷茵",
    department: "生产部",
    hireDate: "2020-04-11",
  },
  {
    employeeNo: "E102",
    name: "刘衍英",
    department: "财务部",
    hireDate: "2018-09-03",
  },
  {
    employeeNo: "E103",
    name: "周玉琼",
    department: "生产部",
    hireDate: "2019-03-18",
  },
  {
    employeeNo: "E104",
    name: "胡国邵",
    department: "生产部",
    hireDate: "2017-06-01",
  },
  {
    employeeNo: "E105",
    name: "李金辉",
    department: "生产部",
    hireDate: "2021-11-08",
  },
  {
    employeeNo: "E106",
    name: "黄佳誉",
    department: "技术部",
    hireDate: "2020-02-17",
  },
  {
    employeeNo: "E107",
    name: "梁林高",
    department: "行政部",
    hireDate: "2016-05-23",
  },
  {
    employeeNo: "E108",
    name: "黄国锋",
    department: "生产部",
    hireDate: "2019-08-30",
  },
  {
    employeeNo: "E109",
    name: "申佳林",
    department: "行政部",
    hireDate: "2015-10-12",
  },
  {
    employeeNo: "E110",
    name: "张伟",
    department: "生产部",
    hireDate: "2019-01-01",
  },
  {
    employeeNo: "E111",
    name: "张伟",
    department: "财务部",
    hireDate: "2020-01-01",
  },
  {
    employeeNo: "E112",
    name: "王强",
    department: "生产部",
    hireDate: "2018-01-01",
    resignDate: "2026-08-31",
  },
  {
    employeeNo: "E113",
    name: "李娜",
    department: "生产部",
    hireDate: "2026-09-15",
  },
]

/** Actual employee numbers are prefixed so repeated local runs never collide. */
type EmployeeNumberMap = Record<string, string>

function employeeNumberMap(): EmployeeNumberMap {
  const prefix = randomEmployeeNo()
  return Object.fromEntries(
    FIXTURE_EMPLOYEES.map((employee) => [
      employee.employeeNo,
      `${prefix}-${employee.employeeNo}`,
    ]),
  )
}

async function setup(page: Page): Promise<EmployeeNumberMap> {
  const company = await createCompany({
    company_code: randomCompanyCode(),
    company_name: randomCompanyName(),
  })
  const departments: Record<string, ApiDepartment> = {}
  for (const name of ["生产部", "财务部", "技术部", "行政部"]) {
    departments[name] = await createDepartment({
      company_id: company.id,
      dept_code: randomDepartmentCode(),
      dept_name: name,
    })
  }
  const position = await createPosition({
    company_id: company.id,
    position_code: randomPositionCode(),
    position_name: "员工级",
  })
  const numbers = employeeNumberMap()
  for (const employee of FIXTURE_EMPLOYEES) {
    const created = await createEmployee({
      employee_no: numbers[employee.employeeNo],
      name: employee.name,
      dept_id: departments[employee.department].id,
      position_id: position.id,
      hire_date: employee.hireDate,
    })
    if (employee.resignDate) {
      await resignEmployee(created.id, employee.resignDate)
    }
  }
  await setActiveCompany(page, company.id)
  await page.goto("/attendance/imports")
  await page.getByLabel("考勤月份").fill(MONTH)
  await expect(page.getByLabel("考勤月份")).toHaveValue(MONTH)
  await expect(page.getByTestId("import-type-punch")).toBeVisible()
  return numbers
}

function withPrefixedEmployeeNumbers(
  text: string,
  numbers: EmployeeNumberMap,
): string {
  return text.replace(/\bE\d{3}\b/g, (match) => numbers[match] ?? match)
}

async function uploadFixture(
  page: Page,
  fileName: string,
  numbers: EmployeeNumberMap,
): Promise<void> {
  const content = fs.readFileSync(path.join(FIXTURE_DIR, fileName), "utf8")
  await page.getByLabel("选择导入文件").setInputFiles({
    name: fileName,
    mimeType: "text/csv",
    buffer: Buffer.from(withPrefixedEmployeeNumbers(content, numbers), "utf8"),
  })
  await expect(page.getByTestId("selected-file")).toContainText(fileName)
  await page.getByTestId("parse-preview").click()
  await expect(page.getByTestId("import-preview-step")).toBeVisible()
}

async function expectStat(
  page: Page,
  name: string,
  value: number,
): Promise<void> {
  await expect(page.getByTestId(`import-stat-${name}`)).toContainText(
    String(value),
  )
}

test("uploads the punch fixture and shows stats, errors, and samples", async ({
  page,
}) => {
  const numbers = await setup(page)
  await uploadFixture(page, "punch-2026-09.csv", numbers)

  await expectStat(page, "source-rows", 37)
  await expectStat(page, "valid-records", 27)
  await expectStat(page, "skipped-records", 10)
  await expectStat(page, "error-records", 4)
  await expectStat(page, "warning-records", 5)
  await expect(page.getByTestId("import-mapping-step")).toContainText(
    "第 1 行为表头",
  )
  await expect(page.getByLabel("工号映射列")).toContainText("工号")
  await expect(page.getByText("显示 9 / 共 9 条")).toBeVisible()

  const unknownRow = page.getByRole("row").filter({ hasText: "员工不存在" })
  await expect(unknownRow).toHaveCount(1)
  await expect(unknownRow).toContainText("11")
  await expect(
    page.getByRole("row").filter({ hasText: "重复打卡" }),
  ).toHaveCount(0)

  await expect(page.getByText("当前没有生效批次")).toBeVisible()
  await expect(page.getByText("预览校验通过")).toBeVisible()
  await expect(page.getByText("冯芷茵").first()).toBeVisible()
})

test("uploads the trip fixture and lists ignored columns", async ({ page }) => {
  const numbers = await setup(page)
  await page.getByTestId("import-type-trip").click()
  await uploadFixture(page, "oa-trip-2026-09.csv", numbers)

  await expectStat(page, "source-rows", 15)
  await expectStat(page, "valid-records", 8)
  await expectStat(page, "skipped-records", 9)
  await expectStat(page, "error-records", 5)
  await expectStat(page, "warning-records", 0)
  await expect(page.getByTestId("import-mapping-step")).toContainText(
    "已忽略列",
  )
  await expect(page.getByTestId("import-mapping-step")).toContainText("序号")
  await expect(page.getByLabel("出差人映射列")).toContainText("出差人")
})

test("uploads the overtime fixture and shows per-day minutes", async ({
  page,
}) => {
  const numbers = await setup(page)
  await page.getByTestId("import-type-ot").click()
  await uploadFixture(page, "oa-overtime-2026-09.csv", numbers)

  await expectStat(page, "valid-records", 8)
  await expectStat(page, "skipped-records", 7)
  await expectStat(page, "error-records", 3)
  await expectStat(page, "warning-records", 1)
  await expect(page.getByText("填报时长与计算时长相差较大 × 1")).toBeVisible()
  await expect(page.getByText("2026-09-14 480 分钟").first()).toBeVisible()
})

test("uploads the leave fixture and shows duplicate-name errors", async ({
  page,
}) => {
  const numbers = await setup(page)
  await page.getByTestId("import-type-leave").click()
  await uploadFixture(page, "oa-leave-2026-09.csv", numbers)

  await expectStat(page, "valid-records", 8)
  await expectStat(page, "skipped-records", 11)
  await expectStat(page, "error-records", 8)
  await expectStat(page, "warning-records", 1)
  await expect(
    page.getByRole("row").filter({ hasText: "员工重名" }),
  ).toHaveCount(1)
  await expect(
    page.getByRole("row").filter({ hasText: "未识别请假类型" }),
  ).toHaveCount(2)
})

test("pastes punch rows and applies a column mapping override", async ({
  page,
}) => {
  const numbers = await setup(page)
  await page.getByRole("button", { name: "粘贴内容" }).click()
  await page
    .getByLabel("粘贴导入内容")
    .fill(
      [
        "工号\t考勤日期\t打卡时间\t打卡结果\t打卡设备\t打卡地址\t备用设备",
        `${numbers.E101}\t2026-09-01\t2026-09-01 08:18\t正常\t考勤机\t一号门\t备用机`,
      ].join("\n"),
    )
  await page.getByTestId("parse-preview").click()
  await expect(page.getByTestId("import-preview-step")).toBeVisible()

  await expectStat(page, "valid-records", 1)
  await expect(page.getByText("粘贴内容").first()).toBeVisible()
  await expect(page.getByLabel("打卡设备映射列")).toContainText("打卡设备")
  await expect(page.getByTestId("ignored-columns")).toContainText("备用设备")

  await page.getByLabel("打卡设备映射列").click()
  await page.getByRole("option", { name: "备用设备" }).click()
  await page.getByTestId("apply-mapping").click()

  await expect(page.getByLabel("打卡设备映射列")).toContainText("备用设备")
  await expect(page.getByTestId("ignored-columns")).toContainText("打卡设备")
  await expect(page.getByTestId("import-error")).toHaveCount(0)
  await expectStat(page, "valid-records", 1)

  // Two canonical fields on one source column is a fatal mapping error.
  await page.getByLabel("打卡设备映射列").click()
  await page.getByRole("option", { name: "打卡地址" }).click()
  await page.getByTestId("apply-mapping").click()
  await expect(page.getByTestId("import-error")).toContainText(
    "同一列不能映射到多个字段",
  )
})

test("shows the expired preview state when the 24-hour window has passed", async ({
  page,
}) => {
  await page.route("**/api/v1/attendance/imports/preview", async (route) => {
    const response = await route.fetch()
    const body = (await response.json()) as {
      batch?: { expires_at?: string }
    }
    if (body.batch) body.batch.expires_at = "2020-01-01T00:00:00Z"
    await route.fulfill({ response, json: body })
  })
  const numbers = await setup(page)
  await uploadFixture(page, "punch-2026-09.csv", numbers)

  await expect(page.getByTestId("preview-expired")).toBeVisible()
  await expect(page.getByTestId("preview-expired")).toContainText("预览已过期")
})
