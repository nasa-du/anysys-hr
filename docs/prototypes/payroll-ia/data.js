/* Payroll IA prototype — seed data, a tiny formula evaluator, and derived results.
 * NOT production code. The evaluator is a simplified JS stand-in for the in-house
 * Decimal engine described in ADR-0007; golden cases remain the contract. */
(() => {
  "use strict";

  /* ---------------------------------------------------------------- helpers */

  const clone = (value) => JSON.parse(JSON.stringify(value));
  const round2 = (n) => {
    const sign = n < 0 ? -1 : 1;
    return (sign * Math.round(Math.abs(n) * 100 + 1e-9)) / 100;
  };
  const roundHalfUp = (n, digits) => {
    const f = 10 ** digits;
    const sign = n < 0 ? -1 : 1;
    return (sign * Math.round(Math.abs(n) * f + 1e-9)) / f;
  };
  const sum = (list, key) => list.reduce((acc, item) => acc + (Number(item[key]) || 0), 0);

  const CATEGORY = {
    earning: "计薪项",
    addon: "加减项",
    deduction: "代扣项",
    total: "合计项",
    reference: "参考项",
  };
  const CATEGORY_ORDER = ["earning", "addon", "deduction", "reference", "total"];
  const CALC_MODE = { plan: "构成", formula: "公式", import: "导入", fixed: "固定值" };

  /* ---------------------------------------------------------------- seed */

  const COMPANIES = [
    { id: "c1", code: "RX", name: "荣新矿业", active: true, note: "煤矿生产与洗选（薪资样例数据）" },
    { id: "c2", code: "RXWL", name: "荣新物流", active: true, note: "物流运输与仓储（原型中暂无薪资数据）" },
  ];

  const DEPARTMENTS = [
    { id: "d1", companyId: "c1", name: "总部", parentId: null, order: 10 },
    { id: "d2", companyId: "c1", name: "生产部", parentId: "d1", order: 20 },
    { id: "d3", companyId: "c1", name: "财务部", parentId: "d1", order: 30 },
    { id: "d4", companyId: "c1", name: "技术部", parentId: "d1", order: 40 },
    { id: "d5", companyId: "c1", name: "行政部", parentId: "d1", order: 50 },
    { id: "d6", companyId: "c1", name: "一车间", parentId: "d2", order: 10 },
    { id: "d7", companyId: "c1", name: "二车间", parentId: "d2", order: 20 },
  ];

  const POSITIONS = [
    {
      id: "p-line", companyId: "c1", name: "生产线班长", defaultDeptId: "d2", active: true,
      payroll: { compositionCode: "OP", schemeCode: "OP", workdayCode: "PROD" },
    },
    {
      id: "p-op", companyId: "c1", name: "操作工", defaultDeptId: "d2", active: true,
      payroll: { compositionCode: "OP", schemeCode: "OP", workdayCode: "PROD" },
    },
    {
      id: "p-acc", companyId: "c1", name: "会计", defaultDeptId: "d3", active: true,
      payroll: { compositionCode: "ADMIN", schemeCode: "ADMIN", workdayCode: "ADM" },
    },
    {
      id: "p-tech", companyId: "c1", name: "技术员", defaultDeptId: "d4", active: true,
      payroll: { compositionCode: "STD", schemeCode: "STD", workdayCode: "STD" },
    },
    {
      id: "p-admin", companyId: "c1", name: "行政专员", defaultDeptId: "d5", active: true,
      payroll: { compositionCode: "ADMIN", schemeCode: "ADMIN", workdayCode: "ADM" },
    },
    {
      id: "p-driver", companyId: "c1", name: "司机", defaultDeptId: "d5", active: true,
      payroll: null,
    },
  ];

  const EMPLOYEES = [
    { id: "E101", no: "E101", name: "冯芷茵", deptId: "d6", positionId: "p-op", costCenterId: "cc-mine", hireDate: "2020-04-11", resignDate: null, status: "active" },
    { id: "E102", no: "E102", name: "刘衍英", deptId: "d3", positionId: "p-acc", costCenterId: "cc-admin", hireDate: "2018-09-03", resignDate: null, status: "active" },
    { id: "E103", no: "E103", name: "周玉琼", deptId: "d6", positionId: "p-op", costCenterId: "cc-mine", hireDate: "2019-03-18", resignDate: null, status: "active" },
    { id: "E104", no: "E104", name: "胡国邵", deptId: "d6", positionId: "p-op", costCenterId: "cc-mine", hireDate: "2017-06-01", resignDate: null, status: "active" },
    { id: "E105", no: "E105", name: "李金辉", deptId: "d7", positionId: "p-op", costCenterId: "cc-smelt", hireDate: "2021-11-08", resignDate: null, status: "active" },
    { id: "E106", no: "E106", name: "黄佳誉", deptId: "d4", positionId: "p-tech", costCenterId: "cc-tech", hireDate: "2020-02-17", resignDate: null, status: "active" },
    { id: "E107", no: "E107", name: "梁林高", deptId: "d5", positionId: "p-admin", costCenterId: "cc-admin", hireDate: "2016-05-23", resignDate: null, status: "active" },
    { id: "E108", no: "E108", name: "黄国锋", deptId: "d7", positionId: "p-line", costCenterId: "cc-smelt", hireDate: "2019-08-30", resignDate: null, status: "active" },
    { id: "E109", no: "E109", name: "申佳林", deptId: "d5", positionId: "p-admin", costCenterId: "cc-admin", hireDate: "2015-10-12", resignDate: null, status: "active" },
    { id: "E110", no: "E110", name: "张伟", deptId: "d6", positionId: "p-op", costCenterId: null, hireDate: "2019-01-01", resignDate: null, status: "active" },
    { id: "E111", no: "E111", name: "张伟", deptId: "d3", positionId: "p-acc", costCenterId: "cc-admin", hireDate: "2020-01-01", resignDate: null, status: "active" },
    { id: "E112", no: "E112", name: "王强", deptId: "d6", positionId: "p-op", costCenterId: "cc-mine", hireDate: "2018-01-01", resignDate: "2026-08-31", status: "resigned" },
    { id: "E113", no: "E113", name: "李娜", deptId: "d7", positionId: "p-op", costCenterId: "cc-smelt", hireDate: "2026-09-15", resignDate: null, status: "probation" },
    { id: "E114", no: "E114", name: "赵志强", deptId: "d5", positionId: "p-driver", costCenterId: "cc-admin", hireDate: "2026-12-01", resignDate: null, status: "active" },
    { id: "E115", no: "E115", name: "陈晓", deptId: "d4", positionId: "p-tech", costCenterId: "cc-tech", hireDate: "2021-07-19", resignDate: null, status: "active" },
  ];

  const COST_CENTERS = [
    { id: "cc-prod", code: "CC-PROD", name: "生产成本中心", parentId: null, budget: 100000, warnPct: 90, active: true },
    { id: "cc-mine", code: "CC-MINE", name: "采选成本中心", parentId: "cc-prod", budget: 20000, warnPct: 90, active: true },
    { id: "cc-smelt", code: "CC-SMELT", name: "冶炼成本中心", parentId: "cc-prod", budget: 22000, warnPct: 90, active: true },
    { id: "cc-tech", code: "CC-TECH", name: "技术成本中心", parentId: null, budget: 25000, warnPct: 90, active: true },
    { id: "cc-admin", code: "CC-ADMIN", name: "行政成本中心", parentId: null, budget: 24000, warnPct: 90, active: true },
    { id: "cc-empty", code: "CC-EMPTY", name: "待启用成本中心", parentId: null, budget: 0, warnPct: 90, active: true },
  ];

  const COMPOSITIONS = [
    {
      code: "STD",
      name: "标准薪资构成",
      versions: [
        {
          version: 3, createdAt: "2026-09-01 09:10", createdBy: "管理员", note: "2026 年度技术岗调薪",
          amounts: { base_salary: 10000, hightemp_subsidy: 300, performance_salary: 2000, overtime_pay: 1000, confidentiality_allowance: 500, social_subsidy: 200, noncompete_subsidy: 0, total_package: 14000 },
        },
        {
          version: 2, createdAt: "2025-09-01 09:00", createdBy: "管理员", note: "年度普调",
          amounts: { base_salary: 9500, hightemp_subsidy: 300, performance_salary: 1800, overtime_pay: 1000, confidentiality_allowance: 500, social_subsidy: 200, noncompete_subsidy: 0, total_package: 13300 },
        },
        {
          version: 1, createdAt: "2024-06-01 10:20", createdBy: "管理员", note: "初始版本",
          amounts: { base_salary: 9000, hightemp_subsidy: 300, performance_salary: 1500, overtime_pay: 800, confidentiality_allowance: 500, social_subsidy: 200, noncompete_subsidy: 0, total_package: 12300 },
        },
      ],
    },
    {
      code: "OP",
      name: "生产岗位薪资构成",
      versions: [
        {
          version: 2, createdAt: "2026-07-01 14:05", createdBy: "管理员", note: "高温补贴与绩效调整",
          amounts: { base_salary: 5200, hightemp_subsidy: 300, performance_salary: 800, overtime_pay: 600, confidentiality_allowance: 0, social_subsidy: 200, noncompete_subsidy: 0, total_package: 7100 },
        },
        {
          version: 1, createdAt: "2025-01-01 09:00", createdBy: "管理员", note: "初始版本",
          amounts: { base_salary: 4800, hightemp_subsidy: 300, performance_salary: 700, overtime_pay: 500, confidentiality_allowance: 0, social_subsidy: 200, noncompete_subsidy: 0, total_package: 6500 },
        },
      ],
    },
    {
      code: "ADMIN",
      name: "职能岗位薪资构成",
      versions: [
        {
          version: 1, createdAt: "2026-01-01 09:00", createdBy: "管理员", note: "初始版本",
          amounts: { base_salary: 6800, hightemp_subsidy: 0, performance_salary: 1000, overtime_pay: 0, confidentiality_allowance: 500, social_subsidy: 200, noncompete_subsidy: 0, total_package: 8500 },
        },
      ],
    },
  ];

  const COMPOSITION_ITEMS = [
    { key: "base_salary", label: "基本工资" },
    { key: "hightemp_subsidy", label: "高温补贴" },
    { key: "performance_salary", label: "绩效工资" },
    { key: "overtime_pay", label: "加班费标准" },
    { key: "confidentiality_allowance", label: "保密津贴" },
    { key: "social_subsidy", label: "社保补贴" },
    { key: "noncompete_subsidy", label: "竞业补贴" },
  ];

  const SCHEMES = [
    {
      code: "STD", name: "标准计算方案", overrides: {},
      updatedAt: "2026-09-01 09:10", revisions: [],
    },
    {
      code: "OP", name: "生产计件方案",
      overrides: {
        performance: "ROUND(performance_salary - total_package / (weekday_full + weekend_full) * ((weekday_full + weekend_full) - weekday_attended - weekend_attended) + (base_salary - base_pay) + (overtime_pay - overtime_pay_actual) + production_bonus * 0.2, 2)",
        ot_subsidy: "ROUND(base_salary / {avg_pay_days} / {work_hours} * {ot_mult_weekend} * (ot_weekday_hours + ot_weekend_hours + ot_holiday_hours), 2)",
      },
      updatedAt: "2026-10-18 16:40",
      revisions: [
        { at: "2026-10-18 16:40", by: "管理员", field: "ot_subsidy", from: "ROUND(base_salary / {avg_pay_days} / {work_hours} * {ot_mult_weekday} * ot_weekday_hours + base_salary / {avg_pay_days} / {work_hours} * {ot_mult_weekend} * ot_weekend_hours + base_salary / {avg_pay_days} / {work_hours} * {ot_mult_holiday} * ot_holiday_hours, 2)", to: "ROUND(base_salary / {avg_pay_days} / {work_hours} * {ot_mult_weekend} * (ot_weekday_hours + ot_weekend_hours + ot_holiday_hours), 2)", note: "生产岗统一按周末倍数计加班" },
      ],
    },
    { code: "ADMIN", name: "职能计算方案", overrides: {}, updatedAt: "2026-01-01 09:00", revisions: [] },
  ];

  const WORKDAY_PARAMS = [
    { code: "STD", name: "标准工时", avg_pay_days: 21.75, work_hours: 8, ot_mult_weekday: 1.5, ot_mult_weekend: 2, ot_mult_holiday: 3, min_wage: 2040, updatedAt: "2026-01-01 09:00" },
    { code: "PROD", name: "生产工时", avg_pay_days: 26, work_hours: 8, ot_mult_weekday: 1.5, ot_mult_weekend: 2, ot_mult_holiday: 3, min_wage: 2040, updatedAt: "2026-07-01 14:05" },
    { code: "ADM", name: "职能工时", avg_pay_days: 21.75, work_hours: 7.5, ot_mult_weekday: 1.5, ot_mult_weekend: 2, ot_mult_holiday: 3, min_wage: 2040, updatedAt: "2026-01-01 09:00" },
  ];

  const GLOBAL_PARAMS = [
    { key: "tax_threshold", label: "个税起征点", value: 5000, type: "number", group: "个税", description: "月度综合所得减除费用；本期个税仍由导入提供。", updatedAt: "2026-01-01 09:00" },
    { key: "tax_rate", label: "预设个税税率", value: 0.03, type: "number", group: "个税", description: "仅作试算参考，V1 不做累进税率自动计算。", updatedAt: "2026-01-01 09:00" },
    { key: "social_rate", label: "社保费率（个人部分）", value: 0.23338, type: "number", group: "社保", description: "按基本工资计；本期社保仍由导入提供。", updatedAt: "2026-04-01 09:00" },
    { key: "confidentiality_tiers", label: "保密津贴档", value: [{ level: "A", amount: 500 }, { level: "B", amount: 300 }, { level: "C", amount: 0 }], type: "json", group: "津贴档", description: "岗位装配或导入时选择档位，公式按金额使用。", updatedAt: "2026-01-01 09:00" },
    { key: "hightemp_tiers", label: "高温津贴档", value: [{ months: "6-9", amount: 300 }, { months: "其他", amount: 0 }], type: "json", group: "津贴档", description: "按月份适用的高温补贴档位。", updatedAt: "2026-01-01 09:00" },
  ];

  /* ---------------------------------------------------------------- fields */

  const FIELD_DEFS = [
    { field_key: "base_pay", label: "基本工资(实)", category: "earning", calc_mode: "formula", source_key: null, default_formula: "ROUND(base_salary / weekday_full * weekday_attended, 2)", fixed_value: null, display_order: 10, visible: true, list_default: true, is_system: true, is_active: true },
    { field_key: "hightemp", label: "高温补贴(实)", category: "earning", calc_mode: "plan", source_key: "hightemp_subsidy", default_formula: null, fixed_value: null, display_order: 20, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "performance", label: "绩效(实)", category: "earning", calc_mode: "formula", source_key: null, default_formula: "ROUND(performance_salary - total_package / (weekday_full + weekend_full) * ((weekday_full + weekend_full) - weekday_attended - weekend_attended) + (base_salary - base_pay) + (overtime_pay - overtime_pay_actual), 2)", fixed_value: null, display_order: 30, visible: true, list_default: true, is_system: true, is_active: true },
    { field_key: "overtime_pay_actual", label: "加班费(实)", category: "earning", calc_mode: "formula", source_key: null, default_formula: "ROUND(overtime_pay / weekend_full * weekend_attended, 2)", fixed_value: null, display_order: 40, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "confidential", label: "保密津贴(实)", category: "earning", calc_mode: "plan", source_key: "confidentiality_allowance", default_formula: null, fixed_value: null, display_order: 50, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "social_sub", label: "社保补贴(实)", category: "earning", calc_mode: "plan", source_key: "social_subsidy", default_formula: null, fixed_value: null, display_order: 60, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "noncompete_sub", label: "竞业补贴(实)", category: "earning", calc_mode: "plan", source_key: "noncompete_subsidy", default_formula: null, fixed_value: null, display_order: 70, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "normal_pay", label: "正常出勤工资", category: "total", calc_mode: "formula", source_key: null, default_formula: "ROUND(base_pay + hightemp + performance + overtime_pay_actual + confidential + social_sub + noncompete_sub, 2)", fixed_value: null, display_order: 80, visible: false, list_default: true, is_system: true, is_active: true },
    { field_key: "paid_leave_pay", label: "带薪假工资", category: "addon", calc_mode: "formula", source_key: null, default_formula: "ROUND(base_salary / {avg_pay_days} * paid_leave_days, 2)", fixed_value: null, display_order: 90, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "ot_subsidy", label: "加班补贴", category: "addon", calc_mode: "formula", source_key: null, default_formula: "ROUND(base_salary / {avg_pay_days} / {work_hours} * {ot_mult_weekday} * ot_weekday_hours + base_salary / {avg_pay_days} / {work_hours} * {ot_mult_weekend} * ot_weekend_hours + base_salary / {avg_pay_days} / {work_hours} * {ot_mult_holiday} * ot_holiday_hours, 2)", fixed_value: null, display_order: 100, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "phone_allowance", label: "话费", category: "addon", calc_mode: "import", source_key: "phone_allowance", default_formula: null, fixed_value: null, display_order: 110, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "car_allowance", label: "车补", category: "addon", calc_mode: "import", source_key: "car_allowance", default_formula: null, fixed_value: null, display_order: 120, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "other_addon", label: "其他", category: "addon", calc_mode: "import", source_key: "other_addon", default_formula: null, fixed_value: null, display_order: 130, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "production_bonus", label: "生产奖", category: "addon", calc_mode: "import", source_key: "production_bonus", default_formula: null, fixed_value: null, display_order: 140, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "commission", label: "提成", category: "addon", calc_mode: "import", source_key: "commission", default_formula: null, fixed_value: null, display_order: 150, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "attendance_deduct", label: "考勤扣款", category: "addon", calc_mode: "import", source_key: "attendance_deduct", default_formula: null, fixed_value: null, display_order: 160, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "admin_deduct", label: "行政扣减", category: "addon", calc_mode: "import", source_key: "admin_deduct", default_formula: null, fixed_value: null, display_order: 170, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "addon_sum", label: "加减项小计", category: "total", calc_mode: "formula", source_key: null, default_formula: "ROUND(SUM(paid_leave_pay, ot_subsidy, phone_allowance, car_allowance, other_addon, production_bonus, commission, attendance_deduct, admin_deduct), 2)", fixed_value: null, display_order: 180, visible: false, list_default: true, is_system: true, is_active: true },
    { field_key: "gross", label: "应发工资", category: "total", calc_mode: "formula", source_key: null, default_formula: "ROUND(normal_pay + addon_sum, 2)", fixed_value: null, display_order: 190, visible: false, list_default: true, is_system: true, is_active: true },
    { field_key: "social_this", label: "本期社保", category: "deduction", calc_mode: "import", source_key: "social_this", default_formula: null, fixed_value: null, display_order: 200, visible: true, list_default: true, is_system: true, is_active: true },
    { field_key: "tax", label: "本期个税", category: "deduction", calc_mode: "import", source_key: "tax", default_formula: null, fixed_value: null, display_order: 210, visible: true, list_default: true, is_system: true, is_active: true },
    { field_key: "paid_advance", label: "已发", category: "deduction", calc_mode: "import", source_key: "paid_advance", default_formula: null, fixed_value: null, display_order: 220, visible: true, list_default: false, is_system: true, is_active: true },
    { field_key: "deduct_sum", label: "扣减项小计", category: "total", calc_mode: "formula", source_key: null, default_formula: "ROUND(SUM(social_this, tax, paid_advance), 2)", fixed_value: null, display_order: 230, visible: false, list_default: false, is_system: true, is_active: true },
    { field_key: "net", label: "实发工资", category: "total", calc_mode: "formula", source_key: null, default_formula: "ROUND(gross + deduct_sum, 2)", fixed_value: null, display_order: 240, visible: false, list_default: true, is_system: true, is_active: true },
    { field_key: "weekday_full", label: "工作日满勤", category: "reference", calc_mode: "import", source_key: "weekday_full", default_formula: null, fixed_value: null, display_order: 250, visible: false, list_default: true, is_system: true, is_active: true },
    { field_key: "weekend_full", label: "周末满勤", category: "reference", calc_mode: "import", source_key: "weekend_full", default_formula: null, fixed_value: null, display_order: 260, visible: false, list_default: false, is_system: true, is_active: true },
    { field_key: "weekday_attended", label: "工作日出勤", category: "reference", calc_mode: "import", source_key: "weekday_attended", default_formula: null, fixed_value: null, display_order: 270, visible: false, list_default: true, is_system: true, is_active: true },
    { field_key: "weekend_attended", label: "周末出勤", category: "reference", calc_mode: "import", source_key: "weekend_attended", default_formula: null, fixed_value: null, display_order: 280, visible: false, list_default: false, is_system: true, is_active: true },
    { field_key: "paid_leave_days", label: "带薪假天数", category: "reference", calc_mode: "import", source_key: "paid_leave_days", default_formula: null, fixed_value: null, display_order: 290, visible: false, list_default: false, is_system: true, is_active: true },
    { field_key: "ot_weekday_hours", label: "工作日加班(小时)", category: "reference", calc_mode: "import", source_key: "ot_weekday_hours", default_formula: null, fixed_value: null, display_order: 300, visible: false, list_default: false, is_system: true, is_active: true },
    { field_key: "ot_weekend_hours", label: "周末加班(小时)", category: "reference", calc_mode: "import", source_key: "ot_weekend_hours", default_formula: null, fixed_value: null, display_order: 310, visible: false, list_default: false, is_system: true, is_active: true },
    { field_key: "ot_holiday_hours", label: "节假日加班(小时)", category: "reference", calc_mode: "import", source_key: "ot_holiday_hours", default_formula: null, fixed_value: null, display_order: 320, visible: false, list_default: false, is_system: true, is_active: true },
  ];

  const ATTENDANCE_FIELDS = ["weekday_full", "weekend_full", "weekday_attended", "weekend_attended", "paid_leave_days", "ot_weekday_hours", "ot_weekend_hours", "ot_holiday_hours", "attendance_deduct"];
  const PAYROLL_IMPORT_FIELDS = ["phone_allowance", "car_allowance", "other_addon", "production_bonus", "commission", "admin_deduct", "social_this", "tax", "paid_advance"];
  const IMPORT_COLUMNS = [
    { header: "工号", key: "employee_no", required: true },
    { header: "姓名", key: "employee_name", required: false },
    { header: "话费", key: "phone_allowance", required: false },
    { header: "车补", key: "car_allowance", required: false },
    { header: "其他", key: "other_addon", required: false },
    { header: "生产奖", key: "production_bonus", required: false },
    { header: "提成", key: "commission", required: false },
    { header: "行政扣减", key: "admin_deduct", required: false },
    { header: "本期社保", key: "social_this", required: false },
    { header: "本期个税", key: "tax", required: false },
    { header: "已发", key: "paid_advance", required: false },
  ];
  const ATTENDANCE_COLUMN_ALIASES = {
    工作日出勤: "weekday_attended",
    工作日满勤: "weekday_full",
    周末出勤: "weekend_attended",
    周末满勤: "weekend_full",
    带薪假天数: "paid_leave_days",
    工作日加班: "ot_weekday_hours",
    周末加班: "ot_weekend_hours",
    节假日加班: "ot_holiday_hours",
    考勤扣款: "attendance_deduct",
  };

  /* ---------------------------------------------------------------- formula engine (prototype only) */

  class FormulaError extends Error {
    constructor(code, message) {
      super(message);
      this.code = code;
    }
  }

  function tokenize(input) {
    const tokens = [];
    let i = 0;
    while (i < input.length) {
      const ch = input[i];
      if (/\s/.test(ch)) { i += 1; continue; }
      if (ch === "{") {
        const end = input.indexOf("}", i + 1);
        if (end < 0) throw new FormulaError("unclosed_param", "参数引用缺少右花括号");
        const name = input.slice(i + 1, end).trim();
        if (!name) throw new FormulaError("empty_param", "参数引用为空");
        tokens.push({ type: "param", value: name });
        i = end + 1;
        continue;
      }
      if (/[0-9]/.test(ch) || (ch === "." && /[0-9]/.test(input[i + 1] || ""))) {
        const match = input.slice(i).match(/^(?:\d+\.?\d*|\.\d+)/);
        tokens.push({ type: "num", value: Number(match[0]) });
        i += match[0].length;
        continue;
      }
      if (/[A-Za-z_]/.test(ch)) {
        const match = input.slice(i).match(/^[A-Za-z_][A-Za-z0-9_]*/);
        tokens.push({ type: "ident", value: match[0] });
        i += match[0].length;
        continue;
      }
      const two = input.slice(i, i + 2);
      if (["<=", ">=", "==", "!=", "<>"].includes(two)) {
        tokens.push({ type: "op", value: two });
        i += 2;
        continue;
      }
      if ("+-*/<>()=,".includes(ch)) {
        tokens.push({ type: "op", value: ch });
        i += 1;
        continue;
      }
      throw new FormulaError("unexpected_char", `无法识别的字符：${ch}`);
    }
    return tokens;
  }

  function parseTokens(tokens) {
    let pos = 0;
    const peek = () => tokens[pos];
    const take = () => tokens[pos++];

    function parseComparison() {
      let node = parseAdditive();
      while (peek() && peek().type === "op" && ["<", ">", "<=", ">=", "==", "!=", "<>", "="].includes(peek().value)) {
        const op = take().value;
        node = { t: "bin", op: op === "=" ? "==" : op === "<>" ? "!=" : op, a: node, b: parseAdditive() };
      }
      return node;
    }
    function parseAdditive() {
      let node = parseMultiplicative();
      while (peek() && peek().type === "op" && ["+", "-"].includes(peek().value)) {
        const op = take().value;
        node = { t: "bin", op, a: node, b: parseMultiplicative() };
      }
      return node;
    }
    function parseMultiplicative() {
      let node = parseUnary();
      while (peek() && peek().type === "op" && ["*", "/"].includes(peek().value)) {
        const op = take().value;
        node = { t: "bin", op, a: node, b: parseUnary() };
      }
      return node;
    }
    function parseUnary() {
      if (peek() && peek().type === "op" && peek().value === "-") {
        take();
        return { t: "un", op: "-", a: parseUnary() };
      }
      if (peek() && peek().type === "op" && peek().value === "+") {
        take();
        return parseUnary();
      }
      return parsePrimary();
    }
    function parsePrimary() {
      const token = take();
      if (!token) throw new FormulaError("unexpected_end", "公式意外结束");
      if (token.type === "num") return { t: "num", v: token.value };
      if (token.type === "param") return { t: "param", name: token.value };
      if (token.type === "ident") {
        if (peek() && peek().type === "op" && peek().value === "(") {
          take();
          const args = [];
          if (!(peek() && peek().type === "op" && peek().value === ")")) {
            args.push(parseComparison());
            while (peek() && peek().type === "op" && peek().value === ",") {
              take();
              args.push(parseComparison());
            }
          }
          if (!(peek() && peek().type === "op" && peek().value === ")")) {
            throw new FormulaError("expected_paren", "函数调用缺少右括号");
          }
          take();
          return { t: "call", name: token.value, args };
        }
        return { t: "ref", name: token.value };
      }
      if (token.type === "op" && token.value === "(") {
        const node = parseComparison();
        if (!(peek() && peek().type === "op" && peek().value === ")")) {
          throw new FormulaError("expected_paren", "缺少右括号");
        }
        take();
        return node;
      }
      throw new FormulaError("unexpected_token", `无法解析的记号：${token.value}`);
    }

    const ast = parseComparison();
    if (pos < tokens.length) {
      throw new FormulaError("trailing_token", `公式存在多余内容：${tokens[pos].value}`);
    }
    return ast;
  }

  function parseFormula(formula) {
    if (!formula || !String(formula).trim()) throw new FormulaError("empty_formula", "公式不能为空");
    return parseTokens(tokenize(String(formula)));
  }

  const FUNCTIONS = {
    ROUND: { arity: 2, fn: (args) => roundHalfUp(args[0], Math.max(0, Math.min(6, Math.trunc(args[1])))) },
    SUM: { arity: [1, Infinity], fn: (args) => round2(args.reduce((a, b) => a + b, 0)) },
    MIN: { arity: [1, Infinity], fn: (args) => Math.min(...args) },
    MAX: { arity: [1, Infinity], fn: (args) => Math.max(...args) },
    ABS: { arity: 1, fn: (args) => Math.abs(args[0]) },
    IF: { arity: 3, lazy: true },
  };

  function evaluateAst(ast, context, params) {
    switch (ast.t) {
      case "num":
        return ast.v;
      case "ref": {
        if (!(ast.name in context)) throw new FormulaError("unknown_field", `未知字段：${ast.name}`);
        const value = context[ast.name];
        if (value == null || Number.isNaN(Number(value))) throw new FormulaError("missing_value", `字段 ${ast.name} 缺少值`);
        return Number(value);
      }
      case "param": {
        if (!(ast.name in params)) throw new FormulaError("unknown_parameter", `未知参数：{${ast.name}}`);
        const value = params[ast.name];
        if (value == null || Number.isNaN(Number(value))) throw new FormulaError("missing_parameter", `参数 {${ast.name}} 缺少值`);
        return Number(value);
      }
      case "un":
        return -evaluateAst(ast.a, context, params);
      case "bin": {
        const a = evaluateAst(ast.a, context, params);
        const b = evaluateAst(ast.b, context, params);
        switch (ast.op) {
          case "+": return a + b;
          case "-": return a - b;
          case "*": return a * b;
          case "/":
            if (b === 0) throw new FormulaError("division_by_zero", "除数为零");
            return a / b;
          case "<": return a < b ? 1 : 0;
          case ">": return a > b ? 1 : 0;
          case "<=": return a <= b ? 1 : 0;
          case ">=": return a >= b ? 1 : 0;
          case "==": return a === b ? 1 : 0;
          case "!=": return a !== b ? 1 : 0;
          default: throw new FormulaError("unknown_operator", `未知运算符：${ast.op}`);
        }
      }
      case "call": {
        const fn = FUNCTIONS[ast.name];
        if (!fn) throw new FormulaError("unknown_function", `未知函数：${ast.name}`);
        const checkArity = () => {
          const min = Array.isArray(fn.arity) ? fn.arity[0] : fn.arity;
          const max = Array.isArray(fn.arity) ? fn.arity[1] : fn.arity;
          if (ast.args.length < min || ast.args.length > max) {
            throw new FormulaError("arity_error", `${ast.name} 需要 ${min === max ? min : `${min}–${max}`} 个参数，实际 ${ast.args.length} 个`);
          }
        };
        if (ast.name === "IF") {
          checkArity();
          const cond = evaluateAst(ast.args[0], context, params);
          return cond ? evaluateAst(ast.args[1], context, params) : evaluateAst(ast.args[2], context, params);
        }
        checkArity();
        return fn.fn(ast.args.map((arg) => evaluateAst(arg, context, params)));
      }
      default:
        throw new FormulaError("unknown_ast", "未知表达式节点");
    }
  }

  function evaluateFormula(formula, context, params) {
    const ast = parseFormula(formula);
    const value = evaluateAst(ast, context, params);
    if (!Number.isFinite(value)) throw new FormulaError("non_finite", "公式结果不是有限数值");
    return value;
  }

  function collectRefs(ast, refs = new Set(), params = new Set()) {
    if (!ast) return { refs, params };
    if (ast.t === "ref") refs.add(ast.name);
    if (ast.t === "param") params.add(ast.name);
    if (ast.t === "un") collectRefs(ast.a, refs, params);
    if (ast.t === "bin") { collectRefs(ast.a, refs, params); collectRefs(ast.b, refs, params); }
    if (ast.t === "call") ast.args.forEach((arg) => collectRefs(arg, refs, params));
    return { refs, params };
  }

  function formulaRefs(formula) {
    try {
      return collectRefs(parseFormula(formula));
    } catch {
      return { refs: new Set(), params: new Set(), invalid: true };
    }
  }

  function effectiveFormula(field, scheme) {
    if (field.calc_mode !== "formula") return null;
    return (scheme && scheme.overrides && scheme.overrides[field.field_key]) || field.default_formula;
  }

  function topoOrder(fieldDefs, scheme) {
    const formulaFields = fieldDefs.filter((f) => f.calc_mode === "formula" && f.is_active !== false);
    const formulaKeys = new Set(formulaFields.map((f) => f.field_key));
    const order = [];
    const state = new Map();
    const stack = [];
    function visit(key) {
      const mark = state.get(key);
      if (mark === "done") return;
      if (mark === "visiting") {
        const start = stack.indexOf(key);
        const cycle = [...stack.slice(start), key];
        throw new FormulaError("cycle", `检测到循环引用：${cycle.join(" → ")}`);
      }
      state.set(key, "visiting");
      stack.push(key);
      const field = fieldDefs.find((f) => f.field_key === key);
      const formula = effectiveFormula(field, scheme);
      const { refs } = formulaRefs(formula);
      for (const ref of refs) {
        if (formulaKeys.has(ref)) visit(ref);
      }
      stack.pop();
      state.set(key, "done");
      order.push(key);
    }
    for (const field of formulaFields) visit(field.field_key);
    return order;
  }

  function checkScale(value, field) {
    if (["earning", "addon", "deduction", "total"].includes(field.category)) {
      const scaled = Math.abs(value * 100 - Math.round(value * 100));
      if (scaled > 1e-6) {
        throw new FormulaError("formula_value_scale", `金额字段 ${field.field_key} 的结果不是 2 位小数（${value}）`);
      }
    }
    return value;
  }

  /* ---------------------------------------------------------------- runtime */

  function createDb() {
    const db = {
      companies: clone(COMPANIES),
      departments: clone(DEPARTMENTS),
      positions: clone(POSITIONS),
      employees: clone(EMPLOYEES),
      costCenters: clone(COST_CENTERS),
      compositions: clone(COMPOSITIONS),
      compositionItems: clone(COMPOSITION_ITEMS),
      schemes: clone(SCHEMES),
      workdayParams: clone(WORKDAY_PARAMS),
      globalParams: clone(GLOBAL_PARAMS),
      fieldDefs: clone(FIELD_DEFS),
      months: {},
      runs: [],
      events: [],
      exportJobs: [],
      configRevisions: [],
      engineVersion: "payroll-engine-1.0.0",
    };
    seedMonths(db);
    return db;
  }

  function employeesInScope(db, companyId, monthKey) {
    const [y, m] = monthKey.split("-").map(Number);
    const monthStart = `${monthKey}-01`;
    const monthEnd = new Date(Date.UTC(y, m, 0)).toISOString().slice(0, 10);
    return db.employees.filter((emp) => {
      const dept = db.departments.find((d) => d.id === emp.deptId);
      if (!dept || dept.companyId !== companyId) return false;
      if (emp.status === "resigned") {
        return Boolean(emp.resignDate && emp.resignDate >= monthStart);
      }
      if (emp.hireDate > monthEnd) return false;
      if (emp.resignDate && emp.resignDate < monthStart) return false;
      return true;
    });
  }

  function deptPath(db, deptId) {
    const path = [];
    let current = db.departments.find((d) => d.id === deptId);
    while (current) {
      path.unshift({ id: current.id, code: current.id, name: current.name });
      current = db.departments.find((d) => d.id === current.parentId);
    }
    return path;
  }

  function costPath(db, costCenterId) {
    const path = [];
    if (!costCenterId) return path;
    let current = db.costCenters.find((c) => c.id === costCenterId);
    while (current) {
      path.unshift({ id: current.id, code: current.code, name: current.name });
      current = db.costCenters.find((c) => c.id === current.parentId);
    }
    return path;
  }

  function currentComposition(db, code) {
    const composition = db.compositions.find((c) => c.code === code);
    if (!composition) return null;
    return composition.versions.reduce((best, version) => (version.version > best.version ? version : best), composition.versions[0]);
  }

  function schemeFor(db, code) {
    return db.schemes.find((s) => s.code === code) || null;
  }

  function workdayFor(db, code) {
    return db.workdayParams.find((w) => w.code === code) || null;
  }

  function numericGlobalParams(db) {
    const params = {};
    for (const param of db.globalParams) {
      if (param.type === "number") params[param.key] = Number(param.value);
    }
    return params;
  }

  function seedInput(emp, monthKey) {
    const isOct = monthKey === "2026-10";
    const index = Number(emp.no.slice(1)) - 101;
    const weekdayFull = isOct ? 21 : 20;
    const weekendFull = isOct ? 9 : 10;
    const absence = emp.no === "E104" ? 1 : emp.no === "E105" ? 0.5 : emp.no === "E110" ? 2 : 0;
    const weekdayAttended = Math.max(0, weekdayFull - absence);
    const weekendAttended = [2, 4, 6, 0, 8, 4, 2, 6, 0, 4, 2, 0, 6, 0, 4][index % 15];
    const paidLeaveDays = emp.no === "E102" ? 0.5 : emp.no === "E113" ? 1 : 0;
    const otWeekday = [2, 0, 4, 6, 0, 2, 0, 8, 0, 4, 0, 0, 6, 0, 2][index % 15];
    const otWeekend = [4, 0, 8, 2, 6, 0, 0, 10, 0, 4, 0, 0, 8, 0, 4][index % 15];
    const otHoliday = isOct && emp.no === "E108" ? 4 : 0;
    const packageTotal = Number(emp.no === "E112" ? 7100 : 0) || 0;
    const baseEstimate = emp.positionId === "p-tech" ? 14000 : emp.positionId === "p-line" || emp.positionId === "p-op" ? 7100 : 8500;
    const social = -round2(baseEstimate * 0.105);
    const tax = -round2(Math.max(0, baseEstimate - 5000) * 0.03);
    return {
      weekday_full: weekdayFull,
      weekend_full: weekendFull,
      weekday_attended: weekdayAttended,
      weekend_attended: weekendAttended,
      paid_leave_days: paidLeaveDays,
      ot_weekday_hours: otWeekday,
      ot_weekend_hours: otWeekend,
      ot_holiday_hours: otHoliday,
      attendance_deduct: emp.no === "E104" ? -200 : emp.no === "E105" ? -100 : 0,
      phone_allowance: 100,
      car_allowance: index % 3 === 0 ? 300 : 200,
      other_addon: emp.no === "E107" ? 100 : 0,
      production_bonus: ["p-op", "p-line"].includes(emp.positionId) ? 200 + (index % 4) * 100 : 0,
      commission: 0,
      admin_deduct: emp.no === "E109" ? -50 : 0,
      social_this: social,
      tax,
      paid_advance: 0,
      packageTotal,
    };
  }

  function resolvedConfig(db, emp) {
    const position = db.positions.find((p) => p.id === emp.positionId);
    if (!position) return { error: new FormulaError("position_missing", `员工 ${emp.no} 的岗位不存在`) };
    if (!position.payroll) return { error: new FormulaError("position_unconfigured", `岗位「${position.name}」未装配薪资配置`) };
    const composition = currentComposition(db, position.payroll.compositionCode);
    const scheme = schemeFor(db, position.payroll.schemeCode);
    const workday = workdayFor(db, position.payroll.workdayCode);
    if (!composition || !scheme || !workday) {
      return { error: new FormulaError("config_missing", `岗位「${position.name}」的薪资配置不完整`) };
    }
    return { position, composition, scheme, workday };
  }

  function computeEmployee(db, emp, monthKey, input, attendance) {
    if (!attendance.locked) throw new FormulaError("attendance_unlocked", "考勤月未锁定");
    if (attendance.status === "missing") throw new FormulaError("attendance_missing", "缺少考勤月汇总");
    const resolved = resolvedConfig(db, emp);
    if (resolved.error) throw resolved.error;
    const { position, composition, scheme, workday } = resolved;
    const fieldDefs = db.fieldDefs.filter((f) => f.is_active !== false);
    const values = {};
    const context = { ...composition.amounts };
    const params = {
      ...numericGlobalParams(db),
      avg_pay_days: workday.avg_pay_days,
      work_hours: workday.work_hours,
      ot_mult_weekday: workday.ot_mult_weekday,
      ot_mult_weekend: workday.ot_mult_weekend,
      ot_mult_holiday: workday.ot_mult_holiday,
      min_wage: workday.min_wage,
    };
    for (const field of fieldDefs) {
      if (field.calc_mode === "plan") {
        values[field.field_key] = Number(composition.amounts[field.source_key] || 0);
      } else if (field.calc_mode === "import") {
        values[field.field_key] = Number(input[field.source_key] || 0);
      } else if (field.calc_mode === "fixed") {
        values[field.field_key] = Number(field.fixed_value || 0);
      }
    }
    Object.assign(context, values, input);
    const order = topoOrder(fieldDefs, scheme);
    for (const key of order) {
      const field = fieldDefs.find((f) => f.field_key === key);
      const formula = effectiveFormula(field, scheme);
      const value = evaluateFormula(formula, context, params);
      checkScale(value, field);
      values[key] = value;
      context[key] = value;
    }
    return {
      employeeId: emp.id,
      employeeNo: emp.no,
      employeeName: emp.name,
      deptId: emp.deptId,
      deptName: db.departments.find((d) => d.id === emp.deptId)?.name || "",
      deptPath: deptPath(db, emp.deptId),
      positionId: position.id,
      positionName: position.name,
      costCenterId: emp.costCenterId,
      costPath: costPath(db, emp.costCenterId),
      values,
      config: {
        compositionCode: composition.code,
        compositionName: composition.name,
        compositionVersion: composition.version,
        schemeCode: scheme.code,
        schemeName: scheme.name,
        workdayCode: workday.code,
        workdayName: workday.name,
        engineVersion: db.engineVersion,
      },
    };
  }

  function computeMonth(db, monthKey) {
    const month = db.months[monthKey];
    if (!month) throw new FormulaError("month_missing", "薪资月不存在");
    const companyEmployees = employeesInScope(db, month.companyId, monthKey).filter((emp) => emp.companyId !== "c2");
    const results = [];
    const errors = [];
    for (const emp of companyEmployees) {
      try {
        const result = computeEmployee(db, emp, monthKey, month.inputs[emp.id] || {}, month.attendance);
        results.push(result);
      } catch (error) {
        errors.push({ employeeId: emp.id, employeeNo: emp.no, employeeName: emp.name, code: error.code || "error", message: error.message });
      }
    }
    const totals = aggregateResults(results);
    return { results, errors, totals };
  }

  function aggregateResults(results) {
    return {
      count: results.length,
      gross: round2(sum(results.map((r) => r.values), "gross")),
      social: round2(sum(results.map((r) => r.values), "social_this")),
      tax: round2(sum(results.map((r) => r.values), "tax")),
      net: round2(sum(results.map((r) => r.values), "net")),
      normal: round2(sum(results.map((r) => r.values), "normal_pay")),
    };
  }

  function seedMonths(db) {
    const now = "2026-11-28 09:00";
    const months = {
      "2026-10": {
        key: "2026-10", companyId: "c1", state: "paid", inputVersion: 5,
        attendance: { locked: true, status: "fresh", version: 2, summaryCount: 15, pulledAt: "2026-11-02 09:12" },
        configStale: false, scopeStale: false,
        inputs: {}, manualValues: {},
        batches: [
          { id: "B-202610-01", source: "file", fileName: "payroll-2026-10.csv", status: "committed", rows: 15, columns: 9, committedAt: "2026-11-02 10:35", inputVersion: 5, note: "覆盖式刷新" },
        ],
        runs: [], events: [], results: [], paidSnapshot: null, lastRunId: null,
      },
      "2026-11": {
        key: "2026-11", companyId: "c1", state: "calculated", inputVersion: 7,
        attendance: { locked: true, status: "fresh", version: 3, summaryCount: 13, pulledAt: "2026-11-25 08:40" },
        configStale: false, scopeStale: false,
        inputs: {}, manualValues: {},
        batches: [
          { id: "B-202611-01", source: "file", fileName: "payroll-2026-11-v1.csv", status: "superseded", rows: 12, columns: 9, committedAt: "2026-11-20 14:08", inputVersion: 6, note: "被 11-24 导入替代" },
          { id: "B-202611-02", source: "file", fileName: "payroll-2026-11.csv", status: "committed", rows: 13, columns: 9, committedAt: "2026-11-24 17:22", inputVersion: 7, note: "覆盖式刷新；3 个手工值被覆盖" },
        ],
        runs: [], events: [], results: [], paidSnapshot: null, lastRunId: null,
      },
      "2026-12": {
        key: "2026-12", companyId: "c1", state: "draft", inputVersion: 0,
        attendance: { locked: false, status: "missing", version: 0, summaryCount: 0, pulledAt: null },
        configStale: false, scopeStale: false,
        inputs: {}, manualValues: {},
        batches: [],
        runs: [], events: [], results: [], paidSnapshot: null, lastRunId: null,
      },
    };
    db.months = months;
    for (const monthKey of Object.keys(months)) {
      const month = months[monthKey];
      for (const emp of employeesInScope(db, month.companyId, monthKey)) {
        month.inputs[emp.id] = seedInput(emp, monthKey);
      }
    }
    // A manual value that a re-import will overwrite — shown amber in the preview.
    months["2026-11"].inputs.E104.phone_allowance = 150;
    months["2026-11"].manualValues.E104 = { at: "2026-11-23 15:40", by: "管理员", fields: ["phone_allowance"] };
    // 2026-10 — paid month, snapshot is the value-level history.
    const oct = months["2026-10"];
    const octComputed = computeMonth(db, "2026-10");
    oct.results = octComputed.results;
    oct.events = [
      { at: "2026-11-01 09:00", type: "created", label: "薪资月创建", by: "管理员", reason: "" },
      { at: "2026-11-03 10:12", type: "calculated", label: "核算成功 · R-2610-01", by: "管理员", reason: "" },
      { at: "2026-11-04 16:30", type: "confirmed", label: "确认工资表", by: "管理员", reason: "" },
      { at: "2026-11-05 15:20", type: "paid", label: "标记已发 · 快照 v1", by: "管理员", reason: "" },
    ];
    const octRun = makeRunRecord("R-2610-01", "2026-10", "manual", "success", "2026-11-03 10:12", "2026-11-03 10:13", 7, 5, 2, 15, octComputed.totals, "管理员", null);
    oct.runs = [octRun];
    oct.lastRunId = octRun.id;
    oct.paidSnapshot = {
      version: 1, paidAt: "2026-11-05 15:20", by: "管理员", runId: octRun.id,
      results: clone(oct.results), fieldDefs: clone(db.fieldDefs), totals: clone(octComputed.totals),
      configSummary: { engineVersion: db.engineVersion, composition: "岗位当前版本", scheme: "岗位计算方案", workday: "岗位工作日参数" },
      attendanceVersion: 2,
      inputVersion: oct.inputVersion,
    };
    db.runs.push(octRun);
    // 2026-11 — current month, successful results, one failed attempt in history.
    const nov = months["2026-11"];
    const novComputed = computeMonth(db, "2026-11");
    nov.results = novComputed.results;
    const failedRun = makeRunRecord("R-2611-01", "2026-11", "manual", "failed", "2026-11-24 16:02", "2026-11-24 16:02", 0, 7, 3, 13, null, "管理员", "3 名员工缺少 2026-11 考勤月汇总（E101、E105、E113）");
    const runA = makeRunRecord("R-2611-02", "2026-11", "manual", "success", "2026-11-25 09:18", "2026-11-25 09:19", 8, 6, 3, 13, clone(novComputed.totals), "管理员", null);
    const runB = makeRunRecord("R-2611-03", "2026-11", "recalc", "success", "2026-11-26 10:24", "2026-11-26 10:25", 6, 7, 3, 13, clone(novComputed.totals), "管理员", null);
    nov.runs = [failedRun, runA, runB];
    nov.lastRunId = runB.id;
    nov.events = [
      { at: "2026-11-01 09:00", type: "created", label: "薪资月创建", by: "管理员", reason: "" },
      { at: "2026-11-24 16:02", type: "failed", label: "核算失败 · R-2611-01", by: "管理员", reason: "缺少考勤月汇总" },
      { at: "2026-11-25 09:18", type: "calculated", label: "核算成功 · R-2611-02", by: "管理员", reason: "" },
      { at: "2026-11-26 10:24", type: "calculated", label: "重新核算 · R-2611-03", by: "管理员", reason: "导入 v7 后重算" },
    ];
    db.runs.push(failedRun, runA, runB);
    // 2026-12 — future/current draft, no run.
    months["2026-12"].events = [{ at: "2026-11-20 09:00", type: "created", label: "预建下月薪资月", by: "管理员", reason: "" }];
    db.exportJobs = [
      { id: "EXP-1001", monthKey: "2026-10", type: "batch", format: "zip", sourceLabel: "已发快照 v1", count: 13, status: "succeeded", progress: 100, createdAt: "2026-11-06 10:12", expiresAt: "2026-11-07 10:12", downloads: 4, lastDownloadedBy: "管理员" },
      { id: "EXP-1002", monthKey: "2026-11", type: "batch", format: "merged", sourceLabel: "当前成功批次 R-2611-03", count: 13, status: "expired", progress: 100, createdAt: "2026-11-26 11:00", expiresAt: "2026-11-27 11:00", downloads: 2, lastDownloadedBy: "管理员" },
    ];
  }

  function makeRunRecord(id, monthKey, trigger, status, startedAt, finishedAt, durationMs, inputVersion, attendanceVersion, employeeCount, totals, operator, error) {
    return {
      id, monthKey, trigger, status, startedAt, finishedAt, durationMs, inputVersion, attendanceVersion,
      employeeCount: totals ? totals.count : employeeCount,
      totals: totals ? clone(totals) : null,
      operator, error,
      configSnapshot: {
        engineVersion: "payroll-engine-1.0.0",
        compositions: "岗位当前版本",
        schemes: "岗位计算方案",
        workday: "岗位工作日参数",
        fieldDefs: "32 个字段定义",
      },
      inputSnapshot: `输入版本 v${inputVersion}`,
      attendanceSnapshot: `考勤锁定快照 v${attendanceVersion}`,
    };
  }

  /* ---------------------------------------------------------------- derived views */

  function employeeById(db, id) {
    return db.employees.find((e) => e.id === id) || null;
  }

  function monthResults(db, month) {
    if (!month) return null;
    if (month.state === "paid" && month.paidSnapshot) {
      return { source: "paid", label: `已发快照 v${month.paidSnapshot.version}`, results: month.paidSnapshot.results, fieldDefs: month.paidSnapshot.fieldDefs, totals: month.paidSnapshot.totals, at: month.paidSnapshot.paidAt };
    }
    if (month.results && month.results.length) {
      return { source: "run", label: `当前成功批次 ${month.lastRunId || ""}`.trim(), results: month.results, fieldDefs: db.fieldDefs, totals: aggregateResults(month.results), at: lastSuccessRun(db, month)?.finishedAt || "" };
    }
    return null;
  }

  function lastSuccessRun(db, month) {
    if (!month) return null;
    return [...month.runs].reverse().find((r) => r.status === "success") || null;
  }

  function lastRun(db, month) {
    if (!month) return null;
    return month.runs[month.runs.length - 1] || null;
  }

  function monthClass(db, monthKey) {
    // Prototype scenario "today" is 2026-11-28; months after it are future/current.
    return monthKey >= "2026-11" ? "current" : "historical";
  }

  function monthFlags(db, month) {
    if (!month) return { needsRecalc: false, attendanceStale: false, inputChanged: false, configStale: false, scopeStale: false, lastFailed: false, hasRun: false, hasResults: false };
    const success = lastSuccessRun(db, month);
    const inputChanged = Boolean(success && success.inputVersion !== month.inputVersion);
    const attendanceStale = month.attendance.status === "stale";
    const lastFailed = Boolean(lastRun(db, month) && lastRun(db, month).status === "failed");
    return {
      needsRecalc: Boolean(success && (inputChanged || attendanceStale || month.scopeStale || month.configStale)),
      inputChanged,
      attendanceStale,
      configStale: Boolean(month.configStale && month.state !== "paid"),
      scopeStale: Boolean(month.scopeStale),
      lastFailed,
      hasRun: month.runs.length > 0,
      hasResults: Boolean(month.results && month.results.length),
      success,
    };
  }

  function consistencyChecks(result) {
    const v = result.values;
    const earningSum = round2(["base_pay", "hightemp", "performance", "overtime_pay_actual", "confidential", "social_sub", "noncompete_sub"].reduce((a, k) => a + (v[k] || 0), 0));
    const addonSum = round2(["paid_leave_pay", "ot_subsidy", "phone_allowance", "car_allowance", "other_addon", "production_bonus", "commission", "attendance_deduct", "admin_deduct"].reduce((a, k) => a + (v[k] || 0), 0));
    const deductSum = round2(["social_this", "tax", "paid_advance"].reduce((a, k) => a + (v[k] || 0), 0));
    return [
      { key: "normal_pay", label: "normal_pay = Σ 计薪项", pass: Math.abs(round2(v.normal_pay) - earningSum) < 0.005, actual: v.normal_pay, expected: earningSum },
      { key: "addon_sum", label: "addon_sum = Σ 加减项", pass: Math.abs(round2(v.addon_sum) - addonSum) < 0.005, actual: v.addon_sum, expected: addonSum },
      { key: "gross", label: "gross = normal_pay + addon_sum", pass: Math.abs(round2(v.gross) - round2(v.normal_pay + v.addon_sum)) < 0.005, actual: v.gross, expected: round2(v.normal_pay + v.addon_sum) },
      { key: "deduct_sum", label: "deduct_sum = Σ 代扣项", pass: Math.abs(round2(v.deduct_sum) - deductSum) < 0.005, actual: v.deduct_sum, expected: deductSum },
      { key: "net", label: "net = gross + deduct_sum", pass: Math.abs(round2(v.net) - round2(v.gross + v.deduct_sum)) < 0.005, actual: v.net, expected: round2(v.gross + v.deduct_sum) },
    ];
  }

  function audienceFor(month) {
    return monthResults(null, month);
  }

  function costStats(db, monthKey) {
    const month = db.months[monthKey];
    const source = monthResults(db, month);
    if (!source) return null;
    const results = source.results;
    const costById = new Map(db.costCenters.map((c) => [c.id, c]));
    const nodes = db.costCenters.map((c) => ({ ...c, children: [] }));
    const nodeById = new Map(nodes.map((n) => [n.id, n]));
    const roots = [];
    for (const node of nodes) {
      if (node.parentId && nodeById.has(node.parentId)) nodeById.get(node.parentId).children.push(node);
      else roots.push(node);
    }
    const frozenCodes = new Set();
    for (const result of results) for (const step of result.costPath || []) frozenCodes.add(step.code);
    for (const node of nodes) node.frozen = frozenCodes.has(node.code);
    const resultHas = (node) => results.filter((r) => (r.costPath || []).some((step) => step.code === node.code));
    const rows = [];
    const walk = (node, depth) => {
      const scoped = resultHas(node);
      const sums = aggregateResults(scoped);
      const budget = Number(node.budget || 0);
      const gross = sums.gross;
      const rate = budget > 0 ? (gross / budget) * 100 : null;
      let status = "none";
      if (budget > 0) {
        if (rate >= 100) status = "over";
        else if (rate >= Number(node.warnPct || 90)) status = "warn";
        else status = "normal";
      }
      const row = {
        id: node.id, code: node.code, name: node.name, depth,
        parentId: node.parentId, active: node.active !== false,
        headcount: sums.count, gross: sums.gross, social: sums.social, tax: sums.tax, net: sums.net,
        budget, warnPct: Number(node.warnPct || 90), rate, status,
        hasResults: scoped.length > 0,
        frozen: node.frozen,
        children: node.children,
      };
      rows.push(row);
      for (const child of node.children) walk(child, depth + 1);
    };
    for (const root of roots) walk(root, 0);
    const assignedIds = new Set();
    for (const result of results) for (const step of result.costPath || []) assignedIds.add(step.code);
    const unassigned = results.filter((r) => !(r.costPath || []).length);
    const unassignedSums = aggregateResults(unassigned);
    const all = aggregateResults(results);
    const companyBudget = round2(roots.reduce((acc, r) => acc + Number(r.budget || 0), 0));
    const companyRate = companyBudget > 0 ? (all.gross / companyBudget) * 100 : null;
    const companyStatus = companyBudget <= 0 ? "none" : companyRate >= 100 ? "over" : companyRate >= 90 ? "warn" : "normal";
    const rootCoverage = roots.map((root) => ({
      code: root.code, name: root.name, budget: Number(root.budget || 0),
      spend: aggregateResults(resultHas(root)).gross,
    }));
    return {
      source, rows, roots: rootCoverage, unassigned: { ...unassignedSums, employees: unassigned },
      company: { ...all, budget: companyBudget, rate: companyRate, status: companyStatus },
      warnCount: rows.filter((r) => r.status === "warn" || r.status === "over").length,
      coverageWarning: rootCoverage.some((r) => r.budget === 0 && r.spend > 0.005),
      activeCodes: new Set(db.costCenters.filter((c) => c.active !== false).map((c) => c.code)),
    };
  }

  function costDrill(db, monthKey, code) {
    const month = db.months[monthKey];
    const source = monthResults(db, month);
    if (!source) return null;
    const employees = source.results.filter((r) => (r.costPath || []).some((step) => step.code === code));
    return { code, employees, totals: aggregateResults(employees) };
  }

  /* ---------------------------------------------------------------- trial calculation */

  function sampleEmployee(db, monthKey) {
    const month = db.months[monthKey];
    if (!month) return null;
    return db.employees.find((e) => e.no === "E101") || null;
  }

  function trialFormula(db, { schemeCode, fieldKey, formula, monthKey }) {
    const month = db.months[monthKey] || db.months["2026-11"];
    const emp = sampleEmployee(db, monthKey) || db.employees[0];
    const resolved = resolvedConfig(db, emp);
    if (resolved.error) return { ok: false, error: resolved.error.code, message: resolved.error.message };
    const scheme = clone(resolved.scheme);
    if (schemeCode && schemeCode !== scheme.code) {
      const other = schemeFor(db, schemeCode);
      if (other) Object.assign(scheme, clone(other));
    }
    const draftScheme = { ...scheme, overrides: { ...(scheme.overrides || {}) } };
    if (formula != null) draftScheme.overrides[fieldKey] = formula;
    else delete draftScheme.overrides[fieldKey];
    try {
      const result = computeEmployee(db, emp, month.key, month.inputs[emp.id] || {}, month.attendance);
      if (formula == null) {
        return { ok: true, value: result.values[fieldKey], employee: emp, result };
      }
      // Recompute with the draft formula.
      const fieldDefs = db.fieldDefs.filter((f) => f.is_active !== false);
      const field = fieldDefs.find((f) => f.field_key === fieldKey);
      const order = topoOrder(fieldDefs, draftScheme);
      const values = {};
      const context = { ...resolved.composition.amounts };
      const params = {
        ...numericGlobalParams(db),
        avg_pay_days: resolved.workday.avg_pay_days,
        work_hours: resolved.workday.work_hours,
        ot_mult_weekday: resolved.workday.ot_mult_weekday,
        ot_mult_weekend: resolved.workday.ot_mult_weekend,
        ot_mult_holiday: resolved.workday.ot_mult_holiday,
        min_wage: resolved.workday.min_wage,
      };
      const input = month.inputs[emp.id] || {};
      for (const item of fieldDefs) {
        if (item.calc_mode === "plan") values[item.field_key] = Number(resolved.composition.amounts[item.source_key] || 0);
        else if (item.calc_mode === "import") values[item.field_key] = Number(input[item.source_key] || 0);
        else if (item.calc_mode === "fixed") values[item.field_key] = Number(item.fixed_value || 0);
      }
      Object.assign(context, values, input);
      for (const key of order) {
        const item = fieldDefs.find((f) => f.field_key === key);
        const formulaText = effectiveFormula(item, draftScheme);
        const value = evaluateFormula(formulaText, context, params);
        checkScale(value, item);
        values[key] = value;
        context[key] = value;
      }
      return { ok: true, value: values[fieldKey], employee: emp, result: { ...result, values }, order };
    } catch (error) {
      return { ok: false, error: error.code || "error", message: error.message };
    }
  }

  /* ---------------------------------------------------------------- exports */

  window.PayrollData = {
    createDb,
    CATEGORY,
    CATEGORY_ORDER,
    CALC_MODE,
    ATTENDANCE_FIELDS,
    PAYROLL_IMPORT_FIELDS,
    IMPORT_COLUMNS,
    ATTENDANCE_COLUMN_ALIASES,
    COMPOSITION_ITEMS,
    FormulaError,
    helpers: {
      clone, round2, sum, money: round2,
      employeesInScope, employeeById, deptPath, costPath,
      currentComposition, schemeFor, workdayFor,
      effectiveFormula, topoOrder, formulaRefs, evaluateFormula, parseFormula,
      computeMonth, aggregateResults, monthResults, lastRun, lastSuccessRun,
      monthClass, monthFlags, consistencyChecks, costStats, costDrill, trialFormula,
      resolvedConfig, sampleEmployee, seedInput, makeRunRecord,
    },
  };
})();
