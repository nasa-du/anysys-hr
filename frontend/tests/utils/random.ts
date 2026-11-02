export const randomEmail = () =>
  `test_${Math.random().toString(36).substring(7)}@example.com`

export const randomTeamName = () =>
  `Team ${Math.random().toString(36).substring(7)}`

export const randomPassword = () => `${Math.random().toString(36).substring(2)}`

export const randomCompanyCode = () =>
  `T${Math.random().toString(36).substring(2, 8).toUpperCase()}`

export const randomCompanyName = () =>
  `测试公司 ${Math.random().toString(36).substring(2, 8).toUpperCase()}`

export const randomDepartmentCode = () =>
  `D${Math.random().toString(36).substring(2, 8).toUpperCase()}`

export const randomDepartmentName = () =>
  `测试部门 ${Math.random().toString(36).substring(2, 8).toUpperCase()}`

export const randomPositionCode = () =>
  `P${Math.random().toString(36).substring(2, 8).toUpperCase()}`

export const randomPositionName = () =>
  `测试岗位 ${Math.random().toString(36).substring(2, 8).toUpperCase()}`

export const randomCostCenterCode = () =>
  `K${Math.random().toString(36).substring(2, 8).toUpperCase()}`

export const randomCostCenterName = () =>
  `测试成本中心 ${Math.random().toString(36).substring(2, 8).toUpperCase()}`

export const randomEmployeeNo = () =>
  `E${Math.random().toString(36).substring(2, 10).toUpperCase()}`

export const randomEmployeeName = () =>
  `测试员工 ${Math.random().toString(36).substring(2, 8).toUpperCase()}`

export const slugify = (text: string) =>
  text
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^\w-]+/g, "")
