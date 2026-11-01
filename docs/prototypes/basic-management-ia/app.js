(() => {
  "use strict";

  /* ================================================================ icons */

  const ICONS = {
    dashboard:
      '<rect x="3" y="3" width="7" height="7" rx="1.2"/><rect x="14" y="3" width="7" height="7" rx="1.2"/><rect x="3" y="14" width="7" height="7" rx="1.2"/><rect x="14" y="14" width="7" height="7" rx="1.2"/>',
    building:
      '<path d="M3 21h18"/><path d="M5 21V5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v16"/><path d="M15 21V9h2a2 2 0 0 1 2 2v10"/><path d="M9 7h2"/><path d="M9 11h2"/><path d="M9 15h2"/>',
    network:
      '<rect x="9" y="3" width="6" height="5" rx="1"/><rect x="3" y="16" width="6" height="5" rx="1"/><rect x="15" y="16" width="6" height="5" rx="1"/><path d="M12 8v4"/><path d="M6 16v-2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v2"/>',
    users:
      '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    briefcase:
      '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><path d="M2 12h20"/>',
    wallet:
      '<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>',
    settings:
      '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.51a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2Z"/><circle cx="12" cy="12" r="3"/>',
    plus: '<path d="M12 5v14"/><path d="M5 12h14"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "chevron-left": '<path d="m15 18-6-6 6-6"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    alert:
      '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    trash:
      '<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/>',
    "arrow-left": '<path d="M19 12H5"/><path d="m12 19-7-7 7-7"/>',
    refresh:
      '<path d="M3 12a9 9 0 0 1 15.5-6.2L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15.5 6.2L3 16"/><path d="M3 21v-5h5"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/>',
    lock: '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    calendar:
      '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    coins:
      '<circle cx="8" cy="8" r="6"/><path d="M18.1 10.5A6 6 0 1 1 10.5 18"/><path d="M7 6h1v4"/><path d="M16 18h2"/><path d="M22 18h-2"/><path d="M18 16v4"/>',
    layers:
      '<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/>',
    "more-horizontal":
      '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    external:
      '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    flag: '<path d="M4 22V4"/><path d="M4 4c5-3 8 3 13 0v9c-5 3-8-3-13 0"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
    moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  };

  function icon(name) {
    const content = ICONS[name] || "";
    return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${content}</svg>`;
  }

  /* ================================================================ data */

  const TODAY = "2026-11-01";

  const companies = [
    {
      id: "c1",
      code: "RX",
      name: "荣新矿业",
      active: true,
      note: "煤矿生产与洗选",
    },
    {
      id: "c2",
      code: "RXWL",
      name: "荣新物流",
      active: true,
      note: "物流运输与仓储",
    },
    {
      id: "c3",
      code: "RXJS",
      name: "荣新建设",
      active: true,
      note: "新设公司，暂无组织数据",
    },
  ];

  const departments = [
    {
      id: "d1",
      companyId: "c1",
      code: "D1",
      name: "总部",
      parentId: null,
      managerId: "e1",
      orderNo: 10,
      active: true,
      note: "公司总部",
    },
    {
      id: "d2",
      companyId: "c1",
      code: "D2",
      name: "行政部",
      parentId: "d1",
      managerId: "e2",
      orderNo: 20,
      active: true,
      note: "",
    },
    {
      id: "d3",
      companyId: "c1",
      code: "D3",
      name: "生产部",
      parentId: "d1",
      managerId: "e3",
      orderNo: 30,
      active: true,
      note: "生产条线",
    },
    {
      id: "d9",
      companyId: "c1",
      code: "D9",
      name: "皓程车间",
      parentId: "d3",
      managerId: "e4",
      orderNo: 10,
      active: true,
      note: "生产部下属车间",
    },
    {
      id: "d4",
      companyId: "c1",
      code: "D4",
      name: "财务部",
      parentId: "d1",
      managerId: "e5",
      orderNo: 40,
      active: true,
      note: "",
    },
    {
      id: "d5",
      companyId: "c1",
      code: "D5",
      name: "人力资源部",
      parentId: "d1",
      managerId: "e6",
      orderNo: 50,
      active: true,
      note: "",
    },
    {
      id: "d8",
      companyId: "c1",
      code: "D6",
      name: "老厂区",
      parentId: "d1",
      managerId: null,
      orderNo: 60,
      active: false,
      note: "已停用，仅保留历史数据",
    },
    {
      id: "d6",
      companyId: "c2",
      code: "D1",
      name: "物流总部",
      parentId: null,
      managerId: "e13",
      orderNo: 10,
      active: true,
      note: "",
    },
    {
      id: "d7",
      companyId: "c2",
      code: "D2",
      name: "仓储部",
      parentId: "d6",
      managerId: "e14",
      orderNo: 20,
      active: true,
      note: "",
    },
  ];

  const positions = [
    {
      id: "p1",
      companyId: "c1",
      code: "POS-ADMIN",
      name: "行政专员",
      deptId: "d2",
      orderNo: 10,
      active: true,
      note: "",
    },
    {
      id: "p2",
      companyId: "c1",
      code: "POS-FIN",
      name: "财务专员",
      deptId: "d4",
      orderNo: 20,
      active: true,
      note: "",
    },
    {
      id: "p3",
      companyId: "c1",
      code: "POS-HR",
      name: "人事专员",
      deptId: "d5",
      orderNo: 30,
      active: true,
      note: "",
    },
    {
      id: "p4",
      companyId: "c1",
      code: "POS-PROD",
      name: "生产主管",
      deptId: "d3",
      orderNo: 40,
      active: true,
      note: "",
    },
    {
      id: "p5",
      companyId: "c1",
      code: "POS-LEAD",
      name: "车间班长",
      deptId: "d9",
      orderNo: 50,
      active: true,
      note: "",
    },
    {
      id: "p6",
      companyId: "c1",
      code: "POS-OP",
      name: "操作工",
      deptId: "d9",
      orderNo: 60,
      active: true,
      note: "",
    },
    {
      id: "p7",
      companyId: "c1",
      code: "POS-DIR",
      name: "总经理",
      deptId: "d1",
      orderNo: 70,
      active: true,
      note: "",
    },
    {
      id: "p10",
      companyId: "c1",
      code: "POS-OLD",
      name: "旧厂值班员",
      deptId: "d8",
      orderNo: 90,
      active: false,
      note: "随老厂区停用",
    },
    {
      id: "p8",
      companyId: "c2",
      code: "POS-DISP",
      name: "调度员",
      deptId: "d6",
      orderNo: 10,
      active: true,
      note: "",
    },
    {
      id: "p9",
      companyId: "c2",
      code: "POS-WH",
      name: "仓管员",
      deptId: "d7",
      orderNo: 20,
      active: true,
      note: "",
    },
  ];

  const costCenters = [
    {
      id: "cc1",
      companyId: "c1",
      code: "CO-PROD",
      name: "生产成本中心",
      parentId: null,
      managerId: "e3",
      budget: 120000,
      warnPct: 85,
      orderNo: 10,
      active: true,
      note: "生产条线",
    },
    {
      id: "cc2",
      companyId: "c1",
      code: "CO-PROD-1",
      name: "皓程车间",
      parentId: "cc1",
      managerId: "e4",
      budget: 50000,
      warnPct: 80,
      orderNo: 10,
      active: true,
      note: "",
    },
    {
      id: "cc3",
      companyId: "c1",
      code: "CO-ADMIN",
      name: "职能成本中心",
      parentId: null,
      managerId: "e2",
      budget: 80000,
      warnPct: 90,
      orderNo: 20,
      active: true,
      note: "总部职能",
    },
    {
      id: "cc4",
      companyId: "c1",
      code: "CO-PROJ",
      name: "项目成本中心",
      parentId: null,
      managerId: null,
      budget: 0,
      warnPct: 85,
      orderNo: 30,
      active: true,
      note: "0 = 不设预算",
    },
    {
      id: "cc7",
      companyId: "c1",
      code: "CO-OLD",
      name: "旧生产线",
      parentId: "cc1",
      managerId: null,
      budget: 0,
      warnPct: 85,
      orderNo: 30,
      active: false,
      note: "已停用",
    },
    {
      id: "cc5",
      companyId: "c2",
      code: "CO-WL",
      name: "物流成本中心",
      parentId: null,
      managerId: "e13",
      budget: 60000,
      warnPct: 85,
      orderNo: 10,
      active: true,
      note: "",
    },
    {
      id: "cc6",
      companyId: "c2",
      code: "CO-WL-1",
      name: "仓储成本中心",
      parentId: "cc5",
      managerId: "e14",
      budget: 30000,
      warnPct: 80,
      orderNo: 10,
      active: true,
      note: "",
    },
  ];

  const employees = [
    {
      id: "e1",
      no: "E1001",
      name: "张建国",
      gender: "male",
      deptId: "d1",
      positionId: "p7",
      costId: "cc3",
      managerId: null,
      status: "active",
      hireDate: "2015-03-01",
      resignDate: null,
      contract: "full_time",
      dailyHours: "8",
      monthlyRest: 8,
      confidentiality: 3,
      note: "公司总经理",
    },
    {
      id: "e2",
      no: "E1002",
      name: "王丽",
      gender: "female",
      deptId: "d2",
      positionId: "p1",
      costId: "cc3",
      managerId: "e1",
      status: "active",
      hireDate: "2017-06-12",
      resignDate: null,
      contract: "full_time",
      dailyHours: "8",
      monthlyRest: 8,
      confidentiality: 2,
      note: "行政部负责人",
    },
    {
      id: "e3",
      no: "E1003",
      name: "李强",
      gender: "male",
      deptId: "d3",
      positionId: "p4",
      costId: "cc1",
      managerId: "e1",
      status: "active",
      hireDate: "2016-09-01",
      resignDate: null,
      contract: "full_time",
      dailyHours: "8",
      monthlyRest: 4,
      confidentiality: 4,
      note: "生产部负责人",
    },
    {
      id: "e4",
      no: "E1004",
      name: "黄国锋",
      gender: "male",
      deptId: "d9",
      positionId: "p5",
      costId: "cc2",
      managerId: "e3",
      status: "active",
      hireDate: "2018-04-15",
      resignDate: null,
      contract: "full_time",
      dailyHours: "8",
      monthlyRest: 4,
      confidentiality: 4,
      note: "皓程车间负责人",
    },
    {
      id: "e5",
      no: "E1005",
      name: "赵敏",
      gender: "female",
      deptId: "d4",
      positionId: "p2",
      costId: "cc3",
      managerId: "e1",
      status: "active",
      hireDate: "2019-02-20",
      resignDate: null,
      contract: "full_time",
      dailyHours: "8",
      monthlyRest: 8,
      confidentiality: 3,
      note: "财务部负责人",
    },
    {
      id: "e6",
      no: "E1006",
      name: "陈静",
      gender: "female",
      deptId: "d5",
      positionId: "p3",
      costId: "cc3",
      managerId: "e1",
      status: "active",
      hireDate: "2020-07-01",
      resignDate: null,
      contract: "full_time",
      dailyHours: "8",
      monthlyRest: 8,
      confidentiality: 3,
      note: "人力资源部负责人",
    },
    {
      id: "e7",
      no: "E1007",
      name: "刘洋",
      gender: "male",
      deptId: "d9",
      positionId: "p6",
      costId: "cc2",
      managerId: "e4",
      status: "active",
      hireDate: "2021-03-10",
      resignDate: null,
      contract: "full_time",
      dailyHours: "8",
      monthlyRest: 4,
      confidentiality: 2,
      note: "",
    },
    {
      id: "e8",
      no: "E1008",
      name: "周杰",
      gender: "male",
      deptId: "d9",
      positionId: "p6",
      costId: "cc2",
      managerId: "e4",
      status: "probation",
      hireDate: "2025-09-01",
      resignDate: null,
      contract: "full_time",
      dailyHours: "8",
      monthlyRest: 4,
      confidentiality: 1,
      note: "试用期",
    },
    {
      id: "e9",
      no: "E1009",
      name: "孙梅",
      gender: "female",
      deptId: "d9",
      positionId: "p6",
      costId: "cc2",
      managerId: "e4",
      status: "resigned",
      hireDate: "2019-11-05",
      resignDate: "2026-08-31",
      contract: "full_time",
      dailyHours: "8",
      monthlyRest: 4,
      confidentiality: 2,
      note: "离职，档案保留",
    },
    {
      id: "e10",
      no: "E1010",
      name: "吴刚",
      gender: "male",
      deptId: "d9",
      positionId: "p6",
      costId: null,
      managerId: "e4",
      status: "active",
      hireDate: "2022-05-18",
      resignDate: null,
      contract: "full_time",
      dailyHours: "8",
      monthlyRest: 4,
      confidentiality: 1,
      note: "成本中心未分配",
    },
    {
      id: "e11",
      no: "E1011",
      name: "郑爽",
      gender: "female",
      deptId: "d2",
      positionId: "p1",
      costId: "cc3",
      managerId: "e2",
      status: "active",
      hireDate: "2023-08-01",
      resignDate: null,
      contract: "part_time",
      dailyHours: "4",
      monthlyRest: 8,
      confidentiality: 1,
      note: "兼职",
    },
    {
      id: "e12",
      no: "E1012",
      name: "冯涛",
      gender: "male",
      deptId: "d3",
      positionId: "p6",
      costId: "cc1",
      managerId: "e3",
      status: "active",
      hireDate: "2020-12-01",
      resignDate: null,
      contract: "full_time",
      dailyHours: "8",
      monthlyRest: 4,
      confidentiality: 2,
      note: "",
    },
    {
      id: "e13",
      no: "E2001",
      name: "林峰",
      gender: "male",
      deptId: "d6",
      positionId: "p8",
      costId: "cc5",
      managerId: null,
      status: "active",
      hireDate: "2018-01-10",
      resignDate: null,
      contract: "full_time",
      dailyHours: "8",
      monthlyRest: 8,
      confidentiality: 4,
      note: "物流负责人",
    },
    {
      id: "e14",
      no: "E2002",
      name: "何静",
      gender: "female",
      deptId: "d7",
      positionId: "p9",
      costId: "cc6",
      managerId: "e13",
      status: "active",
      hireDate: "2021-06-01",
      resignDate: null,
      contract: "full_time",
      dailyHours: "8",
      monthlyRest: 8,
      confidentiality: 1,
      note: "",
    },
    {
      id: "e15",
      no: "E2003",
      name: "高远",
      gender: "male",
      deptId: "d6",
      positionId: "p8",
      costId: "cc5",
      managerId: "e13",
      status: "active",
      hireDate: "2022-10-01",
      resignDate: null,
      contract: "full_time",
      dailyHours: "8",
      monthlyRest: 8,
      confidentiality: 2,
      note: "",
    },
  ];

  /* ================================================================ state */

  const params = new URLSearchParams(window.location.search);
  const requestedVariant = (params.get("variant") || "A").toUpperCase();

  const state = {
    variant: ["A", "B", "C"].includes(requestedVariant)
      ? requestedVariant
      : "A",
    theme: params.get("theme") === "dark" ? "dark" : "light",
    companyId: companies.some((c) => c.id === params.get("company"))
      ? params.get("company")
      : "c1",
    aScreen: "employees",
    cScreen: "employees",
    cOrgTab: "departments",
    aDeptId: "d3",
    aDeptSearch: "",
    aEmpDeptId: "all",
    aEmpSearch: "",
    aEmpStatus: "active",
    aEmpSub: true,
    aCostId: "cc1",
    aCostSearch: "",
    aPosSearch: "",
    aPosStatus: "all",
    bTree: "dept",
    bNodeId: "d3",
    bTab: "overview",
    bView: "detail",
    bEmployeeId: null,
    bTreeSearch: "",
    bEmpSearch: "",
    bEmpStatus: "active",
    bEmpSub: true,
    cDeptId: "d3",
    cDeptSearch: "",
    cEmpDept: "all",
    cEmpSearch: "",
    cEmpStatus: "active",
    cEmpSub: true,
    cPosSearch: "",
    cCostSearch: "",
    cExpandedCosts: new Set(["cc1", "cc3", "cc4", "cc5"]),
    expandedDepts: new Set(["d1", "d3", "d6"]),
    expandedCosts: new Set(["cc1", "cc3", "cc5"]),
    companyMenuOpen: false,
    preview: "normal",
    overlay: null,
    form: null,
    toast: null,
  };

  const requestedScreen = params.get("screen");
  if (state.variant === "A") {
    if (
      [
        "companies",
        "departments",
        "employees",
        "positions",
        "costcenters",
      ].includes(requestedScreen)
    ) {
      state.aScreen = requestedScreen;
    }
  } else if (state.variant === "C") {
    if (
      ["employees", "organization", "costcenters", "companies"].includes(
        requestedScreen,
      )
    ) {
      state.cScreen = requestedScreen;
    }
  }

  const requestedOrgTab = params.get("org");
  if (["departments", "positions"].includes(requestedOrgTab)) {
    state.cOrgTab = requestedOrgTab;
  }

  /* ================================================================ helpers */

  const esc = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");

  const attr = (value) => esc(value);
  const money = (value) =>
    new Intl.NumberFormat("zh-CN", {
      style: "currency",
      currency: "CNY",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Number(value || 0));

  const byOrderCode = (a, b) =>
    Number(a.orderNo || 0) - Number(b.orderNo || 0) ||
    String(a.code).localeCompare(String(b.code), "zh-CN") ||
    String(a.name).localeCompare(String(b.name), "zh-CN");

  const byEmployeeNo = (a, b) =>
    String(a.no).localeCompare(String(b.no), "zh-CN") ||
    String(a.name).localeCompare(String(b.name), "zh-CN");

  const STATUS = {
    active: { label: "在职", cls: "badge-green" },
    probation: { label: "试用期", cls: "badge-blue" },
    resigned: { label: "离职", cls: "badge-gray" },
  };

  const GENDER = { male: "男", female: "女", unknown: "未说明" };
  const CONTRACT = {
    full_time: "全职",
    part_time: "兼职",
    intern: "实习",
    labor: "劳务",
  };

  function getCompany(id) {
    return companies.find((item) => item.id === id) || null;
  }

  function getDept(id) {
    return departments.find((item) => item.id === id) || null;
  }

  function getPosition(id) {
    return positions.find((item) => item.id === id) || null;
  }

  function getCost(id) {
    return costCenters.find((item) => item.id === id) || null;
  }

  function getEmployee(id) {
    return employees.find((item) => item.id === id) || null;
  }

  function deptsOfCompany(companyId) {
    return departments
      .filter((dept) => dept.companyId === companyId)
      .sort(byOrderCode);
  }

  function positionsOfCompany(companyId) {
    return positions
      .filter((position) => position.companyId === companyId)
      .sort(byOrderCode);
  }

  function costsOfCompany(companyId) {
    return costCenters
      .filter((cost) => cost.companyId === companyId)
      .sort(byOrderCode);
  }

  function employeesOfCompany(companyId) {
    const deptIds = new Set(
      deptsOfCompany(companyId).map((dept) => dept.id),
    );
    return employees
      .filter((employee) => deptIds.has(employee.deptId))
      .sort(byEmployeeNo);
  }

  function deptChildren(companyId, parentId) {
    return deptsOfCompany(companyId)
      .filter((dept) => dept.parentId === parentId)
      .sort(byOrderCode);
  }

  function costChildren(companyId, parentId) {
    return costsOfCompany(companyId)
      .filter((cost) => cost.parentId === parentId)
      .sort(byOrderCode);
  }

  function deptDescendants(deptId) {
    const result = [];
    const stack = [deptId];
    while (stack.length) {
      const current = stack.pop();
      for (const child of departments) {
        if (child.parentId === current) {
          result.push(child.id);
          stack.push(child.id);
        }
      }
    }
    return result;
  }

  function costDescendants(costId) {
    const result = [];
    const stack = [costId];
    while (stack.length) {
      const current = stack.pop();
      for (const child of costCenters) {
        if (child.parentId === current) {
          result.push(child.id);
          stack.push(child.id);
        }
      }
    }
    return result;
  }

  function deptPath(id) {
    const path = [];
    let current = getDept(id);
    const seen = new Set();
    while (current && !seen.has(current.id)) {
      seen.add(current.id);
      path.unshift(current);
      current = current.parentId ? getDept(current.parentId) : null;
    }
    return path;
  }

  function costPath(id) {
    const path = [];
    let current = getCost(id);
    const seen = new Set();
    while (current && !seen.has(current.id)) {
      seen.add(current.id);
      path.unshift(current);
      current = current.parentId ? getCost(current.parentId) : null;
    }
    return path;
  }

  function deptPathLabel(id, separator = " / ") {
    return deptPath(id)
      .map((dept) => dept.name)
      .join(separator);
  }

  function costPathLabel(id, separator = " / ") {
    return costPath(id)
      .map((cost) => cost.name)
      .join(separator);
  }

  function isDescendantDept(candidateId, ancestorId) {
    return deptDescendants(ancestorId).includes(candidateId);
  }

  function isDescendantCost(candidateId, ancestorId) {
    return costDescendants(ancestorId).includes(candidateId);
  }

  function employeesInDept(deptId, includeDesc, includeResigned) {
    const ids = new Set([
      deptId,
      ...(includeDesc ? deptDescendants(deptId) : []),
    ]);
    return employees.filter(
      (employee) =>
        ids.has(employee.deptId) &&
        (includeResigned || employee.status !== "resigned"),
    );
  }

  function employeesInCost(costId, includeDesc, includeResigned) {
    const ids = new Set([
      costId,
      ...(includeDesc ? costDescendants(costId) : []),
    ]);
    return employees.filter(
      (employee) =>
        ids.has(employee.costId) &&
        (includeResigned || employee.status !== "resigned"),
    );
  }

  function unassignedEmployees(companyId, includeResigned = true) {
    return employeesOfCompany(companyId).filter(
      (employee) =>
        !employee.costId &&
        (includeResigned || employee.status !== "resigned"),
    );
  }

  function activeEmployeeCount(companyId) {
    return employeesOfCompany(companyId).filter(
      (employee) => employee.status !== "resigned",
    ).length;
  }

  function employeeCountLabel(companyId) {
    const all = employeesOfCompany(companyId);
    const active = all.filter((employee) => employee.status !== "resigned");
    return `${active.length} 人在职/试用期，${all.length - active.length} 人离职`;
  }

  function positionEmployeeCount(positionId, includeResigned = true) {
    return employees.filter(
      (employee) =>
        employee.positionId === positionId &&
        (includeResigned || employee.status !== "resigned"),
    ).length;
  }

  function costEmployeeCount(costId, includeDesc = false, includeResigned = false) {
    return employeesInCost(costId, includeDesc, includeResigned).length;
  }

  function statusBadge(status) {
    const info = STATUS[status] || { label: status, cls: "badge-gray" };
    return `<span class="badge ${info.cls} badge-dot">${info.label}</span>`;
  }

  function activeBadge(active) {
    return active
      ? '<span class="badge badge-green badge-dot">启用</span>'
      : '<span class="badge badge-gray">已停用</span>';
  }

  function statusOptionsForEmployee(mode, currentStatus) {
    if (mode === "create") {
      return [
        { value: "active", label: "在职" },
        { value: "probation", label: "试用期" },
      ];
    }
    if (currentStatus === "active") {
      return [
        { value: "active", label: "在职" },
        { value: "resigned", label: "离职" },
      ];
    }
    if (currentStatus === "probation") {
      return [
        { value: "probation", label: "试用期" },
        { value: "active", label: "在职" },
        { value: "resigned", label: "离职" },
      ];
    }
    return [{ value: "resigned", label: "离职" }];
  }

  function deptSelectOptions(companyId, currentId) {
    return deptsOfCompany(companyId).map((dept) => ({
      value: dept.id,
      label: `${dept.code} · ${dept.name}${dept.active ? "" : "（已停用）"}`,
      disabled: !dept.active && dept.id !== currentId,
    }));
  }

  function positionSelectOptions(companyId, currentId) {
    return positionsOfCompany(companyId).map((position) => ({
      value: position.id,
      label: `${position.code} · ${position.name}${
        position.active ? "" : "（已停用）"
      }`,
      disabled: !position.active && position.id !== currentId,
    }));
  }

  function costSelectOptions(companyId, currentId) {
    return [
      { value: "", label: "未分配" },
      ...costsOfCompany(companyId).map((cost) => ({
        value: cost.id,
        label: `${cost.code} · ${cost.name}${
          cost.active ? "" : "（已停用）"
        }`,
        disabled: !cost.active && cost.id !== currentId,
      })),
    ];
  }

  function managerOptions(companyId, currentManagerId) {
    return [
      { value: "", label: "未指定" },
      ...employeesOfCompany(companyId)
        .filter(
          (employee) =>
            employee.status !== "resigned" ||
            employee.id === currentManagerId,
        )
        .map((employee) => ({
          value: employee.id,
          label: `${employee.name}（${employee.no}）${
            employee.status === "resigned" ? " · 已离职" : ""
          }`,
        })),
    ];
  }

  function managerCycle(employeeId, managerId) {
    if (!employeeId || !managerId) return false;
    if (employeeId === managerId) return true;
    let current = getEmployee(managerId);
    const seen = new Set();
    while (current && current.managerId && !seen.has(current.id)) {
      seen.add(current.id);
      if (current.managerId === employeeId) return true;
      current = getEmployee(current.managerId);
    }
    return false;
  }

  function employeeManagerOptions(companyId, employeeId, currentManagerId) {
    return [
      { value: "", label: "无直属上级" },
      ...employeesOfCompany(companyId)
        .filter((employee) => employee.id !== employeeId)
        .map((employee) => {
          const inactive =
            employee.status === "resigned" &&
            employee.id !== currentManagerId;
          const cycle = managerCycle(employeeId, employee.id);
          const disabled = inactive || cycle;
          return {
            value: employee.id,
            label: `${employee.name}（${employee.no}）${
              employee.status === "resigned" ? " · 已离职" : ""
            }${cycle ? " · 会成环" : inactive ? " · 不可选" : ""}`,
            disabled,
          };
        }),
    ];
  }

  function deptParentOptions(companyId, deptId, currentParentId) {
    const excluded = deptId
      ? new Set([deptId, ...deptDescendants(deptId)])
      : new Set();
    return [
      { value: "", label: "无（顶层部门）" },
      ...deptsOfCompany(companyId).map((dept) => {
        const blocked = excluded.has(dept.id);
        const inactiveBlocked =
          !dept.active && dept.id !== currentParentId;
        return {
          value: dept.id,
          label: `${dept.code} · ${dept.name}${
            blocked
              ? "（自身或下级，不可选）"
              : !dept.active
                ? "（已停用）"
                : ""
          }`,
          disabled: blocked || inactiveBlocked,
        };
      }),
    ];
  }

  function costParentOptions(companyId, costId, currentParentId) {
    const excluded = costId
      ? new Set([costId, ...costDescendants(costId)])
      : new Set();
    return [
      { value: "", label: "无（顶层成本中心）" },
      ...costsOfCompany(companyId).map((cost) => {
        const blocked = excluded.has(cost.id);
        const inactiveBlocked =
          !cost.active && cost.id !== currentParentId;
        return {
          value: cost.id,
          label: `${cost.code} · ${cost.name}${
            blocked
              ? "（自身或下级，不可选）"
              : !cost.active
                ? "（已停用）"
                : ""
          }`,
          disabled: blocked || inactiveBlocked,
        };
      }),
    ];
  }

  function flatDeptOptions(companyId) {
    const result = [];
    const walk = (parentId, depth) => {
      deptChildren(companyId, parentId).forEach((dept) => {
        result.push({
          value: dept.id,
          label: `${"　".repeat(depth)}${dept.name}${
            dept.active ? "" : "（已停用）"
          }`,
        });
        walk(dept.id, depth + 1);
      });
    };
    walk(null, 0);
    return result;
  }

  function inferCompanyFromDept(deptId) {
    const dept = getDept(deptId);
    return dept ? dept.companyId : null;
  }

  function resetCompanyScopedState() {
    const depts = deptsOfCompany(state.companyId);
    const roots = depts.filter((dept) => !dept.parentId);
    const costs = costsOfCompany(state.companyId);
    const costRoots = costs.filter((cost) => !cost.parentId);

    state.aDeptId = roots[0]?.id || null;
    state.aCostId = costRoots[0]?.id || "all";
    state.aEmpDeptId = "all";
    state.aDeptSearch = "";
    state.aCostSearch = "";
    state.aEmpSearch = "";
    state.aPosSearch = "";
    state.bTreeSearch = "";
    state.bEmpSearch = "";
    state.cDeptSearch = "";
    state.cEmpSearch = "";
    state.cPosSearch = "";
    state.cCostSearch = "";
    state.cEmpDept = "all";
    state.cDeptId = roots[0]?.id || null;
    state.bView = "detail";
    state.bTab = "overview";
    state.bEmployeeId = null;
    if (state.bTree === "dept") {
      state.bNodeId = roots[0]?.id || "all";
    } else {
      state.bNodeId = costRoots[0]?.id || "all";
    }
    state.expandedDepts = new Set(roots.map((dept) => dept.id));
    state.expandedCosts = new Set(costRoots.map((cost) => cost.id));
    state.cExpandedCosts = new Set(
      costRoots.flatMap((cost) => [cost.id, ...costDescendants(cost.id)]),
    );
  }

  function syncUrl() {
    const next = new URLSearchParams();
    next.set("variant", state.variant);
    next.set("company", state.companyId);
    next.set("theme", state.theme);
    if (state.variant === "A") {
      next.set("screen", state.aScreen);
    } else if (state.variant === "C") {
      next.set("screen", state.cScreen);
      if (state.cScreen === "organization") {
        next.set("org", state.cOrgTab);
      }
    } else {
      next.set("screen", "hub");
    }
    window.history.replaceState(
      null,
      "",
      `${window.location.pathname}?${next.toString()}`,
    );
  }

  function setState(patch, options = {}) {
    Object.assign(state, patch);
    if (options.sync !== false) syncUrl();
    render();
  }

  function showToast(message, type = "success") {
    state.toast = { message, type };
    render();
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
      state.toast = null;
      render();
    }, 2400);
  }

  function rerenderPreservingFocus() {
    const active = document.activeElement;
    const key = active?.getAttribute?.("data-input");
    const start = active?.selectionStart;
    const end = active?.selectionEnd;
    render();
    if (!key) return;
    const next = document.querySelector(`[data-input="${key}"]`);
    if (!next) return;
    next.focus();
    if (typeof start === "number" && next.setSelectionRange) {
      try {
        next.setSelectionRange(start, end);
      } catch {
        /* ignore */
      }
    }
  }

  /* ================================================================ root */

  function applyTheme() {
    document.documentElement.classList.toggle("dark", state.theme === "dark");
  }

  function render() {
    applyTheme();
    const app = document.getElementById("app");
    if (!app) return;

    if (state.variant === "A") {
      app.innerHTML = renderA();
    } else if (state.variant === "B") {
      app.innerHTML = renderB();
    } else {
      app.innerHTML = renderC();
    }

    renderPrototypeBar();
    renderOverlayRoot();
  }

  function renderPrototypeBar() {
    const bar = document.getElementById("prototype-bar");
    if (!bar) return;
    const names = {
      A: "A · 五模块独立",
      B: "B · 组织工作台",
      C: "C · 顶栏导航",
    };
    bar.innerHTML = `
      <button class="pb-btn" data-action="variant-prev" title="上一个方案（←）" aria-label="上一个方案">${icon("chevron-left")}</button>
      <span class="pb-label"><span class="pb-tag">原型</span><span class="pb-variant">${names[state.variant]}</span></span>
      <button class="pb-btn" data-action="variant-next" title="下一个方案（→）" aria-label="下一个方案">${icon("chevron-right")}</button>
      <button class="pb-btn" data-action="toggle-theme" title="切换深色 / 浅色">${icon(
        state.theme === "dark" ? "sun" : "moon",
      )} ${state.theme === "dark" ? "浅色" : "深色"}</button>
      <span class="pb-divider"></span>
      <button class="pb-btn" data-action="open-flow">${icon("network")} 页面流程</button>
      <button class="pb-btn" data-action="open-diff">${icon("layers")} 需求差异</button>
      <span class="pb-label">状态
        <select data-select="preview" aria-label="预览状态">
          <option value="normal" ${state.preview === "normal" ? "selected" : ""}>正常</option>
          <option value="loading" ${state.preview === "loading" ? "selected" : ""}>加载中</option>
          <option value="empty" ${state.preview === "empty" ? "selected" : ""}>空数据</option>
          <option value="error" ${state.preview === "error" ? "selected" : ""}>错误</option>
        </select>
      </span>
      <button class="pb-btn" data-action="reset-prototype">${icon("refresh")} 重置</button>
    `;
  }

  /* ================================================================ shared UI */

  function renderLogo() {
    return `<div class="logo">
      <div class="logo-mark">A</div>
      <div class="logo-text"><strong>AnySys HR</strong><span class="sub">基础管理原型</span></div>
    </div>`;
  }

  function renderUser() {
    return `<div class="user-row">
      <div class="avatar">管</div>
      <div class="user-meta"><strong>管理员</strong><span class="sub">admin@example.com</span></div>
    </div>`;
  }

  function renderSidebarA() {
    const items = [
      { key: "dashboard", icon: "dashboard", label: "仪表盘", stub: true },
      { key: "companies", icon: "building", label: "公司" },
      { key: "departments", icon: "network", label: "部门" },
      { key: "employees", icon: "users", label: "员工" },
      { key: "positions", icon: "briefcase", label: "岗位" },
      { key: "costcenters", icon: "wallet", label: "成本中心" },
    ];

    return `<aside class="sidebar">
      ${renderLogo()}
      <nav class="nav" aria-label="主导航">
        ${
          items[0].stub
            ? `<button class="nav-item" data-action="stub" data-label="仪表盘">${icon(
                items[0].icon,
              )}<span>${items[0].label}</span></button>`
            : ""
        }
        <div class="nav-label">基础管理</div>
        ${items
          .slice(1)
          .map(
            (item) => `<button class="nav-item ${
              state.aScreen === item.key ? "active" : ""
            }" data-action="nav-a" data-screen="${item.key}">${icon(
              item.icon,
            )}<span>${item.label}</span></button>`,
          )
          .join("")}
        <div class="nav-label">系统</div>
        <button class="nav-item" data-action="stub" data-label="管理后台">${icon(
          "settings",
        )}<span>管理后台</span><span class="nav-badge">保留</span></button>
      </nav>
      <div class="sidebar-footer">${renderUser()}</div>
    </aside>`;
  }

  function renderSidebarB() {
    return `<aside class="sidebar">
      ${renderLogo()}
      <nav class="nav" aria-label="主导航">
        <button class="nav-item" data-action="stub" data-label="仪表盘">${icon(
          "dashboard",
        )}<span>仪表盘</span></button>
        <button class="nav-item active" data-action="b-home">${icon(
          "layers",
        )}<span>基础管理</span></button>
        <div class="nav-label">系统</div>
        <button class="nav-item" data-action="stub" data-label="管理后台">${icon(
          "settings",
        )}<span>管理后台</span><span class="nav-badge">保留</span></button>
      </nav>
      <div class="sidebar-footer">${renderUser()}</div>
    </aside>`;
  }

  function renderTopbar(breadcrumbHtml, extra = "") {
    return `<header class="topbar">
      <div class="breadcrumb">${breadcrumbHtml}</div>
      <div class="topbar-right">${extra}${renderCompanySwitch()}<div class="avatar" title="管理员">管</div></div>
    </header>`;
  }

  function renderCompanySwitch() {
    const company = getCompany(state.companyId) || companies[0];
    return `<div class="company-switch-wrap">
      <button class="company-switch" data-action="toggle-company-menu" aria-haspopup="menu" aria-expanded="${
        state.companyMenuOpen ? "true" : "false"
      }">
        ${icon("building")}
        <span>${esc(company.name)}</span>
        <span class="code">${esc(company.code)}</span>
        ${icon("chevron-down")}
      </button>
      ${
        state.companyMenuOpen
          ? `<div class="company-menu" role="menu">
              <div class="company-menu-head">切换当前公司</div>
              ${companies
                .map(
                  (item) => `<button class="company-menu-item ${
                    item.id === state.companyId ? "active" : ""
                  }" data-action="select-company" data-company="${item.id}" role="menuitem">
                    <span class="company-menu-dot"></span>
                    <span class="company-menu-text">
                      <strong>${esc(item.name)}</strong>
                      <span class="company-menu-meta">${esc(item.code)} · ${
                        deptsOfCompany(item.id).length
                      } 个部门 · ${activeEmployeeCount(item.id)} 名在职/试用期</span>
                    </span>
                    ${item.id === state.companyId ? icon("check") : ""}
                  </button>`,
                )
                .join("")}
              <div class="company-menu-foot">
                <button class="btn btn-ghost btn-sm" data-action="manage-companies">${icon(
                  "settings",
                )} 管理公司</button>
              </div>
            </div>`
          : ""
      }
    </div>`;
  }

  function pageHead(title, sub, actions = "") {
    return `<div class="page-head">
      <div><h1 class="page-title">${title}</h1><p class="page-sub">${sub}</p></div>
      <div class="actions">${actions}</div>
    </div>`;
  }

  function renderCompanyHint() {
    const company = getCompany(state.companyId);
    return `<div class="notice info">${icon(
      "info",
    )}<div>当前公司：<strong>${esc(company.name)}</strong>（${esc(
      company.code,
    )}）。切换公司后，部门、岗位、员工、成本中心页面只显示该公司数据。</div></div>`;
  }

  function renderPreview(kind, options = {}) {
    if (state.preview === "normal") return null;
    if (state.preview === "loading") {
      return `<div class="skeleton-page">
        <div class="skeleton-cards">
          ${Array.from({ length: 4 })
            .map(() => '<div class="skeleton-card"></div>')
            .join("")}
        </div>
        ${Array.from({ length: 6 })
          .map(
            () =>
              '<div class="skeleton w-70"></div><div class="skeleton w-50"></div><div class="skeleton w-30"></div>',
          )
          .join("")}
      </div>`;
    }
    if (state.preview === "error") {
      return `<div class="error-state">
        <div class="empty-icon">${icon("alert")}</div>
        <h3>数据加载失败</h3>
        <p>${esc(options.error || "网络异常，请稍后重试。")}</p>
        <button class="btn btn-outline" data-action="retry-preview">${icon(
          "refresh",
        )} 重试</button>
      </div>`;
    }
    return `<div class="empty">
      <div class="empty-icon">${icon(options.icon || "search")}</div>
      <h3>${esc(options.title || "暂无数据")}</h3>
      <p>${esc(options.message || "当前条件下没有可展示的数据。")}</p>
      ${options.action || ""}
    </div>`;
  }

  function selectHtml(name, value, options, extra = "") {
    return `<select class="select" data-select="${name}" ${extra}>${options
      .map(
        (option) =>
          `<option value="${attr(option.value)}" ${
            String(option.value) === String(value ?? "") ? "selected" : ""
          } ${option.disabled ? "disabled" : ""}>${esc(option.label)}</option>`,
      )
      .join("")}</select>`;
  }

  function switchHtml(name, checked, options = {}) {
    return `<label class="switch">
      <input type="checkbox" role="switch" data-input="form:${name}" ${
        checked ? "checked" : ""
      } ${options.disabled ? "disabled" : ""} aria-label="启用状态" />
      <span class="switch-track" aria-hidden="true"><span class="switch-thumb"></span></span>
      <span class="switch-label">${checked ? "启用" : "停用"}</span>
    </label>`;
  }

  function inputHtml(name, value, options = {}) {
    const type = options.type || "text";
    return `<input class="input" type="${type}" data-input="form:${name}" value="${attr(
      value ?? "",
    )}" placeholder="${attr(options.placeholder || "")}" ${
      options.disabled ? "disabled" : ""
    } ${options.required ? "required" : ""} ${
      options.min !== undefined ? `min="${options.min}"` : ""
    } ${options.max !== undefined ? `max="${options.max}"` : ""} ${
      options.step !== undefined ? `step="${options.step}"` : ""
    } />`;
  }

  function textareaHtml(name, value, options = {}) {
    return `<textarea class="input" data-input="form:${name}" placeholder="${attr(
      options.placeholder || "",
    )}" ${options.disabled ? "disabled" : ""}>${esc(value ?? "")}</textarea>`;
  }

  function fieldHtml(label, control, options = {}) {
    return `<div class="field ${options.full ? "full" : ""}">
      <label>${label}${options.required ? '<span class="req">*</span>' : ""}</label>
      ${control}
      ${options.hint ? `<span class="hint">${options.hint}</span>` : ""}
      ${
        options.error
          ? `<span class="error-text" data-error-for="${options.errorName}">${esc(
              options.error,
            )}</span>`
          : ""
      }
    </div>`;
  }

  function renderTableFooter(total, pageLabel = "第 1 / 1 页") {
    return `<div class="table-foot">
      <span>共 ${total} 条</span>
      <div class="pagination" aria-label="分页（示意）">
        <button disabled>‹</button>
        <button class="active">1</button>
        <button disabled>›</button>
        <span style="margin-left:6px">${pageLabel}</span>
      </div>
    </div>`;
  }

  function renderEmployeeTable(list, options = {}) {
    if (!list.length) {
      return `<div class="empty">
        <div class="empty-icon">${icon("users")}</div>
        <h3>${options.emptyTitle || "没有符合条件的员工"}</h3>
        <p>${options.emptyMessage || "调整搜索或筛选条件后再试。"}</p>
        <button class="btn btn-outline" data-action="${options.emptyAction || "clear-emp-filters"}">${
          options.emptyActionLabel || "清除筛选"
        }</button>
      </div>`;
    }

    return `<div class="table-wrap">
      <table class="table">
        <thead><tr>
          <th>工号</th><th>姓名</th><th>部门</th><th>岗位</th><th>成本中心</th><th>状态</th><th>入职日期</th><th></th>
        </tr></thead>
        <tbody>
          ${list
            .map((employee) => {
              const dept = getDept(employee.deptId);
              const position = getPosition(employee.positionId);
              const cost = getCost(employee.costId);
              const manager = getEmployee(employee.managerId);
              return `<tr>
                <td><span class="code">${esc(employee.no)}</span></td>
                <td>
                  <button class="name" style="border:0;background:none;padding:0;text-align:left" data-action="${options.viewAction || "view-employee"}" data-id="${employee.id}">${esc(
                    employee.name,
                  )}</button>
                  <div class="sub">${GENDER[employee.gender] || "未说明"}${
                    manager ? ` · 上级 ${esc(manager.name)}` : ""
                  }</div>
                </td>
                <td>${dept ? esc(dept.name) : "—"}<div class="sub">${dept ? esc(dept.code) : ""}</div></td>
                <td>${position ? esc(position.name) : "—"}<div class="sub">${position ? esc(position.code) : ""}</div></td>
                <td>${
                  cost
                    ? `${esc(cost.name)}<div class="sub">${esc(cost.code)}</div>`
                    : '<span class="badge badge-gray">未分配</span>'
                }</td>
                <td>${statusBadge(employee.status)}</td>
                <td class="nowrap">${esc(employee.hireDate)}</td>
                <td class="td-actions">
                  <div class="row-tight" style="justify-content:flex-end">
                    <button class="btn btn-ghost btn-sm" data-action="${options.editAction || "edit-employee"}" data-id="${employee.id}">编辑</button>
                    ${
                      employee.status !== "resigned"
                        ? `<button class="btn btn-ghost btn-sm" data-action="${options.resignAction || "resign-employee"}" data-id="${employee.id}">离职</button>`
                        : ""
                    }
                  </div>
                </td>
              </tr>`;
            })
            .join("")}
        </tbody>
      </table>
    </div>
    ${renderTableFooter(list.length)}`;
  }

  function renderDeptTree(companyId, options = {}) {
    const query = (options.query || "").trim().toLowerCase();
    const selected = options.selectedId;
    const action = options.action || "select-dept";
    const counts = options.counts !== false;
    const showAll = options.showAll !== false;

    const matches = (dept) =>
      !query ||
      dept.name.toLowerCase().includes(query) ||
      dept.code.toLowerCase().includes(query) ||
      (dept.note || "").toLowerCase().includes(query);

    const subtreeMatches = (dept) =>
      matches(dept) ||
      deptChildren(companyId, dept.id).some((child) => subtreeMatches(child));

    const renderNode = (dept) => {
      const children = deptChildren(companyId, dept.id).filter(subtreeMatches);
      const expanded =
        query.length > 0 || state.expandedDepts.has(dept.id);
      const activeCount = employeesInDept(dept.id, true, false).length;
      return `<div class="tree-node">
        <div class="tree-row ${selected === dept.id ? "active" : ""}" data-action="${action}" data-id="${dept.id}">
          ${
            children.length
              ? `<button class="twisty" data-action="toggle-dept-expand" data-id="${
                  dept.id
                }" aria-label="${expanded ? "收起" : "展开"}">${icon(
                  expanded ? "chevron-down" : "chevron-right",
                )}</button>`
              : '<span class="twisty"></span>'
          }
          <span class="label">${esc(dept.name)}${
            dept.active ? "" : '<span class="tree-inactive">停用</span>'
          }</span>
          ${counts ? `<span class="count">${activeCount}</span>` : ""}
        </div>
        ${
          children.length && expanded
            ? `<div class="tree-children">${children
                .map(renderNode)
                .join("")}</div>`
            : ""
        }
      </div>`;
    };

    const roots = deptChildren(companyId, null).filter(subtreeMatches);
    if (!roots.length) {
      return `<div class="tree-empty">${query ? "没有匹配的部门" : "当前公司还没有部门"}</div>`;
    }

    return `<div class="tree">
      ${
        showAll
          ? `<div class="tree-row ${
              selected === "all" ? "active" : ""
            }" data-action="${action}" data-id="all">
              <span class="twisty"></span>
              <span class="label">全部部门</span>
              ${counts ? `<span class="count">${activeEmployeeCount(companyId)}</span>` : ""}
            </div>`
          : ""
      }
      ${roots.map(renderNode).join("")}
    </div>`;
  }

  function renderCostTree(companyId, options = {}) {
    const query = (options.query || "").trim().toLowerCase();
    const selected = options.selectedId;
    const action = options.action || "select-cost";
    const counts = options.counts !== false;

    const matches = (cost) =>
      !query ||
      cost.name.toLowerCase().includes(query) ||
      cost.code.toLowerCase().includes(query) ||
      (cost.note || "").toLowerCase().includes(query);

    const subtreeMatches = (cost) =>
      matches(cost) ||
      costChildren(companyId, cost.id).some((child) => subtreeMatches(child));

    const renderNode = (cost) => {
      const children = costChildren(companyId, cost.id).filter(subtreeMatches);
      const expanded =
        query.length > 0 || state.expandedCosts.has(cost.id);
      const activeCount = employeesInCost(cost.id, true, false).length;
      return `<div class="tree-node">
        <div class="tree-row ${selected === cost.id ? "active" : ""}" data-action="${action}" data-id="${cost.id}">
          ${
            children.length
              ? `<button class="twisty" data-action="toggle-cost-expand" data-id="${
                  cost.id
                }" aria-label="${expanded ? "收起" : "展开"}">${icon(
                  expanded ? "chevron-down" : "chevron-right",
                )}</button>`
              : '<span class="twisty"></span>'
          }
          <span class="label">${esc(cost.name)}${
            cost.active ? "" : '<span class="tree-inactive">停用</span>'
          }</span>
          ${counts ? `<span class="count">${activeCount}</span>` : ""}
        </div>
        ${
          children.length && expanded
            ? `<div class="tree-children">${children
                .map(renderNode)
                .join("")}</div>`
            : ""
        }
      </div>`;
    };

    const roots = costChildren(companyId, null).filter(subtreeMatches);
    if (!roots.length && !query) {
      return `<div class="tree">
        <div class="tree-row ${
          selected === "all" ? "active" : ""
        }" data-action="${action}" data-id="all">
          <span class="twisty"></span><span class="label">全部成本中心</span>
          <span class="count">${activeEmployeeCount(companyId)}</span>
        </div>
      </div>`;
    }
    if (!roots.length) {
      return `<div class="tree-empty">没有匹配的成本中心</div>`;
    }

    const unassigned = unassignedEmployees(companyId, false).length;

    return `<div class="tree">
      <div class="tree-row ${selected === "all" ? "active" : ""}" data-action="${action}" data-id="all">
        <span class="twisty"></span>
        <span class="label">全部成本中心</span>
        ${counts ? `<span class="count">${activeEmployeeCount(companyId)}</span>` : ""}
      </div>
      ${roots.map(renderNode).join("")}
      <div class="tree-unassigned">
        <div class="tree-row ${selected === "unassigned" ? "active" : ""}" data-action="${action}" data-id="unassigned">
          <span class="twisty"></span>
          <span class="label">未分配</span>
          ${counts ? `<span class="count">${unassigned}</span>` : ""}
        </div>
      </div>
    </div>`;
  }

  function renderCompanyTable(options = {}) {
    return `<div class="table-wrap">
      <table class="table">
        <thead><tr><th>编码</th><th>公司名称</th><th>部门</th><th>岗位</th><th>员工</th><th>状态</th><th></th></tr></thead>
        <tbody>
          ${companies
            .map((company) => {
              const deptCount = deptsOfCompany(company.id).length;
              const positionCount = positionsOfCompany(company.id).length;
              const allEmployees = employeesOfCompany(company.id);
              const activeCount = allEmployees.filter(
                (employee) => employee.status !== "resigned",
              ).length;
              return `<tr class="${
                company.id === state.companyId ? "is-current" : ""
              }">
                <td><span class="code">${esc(company.code)}</span></td>
                <td>
                  <div class="name">${esc(company.name)} ${
                    company.id === state.companyId
                      ? '<span class="badge badge-blue">当前公司</span>'
                      : ""
                  }</div>
                  <div class="sub">${esc(company.note || "—")}</div>
                </td>
                <td>${deptCount}</td>
                <td>${positionCount}</td>
                <td>${activeCount} <span class="sub">/ ${allEmployees.length} 人</span></td>
                <td>${activeBadge(company.active)}</td>
                <td class="td-actions">
                  ${
                    company.id !== state.companyId
                      ? `<button class="btn btn-ghost btn-sm" data-action="switch-company" data-company="${company.id}">切换</button>`
                      : ""
                  }
                  <button class="btn btn-ghost btn-sm" data-action="edit-company" data-id="${company.id}">编辑</button>
                  <button class="btn btn-ghost btn-sm danger-text" data-action="delete-company" data-id="${company.id}">删除</button>
                </td>
              </tr>`;
            })
            .join("")}
        </tbody>
      </table>
    </div>
    ${renderTableFooter(companies.length, "公司之间扁平，不设上下级")}`;
  }

  function renderPositionTable(companyId, options = {}) {
    const list = positionsOfCompany(companyId).filter((position) => {
      if (options.query) {
        const q = options.query.toLowerCase();
        if (
          !position.name.toLowerCase().includes(q) &&
          !position.code.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      if (options.status === "active" && !position.active) return false;
      if (options.status === "inactive" && position.active) return false;
      if (options.deptId && position.deptId !== options.deptId) return false;
      return true;
    });

    if (!list.length) {
      return `<div class="empty">
        <div class="empty-icon">${icon("briefcase")}</div>
        <h3>${options.emptyTitle || "还没有岗位"}</h3>
        <p>${options.emptyMessage || "员工必须绑定岗位，建议先维护岗位档案。岗位是公司级可复用档案，默认部门仅用于带出。"}</p>
        <button class="btn btn-primary" data-action="add-position" ${options.deptId ? `data-dept="${options.deptId}"` : ""}>${icon(
          "plus",
        )} 新建岗位</button>
      </div>`;
    }

    return `<div class="table-wrap">
      <table class="table">
        <thead><tr><th>编码</th><th>岗位名称</th><th>默认部门</th><th>员工数</th><th>状态</th><th></th></tr></thead>
        <tbody>
          ${list
            .map((position) => {
              const dept = getDept(position.deptId);
              const activeCount = positionEmployeeCount(position.id, false);
              const allCount = positionEmployeeCount(position.id, true);
              return `<tr>
                <td><span class="code">${esc(position.code)}</span></td>
                <td><div class="name">${esc(position.name)}</div>${
                  position.note ? `<div class="sub">${esc(position.note)}</div>` : ""
                }</td>
                <td>${
                  dept
                    ? `${esc(dept.name)}<div class="sub">${esc(dept.code)}</div>`
                    : '<span class="sub">未设默认部门</span>'
                }</td>
                <td>${activeCount} <span class="sub">/ ${allCount} 人</span></td>
                <td>${activeBadge(position.active)}</td>
                <td class="td-actions">
                  <button class="btn btn-ghost btn-sm" data-action="edit-position" data-id="${position.id}">编辑</button>
                  <button class="btn btn-ghost btn-sm danger-text" data-action="delete-position" data-id="${position.id}">删除</button>
                </td>
              </tr>`;
            })
            .join("")}
        </tbody>
      </table>
    </div>
    ${renderTableFooter(list.length)}`;
  }

  /* ================================================================ variant A */

  function renderA() {
    const labels = {
      companies: "公司",
      departments: "部门",
      employees: "员工",
      positions: "岗位",
      costcenters: "成本中心",
    };
    const screens = {
      companies: screenACompanies,
      departments: screenADepartments,
      employees: screenAEmployees,
      positions: screenAPositions,
      costcenters: screenACostCenters,
    };
    const screen = screens[state.aScreen] || screens.employees;
    return `<div class="app">
      ${renderSidebarA()}
      <div class="main">
        ${renderTopbar(
          `基础管理 ${icon("chevron-right")} <strong>${
            labels[state.aScreen] || "员工"
          }</strong>`,
        )}
        <div class="content">${screen()}</div>
      </div>
    </div>`;
  }

  function screenACompanies() {
    const head = pageHead(
      "公司",
      "管理所有公司档案；公司之间扁平，不设上下级。删除公司前必须先清空其部门、岗位、成本中心与员工。",
      `<button class="btn btn-primary" data-action="add-company">${icon(
        "plus",
      )} 新增公司</button>`,
    );

    if (state.preview !== "normal") {
      return `${head}${renderCompanyHint()}${renderPreview("companies", {
        icon: "building",
        title: "还没有公司",
        message: "创建第一家公司后，才能维护部门、岗位、员工与成本中心。",
        action: `<button class="btn btn-primary" data-action="add-company">${icon(
          "plus",
        )} 新增公司</button>`,
      })}`;
    }

    return `${head}${renderCompanyHint()}
      <div class="panel">${renderCompanyTable()}</div>`;
  }

  function screenADepartments() {
    const depts = deptsOfCompany(state.companyId);
    if (
      state.aDeptId !== null &&
      (!getDept(state.aDeptId) || getDept(state.aDeptId).companyId !== state.companyId)
    ) {
      state.aDeptId = deptChildren(state.companyId, null)[0]?.id || null;
    }
    if (!state.aDeptId && depts.length) {
      state.aDeptId = deptChildren(state.companyId, null)[0]?.id || null;
    }
    const selected = getDept(state.aDeptId);
    const company = getCompany(state.companyId);

    const head = pageHead(
      "部门",
      `${esc(company.name)} · 行政架构，支持任意多级；删除前需清空下级部门与员工。`,
      `<button class="btn btn-primary" data-action="add-dept">${icon(
        "plus",
      )} 新增顶层部门</button>`,
    );

    const tree = `<aside class="tree-panel">
      <div class="tree-head">
        <div class="search">${icon("search")}<input class="input" data-input="a-dept-search" placeholder="搜索部门名称或编码" value="${attr(
          state.aDeptSearch,
        )}" /></div>
      </div>
      <div class="tree-body">${renderDeptTree(state.companyId, {
        selectedId: state.aDeptId,
        query: state.aDeptSearch,
        action: "a-select-dept",
      })}</div>
      <div class="tree-foot">
        <button class="btn btn-outline btn-sm" data-action="add-dept">${icon(
          "plus",
        )} 新增顶层部门</button>
      </div>
    </aside>`;

    return `${head}<div class="split">${tree}${renderADeptDetail(selected)}</div>`;
  }

  function renderADeptDetail(dept) {
    if (!dept) {
      return `<section class="detail">${renderPreview("departments", {
        icon: "network",
        title: "还没有部门",
        message: "先创建顶层部门，再逐级维护下级部门。",
        action: `<button class="btn btn-primary" data-action="add-dept">${icon(
          "plus",
        )} 新增顶层部门</button>`,
      })}</section>`;
    }

    const manager = getEmployee(dept.managerId);
    const children = deptChildren(state.companyId, dept.id);
    const activeDirect = employeesInDept(dept.id, false, false).length;
    const activeSubtree = employeesInDept(dept.id, true, false).length;
    const resignedSubtree = employeesInDept(dept.id, true, true).length - activeSubtree;
    const deptPositions = positionsOfCompany(state.companyId).filter(
      (position) => position.deptId === dept.id,
    );

    const header = `<div class="detail-head">
      <div>
        <div class="b-node-path">${deptPath(dept.id)
          .slice(0, -1)
          .map((item) => esc(item.name))
          .join(` ${icon("chevron-right")} `) || "顶层部门"}</div>
        <h2 class="detail-title">${esc(dept.name)} <span class="code">${esc(
          dept.code,
        )}</span> ${activeBadge(dept.active)}</h2>
        <div class="detail-sub">本部门在职/试用期 ${activeDirect} 人 · 含下级 ${activeSubtree} 人 · 档案共 ${
          activeSubtree + resignedSubtree
        } 人（离职 ${resignedSubtree} 人）</div>
      </div>
      <div class="actions">
        <button class="btn btn-outline btn-sm" data-action="edit-dept" data-id="${dept.id}">${icon(
          "edit",
        )} 编辑</button>
        <button class="btn btn-outline btn-sm" data-action="add-dept" data-parent="${dept.id}">${icon(
          "plus",
        )} 新增子部门</button>
        <button class="btn btn-ghost btn-sm danger-text" data-action="delete-dept" data-id="${dept.id}">${icon(
          "trash",
        )} 删除</button>
      </div>
    </div>`;

    if (state.preview !== "normal") {
      return `<section class="detail">${header}${renderPreview("departments", {
        icon: "network",
        title: "部门数据为空",
        message: "当前筛选条件下没有可展示的部门数据。",
      })}</section>`;
    }

    const info = `<div class="detail-body">
      <div class="kv-grid">
        <dl class="kv">
          <dt>上级部门</dt><dd>${dept.parentId ? esc(deptPathLabel(dept.parentId)) : "无（顶层部门）"}</dd>
          <dt>负责人</dt><dd>${
            manager
              ? `${esc(manager.name)} <span class="sub">${esc(manager.no)} · ${
                  STATUS[manager.status]?.label || manager.status
                }</span>`
              : '<span class="sub">未指定</span>'
          }</dd>
          <dt>排序</dt><dd>${dept.orderNo}</dd>
        </dl>
        <dl class="kv">
          <dt>岗位数</dt><dd>${deptPositions.length} 个（默认部门为本部门）</dd>
          <dt>状态</dt><dd>${activeBadge(dept.active)}</dd>
          <dt>备注</dt><dd>${esc(dept.note || "—")}</dd>
        </dl>
      </div>

      <div class="panel mt-16">
        <div class="card-head"><h3>下级部门</h3><button class="btn btn-outline btn-sm" data-action="add-dept" data-parent="${dept.id}">${icon(
          "plus",
        )} 新增子部门</button></div>
        ${
          children.length
            ? `<div class="table-wrap"><table class="table">
                <thead><tr><th>编码</th><th>部门名称</th><th>负责人</th><th>在职/试用期</th><th>状态</th><th></th></tr></thead>
                <tbody>${children
                  .map((child) => {
                    const childManager = getEmployee(child.managerId);
                    const childCount = employeesInDept(child.id, true, false).length;
                    return `<tr>
                      <td><span class="code">${esc(child.code)}</span></td>
                      <td><button class="name" style="border:0;background:none;padding:0" data-action="a-select-dept" data-id="${child.id}">${esc(
                        child.name,
                      )}</button></td>
                      <td>${childManager ? esc(childManager.name) : '<span class="sub">未指定</span>'}</td>
                      <td>${childCount}</td>
                      <td>${activeBadge(child.active)}</td>
                      <td class="td-actions"><button class="btn btn-ghost btn-sm" data-action="a-select-dept" data-id="${child.id}">查看</button></td>
                    </tr>`;
                  })
                  .join("")}</tbody>
              </table></div>`
            : `<div class="empty" style="padding:28px 18px"><div class="empty-icon">${icon(
                "network",
              )}</div><h3>暂无下级部门</h3><p>可以继续拆分组织，也可以保持当前层级。</p></div>`
        }
      </div>

      <div class="panel">
        <div class="card-head"><h3>默认部门为本部门的岗位</h3><button class="btn btn-outline btn-sm" data-action="add-position" data-dept="${dept.id}">${icon(
          "plus",
        )} 新增岗位</button></div>
        ${
          deptPositions.length
            ? `<div class="table-wrap"><table class="table">
                <thead><tr><th>编码</th><th>岗位</th><th>员工数</th><th>状态</th><th></th></tr></thead>
                <tbody>${deptPositions
                  .map(
                    (position) => `<tr>
                      <td><span class="code">${esc(position.code)}</span></td>
                      <td class="name">${esc(position.name)}</td>
                      <td>${positionEmployeeCount(position.id, true)}</td>
                      <td>${activeBadge(position.active)}</td>
                      <td class="td-actions"><button class="btn btn-ghost btn-sm" data-action="edit-position" data-id="${position.id}">编辑</button></td>
                    </tr>`,
                  )
                  .join("")}</tbody>
              </table></div>`
            : `<div class="empty" style="padding:28px 18px"><div class="empty-icon">${icon(
                "briefcase",
              )}</div><h3>没有默认部门为本部门的岗位</h3><p>岗位是公司级档案，其他部门的员工也可以使用这些岗位。</p></div>`
        }
      </div>
    </div>`;

    return `<section class="detail">${header}${info}</section>`;
  }

  function filteredEmployeesA() {
    let list = employeesOfCompany(state.companyId);

    if (state.aEmpDeptId !== "all") {
      const dept = getDept(state.aEmpDeptId);
      if (dept && dept.companyId === state.companyId) {
        const ids = new Set([
          dept.id,
          ...(state.aEmpSub ? deptDescendants(dept.id) : []),
        ]);
        list = list.filter((employee) => ids.has(employee.deptId));
      }
    }

    if (state.aEmpStatus === "active") {
      list = list.filter((employee) => employee.status !== "resigned");
    } else if (state.aEmpStatus === "resigned") {
      list = list.filter((employee) => employee.status === "resigned");
    }

    if (state.aEmpSearch.trim()) {
      const query = state.aEmpSearch.trim().toLowerCase();
      list = list.filter(
        (employee) =>
          employee.name.toLowerCase().includes(query) ||
          employee.no.toLowerCase().includes(query),
      );
    }

    return list.sort(byEmployeeNo);
  }

  function screenAEmployees() {
    if (
      state.aEmpDeptId !== "all" &&
      (!getDept(state.aEmpDeptId) ||
        getDept(state.aEmpDeptId).companyId !== state.companyId)
    ) {
      state.aEmpDeptId = "all";
    }
    const company = getCompany(state.companyId);
    const list = filteredEmployeesA();
    const all = employeesOfCompany(state.companyId);
    const active = all.filter((employee) => employee.status !== "resigned").length;

    const head = pageHead(
      "员工",
      `${esc(company.name)} · ${active} 人在职/试用期，${all.length - active} 人离职。列表默认显示在职与试用期；离职员工保留档案但不物理删除。`,
      `<button class="btn btn-primary" data-action="add-employee" data-dept="${
        state.aEmpDeptId !== "all" ? state.aEmpDeptId : ""
      }">${icon("plus")} 新增员工</button>`,
    );

    const toolbar = `<div class="toolbar">
      <div class="search">${icon("search")}<input class="input" data-input="a-emp-search" placeholder="搜索工号或姓名" value="${attr(
        state.aEmpSearch,
      )}" /></div>
      <select class="select" data-select="a-emp-status" aria-label="状态筛选">
        <option value="active" ${state.aEmpStatus === "active" ? "selected" : ""}>在职 + 试用期</option>
        <option value="all" ${state.aEmpStatus === "all" ? "selected" : ""}>全部状态</option>
        <option value="resigned" ${state.aEmpStatus === "resigned" ? "selected" : ""}>仅离职</option>
      </select>
      <label class="check"><input type="checkbox" data-input="a-emp-sub" ${
        state.aEmpSub ? "checked" : ""
      } /> 含下级部门</label>
      <span class="spacer"></span>
      <span class="sub">当前显示 ${list.length} 人</span>
    </div>`;

    const tree = `<aside class="tree-panel">
      <div class="tree-head">
        <div class="sub" style="padding:2px 2px 0">按部门过滤</div>
      </div>
      <div class="tree-body">${renderDeptTree(state.companyId, {
        selectedId: state.aEmpDeptId,
        action: "a-select-emp-dept",
      })}</div>
      <div class="tree-foot">
        <button class="btn btn-outline btn-sm" data-action="add-dept">${icon(
          "plus",
        )} 维护部门树</button>
      </div>
    </aside>`;

    let table;
    if (state.preview !== "normal") {
      table = renderPreview("employees", {
        icon: "users",
        title: "没有员工",
        message: "当前公司还没有员工档案。新增员工前，请先确认部门与岗位已维护。",
        action: `<button class="btn btn-primary" data-action="add-employee">${icon(
          "plus",
        )} 新增员工</button>`,
      });
    } else {
      table = renderEmployeeTable(list, {
        emptyTitle: "没有符合条件的员工",
        emptyMessage:
          state.aEmpSearch || state.aEmpStatus !== "active" || state.aEmpDeptId !== "all"
            ? "调整部门、状态或关键字后再试。"
            : "当前公司还没有员工档案。新增员工前，请先确认部门与岗位已维护。",
        emptyAction: list.length ? "clear-emp-filters" : "add-employee",
        emptyActionLabel: list.length ? "清除筛选" : "新增员工",
        viewAction: "a-view-employee",
        editAction: "edit-employee",
        resignAction: "resign-employee",
      });
    }

    return `${head}<div class="split">${tree}<section class="panel">${toolbar}${table}</section></div>`;
  }

  function screenAPositions() {
    const company = getCompany(state.companyId);
    const head = pageHead(
      "岗位",
      `${esc(company.name)} · 岗位是公司级可复用档案；默认部门可选，员工必须绑定岗位。本期不绑定薪酬构成、计算方案或工作日参数。`,
      `<button class="btn btn-primary" data-action="add-position">${icon(
        "plus",
      )} 新增岗位</button>`,
    );

    const toolbar = `<div class="toolbar">
      <div class="search">${icon("search")}<input class="input" data-input="a-pos-search" placeholder="搜索岗位名称或编码" value="${attr(
        state.aPosSearch,
      )}" /></div>
      <select class="select" data-select="a-pos-status" aria-label="岗位状态">
        <option value="all" ${state.aPosStatus === "all" ? "selected" : ""}>全部状态</option>
        <option value="active" ${state.aPosStatus === "active" ? "selected" : ""}>仅启用</option>
        <option value="inactive" ${state.aPosStatus === "inactive" ? "selected" : ""}>仅停用</option>
      </select>
      <span class="spacer"></span>
      <span class="sub">岗位编码在公司内唯一；停用后不再出现在新建员工的选择器中</span>
    </div>`;

    let body;
    if (state.preview !== "normal") {
      body = renderPreview("positions", {
        icon: "briefcase",
        title: "还没有岗位",
        message: "员工必须绑定岗位，建议先维护岗位档案。",
        action: `<button class="btn btn-primary" data-action="add-position">${icon(
          "plus",
        )} 新建岗位</button>`,
      });
    } else {
      body = renderPositionTable(state.companyId, {
        query: state.aPosSearch,
        status: state.aPosStatus,
        emptyTitle: "还没有岗位",
        emptyMessage:
          "员工必须绑定岗位，建议先维护岗位档案。岗位是公司级可复用档案，默认部门仅用于带出。",
      });
    }

    return `${head}<div class="panel">${toolbar}${body}</div>`;
  }

  function screenACostCenters() {
    const costs = costsOfCompany(state.companyId);
    const roots = costChildren(state.companyId, null);
    if (
      state.aCostId !== "all" &&
      state.aCostId !== "unassigned" &&
      (!getCost(state.aCostId) || getCost(state.aCostId).companyId !== state.companyId)
    ) {
      state.aCostId = roots[0]?.id || "all";
    }
    if (!costs.length && state.aCostId !== "unassigned") {
      state.aCostId = "all";
    }
    const company = getCompany(state.companyId);

    const head = pageHead(
      "成本中心",
      `${esc(company.name)} · 与行政架构独立的成本归属维度；预算与预警线本期只录入，不做工资统计或预警。`,
      `<button class="btn btn-primary" data-action="add-cost">${icon(
        "plus",
      )} 新增成本中心</button>`,
    );

    const tree = `<aside class="tree-panel">
      <div class="tree-head">
        <div class="search">${icon("search")}<input class="input" data-input="a-cost-search" placeholder="搜索成本中心名称或编码" value="${attr(
          state.aCostSearch,
        )}" /></div>
      </div>
      <div class="tree-body">${renderCostTree(state.companyId, {
        selectedId: state.aCostId,
        query: state.aCostSearch,
        action: "a-select-cost",
      })}</div>
      <div class="tree-foot">
        <button class="btn btn-outline btn-sm" data-action="add-cost">${icon(
          "plus",
        )} 新增顶层成本中心</button>
      </div>
    </aside>`;

    let detail;
    if (state.preview !== "normal") {
      detail = `<section class="detail">${renderPreview("costcenters", {
        icon: "wallet",
        title: "还没有成本中心",
        message: "成本中心用于工资支出归集；员工可以没有成本中心，显示为未分配。",
        action: `<button class="btn btn-primary" data-action="add-cost">${icon(
          "plus",
        )} 新增成本中心</button>`,
      })}</section>`;
    } else if (state.aCostId === "all") {
      detail = renderACostOverview();
    } else if (state.aCostId === "unassigned") {
      detail = renderAUnassigned();
    } else {
      detail = renderACostDetail(getCost(state.aCostId));
    }

    return `${head}<div class="split">${tree}${detail}</div>`;
  }

  function renderACostOverview() {
    const costs = costsOfCompany(state.companyId);
    const activeCosts = costs.filter((cost) => cost.active).length;
    const totalBudget = costs.reduce(
      (sum, cost) => sum + Number(cost.budget || 0),
      0,
    );
    const unassigned = unassignedEmployees(state.companyId, false).length;

    return `<section class="detail">
      <div class="detail-head">
        <div>
          <h2 class="detail-title">全部成本中心</h2>
          <div class="detail-sub">${esc(
            getCompany(state.companyId).name,
          )} · 含下级汇总的预算与员工数仅为展示口径，本期不做工资统计。</div>
        </div>
        <button class="btn btn-outline btn-sm" data-action="add-cost">${icon(
          "plus",
        )} 新增成本中心</button>
      </div>
      <div class="detail-body">
        <div class="stat-grid">
          <div class="stat"><div class="label">成本中心</div><div class="value">${costs.length}</div><div class="hint">启用 ${activeCosts} 个</div></div>
          <div class="stat"><div class="label">在职/试用期员工</div><div class="value">${activeEmployeeCount(
            state.companyId,
          )}</div><div class="hint">按成本归属统计</div></div>
          <div class="stat"><div class="label">未分配员工</div><div class="value">${unassigned}</div><div class="hint">成本归属为空</div></div>
          <div class="stat"><div class="label">月度预算合计</div><div class="value" style="font-size:18px">${money(
            totalBudget,
          )}</div><div class="hint">0 = 不设预算</div></div>
        </div>

        <div class="panel mt-16">
          <div class="card-head"><h3>成本中心列表</h3><span class="sub">员工数为含下级的在职/试用期人数</span></div>
          ${
            costs.length
              ? `<div class="table-wrap"><table class="table">
                  <thead><tr><th>编码</th><th>名称</th><th>上级</th><th>月度预算</th><th>在职/试用期</th><th>状态</th><th></th></tr></thead>
                  <tbody>${costs
                    .map((cost) => {
                      const count = employeesInCost(cost.id, true, false).length;
                      return `<tr>
                        <td><span class="code">${esc(cost.code)}</span></td>
                        <td><button class="name" style="border:0;background:none;padding:0" data-action="a-select-cost" data-id="${cost.id}">${esc(
                          cost.name,
                        )}</button></td>
                        <td>${cost.parentId ? esc(getCost(cost.parentId)?.name || "—") : '<span class="sub">顶层</span>'}</td>
                        <td class="nowrap">${money(cost.budget)}</td>
                        <td>${count}</td>
                        <td>${activeBadge(cost.active)}</td>
                        <td class="td-actions"><button class="btn btn-ghost btn-sm" data-action="a-select-cost" data-id="${cost.id}">查看</button></td>
                      </tr>`;
                    })
                    .join("")}</tbody>
                </table></div>`
              : `<div class="empty"><div class="empty-icon">${icon(
                  "wallet",
                )}</div><h3>还没有成本中心</h3><p>成本中心与行政架构相互独立，可以稍后再维护。</p><button class="btn btn-primary" data-action="add-cost">${icon(
                  "plus",
                )} 新增成本中心</button></div>`
          }
        </div>
      </div>
    </section>`;
  }

  function renderACostDetail(cost) {
    if (!cost) {
      return `<section class="detail">${renderPreview("costcenters", {
        icon: "wallet",
        title: "请选择成本中心",
        message: "从左侧选择一个成本中心查看详情。",
      })}</section>`;
    }
    const manager = getEmployee(cost.managerId);
    const children = costChildren(state.companyId, cost.id);
    const direct = employeesInCost(cost.id, false, false).length;
    const subtree = employeesInCost(cost.id, true, false).length;
    const resigned = employeesInCost(cost.id, true, true).length - subtree;
    const directEmployees = employees.filter(
      (employee) => employee.costId === cost.id,
    );

    const header = `<div class="detail-head">
      <div>
        <div class="b-node-path">${costPath(cost.id)
          .slice(0, -1)
          .map((item) => esc(item.name))
          .join(` ${icon("chevron-right")} `) || "顶层成本中心"}</div>
        <h2 class="detail-title">${esc(cost.name)} <span class="code">${esc(
          cost.code,
        )}</span> ${activeBadge(cost.active)}</h2>
        <div class="detail-sub">直接归属 ${direct} 人 · 含下级 ${subtree} 人 · 档案共 ${
          subtree + resigned
        } 人（离职 ${resigned} 人） · 预算仅录入，本期不做支出统计</div>
      </div>
      <div class="actions">
        <button class="btn btn-outline btn-sm" data-action="edit-cost" data-id="${cost.id}">${icon(
          "edit",
        )} 编辑</button>
        <button class="btn btn-outline btn-sm" data-action="add-cost" data-parent="${cost.id}">${icon(
          "plus",
        )} 新增子成本中心</button>
        <button class="btn btn-ghost btn-sm danger-text" data-action="delete-cost" data-id="${cost.id}">${icon(
          "trash",
        )} 删除</button>
      </div>
    </div>`;

    const body = `<div class="detail-body">
      <div class="kv-grid">
        <dl class="kv">
          <dt>上级成本中心</dt><dd>${cost.parentId ? esc(costPathLabel(cost.parentId)) : "无（顶层）"}</dd>
          <dt>负责人</dt><dd>${
            manager
              ? `${esc(manager.name)} <span class="sub">${esc(manager.no)} · ${
                  STATUS[manager.status]?.label || manager.status
                }</span>`
              : '<span class="sub">未指定</span>'
          }</dd>
          <dt>排序</dt><dd>${cost.orderNo}</dd>
        </dl>
        <dl class="kv">
          <dt>状态</dt><dd>${activeBadge(cost.active)}</dd>
          <dt>备注</dt><dd>${esc(cost.note || "—")}</dd>
          <dt>员工数</dt><dd>${subtree} 人（含下级在职/试用期）</dd>
        </dl>
      </div>

      <div class="card mt-16">
        <div class="card-body">
          <div class="budget-line"><span>月度工资预算</span><strong>${money(
            cost.budget,
          )}</strong></div>
          <div class="progress"><span></span></div>
          <div class="progress-label"><span>本期未做工资统计</span><span>预警线 ${cost.warnPct}%</span></div>
          <div class="notice info mt-12">${icon(
            "info",
          )}<div>预算与预警线只用于录入和展示；工资支出统计与预警不在本期范围。</div></div>
        </div>
      </div>

      <div class="panel mt-16">
        <div class="card-head"><h3>下级成本中心</h3><button class="btn btn-outline btn-sm" data-action="add-cost" data-parent="${cost.id}">${icon(
          "plus",
        )} 新增</button></div>
        ${
          children.length
            ? `<div class="table-wrap"><table class="table">
                <thead><tr><th>编码</th><th>名称</th><th>负责人</th><th>预算</th><th>在职/试用期</th><th>状态</th><th></th></tr></thead>
                <tbody>${children
                  .map((child) => {
                    const childManager = getEmployee(child.managerId);
                    return `<tr>
                      <td><span class="code">${esc(child.code)}</span></td>
                      <td><button class="name" style="border:0;background:none;padding:0" data-action="a-select-cost" data-id="${child.id}">${esc(
                        child.name,
                      )}</button></td>
                      <td>${childManager ? esc(childManager.name) : '<span class="sub">未指定</span>'}</td>
                      <td class="nowrap">${money(child.budget)}</td>
                      <td>${employeesInCost(child.id, true, false).length}</td>
                      <td>${activeBadge(child.active)}</td>
                      <td class="td-actions"><button class="btn btn-ghost btn-sm" data-action="a-select-cost" data-id="${child.id}">查看</button></td>
                    </tr>`;
                  })
                  .join("")}</tbody>
              </table></div>`
            : `<div class="empty" style="padding:28px 18px"><div class="empty-icon">${icon(
                "wallet",
              )}</div><h3>暂无下级成本中心</h3><p>成本中心支持多级，但本期不要求必须拆分。</p></div>`
        }
      </div>

      <div class="panel">
        <div class="card-head"><h3>直接归属本成本中心的员工</h3><span class="sub">含离职，仅显示直接归属</span></div>
        ${
          directEmployees.length
            ? renderMiniEmployeeTable(directEmployees)
            : `<div class="empty" style="padding:28px 18px"><div class="empty-icon">${icon(
                "users",
              )}</div><h3>暂无直接归属员工</h3><p>下级成本中心的员工不会重复显示在这里。</p></div>`
        }
      </div>
    </div>`;

    return `<section class="detail">${header}${body}</section>`;
  }

  function renderAUnassigned() {
    const list = unassignedEmployees(state.companyId, true);
    return `<section class="detail">
      <div class="detail-head">
        <div>
          <div class="b-node-path">成本架构 ${icon("chevron-right")} 未分配</div>
          <h2 class="detail-title">未分配 <span class="badge badge-gray">${list.length} 人</span></h2>
          <div class="detail-sub">员工没有成本中心归属时显示为未分配；本期不做工资支出统计。</div>
        </div>
        <div class="actions">
          <button class="btn btn-outline btn-sm" data-action="open-unassigned-employees">${icon(
            "users",
          )} 查看员工</button>
        </div>
      </div>
      <div class="detail-body">
        <div class="notice warn">${icon(
          "alert",
        )}<div>未分配不是错误状态。员工可以先不填成本中心，后续在「员工」页面补充；离职员工也计入此列表。</div></div>
        <div class="panel mt-12">
          ${
            list.length
              ? renderMiniEmployeeTable(list)
              : `<div class="empty" style="padding:32px 18px"><div class="empty-icon">${icon(
                  "check",
                )}</div><h3>没有未分配员工</h3><p>当前公司所有员工都有成本中心归属。</p></div>`
          }
        </div>
      </div>
    </section>`;
  }

  function renderMiniEmployeeTable(list) {
    return `<div class="table-wrap"><table class="table">
      <thead><tr><th>工号</th><th>姓名</th><th>部门</th><th>岗位</th><th>状态</th><th></th></tr></thead>
      <tbody>${list
        .map((employee) => {
          const dept = getDept(employee.deptId);
          const position = getPosition(employee.positionId);
          return `<tr>
            <td><span class="code">${esc(employee.no)}</span></td>
            <td class="name">${esc(employee.name)}</td>
            <td>${dept ? esc(dept.name) : "—"}</td>
            <td>${position ? esc(position.name) : "—"}</td>
            <td>${statusBadge(employee.status)}</td>
            <td class="td-actions"><button class="btn btn-ghost btn-sm" data-action="edit-employee" data-id="${employee.id}">编辑</button></td>
          </tr>`;
        })
        .join("")}</tbody>
    </table></div>`;
  }

  /* ================================================================ variant B */

  function renderB() {
    normalizeBNode();
    return `<div class="app">
      ${renderSidebarB()}
      <div class="main">
        ${renderBTopbar()}
        <div class="content wide">
          <div class="page-head">
            <div>
              <h1 class="page-title">基础管理</h1>
              <p class="page-sub">以公司为上下文，在左侧组织树中定位部门或成本中心，再在右侧完成查看与维护；公司档案通过「管理公司」进入。</p>
            </div>
            <div class="actions">
              ${renderCompanySwitch()}
              <button class="btn btn-outline" data-action="open-company-modal">${icon(
                "building",
              )} 管理公司</button>
            </div>
          </div>
          <div class="split b-split">
            ${renderBTreePanel()}
            <section class="detail b-detail">${renderBRight()}</section>
          </div>
        </div>
      </div>
    </div>`;
  }

  function renderBTopbar() {
    return `<header class="topbar">
      <div class="breadcrumb">基础管理 ${icon("chevron-right")} <strong>组织工作台</strong></div>
      <div class="topbar-right"><div class="avatar" title="管理员">管</div></div>
    </header>`;
  }

  function normalizeBNode() {
    if (state.bTree === "dept") {
      const valid =
        state.bNodeId === "all" ||
        (getDept(state.bNodeId) &&
          getDept(state.bNodeId).companyId === state.companyId);
      if (!valid) {
        state.bNodeId =
          deptChildren(state.companyId, null)[0]?.id || "all";
      }
      if (!["overview", "employees", "positions", "children"].includes(state.bTab)) {
        state.bTab = "overview";
      }
    } else {
      const valid =
        state.bNodeId === "all" ||
        state.bNodeId === "unassigned" ||
        (getCost(state.bNodeId) &&
          getCost(state.bNodeId).companyId === state.companyId);
      if (!valid) {
        state.bNodeId =
          costChildren(state.companyId, null)[0]?.id || "all";
      }
      if (!["overview", "employees", "children"].includes(state.bTab)) {
        state.bTab = "overview";
      }
    }
  }

  function renderBTreePanel() {
    const mode = state.bTree;
    return `<aside class="tree-panel">
      <div class="tree-head">
        <div class="segmented" role="tablist">
          <button class="${mode === "dept" ? "active" : ""}" data-action="b-tree-mode" data-mode="dept">行政架构</button>
          <button class="${mode === "cost" ? "active" : ""}" data-action="b-tree-mode" data-mode="cost">成本架构</button>
        </div>
        <div class="search">${icon("search")}<input class="input" data-input="b-tree-search" placeholder="${
          mode === "dept" ? "搜索部门" : "搜索成本中心"
        }" value="${attr(state.bTreeSearch)}" /></div>
      </div>
      <div class="tree-body">${
        mode === "dept"
          ? renderDeptTree(state.companyId, {
              selectedId: state.bNodeId,
              query: state.bTreeSearch,
              action: "b-select-node",
            })
          : renderCostTree(state.companyId, {
              selectedId: state.bNodeId,
              query: state.bTreeSearch,
              action: "b-select-node",
            })
      }</div>
      <div class="tree-foot">
        ${
          mode === "dept"
            ? `<button class="btn btn-outline btn-sm" data-action="add-dept">${icon("plus")} 新增部门</button>`
            : `<button class="btn btn-outline btn-sm" data-action="add-cost">${icon("plus")} 新增成本中心</button>`
        }
      </div>
    </aside>`;
  }

  function renderBRight() {
    if (state.bView === "employee-form") {
      return renderBEmployeeFormPanel();
    }
    if (state.bView === "employee-detail") {
      return renderBEmployeeDetailPanel();
    }
    if (state.bNodeId === "all") {
      return renderBCompanyOverview();
    }
    if (state.bTree === "dept") {
      const dept = getDept(state.bNodeId);
      return dept ? renderBDeptPanel(dept) : renderBCompanyOverview();
    }
    if (state.bNodeId === "unassigned") {
      return renderBUnassignedPanel();
    }
    const cost = getCost(state.bNodeId);
    return cost ? renderBCostPanel(cost) : renderBCompanyOverview();
  }

  function renderBCompanyOverview() {
    const company = getCompany(state.companyId);
    const active = activeEmployeeCount(company.id);
    const roots = deptChildren(company.id, null);
    const costRoots = costChildren(company.id, null);

    if (state.preview !== "normal") {
      return `<div class="detail-head">
        <div>
          <div class="b-node-path">基础管理 ${icon("chevron-right")} ${esc(company.code)}</div>
          <h2 class="detail-title">${esc(company.name)} ${activeBadge(company.active)}</h2>
          <div class="detail-sub">公司概览 · 状态预览</div>
        </div>
      </div>
      <div class="detail-body">${renderPreview("b", {
        icon: "building",
        title: "公司数据为空",
        message: "当前公司还没有可展示的组织数据。",
      })}</div>`;
    }

    return `<div class="detail-head">
      <div>
        <div class="b-node-path">基础管理 ${icon("chevron-right")} ${esc(company.code)}</div>
        <h2 class="detail-title">${esc(company.name)} ${activeBadge(company.active)}</h2>
        <div class="detail-sub">从左侧选择部门或成本中心开始；公司级档案通过「管理公司」维护。</div>
      </div>
      <div class="actions">
        <button class="btn btn-outline btn-sm" data-action="open-company-modal">${icon("building")} 管理公司</button>
      </div>
    </div>
    <div class="detail-body">
      <div class="notice info">${icon(
        "info",
      )}<div>当前公司：<strong>${esc(company.name)}</strong>。左侧树和右侧数据都只显示该公司范围；切换公司后会自动回到首个节点。</div></div>
      <div class="stat-grid mt-16">
        <div class="stat"><div class="label">在职/试用期员工</div><div class="value">${active}</div><div class="hint">共 ${employeesOfCompany(company.id).length} 人档案</div></div>
        <div class="stat"><div class="label">部门</div><div class="value">${deptsOfCompany(company.id).length}</div><div class="hint">顶层 ${roots.length} 个</div></div>
        <div class="stat"><div class="label">岗位</div><div class="value">${positionsOfCompany(company.id).length}</div><div class="hint">公司级可复用档案</div></div>
        <div class="stat"><div class="label">成本中心</div><div class="value">${costsOfCompany(company.id).length}</div><div class="hint">顶层 ${costRoots.length} 个</div></div>
      </div>

      <div class="panel mt-16">
        <div class="card-head"><h3>顶层部门</h3><button class="btn btn-outline btn-sm" data-action="add-dept">${icon(
          "plus",
        )} 新增部门</button></div>
        ${
          roots.length
            ? `<div class="table-wrap"><table class="table">
                <thead><tr><th>编码</th><th>部门</th><th>负责人</th><th>在职/试用期</th><th>状态</th><th></th></tr></thead>
                <tbody>${roots
                  .map((dept) => {
                    const manager = getEmployee(dept.managerId);
                    return `<tr>
                      <td><span class="code">${esc(dept.code)}</span></td>
                      <td><button class="name" style="border:0;background:none;padding:0" data-action="b-select-node" data-id="${dept.id}">${esc(
                        dept.name,
                      )}</button></td>
                      <td>${manager ? esc(manager.name) : '<span class="sub">未指定</span>'}</td>
                      <td>${employeesInDept(dept.id, true, false).length}</td>
                      <td>${activeBadge(dept.active)}</td>
                      <td class="td-actions"><button class="btn btn-ghost btn-sm" data-action="b-select-node" data-id="${dept.id}">查看</button></td>
                    </tr>`;
                  })
                  .join("")}</tbody>
              </table></div>`
            : `<div class="empty" style="padding:30px 18px"><div class="empty-icon">${icon(
                "network",
              )}</div><h3>还没有部门</h3><p>新增顶层部门后，可以在左侧树中逐级维护。</p><button class="btn btn-primary" data-action="add-dept">${icon(
                "plus",
              )} 新增部门</button></div>`
        }
      </div>

      <div class="panel">
        <div class="card-head"><h3>顶层成本中心</h3><button class="btn btn-outline btn-sm" data-action="add-cost">${icon(
          "plus",
        )} 新增成本中心</button></div>
        ${
          costRoots.length
            ? `<div class="table-wrap"><table class="table">
                <thead><tr><th>编码</th><th>成本中心</th><th>负责人</th><th>月度预算</th><th>在职/试用期</th><th>状态</th><th></th></tr></thead>
                <tbody>${costRoots
                  .map((cost) => {
                    const manager = getEmployee(cost.managerId);
                    return `<tr>
                      <td><span class="code">${esc(cost.code)}</span></td>
                      <td><button class="name" style="border:0;background:none;padding:0" data-action="b-select-node" data-id="${cost.id}">${esc(
                        cost.name,
                      )}</button></td>
                      <td>${manager ? esc(manager.name) : '<span class="sub">未指定</span>'}</td>
                      <td class="nowrap">${money(cost.budget)}</td>
                      <td>${employeesInCost(cost.id, true, false).length}</td>
                      <td>${activeBadge(cost.active)}</td>
                      <td class="td-actions"><button class="btn btn-ghost btn-sm" data-action="b-select-node" data-id="${cost.id}">查看</button></td>
                    </tr>`;
                  })
                  .join("")}</tbody>
              </table></div>`
            : `<div class="empty" style="padding:30px 18px"><div class="empty-icon">${icon(
                "wallet",
              )}</div><h3>还没有成本中心</h3><p>成本中心与行政架构相互独立，可以稍后再维护。</p><button class="btn btn-primary" data-action="add-cost">${icon(
                "plus",
              )} 新增成本中心</button></div>`
        }
      </div>
    </div>`;
  }

  function renderBTabs(items) {
    return `<div class="tabs">${items
      .map(
        (item) => `<button class="tab ${
          state.bTab === item.key ? "active" : ""
        }" data-action="b-tab" data-tab="${item.key}">${item.label}${
          item.count !== undefined
            ? `<span class="tab-count">${item.count}</span>`
            : ""
        }</button>`,
      )
      .join("")}</div>`;
  }

  function renderBPreviewOr(content, options) {
    if (state.preview !== "normal") {
      return `<div class="detail-body">${renderPreview("b", options)}</div>`;
    }
    return content;
  }

  function renderBDeptPanel(dept) {
    const manager = getEmployee(dept.managerId);
    const activeDirect = employeesInDept(dept.id, false, false).length;
    const activeSubtree = employeesInDept(dept.id, true, false).length;
    const resigned = employeesInDept(dept.id, true, true).length - activeSubtree;
    const children = deptChildren(state.companyId, dept.id);
    const deptPositions = positionsOfCompany(state.companyId).filter(
      (position) => position.deptId === dept.id,
    );

    const header = `<div class="b-node-head">
      <div>
        <div class="b-node-path">${deptPath(dept.id)
          .map((item) => esc(item.name))
          .join(` ${icon("chevron-right")} `)}</div>
        <h2 class="b-node-title">${esc(dept.name)} <span class="code">${esc(
          dept.code,
        )}</span> ${activeBadge(dept.active)}</h2>
        <div class="b-node-sub">本部门 ${activeDirect} 人在职/试用期 · 含下级 ${activeSubtree} 人 · 档案共 ${
          activeSubtree + resigned
        } 人（离职 ${resigned} 人）</div>
      </div>
      <div class="actions">
        <button class="btn btn-outline btn-sm" data-action="edit-dept" data-id="${dept.id}">${icon(
          "edit",
        )} 编辑</button>
        <button class="btn btn-outline btn-sm" data-action="add-dept" data-parent="${dept.id}">${icon(
          "plus",
        )} 子部门</button>
        <button class="btn btn-ghost btn-sm danger-text" data-action="delete-dept" data-id="${dept.id}">${icon(
          "trash",
        )} 删除</button>
      </div>
    </div>`;

    const tabs = renderBTabs([
      { key: "overview", label: "概览" },
      { key: "employees", label: "员工", count: activeSubtree },
      { key: "positions", label: "岗位", count: deptPositions.length },
      { key: "children", label: "下级部门", count: children.length },
    ]);

    if (state.preview !== "normal") {
      return `${header}${tabs}${renderBPreviewOr("", {
        icon: "network",
        title: "部门数据为空",
        message: "当前条件下没有可展示的部门数据。",
      })}`;
    }

    let body;
    if (state.bTab === "overview") {
      body = `<div class="detail-body">
        <div class="stat-grid">
          <div class="stat"><div class="label">在职/试用期</div><div class="value">${activeSubtree}</div><div class="hint">含下级部门</div></div>
          <div class="stat"><div class="label">离职员工</div><div class="value">${resigned}</div><div class="hint">档案保留，不阻止组织停用</div></div>
          <div class="stat"><div class="label">下级部门</div><div class="value">${children.length}</div><div class="hint">任意多级</div></div>
          <div class="stat"><div class="label">默认岗位</div><div class="value">${deptPositions.length}</div><div class="hint">岗位是公司级档案</div></div>
        </div>
        <div class="panel mt-16">
          <div class="card-head"><h3>部门信息</h3></div>
          <div class="detail-body">
            <div class="kv-grid">
              <dl class="kv">
                <dt>上级部门</dt><dd>${dept.parentId ? esc(deptPathLabel(dept.parentId)) : "无（顶层部门）"}</dd>
                <dt>负责人</dt><dd>${
                  manager
                    ? `${esc(manager.name)} <span class="sub">${esc(manager.no)}</span>`
                    : '<span class="sub">未指定</span>'
                }</dd>
                <dt>排序</dt><dd>${dept.orderNo}</dd>
              </dl>
              <dl class="kv">
                <dt>状态</dt><dd>${activeBadge(dept.active)}</dd>
                <dt>编码</dt><dd><span class="code">${esc(dept.code)}</span></dd>
                <dt>备注</dt><dd>${esc(dept.note || "—")}</dd>
              </dl>
            </div>
          </div>
        </div>
        <div class="panel">
          <div class="card-head"><h3>快捷操作</h3></div>
          <div class="detail-body row">
            <button class="btn btn-outline" data-action="b-add-employee" data-dept="${dept.id}">${icon(
              "plus",
            )} 新增员工</button>
            <button class="btn btn-outline" data-action="add-position" data-dept="${dept.id}">${icon(
              "plus",
            )} 新增岗位</button>
            <button class="btn btn-outline" data-action="add-dept" data-parent="${dept.id}">${icon(
              "plus",
            )} 新增子部门</button>
          </div>
        </div>
      </div>`;
    } else if (state.bTab === "employees") {
      body = renderBEmployeeTab({ kind: "dept", id: dept.id });
    } else if (state.bTab === "positions") {
      body = `<div class="detail-body">
        <div class="notice info">${icon(
          "info",
        )}<div>岗位是公司级可复用档案。这里只显示<strong>默认部门</strong>为本部门的岗位；员工实际部门可以不同。</div></div>
        <div class="panel mt-12">
          ${renderPositionTable(state.companyId, {
            deptId: dept.id,
            emptyTitle: "本部门还没有默认岗位",
            emptyMessage:
              "岗位是公司级档案，新增后可供全公司员工选择；默认部门仅用于建档时带出。",
          })}
        </div>
      </div>`;
    } else {
      body = `<div class="detail-body">
        <div class="panel">
          <div class="card-head"><h3>下级部门</h3><button class="btn btn-outline btn-sm" data-action="add-dept" data-parent="${dept.id}">${icon(
            "plus",
          )} 新增子部门</button></div>
          ${
            children.length
              ? `<div class="table-wrap"><table class="table">
                  <thead><tr><th>编码</th><th>部门</th><th>负责人</th><th>在职/试用期</th><th>状态</th><th></th></tr></thead>
                  <tbody>${children
                    .map((child) => {
                      const childManager = getEmployee(child.managerId);
                      return `<tr>
                        <td><span class="code">${esc(child.code)}</span></td>
                        <td><button class="name" style="border:0;background:none;padding:0" data-action="b-select-node" data-id="${child.id}">${esc(
                          child.name,
                        )}</button></td>
                        <td>${childManager ? esc(childManager.name) : '<span class="sub">未指定</span>'}</td>
                        <td>${employeesInDept(child.id, true, false).length}</td>
                        <td>${activeBadge(child.active)}</td>
                        <td class="td-actions"><button class="btn btn-ghost btn-sm" data-action="b-select-node" data-id="${child.id}">查看</button></td>
                      </tr>`;
                    })
                    .join("")}</tbody>
                </table></div>`
              : `<div class="empty" style="padding:30px 18px"><div class="empty-icon">${icon(
                  "network",
                )}</div><h3>暂无下级部门</h3><p>可以继续拆分，也可以保持当前层级。</p></div>`
          }
        </div>
      </div>`;
    }

    return `${header}${tabs}${body}`;
  }

  function renderBCostPanel(cost) {
    const manager = getEmployee(cost.managerId);
    const children = costChildren(state.companyId, cost.id);
    const activeDirect = employeesInCost(cost.id, false, false).length;
    const activeSubtree = employeesInCost(cost.id, true, false).length;
    const resigned = employeesInCost(cost.id, true, true).length - activeSubtree;

    const header = `<div class="b-node-head">
      <div>
        <div class="b-node-path">${costPath(cost.id)
          .map((item) => esc(item.name))
          .join(` ${icon("chevron-right")} `)}</div>
        <h2 class="b-node-title">${esc(cost.name)} <span class="code">${esc(
          cost.code,
        )}</span> ${activeBadge(cost.active)}</h2>
        <div class="b-node-sub">直接归属 ${activeDirect} 人 · 含下级 ${activeSubtree} 人 · 档案共 ${
          activeSubtree + resigned
        } 人（离职 ${resigned} 人） · 预算仅录入</div>
      </div>
      <div class="actions">
        <button class="btn btn-outline btn-sm" data-action="edit-cost" data-id="${cost.id}">${icon(
          "edit",
        )} 编辑</button>
        <button class="btn btn-outline btn-sm" data-action="add-cost" data-parent="${cost.id}">${icon(
          "plus",
        )} 子成本中心</button>
        <button class="btn btn-ghost btn-sm danger-text" data-action="delete-cost" data-id="${cost.id}">${icon(
          "trash",
        )} 删除</button>
      </div>
    </div>`;

    const tabs = renderBTabs([
      { key: "overview", label: "概览" },
      { key: "employees", label: "员工", count: activeSubtree },
      { key: "children", label: "下级成本中心", count: children.length },
    ]);

    if (state.preview !== "normal") {
      return `${header}${tabs}${renderBPreviewOr("", {
        icon: "wallet",
        title: "成本中心数据为空",
        message: "当前条件下没有可展示的成本中心数据。",
      })}`;
    }

    let body;
    if (state.bTab === "overview") {
      body = `<div class="detail-body">
        <div class="stat-grid">
          <div class="stat"><div class="label">在职/试用期</div><div class="value">${activeSubtree}</div><div class="hint">含下级成本中心</div></div>
          <div class="stat"><div class="label">离职员工</div><div class="value">${resigned}</div><div class="hint">档案保留</div></div>
          <div class="stat"><div class="label">下级成本中心</div><div class="value">${children.length}</div><div class="hint">任意多级</div></div>
          <div class="stat"><div class="label">月度预算</div><div class="value" style="font-size:18px">${money(
            cost.budget,
          )}</div><div class="hint">0 = 不设预算</div></div>
        </div>
        <div class="card mt-16">
          <div class="card-body">
            <div class="budget-line"><span>月度工资预算</span><strong>${money(
              cost.budget,
            )}</strong></div>
            <div class="progress"><span></span></div>
            <div class="progress-label"><span>本期未做工资统计</span><span>预警线 ${cost.warnPct}%</span></div>
          </div>
        </div>
        <div class="panel mt-16">
          <div class="card-head"><h3>成本中心信息</h3></div>
          <div class="detail-body">
            <div class="kv-grid">
              <dl class="kv">
                <dt>上级</dt><dd>${cost.parentId ? esc(costPathLabel(cost.parentId)) : "无（顶层）"}</dd>
                <dt>负责人</dt><dd>${
                  manager
                    ? `${esc(manager.name)} <span class="sub">${esc(manager.no)}</span>`
                    : '<span class="sub">未指定</span>'
                }</dd>
                <dt>排序</dt><dd>${cost.orderNo}</dd>
              </dl>
              <dl class="kv">
                <dt>状态</dt><dd>${activeBadge(cost.active)}</dd>
                <dt>编码</dt><dd><span class="code">${esc(cost.code)}</span></dd>
                <dt>备注</dt><dd>${esc(cost.note || "—")}</dd>
              </dl>
            </div>
          </div>
        </div>
        <div class="notice warn mt-12">${icon(
          "alert",
        )}<div>预算与预警线只用于录入和展示；工资支出统计与预警不在本期范围。</div></div>
      </div>`;
    } else if (state.bTab === "employees") {
      body = renderBEmployeeTab({ kind: "cost", id: cost.id });
    } else {
      body = `<div class="detail-body">
        <div class="panel">
          <div class="card-head"><h3>下级成本中心</h3><button class="btn btn-outline btn-sm" data-action="add-cost" data-parent="${cost.id}">${icon(
            "plus",
          )} 新增子成本中心</button></div>
          ${
            children.length
              ? `<div class="table-wrap"><table class="table">
                  <thead><tr><th>编码</th><th>名称</th><th>负责人</th><th>预算</th><th>在职/试用期</th><th>状态</th><th></th></tr></thead>
                  <tbody>${children
                    .map((child) => {
                      const childManager = getEmployee(child.managerId);
                      return `<tr>
                        <td><span class="code">${esc(child.code)}</span></td>
                        <td><button class="name" style="border:0;background:none;padding:0" data-action="b-select-node" data-id="${child.id}">${esc(
                          child.name,
                        )}</button></td>
                        <td>${childManager ? esc(childManager.name) : '<span class="sub">未指定</span>'}</td>
                        <td class="nowrap">${money(child.budget)}</td>
                        <td>${employeesInCost(child.id, true, false).length}</td>
                        <td>${activeBadge(child.active)}</td>
                        <td class="td-actions"><button class="btn btn-ghost btn-sm" data-action="b-select-node" data-id="${child.id}">查看</button></td>
                      </tr>`;
                    })
                    .join("")}</tbody>
                </table></div>`
              : `<div class="empty" style="padding:30px 18px"><div class="empty-icon">${icon(
                  "wallet",
                )}</div><h3>暂无下级成本中心</h3><p>成本中心支持多级，但本期不要求必须拆分。</p></div>`
          }
        </div>
      </div>`;
    }

    return `${header}${tabs}${body}`;
  }

  function renderBUnassignedPanel() {
    const list = filterEmployeesB({
      base: unassignedEmployees(state.companyId, true),
    });
    return `<div class="b-node-head">
      <div>
        <div class="b-node-path">成本架构 ${icon("chevron-right")} 未分配</div>
        <h2 class="b-node-title">未分配 <span class="badge badge-gray">${list.length} 人</span></h2>
        <div class="b-node-sub">员工没有成本中心归属时显示为未分配；本期不做工资支出统计。</div>
      </div>
    </div>
    <div class="detail-body">
      <div class="notice warn">${icon(
        "alert",
      )}<div>未分配不是错误状态。员工可以先不填成本中心；离职员工也计入此列表。</div></div>
      <div class="panel mt-12">
        <div class="toolbar">
          <div class="search">${icon("search")}<input class="input" data-input="b-emp-search" placeholder="搜索工号或姓名" value="${attr(
            state.bEmpSearch,
          )}" /></div>
          <select class="select" data-select="b-emp-status" aria-label="状态筛选">
            <option value="active" ${state.bEmpStatus === "active" ? "selected" : ""}>在职 + 试用期</option>
            <option value="all" ${state.bEmpStatus === "all" ? "selected" : ""}>全部状态</option>
            <option value="resigned" ${state.bEmpStatus === "resigned" ? "selected" : ""}>仅离职</option>
          </select>
          <span class="spacer"></span>
          <span class="sub">当前显示 ${list.length} 人</span>
        </div>
        ${
          state.preview !== "normal"
            ? renderPreview("b", {
                icon: "users",
                title: "没有未分配员工",
                message: "当前公司所有员工都有成本中心归属。",
              })
            : renderEmployeeTable(list, {
                emptyTitle: "没有未分配员工",
                emptyMessage: "当前公司所有员工都有成本中心归属。",
                emptyAction: "clear-b-emp-filters",
                emptyActionLabel: "清除筛选",
                viewAction: "b-view-employee",
                editAction: "b-edit-employee",
                resignAction: "b-resign-employee",
              })
        }
      </div>
    </div>`;
  }

  function renderBEmployeeTab(context) {
    const dept = context.kind === "dept" ? getDept(context.id) : null;
    const cost = context.kind === "cost" ? getCost(context.id) : null;
    const base =
      context.kind === "dept"
        ? employeesInDept(context.id, state.bEmpSub, true)
        : employeesInCost(context.id, state.bEmpSub, true);
    const list = filterEmployeesB({ base });

    return `<div class="toolbar">
        <div class="search">${icon("search")}<input class="input" data-input="b-emp-search" placeholder="搜索工号或姓名" value="${attr(
          state.bEmpSearch,
        )}" /></div>
        <select class="select" data-select="b-emp-status" aria-label="状态筛选">
          <option value="active" ${state.bEmpStatus === "active" ? "selected" : ""}>在职 + 试用期</option>
          <option value="all" ${state.bEmpStatus === "all" ? "selected" : ""}>全部状态</option>
          <option value="resigned" ${state.bEmpStatus === "resigned" ? "selected" : ""}>仅离职</option>
        </select>
        <label class="check"><input type="checkbox" data-input="b-emp-sub" ${
          state.bEmpSub ? "checked" : ""
        } /> 含下级${context.kind === "dept" ? "部门" : "成本中心"}</label>
        <span class="spacer"></span>
        <button class="btn btn-primary btn-sm" data-action="b-add-employee" data-dept="${
          dept ? dept.id : ""
        }" data-cost="${cost ? cost.id : ""}">${icon("plus")} 新增员工</button>
      </div>
      <div class="detail-body" style="padding:0">
        ${
          state.preview !== "normal"
            ? renderPreview("b", {
                icon: "users",
                title: "没有员工",
                message: "当前节点下没有员工档案。",
                action: `<button class="btn btn-primary" data-action="b-add-employee" data-dept="${
                  dept ? dept.id : ""
                }" data-cost="${cost ? cost.id : ""}">${icon("plus")} 新增员工</button>`,
              })
            : renderEmployeeTable(list, {
                emptyTitle: "当前节点下没有员工",
                emptyMessage: "调整状态或关键字后再试；也可以直接新增员工。",
                emptyAction: "b-add-employee",
                emptyActionLabel: "新增员工",
                viewAction: "b-view-employee",
                editAction: "b-edit-employee",
                resignAction: "b-resign-employee",
              })
        }
      </div>`;
  }

  function filterEmployeesB({ base }) {
    let list = [...base];
    if (state.bEmpStatus === "active") {
      list = list.filter((employee) => employee.status !== "resigned");
    } else if (state.bEmpStatus === "resigned") {
      list = list.filter((employee) => employee.status === "resigned");
    }
    if (state.bEmpSearch.trim()) {
      const query = state.bEmpSearch.trim().toLowerCase();
      list = list.filter(
        (employee) =>
          employee.name.toLowerCase().includes(query) ||
          employee.no.toLowerCase().includes(query),
      );
    }
    return list.sort(byEmployeeNo);
  }

  function renderBEmployeeDetailPanel() {
    const employee = getEmployee(state.bEmployeeId);
    if (!employee) {
      state.bView = "detail";
      return renderBRight();
    }
    return `<div class="detail-head">
      <div>
        <button class="b-back" data-action="b-back">${icon(
          "arrow-left",
        )} 返回员工列表</button>
        <h2 class="detail-title">${esc(employee.name)} <span class="code">${esc(
          employee.no,
        )}</span> ${statusBadge(employee.status)}</h2>
        <div class="detail-sub">${esc(
          deptPathLabel(employee.deptId),
        )} · ${esc(getPosition(employee.positionId)?.name || "未绑定岗位")}</div>
      </div>
      <div class="actions">
        <button class="btn btn-outline btn-sm" data-action="b-edit-employee" data-id="${employee.id}">${icon(
          "edit",
        )} 编辑</button>
        ${
          employee.status !== "resigned"
            ? `<button class="btn btn-outline btn-sm" data-action="b-resign-employee" data-id="${employee.id}">办理离职</button>`
            : ""
        }
      </div>
    </div>
    <div class="detail-body">${renderEmployeeDetailBody(employee)}</div>`;
  }

  /* ================================================================ variant C */

  function renderC() {
    return `<div class="app c-app">
      <div class="c-main">
        ${renderCTopbar()}
        <div class="content c-content">${renderCScreen()}</div>
      </div>
    </div>`;
  }

  function renderCTopbar() {
    const items = [
      { key: "dashboard", label: "仪表盘", icon: "dashboard", stub: true },
      { key: "employees", label: "员工", icon: "users" },
      { key: "organization", label: "组织", icon: "network" },
      { key: "costcenters", label: "成本中心", icon: "wallet" },
      { key: "companies", label: "公司", icon: "building" },
    ];
    return `<header class="topnav">
      <div class="brand"><div class="logo-mark">A</div><span>AnySys HR</span></div>
      <nav class="nav-links" aria-label="主导航">
        ${items
          .map((item) =>
            item.stub
              ? `<button class="nav-link" data-action="stub" data-label="${item.label}">${icon(
                  item.icon,
                )} ${item.label}</button>`
              : `<button class="nav-link ${
                  state.cScreen === item.key ? "active" : ""
                }" data-action="nav-c" data-screen="${item.key}">${icon(
                  item.icon,
                )} ${item.label}</button>`,
          )
          .join("")}
      </nav>
      <div class="topnav-right">
        <button class="btn btn-ghost btn-sm" data-action="stub" data-label="管理后台">管理后台</button>
        ${renderCompanySwitch()}
        <div class="avatar" title="管理员">管</div>
      </div>
    </header>`;
  }

  function renderCScreen() {
    if (state.cScreen === "organization") return screenCOrganization();
    if (state.cScreen === "costcenters") return screenCCostCenters();
    if (state.cScreen === "companies") return screenCCompanies();
    return screenCEmployees();
  }

  function filterEmployeesC() {
    let list = employeesOfCompany(state.companyId);
    if (state.cEmpDept !== "all") {
      const dept = getDept(state.cEmpDept);
      if (dept && dept.companyId === state.companyId) {
        const ids = new Set([
          dept.id,
          ...(state.cEmpSub ? deptDescendants(dept.id) : []),
        ]);
        list = list.filter((employee) => ids.has(employee.deptId));
      }
    }
    if (state.cEmpStatus === "active") {
      list = list.filter((employee) => employee.status !== "resigned");
    } else if (state.cEmpStatus === "resigned") {
      list = list.filter((employee) => employee.status === "resigned");
    }
    if (state.cEmpSearch.trim()) {
      const query = state.cEmpSearch.trim().toLowerCase();
      list = list.filter(
        (employee) =>
          employee.name.toLowerCase().includes(query) ||
          employee.no.toLowerCase().includes(query),
      );
    }
    return list.sort(byEmployeeNo);
  }

  function screenCEmployees() {
    const company = getCompany(state.companyId);
    const all = employeesOfCompany(state.companyId);
    const active = all.filter((employee) => employee.status !== "resigned").length;
    const list = filterEmployeesC();

    const head = pageHead(
      "员工",
      `${esc(company.name)} · ${active} 人在职/试用期，${all.length - active} 人离职。默认显示在职与试用期；离职为终态，不物理删除。`,
      `<button class="btn btn-primary" data-action="add-employee" data-dept="${
        state.cEmpDept !== "all" ? state.cEmpDept : ""
      }">${icon("plus")} 新增员工</button>`,
    );

    const toolbar = `<div class="toolbar">
      <div class="search">${icon("search")}<input class="input" data-input="c-emp-search" placeholder="搜索工号或姓名" value="${attr(
        state.cEmpSearch,
      )}" /></div>
      <select class="select" data-select="c-emp-status" aria-label="状态筛选">
        <option value="active" ${state.cEmpStatus === "active" ? "selected" : ""}>在职 + 试用期</option>
        <option value="all" ${state.cEmpStatus === "all" ? "selected" : ""}>全部状态</option>
        <option value="resigned" ${state.cEmpStatus === "resigned" ? "selected" : ""}>仅离职</option>
      </select>
      <select class="select" data-select="c-emp-dept" aria-label="部门筛选">
        <option value="all" ${state.cEmpDept === "all" ? "selected" : ""}>全部部门</option>
        ${flatDeptOptions(state.companyId)
          .map(
            (dept) =>
              `<option value="${dept.value}" ${
                state.cEmpDept === dept.value ? "selected" : ""
              }>${esc(dept.label)}</option>`,
          )
          .join("")}
      </select>
      <label class="check"><input type="checkbox" data-input="c-emp-sub" ${
        state.cEmpSub ? "checked" : ""
      } /> 含下级部门</label>
      <span class="spacer"></span>
      <span class="sub">当前显示 ${list.length} 人</span>
    </div>`;

    let body;
    if (state.preview !== "normal") {
      body = renderPreview("employees", {
        icon: "users",
        title: "没有员工",
        message: "当前公司还没有员工档案。新增员工前，请先确认部门与岗位已维护。",
        action: `<button class="btn btn-primary" data-action="add-employee">${icon(
          "plus",
        )} 新增员工</button>`,
      });
    } else {
      body = renderEmployeeTable(list, {
        emptyTitle: "没有符合条件的员工",
        emptyMessage:
          state.cEmpSearch ||
          state.cEmpStatus !== "active" ||
          state.cEmpDept !== "all"
            ? "调整部门、状态或关键字后再试。"
            : "当前公司还没有员工档案。新增员工前，请先确认部门与岗位已维护。",
        emptyAction: list.length ? "clear-c-emp-filters" : "add-employee",
        emptyActionLabel: list.length ? "清除筛选" : "新增员工",
        viewAction: "c-view-employee",
        editAction: "edit-employee",
        resignAction: "resign-employee",
      });
    }

    return `${head}<div class="panel">${toolbar}${body}</div>
      <div class="notice mt-12">${icon(
        "info",
      )}<div>这里使用全宽列表 + 部门下拉筛选，不常驻部门树。适合员工数量较少、或更关注搜索与状态筛选的场景。</div></div>`;
  }

  function screenCOrganization() {
    const company = getCompany(state.companyId);
    const head = pageHead(
      "组织",
      `${esc(company.name)} · 部门与岗位放在同一个一级入口下；部门用左树 + 右详情，岗位用独立列表。`,
      `<div class="segmented" style="width:auto">
        <button class="${state.cOrgTab === "departments" ? "active" : ""}" data-action="c-org-tab" data-tab="departments">部门</button>
        <button class="${state.cOrgTab === "positions" ? "active" : ""}" data-action="c-org-tab" data-tab="positions">岗位</button>
      </div>`,
    );

    if (state.cOrgTab === "positions") {
      return `${head}<div class="panel">
        <div class="toolbar">
          <div class="search">${icon("search")}<input class="input" data-input="c-pos-search" placeholder="搜索岗位名称或编码" value="${attr(
            state.cPosSearch,
          )}" /></div>
          <span class="spacer"></span>
          <button class="btn btn-primary btn-sm" data-action="add-position">${icon("plus")} 新增岗位</button>
        </div>
        ${
          state.preview !== "normal"
            ? renderPreview("positions", {
                icon: "briefcase",
                title: "还没有岗位",
                message: "员工必须绑定岗位，建议先维护岗位档案。",
                action: `<button class="btn btn-primary" data-action="add-position">${icon(
                  "plus",
                )} 新建岗位</button>`,
              })
            : renderPositionTable(state.companyId, {
                query: state.cPosSearch,
                emptyTitle: "还没有岗位",
                emptyMessage:
                  "员工必须绑定岗位，建议先维护岗位档案。岗位是公司级可复用档案。",
              })
        }
      </div>`;
    }

    const depts = deptsOfCompany(state.companyId);
    if (
      state.cDeptId !== null &&
      (!getDept(state.cDeptId) || getDept(state.cDeptId).companyId !== state.companyId)
    ) {
      state.cDeptId = deptChildren(state.companyId, null)[0]?.id || null;
    }
    if (!state.cDeptId && depts.length) {
      state.cDeptId = deptChildren(state.companyId, null)[0]?.id || null;
    }

    const tree = `<aside class="tree-panel">
      <div class="tree-head">
        <div class="search">${icon("search")}<input class="input" data-input="c-dept-search" placeholder="搜索部门" value="${attr(
          state.cDeptSearch,
        )}" /></div>
      </div>
      <div class="tree-body">${renderDeptTree(state.companyId, {
        selectedId: state.cDeptId,
        query: state.cDeptSearch,
        action: "c-select-dept",
      })}</div>
      <div class="tree-foot"><button class="btn btn-outline btn-sm" data-action="add-dept">${icon(
        "plus",
      )} 新增顶层部门</button></div>
    </aside>`;

    return `${head}<div class="split">${tree}${renderCDeptDetail(
      getDept(state.cDeptId),
    )}</div>`;
  }

  function renderCDeptDetail(dept) {
    if (!dept) {
      return `<section class="detail">${renderPreview("departments", {
        icon: "network",
        title: "还没有部门",
        message: "先创建顶层部门，再逐级维护下级部门。",
        action: `<button class="btn btn-primary" data-action="add-dept">${icon(
          "plus",
        )} 新增顶层部门</button>`,
      })}</section>`;
    }

    const manager = getEmployee(dept.managerId);
    const children = deptChildren(state.companyId, dept.id);
    const deptPositions = positionsOfCompany(state.companyId).filter(
      (position) => position.deptId === dept.id,
    );
    const activeDirect = employeesInDept(dept.id, false, false).length;
    const activeSubtree = employeesInDept(dept.id, true, false).length;
    const resigned = employeesInDept(dept.id, true, true).length - activeSubtree;

    const header = `<div class="detail-head">
      <div>
        <div class="b-node-path">${deptPath(dept.id)
          .slice(0, -1)
          .map((item) => esc(item.name))
          .join(` ${icon("chevron-right")} `) || "顶层部门"}</div>
        <h2 class="detail-title">${esc(dept.name)} <span class="code">${esc(
          dept.code,
        )}</span> ${activeBadge(dept.active)}</h2>
        <div class="detail-sub">本部门 ${activeDirect} 人在职/试用期 · 含下级 ${activeSubtree} 人 · 档案共 ${
          activeSubtree + resigned
        } 人（离职 ${resigned} 人）</div>
      </div>
      <div class="actions">
        <button class="btn btn-outline btn-sm" data-action="edit-dept" data-id="${dept.id}">${icon(
          "edit",
        )} 编辑</button>
        <button class="btn btn-outline btn-sm" data-action="add-dept" data-parent="${dept.id}">${icon(
          "plus",
        )} 子部门</button>
        <button class="btn btn-ghost btn-sm danger-text" data-action="delete-dept" data-id="${dept.id}">${icon(
          "trash",
        )} 删除</button>
      </div>
    </div>`;

    if (state.preview !== "normal") {
      return `<section class="detail">${header}${renderPreview("departments", {
        icon: "network",
        title: "部门数据为空",
        message: "当前条件下没有可展示的部门数据。",
      })}</section>`;
    }

    return `<section class="detail">${header}
      <div class="detail-body">
        <div class="kv-grid">
          <dl class="kv">
            <dt>上级部门</dt><dd>${dept.parentId ? esc(deptPathLabel(dept.parentId)) : "无（顶层部门）"}</dd>
            <dt>负责人</dt><dd>${
              manager
                ? `${esc(manager.name)} <span class="sub">${esc(manager.no)}</span>`
                : '<span class="sub">未指定</span>'
            }</dd>
            <dt>排序</dt><dd>${dept.orderNo}</dd>
          </dl>
          <dl class="kv">
            <dt>状态</dt><dd>${activeBadge(dept.active)}</dd>
            <dt>默认岗位</dt><dd>${deptPositions.length} 个</dd>
            <dt>备注</dt><dd>${esc(dept.note || "—")}</dd>
          </dl>
        </div>

        <div class="panel mt-16">
          <div class="card-head"><h3>下级部门</h3><button class="btn btn-outline btn-sm" data-action="add-dept" data-parent="${dept.id}">${icon(
            "plus",
          )} 新增子部门</button></div>
          ${
            children.length
              ? `<div class="table-wrap"><table class="table">
                  <thead><tr><th>编码</th><th>部门</th><th>负责人</th><th>在职/试用期</th><th>状态</th><th></th></tr></thead>
                  <tbody>${children
                    .map((child) => {
                      const childManager = getEmployee(child.managerId);
                      return `<tr>
                        <td><span class="code">${esc(child.code)}</span></td>
                        <td><button class="name" style="border:0;background:none;padding:0" data-action="c-select-dept" data-id="${child.id}">${esc(
                          child.name,
                        )}</button></td>
                        <td>${childManager ? esc(childManager.name) : '<span class="sub">未指定</span>'}</td>
                        <td>${employeesInDept(child.id, true, false).length}</td>
                        <td>${activeBadge(child.active)}</td>
                        <td class="td-actions"><button class="btn btn-ghost btn-sm" data-action="c-select-dept" data-id="${child.id}">查看</button></td>
                      </tr>`;
                    })
                    .join("")}</tbody>
                </table></div>`
              : `<div class="empty" style="padding:28px 18px"><div class="empty-icon">${icon(
                  "network",
                )}</div><h3>暂无下级部门</h3><p>可以继续拆分，也可以保持当前层级。</p></div>`
          }
        </div>

        <div class="panel">
          <div class="card-head"><h3>默认部门为本部门的岗位</h3><button class="btn btn-outline btn-sm" data-action="add-position" data-dept="${dept.id}">${icon(
            "plus",
          )} 新增岗位</button></div>
          ${
            deptPositions.length
              ? `<div class="table-wrap"><table class="table">
                  <thead><tr><th>编码</th><th>岗位</th><th>员工数</th><th>状态</th><th></th></tr></thead>
                  <tbody>${deptPositions
                    .map(
                      (position) => `<tr>
                        <td><span class="code">${esc(position.code)}</span></td>
                        <td class="name">${esc(position.name)}</td>
                        <td>${positionEmployeeCount(position.id, true)}</td>
                        <td>${activeBadge(position.active)}</td>
                        <td class="td-actions"><button class="btn btn-ghost btn-sm" data-action="edit-position" data-id="${position.id}">编辑</button></td>
                      </tr>`,
                    )
                    .join("")}</tbody>
                </table></div>`
              : `<div class="empty" style="padding:28px 18px"><div class="empty-icon">${icon(
                  "briefcase",
                )}</div><h3>没有默认部门为本部门的岗位</h3><p>岗位是公司级档案，其他部门的员工也可以使用。</p></div>`
          }
        </div>
      </div>
    </section>`;
  }

  function screenCCostCenters() {
    const company = getCompany(state.companyId);
    const costs = costsOfCompany(state.companyId);
    const unassigned = unassignedEmployees(state.companyId, false).length;
    const totalBudget = costs.reduce(
      (sum, cost) => sum + Number(cost.budget || 0),
      0,
    );

    const head = pageHead(
      "成本中心",
      `${esc(company.name)} · 使用树形表格维护多级成本中心；预算与预警线只录入，本期不做统计。`,
      `<button class="btn btn-primary" data-action="add-cost">${icon(
        "plus",
      )} 新增成本中心</button>`,
    );

    const summary = `<div class="c-summary">
      <div class="stat"><div class="label">成本中心</div><div class="value">${costs.length}</div><div class="hint">启用 ${costs.filter((cost) => cost.active).length} 个</div></div>
      <div class="stat"><div class="label">在职/试用期员工</div><div class="value">${activeEmployeeCount(
        company.id,
      )}</div><div class="hint">按行政归属统计</div></div>
      <div class="stat clickable" data-action="open-unassigned" title="查看未分配员工"><div class="label">未分配员工</div><div class="value">${unassigned}</div><div class="hint">点击查看员工明细</div></div>
      <div class="stat"><div class="label">月度预算合计</div><div class="value" style="font-size:18px">${money(
        totalBudget,
      )}</div><div class="hint">0 = 不设预算</div></div>
    </div>`;

    const toolbar = `<div class="toolbar">
      <div class="search">${icon("search")}<input class="input" data-input="c-cost-search" placeholder="搜索成本中心名称或编码" value="${attr(
        state.cCostSearch,
      )}" /></div>
      <span class="spacer"></span>
      <span class="sub">点击名称查看详情；行内可编辑预算与预警线</span>
    </div>`;

    let table;
    if (state.preview !== "normal") {
      table = renderPreview("costcenters", {
        icon: "wallet",
        title: "还没有成本中心",
        message: "成本中心用于工资支出归集；员工可以没有成本中心，显示为未分配。",
        action: `<button class="btn btn-primary" data-action="add-cost">${icon(
          "plus",
        )} 新增成本中心</button>`,
      });
    } else {
      table = renderCCostTreeTable();
    }

    return `${head}${summary}<div class="panel">${toolbar}${table}</div>
      <div class="notice mt-12">${icon(
        "info",
      )}<div>「未分配」不是错误状态，也没有独立的成本中心实体；它只是员工成本归属为空时的视图。</div></div>`;
  }

  function renderCCostTreeTable() {
    const companyId = state.companyId;
    const query = state.cCostSearch.trim().toLowerCase();

    const matches = (cost) =>
      !query ||
      cost.name.toLowerCase().includes(query) ||
      cost.code.toLowerCase().includes(query);
    const subtreeMatches = (cost) =>
      matches(cost) ||
      costChildren(companyId, cost.id).some((child) => subtreeMatches(child));

    const roots = costChildren(companyId, null).filter(subtreeMatches);
    if (!roots.length) {
      return `<div class="empty">
        <div class="empty-icon">${icon("wallet")}</div>
        <h3>${query ? "没有匹配的成本中心" : "还没有成本中心"}</h3>
        <p>${query ? "调整关键字后再试。" : "成本中心与行政架构相互独立，可以稍后再维护。"}</p>
        ${
          query
            ? `<button class="btn btn-outline" data-action="clear-c-cost-filter">清除搜索</button>`
            : `<button class="btn btn-primary" data-action="add-cost">${icon("plus")} 新增成本中心</button>`
        }
      </div>`;
    }

    const rowsFor = (cost, depth) => {
      const children = costChildren(companyId, cost.id).filter(subtreeMatches);
      const expanded = query.length > 0 || state.cExpandedCosts.has(cost.id);
      const manager = getEmployee(cost.managerId);
      const count = employeesInCost(cost.id, true, false).length;
      const row = `<tr>
        <td>
          <div class="table-tree-name" style="padding-left:${depth * 18}px">
            ${
              children.length
                ? `<button class="twisty" data-action="c-toggle-cost" data-id="${cost.id}" aria-label="${
                    expanded ? "收起" : "展开"
                  }">${icon(expanded ? "chevron-down" : "chevron-right")}</button>`
                : '<span class="twisty"></span>'
            }
            <button class="name-btn" data-action="c-view-cost" data-id="${cost.id}">
              <span class="name">${esc(cost.name)}</span>
              <span class="sub" style="display:block">${esc(cost.code)}</span>
            </button>
          </div>
        </td>
        <td>${cost.parentId ? esc(getCost(cost.parentId)?.name || "—") : '<span class="sub">顶层</span>'}</td>
        <td>${manager ? esc(manager.name) : '<span class="sub">未指定</span>'}</td>
        <td class="nowrap">${money(cost.budget)}</td>
        <td>${cost.warnPct}%</td>
        <td>${count}</td>
        <td>${activeBadge(cost.active)}</td>
        <td class="td-actions">
          <button class="btn btn-ghost btn-sm" data-action="edit-cost" data-id="${cost.id}">编辑</button>
          <button class="btn btn-ghost btn-sm danger-text" data-action="delete-cost" data-id="${cost.id}">删除</button>
        </td>
      </tr>`;
      const childRows = expanded
        ? children.map((child) => rowsFor(child, depth + 1)).join("")
        : "";
      return row + childRows;
    };

    return `<div class="table-wrap"><table class="table">
      <thead><tr><th>成本中心</th><th>上级</th><th>负责人</th><th>月度预算</th><th>预警线</th><th>在职/试用期</th><th>状态</th><th></th></tr></thead>
      <tbody>${roots.map((cost) => rowsFor(cost, 0)).join("")}</tbody>
    </table></div>
    ${renderTableFooter(costsOfCompany(companyId).length, "员工数为含下级的在职/试用期人数")}`;
  }

  function screenCCompanies() {
    const company = getCompany(state.companyId);
    const head = pageHead(
      "公司",
      `以卡片展示公司档案；当前公司为「${esc(
        company.name,
      )}」。公司切换后，员工、组织、成本中心页面都会切到该公司。`,
      `<button class="btn btn-primary" data-action="add-company">${icon(
        "plus",
      )} 新增公司</button>`,
    );

    if (state.preview !== "normal") {
      return `${head}${renderPreview("companies", {
        icon: "building",
        title: "还没有公司",
        message: "创建第一家公司后，才能维护部门、岗位、员工与成本中心。",
        action: `<button class="btn btn-primary" data-action="add-company">${icon(
          "plus",
        )} 新增公司</button>`,
      })}`;
    }

    return `${head}<div class="cards">
      ${companies
        .map((item) => {
          const deptCount = deptsOfCompany(item.id).length;
          const positionCount = positionsOfCompany(item.id).length;
          const allEmployees = employeesOfCompany(item.id);
          const activeCount = allEmployees.filter(
            (employee) => employee.status !== "resigned",
          ).length;
          return `<article class="company-card">
            <div class="company-card-head">
              <div>
                <h3 class="company-card-title">${esc(item.name)} ${
                  item.id === state.companyId
                    ? '<span class="badge badge-blue">当前公司</span>'
                    : ""
                }</h3>
                <div class="sub" style="margin-top:4px"><span class="code">${esc(
                  item.code,
                )}</span> · ${esc(item.note || "—")}</div>
              </div>
              ${activeBadge(item.active)}
            </div>
            <div class="company-card-stats">
              <div><div class="label">部门</div><div class="value">${deptCount}</div></div>
              <div><div class="label">岗位</div><div class="value">${positionCount}</div></div>
              <div><div class="label">在职/试用期</div><div class="value">${activeCount}</div></div>
            </div>
            <div class="company-card-foot">
              ${
                item.id !== state.companyId
                  ? `<button class="btn btn-primary btn-sm" data-action="switch-company" data-company="${item.id}">切换为当前公司</button>`
                  : '<span class="sub">当前上下文</span>'
              }
              <span class="spacer"></span>
              <button class="btn btn-ghost btn-sm" data-action="edit-company" data-id="${item.id}">编辑</button>
              <button class="btn btn-ghost btn-sm danger-text" data-action="delete-company" data-id="${item.id}">删除</button>
            </div>
          </article>`;
        })
        .join("")}
    </div>`;
  }

  /* ================================================================ forms */

  let localSeq = 500;

  function nextId(prefix) {
    localSeq += 1;
    return `${prefix}${localSeq}`;
  }

  function asBool(value) {
    return value === true || value === "true";
  }

  function formTitle() {
    if (!state.form) return "";
    const names = {
      company: "公司",
      dept: "部门",
      position: "岗位",
      cost: "成本中心",
      employee: "员工",
    };
    return `${state.form.mode === "create" ? "新增" : "编辑"}${
      names[state.form.entity]
    }`;
  }

  function formSubtitle() {
    if (!state.form) return "";
    const subtitles = {
      company:
        "公司之间扁平，不设上下级；业务编码创建后不可修改，名称允许重复。",
      dept: "部门归属当前公司；上级部门不能选择自身或下级，编码创建后不可修改。",
      position:
        "岗位是公司级可复用档案；默认部门仅用于员工建档时带出，不限制员工实际部门。",
      cost: "成本中心与行政架构相互独立；0 表示不设预算，本期不做支出统计。",
      employee:
        "员工必须绑定部门与岗位；成本中心可留空。离职为终态，本期不做再入职。",
    };
    return subtitles[state.form.entity] || "";
  }

  function createDraft(entity, mode, id, ctx = {}) {
    if (entity === "company") {
      const company = id ? getCompany(id) : null;
      return {
        code: company?.code || "",
        name: company?.name || "",
        active: company ? company.active : true,
        note: company?.note || "",
      };
    }
    if (entity === "dept") {
      const dept = id ? getDept(id) : null;
      return {
        code: dept?.code || "",
        name: dept?.name || "",
        parentId: dept ? dept.parentId || "" : ctx.parentId || "",
        managerId: dept?.managerId || "",
        orderNo: dept?.orderNo ?? 0,
        active: dept ? dept.active : true,
        note: dept?.note || "",
      };
    }
    if (entity === "position") {
      const position = id ? getPosition(id) : null;
      return {
        code: position?.code || "",
        name: position?.name || "",
        deptId: position
          ? position.deptId || ""
          : ctx.deptId || "",
        orderNo: position?.orderNo ?? 0,
        active: position ? position.active : true,
        note: position?.note || "",
      };
    }
    if (entity === "cost") {
      const cost = id ? getCost(id) : null;
      return {
        code: cost?.code || "",
        name: cost?.name || "",
        parentId: cost ? cost.parentId || "" : ctx.parentId || "",
        managerId: cost?.managerId || "",
        budget: cost ? String(cost.budget) : "0",
        warnPct: cost ? String(cost.warnPct) : "85",
        orderNo: cost?.orderNo ?? 0,
        active: cost ? cost.active : true,
        note: cost?.note || "",
      };
    }
    const employee = id ? getEmployee(id) : null;
    return {
      no: employee?.no || "",
      name: employee?.name || "",
      gender: employee?.gender || "unknown",
      deptId: employee ? employee.deptId : ctx.deptId || "",
      positionId: employee ? employee.positionId : ctx.positionId || "",
      costId: employee ? employee.costId || "" : ctx.costId || "",
      managerId: employee?.managerId || "",
      status: employee?.status || "active",
      hireDate: employee?.hireDate || TODAY,
      resignDate: employee?.resignDate || "",
      contract: employee?.contract || "full_time",
      dailyHours: employee?.dailyHours ?? "",
      monthlyRest: employee?.monthlyRest ?? "",
      confidentiality: employee?.confidentiality ?? "",
      note: employee?.note || "",
    };
  }

  function openForm(entity, mode, id = null, ctx = {}) {
    const draft = createDraft(entity, mode, id, ctx);
    state.form = {
      entity,
      mode,
      id: id || null,
      draft,
      errors: {},
      ctx,
    };
    if (state.variant === "B" && entity === "employee") {
      state.overlay = null;
      state.bView = "employee-form";
      state.bTab = "employees";
      render();
      return;
    }
    state.overlay = { type: "form" };
    render();
  }

  function cancelForm() {
    state.form = null;
    state.overlay = null;
    if (state.variant === "B" && state.bView === "employee-form") {
      state.bView = "detail";
      state.bTab = "employees";
    }
    render();
  }

  function formFieldError(name) {
    return state.form?.errors?.[name];
  }

  function renderFormFields() {
    if (!state.form) return "";
    if (state.form.entity === "company") return renderCompanyFormFields();
    if (state.form.entity === "dept") return renderDeptFormFields();
    if (state.form.entity === "position") return renderPositionFormFields();
    if (state.form.entity === "cost") return renderCostFormFields();
    return renderEmployeeFormFields();
  }

  function renderCompanyFormFields() {
    const draft = state.form.draft;
    const editing = state.form.mode === "edit";
    return `<div class="form-section">
      <div class="form-section-head"><h4>公司信息</h4><p>业务编码用于导入与外部识别，创建后不可修改。</p></div>
      <div class="form-grid">
        ${fieldHtml(
          "公司编码",
          inputHtml("code", draft.code, {
            disabled: editing,
            placeholder: "如 RX",
            required: true,
          }),
          {
            required: true,
            error: formFieldError("code"),
            errorName: "code",
            hint: "大写字母、数字、下划线或短横线，1–32 位",
          },
        )}
        ${fieldHtml(
          "公司名称",
          inputHtml("name", draft.name, {
            placeholder: "如 荣新矿业",
            required: true,
          }),
          { required: true, error: formFieldError("name"), errorName: "name" },
        )}
        ${fieldHtml(
          "状态",
          switchHtml("active", asBool(draft.active)),
          {
            error: formFieldError("active"),
            errorName: "active",
            hint: "停用后不出现在新建/编辑选择器中；已存在的引用保留。",
          },
        )}
        ${fieldHtml(
          "备注",
          textareaHtml("note", draft.note, { placeholder: "可选" }),
          { full: true, error: formFieldError("note"), errorName: "note" },
        )}
      </div>
    </div>`;
  }

  function renderDeptFormFields() {
    const draft = state.form.draft;
    const editing = state.form.mode === "edit";
    const deptId = state.form.id;
    return `<div class="form-section">
      <div class="form-section-head"><h4>部门信息</h4><p>部门归属当前公司；编码在公司内唯一，创建后不可修改。</p></div>
      <div class="form-grid">
        ${fieldHtml(
          "部门编码",
          inputHtml("code", draft.code, {
            disabled: editing,
            placeholder: "如 D3",
            required: true,
          }),
          {
            required: true,
            error: formFieldError("code"),
            errorName: "code",
            hint: "公司内唯一，大写字母、数字、下划线或短横线",
          },
        )}
        ${fieldHtml(
          "部门名称",
          inputHtml("name", draft.name, {
            placeholder: "如 生产部",
            required: true,
          }),
          { required: true, error: formFieldError("name"), errorName: "name" },
        )}
        ${fieldHtml(
          "上级部门",
          selectHtml(
            "form:parentId",
            draft.parentId,
            deptParentOptions(state.companyId, deptId, draft.parentId),
          ),
          {
            error: formFieldError("parentId"),
            errorName: "parentId",
            hint: "不能选择自身或下级部门；停用部门不能作为新上级。",
          },
        )}
        ${fieldHtml(
          "负责人",
          selectHtml(
            "form:managerId",
            draft.managerId,
            managerOptions(state.companyId, draft.managerId),
          ),
          {
            error: formFieldError("managerId"),
            errorName: "managerId",
            hint: "可指定在职或试用期员工；可跨部门。",
          },
        )}
        ${fieldHtml(
          "排序",
          inputHtml("orderNo", draft.orderNo, {
            type: "number",
            step: "1",
            placeholder: "0",
          }),
          { error: formFieldError("orderNo"), errorName: "orderNo" },
        )}
        ${fieldHtml(
          "状态",
          switchHtml("active", asBool(draft.active)),
          {
            error: formFieldError("active"),
            errorName: "active",
            hint: "停用是自下而上的；存在启用中的子部门或员工时不能停用。",
          },
        )}
        ${fieldHtml(
          "备注",
          textareaHtml("note", draft.note, { placeholder: "可选" }),
          { full: true, error: formFieldError("note"), errorName: "note" },
        )}
      </div>
    </div>`;
  }

  function renderPositionFormFields() {
    const draft = state.form.draft;
    const editing = state.form.mode === "edit";
    return `<div class="form-section">
      <div class="form-section-head"><h4>岗位信息</h4><p>岗位是公司级可复用档案；默认部门只是建档时的带出值。</p></div>
      <div class="form-grid">
        ${fieldHtml(
          "岗位编码",
          inputHtml("code", draft.code, {
            disabled: editing,
            placeholder: "如 POS-ADMIN",
            required: true,
          }),
          {
            required: true,
            error: formFieldError("code"),
            errorName: "code",
            hint: "公司内唯一，创建后不可修改",
          },
        )}
        ${fieldHtml(
          "岗位名称",
          inputHtml("name", draft.name, {
            placeholder: "如 行政专员",
            required: true,
          }),
          { required: true, error: formFieldError("name"), errorName: "name" },
        )}
        ${fieldHtml(
          "默认部门",
          selectHtml("form:deptId", draft.deptId, [
            { value: "", label: "不设默认部门" },
            ...deptSelectOptions(state.companyId, draft.deptId),
          ]),
          {
            error: formFieldError("deptId"),
            errorName: "deptId",
            hint: "可选；员工实际部门可以与默认部门不同",
          },
        )}
        ${fieldHtml(
          "排序",
          inputHtml("orderNo", draft.orderNo, {
            type: "number",
            step: "1",
            placeholder: "0",
          }),
          { error: formFieldError("orderNo"), errorName: "orderNo" },
        )}
        ${fieldHtml(
          "状态",
          switchHtml("active", asBool(draft.active)),
          {
            error: formFieldError("active"),
            errorName: "active",
            hint: "存在在职/试用期员工引用时不能停用。",
          },
        )}
        ${fieldHtml(
          "备注",
          textareaHtml("note", draft.note, { placeholder: "可选" }),
          { full: true, error: formFieldError("note"), errorName: "note" },
        )}
      </div>
    </div>`;
  }

  function renderCostFormFields() {
    const draft = state.form.draft;
    const editing = state.form.mode === "edit";
    return `<div class="form-section">
      <div class="form-section-head"><h4>成本中心信息</h4><p>与行政架构相互独立；预算与预警线只录入，本期不做统计。</p></div>
      <div class="form-grid">
        ${fieldHtml(
          "成本中心编码",
          inputHtml("code", draft.code, {
            disabled: editing,
            placeholder: "如 CO-PROD",
            required: true,
          }),
          {
            required: true,
            error: formFieldError("code"),
            errorName: "code",
            hint: "公司内唯一，创建后不可修改",
          },
        )}
        ${fieldHtml(
          "成本中心名称",
          inputHtml("name", draft.name, {
            placeholder: "如 生产成本中心",
            required: true,
          }),
          { required: true, error: formFieldError("name"), errorName: "name" },
        )}
        ${fieldHtml(
          "上级成本中心",
          selectHtml(
            "form:parentId",
            draft.parentId,
            costParentOptions(state.companyId, state.form.id, draft.parentId),
          ),
          {
            error: formFieldError("parentId"),
            errorName: "parentId",
            hint: "不能选择自身或下级成本中心",
          },
        )}
        ${fieldHtml(
          "负责人",
          selectHtml(
            "form:managerId",
            draft.managerId,
            managerOptions(state.companyId, draft.managerId),
          ),
          {
            error: formFieldError("managerId"),
            errorName: "managerId",
            hint: "可指定在职或试用期员工",
          },
        )}
        ${fieldHtml(
          "月度预算",
          inputHtml("budget", draft.budget, {
            type: "number",
            min: "0",
            step: "0.01",
            placeholder: "0",
          }),
          {
            error: formFieldError("budget"),
            errorName: "budget",
            hint: "0 = 不设预算；本期不做支出统计",
          },
        )}
        ${fieldHtml(
          "预警线（%）",
          inputHtml("warnPct", draft.warnPct, {
            type: "number",
            min: "1",
            max: "100",
            step: "1",
            placeholder: "85",
          }),
          { error: formFieldError("warnPct"), errorName: "warnPct" },
        )}
        ${fieldHtml(
          "排序",
          inputHtml("orderNo", draft.orderNo, {
            type: "number",
            step: "1",
            placeholder: "0",
          }),
          { error: formFieldError("orderNo"), errorName: "orderNo" },
        )}
        ${fieldHtml(
          "状态",
          switchHtml("active", asBool(draft.active)),
          {
            error: formFieldError("active"),
            errorName: "active",
            hint: "存在启用中的下级或员工引用时不能停用。",
          },
        )}
        ${fieldHtml(
          "备注",
          textareaHtml("note", draft.note, { placeholder: "可选" }),
          { full: true, error: formFieldError("note"), errorName: "note" },
        )}
      </div>
    </div>`;
  }

  function renderEmployeeFormFields() {
    const draft = state.form.draft;
    const editing = state.form.mode === "edit";
    const employee = editing ? getEmployee(state.form.id) : null;
    const locked = Boolean(employee && employee.status === "resigned");
    const companyId = state.companyId;
    const depts = deptsOfCompany(companyId);
    const companyPositions = positionsOfCompany(companyId);
    const statusOptions = statusOptionsForEmployee(
      state.form.mode,
      employee?.status || "active",
    );
    const lockedAttr = locked ? "disabled" : "";

    return `<div class="form-section">
      <div class="form-section-head"><h4>基本信息</h4><p>工号是全局唯一业务编码，创建后不可修改；离职员工只允许修改备注与离职日期。</p></div>
      ${
        locked
          ? `<div class="notice danger mb-12">${icon(
              "lock",
            )}<div>该员工已离职。部门、岗位、成本中心、合同类型、入职日期与状态均锁定，仅可修改备注与离职日期。</div></div>`
          : ""
      }
      ${
        !depts.length
          ? `<div class="notice warn mb-12">${icon(
              "alert",
            )}<div>当前公司还没有部门。员工必须绑定部门与岗位，请先维护组织架构。</div></div>`
          : ""
      }
      ${
        !companyPositions.length
          ? `<div class="notice warn mb-12">${icon(
              "alert",
            )}<div>当前公司还没有岗位。员工必须绑定岗位，请先创建岗位。</div><button class="btn btn-outline btn-sm" data-action="goto-positions">去创建岗位</button></div>`
          : ""
      }
      <div class="form-grid">
        ${fieldHtml(
          "工号",
          inputHtml("no", draft.no, {
            disabled: editing || locked,
            placeholder: "如 E1001",
            required: true,
          }),
          {
            required: true,
            error: formFieldError("no"),
            errorName: "no",
            hint: "全局唯一，大写字母、数字、下划线或短横线",
          },
        )}
        ${fieldHtml(
          "姓名",
          inputHtml("name", draft.name, {
            placeholder: "如 张建国",
            required: true,
            disabled: locked,
          }),
          { required: true, error: formFieldError("name"), errorName: "name" },
        )}
        ${fieldHtml(
          "性别",
          selectHtml(
            "form:gender",
            draft.gender,
            [
              { value: "male", label: "男" },
              { value: "female", label: "女" },
              { value: "unknown", label: "未说明" },
            ],
            lockedAttr,
          ),
          { hint: "可留空为未说明" },
        )}
        ${fieldHtml(
          "合同类型",
          selectHtml(
            "form:contract",
            draft.contract,
            [
              { value: "full_time", label: "全职" },
              { value: "part_time", label: "兼职" },
              { value: "intern", label: "实习" },
              { value: "labor", label: "劳务" },
            ],
            lockedAttr,
          ),
          { required: true, error: formFieldError("contract"), errorName: "contract" },
        )}
        ${fieldHtml(
          "入职日期",
          inputHtml("hireDate", draft.hireDate, {
            type: "date",
            disabled: locked,
            required: true,
          }),
          {
            required: true,
            error: formFieldError("hireDate"),
            errorName: "hireDate",
            hint: "不晚于今天",
          },
        )}
        ${fieldHtml(
          "状态",
          selectHtml(
            "form:status",
            draft.status,
            statusOptions,
            lockedAttr,
          ),
          {
            error: formFieldError("status"),
            errorName: "status",
            hint: locked
              ? "离职为终态"
              : "在职不能改回试用期；离职后不可恢复",
          },
        )}
        ${
          draft.status === "resigned"
            ? fieldHtml(
                "离职日期",
                inputHtml("resignDate", draft.resignDate, {
                  type: "date",
                  required: true,
                  max: TODAY,
                  disabled: false,
                }),
                {
                  required: true,
                  error: formFieldError("resignDate"),
                  errorName: "resignDate",
                  hint: "不早于入职日期、不晚于今天",
                },
              )
            : ""
        }
      </div>
    </div>

    <div class="form-section">
      <div class="form-section-head"><h4>行政归属</h4><p>部门与岗位必填，且必须属于当前公司；已停用的归属不能重新选中。</p></div>
      <div class="form-grid">
        ${fieldHtml(
          "部门",
          selectHtml(
            "form:deptId",
            draft.deptId,
            [
              { value: "", label: "请选择部门" },
              ...deptSelectOptions(companyId, draft.deptId),
            ],
            lockedAttr,
          ),
          {
            required: true,
            error: formFieldError("deptId"),
            errorName: "deptId",
            hint: "部门树中的任意层级均可选",
          },
        )}
        ${fieldHtml(
          "岗位",
          selectHtml(
            "form:positionId",
            draft.positionId,
            [
              { value: "", label: "请选择岗位" },
              ...positionSelectOptions(companyId, draft.positionId),
            ],
            lockedAttr,
          ),
          {
            required: true,
            error: formFieldError("positionId"),
            errorName: "positionId",
            hint: "岗位是公司级档案；默认部门仅用于带出",
          },
        )}
        ${fieldHtml(
          "直属上级",
          selectHtml(
            "form:managerId",
            draft.managerId,
            employeeManagerOptions(companyId, state.form.id, draft.managerId),
            lockedAttr,
          ),
          {
            full: true,
            error: formFieldError("managerId"),
            errorName: "managerId",
            hint: "可空；不能选择自己或造成汇报线成环；已离职员工不能成为新上级。",
          },
        )}
      </div>
    </div>

    <div class="form-section">
      <div class="form-section-head"><h4>成本归属</h4><p>成本中心与行政架构相互独立，可留空为「未分配」。</p></div>
      <div class="form-grid">
        ${fieldHtml(
          "成本中心",
          selectHtml(
            "form:costId",
            draft.costId,
            costSelectOptions(companyId, draft.costId),
            lockedAttr,
          ),
          {
            full: true,
            error: formFieldError("costId"),
            errorName: "costId",
            hint: "可留空；停用成本中心不能用于新归属",
          },
        )}
      </div>
    </div>

    <div class="form-section">
      <div class="form-section-head"><h4>更多档案字段</h4><p>仅作档案记录，本期不参与工资、考勤或任何计算。</p></div>
      <div class="form-grid">
        ${fieldHtml(
          "每日工时",
          inputHtml("dailyHours", draft.dailyHours, {
            type: "number",
            min: "0",
            max: "24",
            step: "0.01",
            placeholder: "如 8",
            disabled: locked,
          }),
          {
            error: formFieldError("dailyHours"),
            errorName: "dailyHours",
            hint: "0 < 工时 ≤ 24",
          },
        )}
        ${fieldHtml(
          "月休天数",
          inputHtml("monthlyRest", draft.monthlyRest, {
            type: "number",
            min: "0",
            step: "1",
            placeholder: "如 8",
            disabled: locked,
          }),
          { error: formFieldError("monthlyRest"), errorName: "monthlyRest" },
        )}
        ${fieldHtml(
          "保密等级",
          inputHtml("confidentiality", draft.confidentiality, {
            type: "number",
            min: "1",
            max: "5",
            step: "1",
            placeholder: "1–5",
            disabled: locked,
          }),
          {
            error: formFieldError("confidentiality"),
            errorName: "confidentiality",
            hint: "1–5，可留空",
          },
        )}
        ${fieldHtml(
          "备注",
          textareaHtml("note", draft.note, {
            placeholder: "可选",
            disabled: false,
          }),
          { full: true, error: formFieldError("note"), errorName: "note" },
        )}
      </div>
    </div>`;
  }

  function renderFormOverlay() {
    if (!state.form) return "";
    const isSheet = state.variant === "A";
    const body = renderFormFields();
    const head = `<div class="${isSheet ? "sheet-head" : "modal-head"}">
      <div>
        <h2 class="${isSheet ? "sheet-title" : "modal-title"}">${formTitle()}</h2>
        <p class="${isSheet ? "sheet-sub" : "modal-sub"}">${formSubtitle()}</p>
      </div>
      <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
    </div>`;
    const foot = `<div class="${isSheet ? "sheet-foot" : "modal-foot"}">
      <button class="btn btn-outline" data-action="cancel-form">取消</button>
      <button class="btn btn-primary" data-action="save-form">保存</button>
    </div>`;

    if (isSheet) {
      return `<div class="sheet-backdrop" data-action="close-overlay"></div>
        <div class="sheet" role="dialog" aria-modal="true">
          ${head}
          <div class="sheet-body">${body}</div>
          ${foot}
        </div>`;
    }

    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal" role="dialog" aria-modal="true">
        ${head}
        <div class="modal-body">${body}</div>
        ${foot}
      </div>`;
  }

  function renderBEmployeeFormPanel() {
    if (!state.form) {
      state.bView = "detail";
      return renderBRight();
    }
    return `<div class="b-inline-form">
      <div class="b-node-head">
        <div>
          <button class="b-back" data-action="cancel-form">${icon(
            "arrow-left",
          )} 返回员工列表</button>
          <h2 class="b-node-title">${formTitle()}</h2>
          <div class="b-node-sub">${formSubtitle()}</div>
        </div>
      </div>
      <div class="b-inline-form-body">${renderEmployeeFormFields()}</div>
      <div class="b-inline-form-foot">
        <button class="btn btn-outline" data-action="cancel-form">取消</button>
        <button class="btn btn-primary" data-action="save-form">保存</button>
      </div>
    </div>`;
  }

  function renderEmployeeDetailBody(employee) {
    const dept = getDept(employee.deptId);
    const position = getPosition(employee.positionId);
    const cost = getCost(employee.costId);
    const manager = getEmployee(employee.managerId);

    return `<div class="panel">
      <div class="card-head"><h3>基本信息</h3><span class="sub">工号 ${esc(
        employee.no,
      )}</span></div>
      <div class="detail-body">
        <div class="kv-grid">
          <dl class="kv">
            <dt>姓名</dt><dd>${esc(employee.name)}</dd>
            <dt>性别</dt><dd>${GENDER[employee.gender] || "未说明"}</dd>
            <dt>合同类型</dt><dd>${CONTRACT[employee.contract] || employee.contract}</dd>
            <dt>入职日期</dt><dd>${esc(employee.hireDate)}</dd>
          </dl>
          <dl class="kv">
            <dt>状态</dt><dd>${statusBadge(employee.status)}</dd>
            <dt>离职日期</dt><dd>${employee.resignDate ? esc(employee.resignDate) : "—"}</dd>
            <dt>每日工时</dt><dd>${employee.dailyHours || "—"}</dd>
            <dt>月休天数</dt><dd>${employee.monthlyRest ?? "—"}</dd>
          </dl>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="card-head"><h3>行政归属</h3><span class="sub">行政架构</span></div>
      <div class="detail-body">
        <dl class="kv">
          <dt>部门</dt><dd>${dept ? `${esc(deptPathLabel(dept.id))} <span class="code">${esc(dept.code)}</span>` : "—"}</dd>
          <dt>岗位</dt><dd>${position ? `${esc(position.name)} <span class="code">${esc(position.code)}</span>` : "—"}</dd>
          <dt>直属上级</dt><dd>${
            manager
              ? `${esc(manager.name)} <span class="sub">${esc(manager.no)} · ${
                  STATUS[manager.status]?.label || manager.status
                }</span>`
              : '<span class="sub">无</span>'
          }</dd>
        </dl>
      </div>
    </div>

    <div class="panel">
      <div class="card-head"><h3>成本归属</h3><span class="sub">成本架构</span></div>
      <div class="detail-body">
        <dl class="kv">
          <dt>成本中心</dt><dd>${
            cost
              ? `${esc(costPathLabel(cost.id))} <span class="code">${esc(cost.code)}</span>`
              : '<span class="badge badge-gray">未分配</span>'
          }</dd>
          <dt>保密等级</dt><dd>${employee.confidentiality ?? "—"}</dd>
          <dt>备注</dt><dd>${esc(employee.note || "—")}</dd>
        </dl>
      </div>
    </div>

    ${
      employee.status === "resigned"
        ? `<div class="notice info mt-12">${icon(
            "lock",
          )}<div>该员工已离职。离职为生命周期终点，本期不做再入职；档案保留，部门、岗位与成本中心引用仍会阻止组织删除。</div></div>`
        : `<div class="notice info mt-12">${icon(
            "info",
          )}<div>状态机：试用期可转正；在职不能改回试用期；在职/试用期可办理离职；离职后不可恢复。</div></div>`
    }`;
  }

  function renderEmployeeDetailOverlay() {
    const employee = getEmployee(state.overlay.id);
    if (!employee) return "";
    const isSheet = state.variant === "A";
    const head = `<div class="${isSheet ? "sheet-head" : "modal-head"}">
      <div>
        <h2 class="${isSheet ? "sheet-title" : "modal-title"}">${esc(
          employee.name,
        )} <span class="code">${esc(employee.no)}</span> ${statusBadge(
          employee.status,
        )}</h2>
        <p class="${isSheet ? "sheet-sub" : "modal-sub"}">${esc(
          deptPathLabel(employee.deptId),
        )} · ${esc(getPosition(employee.positionId)?.name || "未绑定岗位")}</p>
      </div>
      <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon(
        "x",
      )}</button>
    </div>`;
    const actions = `<div class="${isSheet ? "sheet-foot" : "modal-foot"}">
      <button class="btn btn-outline" data-action="close-overlay">关闭</button>
      <button class="btn btn-primary" data-action="edit-employee" data-id="${employee.id}">${icon(
        "edit",
      )} 编辑</button>
      ${
        employee.status !== "resigned"
          ? `<button class="btn btn-outline" data-action="resign-employee" data-id="${employee.id}">办理离职</button>`
          : ""
      }
    </div>`;
    const body = `<div class="${isSheet ? "sheet-body" : "modal-body"}">${renderEmployeeDetailBody(
      employee,
    )}</div>`;

    if (isSheet) {
      return `<div class="sheet-backdrop" data-action="close-overlay"></div>
        <div class="sheet" role="dialog" aria-modal="true">${head}${body}${actions}</div>`;
    }
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal lg" role="dialog" aria-modal="true">${head}${body}${actions}</div>`;
  }

  /* ================================================================ overlays */

  function renderOverlayRoot() {
    const root = document.getElementById("overlay-root");
    if (!root) return;
    let html = "";

    if (state.overlay) {
      const type = state.overlay.type;
      if (type === "form") html += renderFormOverlay();
      else if (type === "employee-detail") html += renderEmployeeDetailOverlay();
      else if (type === "blocked") html += renderBlockedOverlay();
      else if (type === "confirm-delete") html += renderConfirmDeleteOverlay();
      else if (type === "company-modal") html += renderCompanyModal();
      else if (type === "unassigned") html += renderUnassignedOverlay();
      else if (type === "cost-detail") html += renderCostDetailOverlay();
      else if (type === "flow") html += renderFlowOverlay();
      else if (type === "diff") html += renderDiffOverlay();
    }

    if (state.toast) {
      html += `<div class="toast ${state.toast.type}">${icon(
        state.toast.type === "error" ? "alert" : "check",
      )}<span>${esc(state.toast.message)}</span></div>`;
    }

    root.innerHTML = html;
  }

  function renderBlockedOverlay() {
    const overlay = state.overlay;
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal sm" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div><h2 class="modal-title">${esc(
            overlay.title,
          )}</h2><p class="modal-sub">操作被引用约束阻止</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon(
            "x",
          )}</button>
        </div>
        <div class="modal-body">
          <div class="notice danger">${icon("alert")}<div>${esc(
            overlay.message,
          )}</div></div>
          ${
            overlay.details?.length
              ? `<div class="blocked-list">${overlay.details
                  .map(
                    (detail) =>
                      `<div class="blocked-item">${icon(
                        "flag",
                      )}<span>${esc(detail)}</span></div>`,
                  )
                  .join("")}</div>`
              : ""
          }
        </div>
        <div class="modal-foot"><button class="btn btn-primary" data-action="close-overlay">知道了</button></div>
      </div>`;
  }

  function renderConfirmDeleteOverlay() {
    const overlay = state.overlay;
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal sm" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div><h2 class="modal-title">${esc(
            overlay.title,
          )}</h2><p class="modal-sub">删除后不可恢复</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon(
            "x",
          )}</button>
        </div>
        <div class="modal-body">
          <div class="notice warn">${icon("alert")}<div>${esc(
            overlay.message,
          )}</div></div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-danger" data-action="confirm-delete" data-entity="${overlay.entity}" data-id="${overlay.id}">确认删除</button>
        </div>
      </div>`;
  }

  function renderCompanyModal() {
    return `<div class="overlay-backdrop" data-action="close-overlay"></div>
      <div class="overlay-card" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div><h2 class="modal-title">公司管理</h2><p class="modal-sub">公司之间扁平，不设上下级；切换当前公司会影响左侧组织树与所有基础管理页面。</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon(
            "x",
          )}</button>
        </div>
        <div class="modal-body">
          <div class="row mb-12">
            <button class="btn btn-primary" data-action="add-company">${icon(
              "plus",
            )} 新增公司</button>
            <span class="spacer"></span>
            <span class="sub">当前公司：${esc(
              getCompany(state.companyId)?.name || "—",
            )}</span>
          </div>
          <div class="panel">${renderCompanyTable()}</div>
          <div class="notice info mt-12">${icon(
            "info",
          )}<div>删除公司前必须先清空其部门、岗位、成本中心与员工；当前原型中「荣新建设」没有组织数据，可用于体验删除确认。</div></div>
        </div>
        <div class="modal-foot"><button class="btn btn-outline" data-action="close-overlay">关闭</button></div>
      </div>`;
  }

  function renderUnassignedOverlay() {
    const list = unassignedEmployees(state.companyId, true);
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal lg" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div><h2 class="modal-title">未分配员工 <span class="badge badge-gray">${
            list.length
          } 人</span></h2><p class="modal-sub">员工没有成本中心归属时的视图；含离职员工，不是独立的成本中心实体。</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon(
            "x",
          )}</button>
        </div>
        <div class="modal-body">
          <div class="notice warn">${icon(
            "alert",
          )}<div>未分配不是错误状态。可以在员工编辑表单中补充成本中心；本期不做工资支出统计。</div></div>
          <div class="panel mt-12">
            ${
              list.length
                ? renderMiniEmployeeTable(list)
                : `<div class="empty" style="padding:32px 18px"><div class="empty-icon">${icon(
                    "check",
                  )}</div><h3>没有未分配员工</h3><p>当前公司所有员工都有成本中心归属。</p></div>`
            }
          </div>
        </div>
        <div class="modal-foot"><button class="btn btn-outline" data-action="close-overlay">关闭</button></div>
      </div>`;
  }

  function renderCostDetailOverlay() {
    const cost = getCost(state.overlay.id);
    if (!cost) return "";
    const manager = getEmployee(cost.managerId);
    const children = costChildren(state.companyId, cost.id);
    const directEmployees = employees.filter(
      (employee) => employee.costId === cost.id,
    );
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal lg" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div>
            <h2 class="modal-title">${esc(cost.name)} <span class="code">${esc(
              cost.code,
            )}</span> ${activeBadge(cost.active)}</h2>
            <p class="modal-sub">${esc(
              costPathLabel(cost.id),
            )} · 直接归属 ${directEmployees.length} 人（含离职）</p>
          </div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon(
            "x",
          )}</button>
        </div>
        <div class="modal-body">
          <div class="kv-grid">
            <dl class="kv">
              <dt>上级</dt><dd>${cost.parentId ? esc(costPathLabel(cost.parentId)) : "无（顶层）"}</dd>
              <dt>负责人</dt><dd>${
                manager
                  ? `${esc(manager.name)} <span class="sub">${esc(manager.no)}</span>`
                  : '<span class="sub">未指定</span>'
              }</dd>
              <dt>排序</dt><dd>${cost.orderNo}</dd>
            </dl>
            <dl class="kv">
              <dt>状态</dt><dd>${activeBadge(cost.active)}</dd>
              <dt>预警线</dt><dd>${cost.warnPct}%</dd>
              <dt>备注</dt><dd>${esc(cost.note || "—")}</dd>
            </dl>
          </div>
          <div class="card mt-16">
            <div class="card-body">
              <div class="budget-line"><span>月度工资预算</span><strong>${money(
                cost.budget,
              )}</strong></div>
              <div class="progress"><span></span></div>
              <div class="progress-label"><span>本期未做工资统计</span><span>预警线 ${cost.warnPct}%</span></div>
            </div>
          </div>
          <div class="panel mt-12">
            <div class="card-head"><h3>下级成本中心</h3><button class="btn btn-outline btn-sm" data-action="add-cost" data-parent="${cost.id}">${icon(
              "plus",
            )} 新增</button></div>
            ${
              children.length
                ? `<div class="table-wrap"><table class="table">
                    <thead><tr><th>编码</th><th>名称</th><th>预算</th><th>在职/试用期</th><th>状态</th></tr></thead>
                    <tbody>${children
                      .map(
                        (child) => `<tr>
                          <td><span class="code">${esc(child.code)}</span></td>
                          <td class="name">${esc(child.name)}</td>
                          <td>${money(child.budget)}</td>
                          <td>${employeesInCost(child.id, true, false).length}</td>
                          <td>${activeBadge(child.active)}</td>
                        </tr>`,
                      )
                      .join("")}</tbody>
                  </table></div>`
                : `<div class="empty" style="padding:26px 18px"><h3>暂无下级成本中心</h3><p>成本中心支持多级。</p></div>`
            }
          </div>
          <div class="panel">
            <div class="card-head"><h3>直接归属员工</h3><span class="sub">含离职，仅直接归属</span></div>
            ${
              directEmployees.length
                ? renderMiniEmployeeTable(directEmployees)
                : `<div class="empty" style="padding:26px 18px"><h3>暂无直接归属员工</h3><p>下级成本中心的员工不会重复显示。</p></div>`
            }
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-ghost danger-text" data-action="delete-cost" data-id="${cost.id}">${icon(
            "trash",
          )} 删除</button>
          <span class="spacer"></span>
          <button class="btn btn-outline" data-action="edit-cost" data-id="${cost.id}">${icon(
            "edit",
          )} 编辑</button>
          <button class="btn btn-outline" data-action="add-cost" data-parent="${cost.id}">${icon(
            "plus",
          )} 新增子成本中心</button>
          <button class="btn btn-primary" data-action="close-overlay">关闭</button>
        </div>
      </div>`;
  }

  /* ================================================================ save */

  function failForm() {
    render();
    showToast("请检查表单中的错误", "error");
  }

  function finishForm(message) {
    state.form = null;
    state.overlay = null;
    render();
    showToast(message);
  }

  function saveForm() {
    if (!state.form) return;
    const form = state.form;
    const draft = form.draft;
    form.errors = {};
    let valid = true;
    const addError = (field, message) => {
      if (!form.errors[field]) form.errors[field] = message;
      valid = false;
    };
    const companyId = state.companyId;
    const codePattern = /^[A-Z0-9_-]{1,32}$/;

    if (form.entity === "company") {
      const code = (draft.code || "").trim().toUpperCase();
      const name = (draft.name || "").trim();
      const note = (draft.note || "").trim();
      const active = asBool(draft.active);
      const original = form.id ? getCompany(form.id) : null;
      if (!code) addError("code", "请输入公司编码");
      else if (!codePattern.test(code))
        addError("code", "编码只能包含大写字母、数字、下划线或短横线，1–32 位");
      else if (
        companies.some(
          (company) =>
            company.code.toUpperCase() === code && company.id !== form.id,
        )
      )
        addError("code", "公司编码已存在");
      if (!name) addError("name", "请输入公司名称");
      else if (name.length > 100) addError("name", "公司名称不能超过 100 个字符");
      if (note.length > 500) addError("note", "备注不能超过 500 个字符");

      if (original?.active && !active) {
        const activeDepts = deptsOfCompany(form.id).filter(
          (dept) => dept.active,
        ).length;
        const activePositions = positionsOfCompany(form.id).filter(
          (position) => position.active,
        ).length;
        const activeCosts = costsOfCompany(form.id).filter(
          (cost) => cost.active,
        ).length;
        const activeEmployees = employeesOfCompany(form.id).filter(
          (employee) => employee.status !== "resigned",
        ).length;
        const reasons = [];
        if (activeDepts) reasons.push(`${activeDepts} 个启用部门`);
        if (activePositions) reasons.push(`${activePositions} 个启用岗位`);
        if (activeCosts) reasons.push(`${activeCosts} 个启用成本中心`);
        if (activeEmployees)
          reasons.push(`${activeEmployees} 名在职/试用期员工`);
        if (reasons.length) {
          addError("active", `不能停用公司：仍有 ${reasons.join("、")}。`);
        }
      }

      if (!valid) return failForm();

      if (form.mode === "create") {
        companies.push({
          id: nextId("c"),
          code,
          name,
          active,
          note,
        });
      } else {
        const company = getCompany(form.id);
        if (!company) return failForm();
        Object.assign(company, { code, name, active, note });
      }
      return finishForm(form.mode === "create" ? "公司已创建" : "公司已保存");
    }

    if (form.entity === "dept") {
      const code = (draft.code || "").trim().toUpperCase();
      const name = (draft.name || "").trim();
      const note = (draft.note || "").trim();
      const parentId = draft.parentId || null;
      const managerId = draft.managerId || null;
      const orderNo = Number(draft.orderNo);
      const active = asBool(draft.active);
      const original = form.id ? getDept(form.id) : null;

      if (!code) addError("code", "请输入部门编码");
      else if (!codePattern.test(code))
        addError("code", "编码只能包含大写字母、数字、下划线或短横线，1–32 位");
      else if (
        deptsOfCompany(companyId).some(
          (dept) =>
            dept.code.toUpperCase() === code && dept.id !== form.id,
        )
      )
        addError("code", "部门编码在当前公司内已存在");
      if (!name) addError("name", "请输入部门名称");
      else if (name.length > 100) addError("name", "部门名称不能超过 100 个字符");
      if (note.length > 500) addError("note", "备注不能超过 500 个字符");
      if (!Number.isInteger(orderNo)) addError("orderNo", "排序必须是整数");

      if (parentId) {
        const parent = getDept(parentId);
        if (!parent || parent.companyId !== companyId) {
          addError("parentId", "上级部门不存在或不属于当前公司");
        } else if (
          parentId === form.id ||
          (form.id && isDescendantDept(parentId, form.id))
        ) {
          addError("parentId", "不能选择自身或下级部门作为上级");
        } else if (!parent.active && parentId !== original?.parentId) {
          addError("parentId", "上级部门已停用，不能作为新上级");
        } else if (
          active &&
          deptPath(parentId).some((item) => !item.active)
        ) {
          addError("parentId", "启用部门要求所有上级部门均启用");
        }
      }
      if (managerId) {
        const manager = getEmployee(managerId);
        if (!manager || inferCompanyFromDept(manager.deptId) !== companyId) {
          addError("managerId", "负责人不存在或不属于当前公司");
        } else if (manager.status === "resigned") {
          addError("managerId", "已离职员工不能成为部门负责人");
        }
      }

      if (active) {
        const company = getCompany(companyId);
        if (!company?.active) addError("active", "所属公司已停用，不能启用部门");
      }

      if (original?.active && !active) {
        const activeChildren = departments.filter(
          (dept) => dept.parentId === form.id && dept.active,
        ).length;
        const activeEmployees = employees.filter(
          (employee) =>
            employee.deptId === form.id && employee.status !== "resigned",
        ).length;
        const reasons = [];
        if (activeChildren) reasons.push(`${activeChildren} 个启用下级部门`);
        if (activeEmployees)
          reasons.push(`${activeEmployees} 名在职/试用期员工`);
        if (reasons.length) {
          addError("active", `不能停用部门：仍有 ${reasons.join("、")}。`);
        }
      }

      if (!valid) return failForm();

      let saved;
      if (form.mode === "create") {
        saved = {
          id: nextId("d"),
          companyId,
          code,
          name,
          parentId,
          managerId,
          orderNo,
          active,
          note,
        };
        departments.push(saved);
      } else {
        saved = getDept(form.id);
        if (!saved) return failForm();
        Object.assign(saved, { code, name, parentId, managerId, orderNo, active, note });
      }

      if (parentId) state.expandedDepts.add(parentId);
      if (state.variant === "A" && state.aScreen === "departments") {
        state.aDeptId = saved.id;
      }
      if (state.variant === "B") {
        state.bTree = "dept";
        state.bNodeId = saved.id;
        state.bView = "detail";
        state.bTab = "overview";
      }
      if (state.variant === "C") {
        state.cScreen = "organization";
        state.cOrgTab = "departments";
        state.cDeptId = saved.id;
      }
      return finishForm(form.mode === "create" ? "部门已创建" : "部门已保存");
    }

    if (form.entity === "position") {
      const code = (draft.code || "").trim().toUpperCase();
      const name = (draft.name || "").trim();
      const note = (draft.note || "").trim();
      const deptId = draft.deptId || null;
      const orderNo = Number(draft.orderNo);
      const active = asBool(draft.active);
      const original = form.id ? getPosition(form.id) : null;

      if (!code) addError("code", "请输入岗位编码");
      else if (!codePattern.test(code))
        addError("code", "编码只能包含大写字母、数字、下划线或短横线，1–32 位");
      else if (
        positionsOfCompany(companyId).some(
          (position) =>
            position.code.toUpperCase() === code && position.id !== form.id,
        )
      )
        addError("code", "岗位编码在当前公司内已存在");
      if (!name) addError("name", "请输入岗位名称");
      else if (name.length > 100) addError("name", "岗位名称不能超过 100 个字符");
      if (note.length > 500) addError("note", "备注不能超过 500 个字符");
      if (!Number.isInteger(orderNo)) addError("orderNo", "排序必须是整数");

      if (deptId) {
        const dept = getDept(deptId);
        if (!dept || dept.companyId !== companyId) {
          addError("deptId", "默认部门不存在或不属于当前公司");
        } else if (!dept.active && deptId !== original?.deptId) {
          addError("deptId", "默认部门已停用，不能作为新的默认部门");
        }
      }

      if (active) {
        const company = getCompany(companyId);
        if (!company?.active) addError("active", "所属公司已停用，不能启用岗位");
      }

      if (original?.active && !active) {
        const activeEmployees = employees.filter(
          (employee) =>
            employee.positionId === form.id &&
            employee.status !== "resigned",
        ).length;
        if (activeEmployees) {
          addError(
            "active",
            `不能停用岗位：仍有 ${activeEmployees} 名在职/试用期员工。`,
          );
        }
      }

      if (!valid) return failForm();

      let saved;
      if (form.mode === "create") {
        saved = {
          id: nextId("p"),
          companyId,
          code,
          name,
          deptId,
          orderNo,
          active,
          note,
        };
        positions.push(saved);
      } else {
        saved = getPosition(form.id);
        if (!saved) return failForm();
        Object.assign(saved, { code, name, deptId, orderNo, active, note });
      }

      if (state.variant === "B" && state.bTree === "dept" && state.bNodeId !== "all") {
        state.bView = "detail";
        state.bTab = "positions";
      }
      return finishForm(form.mode === "create" ? "岗位已创建" : "岗位已保存");
    }

    if (form.entity === "cost") {
      const code = (draft.code || "").trim().toUpperCase();
      const name = (draft.name || "").trim();
      const note = (draft.note || "").trim();
      const parentId = draft.parentId || null;
      const managerId = draft.managerId || null;
      const orderNo = Number(draft.orderNo);
      const budget = Number(draft.budget === "" ? 0 : draft.budget);
      const warnPct = Number(draft.warnPct === "" ? 85 : draft.warnPct);
      const active = asBool(draft.active);
      const original = form.id ? getCost(form.id) : null;

      if (!code) addError("code", "请输入成本中心编码");
      else if (!codePattern.test(code))
        addError("code", "编码只能包含大写字母、数字、下划线或短横线，1–32 位");
      else if (
        costsOfCompany(companyId).some(
          (cost) => cost.code.toUpperCase() === code && cost.id !== form.id,
        )
      )
        addError("code", "成本中心编码在当前公司内已存在");
      if (!name) addError("name", "请输入成本中心名称");
      else if (name.length > 100)
        addError("name", "成本中心名称不能超过 100 个字符");
      if (note.length > 500) addError("note", "备注不能超过 500 个字符");
      if (!Number.isInteger(orderNo)) addError("orderNo", "排序必须是整数");
      if (!Number.isFinite(budget) || budget < 0)
        addError("budget", "预算必须是大于等于 0 的数字");
      if (!Number.isInteger(warnPct) || warnPct < 1 || warnPct > 100)
        addError("warnPct", "预警线必须是 1–100 的整数");

      if (parentId) {
        const parent = getCost(parentId);
        if (!parent || parent.companyId !== companyId) {
          addError("parentId", "上级成本中心不存在或不属于当前公司");
        } else if (
          parentId === form.id ||
          (form.id && isDescendantCost(parentId, form.id))
        ) {
          addError("parentId", "不能选择自身或下级成本中心作为上级");
        } else if (!parent.active && parentId !== original?.parentId) {
          addError("parentId", "上级成本中心已停用，不能作为新上级");
        } else if (
          active &&
          costPath(parentId).some((item) => !item.active)
        ) {
          addError("parentId", "启用成本中心要求所有上级均启用");
        }
      }
      if (managerId) {
        const manager = getEmployee(managerId);
        if (!manager || inferCompanyFromDept(manager.deptId) !== companyId) {
          addError("managerId", "负责人不存在或不属于当前公司");
        } else if (manager.status === "resigned") {
          addError("managerId", "已离职员工不能成为成本中心负责人");
        }
      }

      if (active) {
        const company = getCompany(companyId);
        if (!company?.active)
          addError("active", "所属公司已停用，不能启用成本中心");
      }

      if (original?.active && !active) {
        const activeChildren = costCenters.filter(
          (cost) => cost.parentId === form.id && cost.active,
        ).length;
        const activeEmployees = employees.filter(
          (employee) =>
            employee.costId === form.id && employee.status !== "resigned",
        ).length;
        const reasons = [];
        if (activeChildren)
          reasons.push(`${activeChildren} 个启用下级成本中心`);
        if (activeEmployees)
          reasons.push(`${activeEmployees} 名在职/试用期员工`);
        if (reasons.length) {
          addError("active", `不能停用成本中心：仍有 ${reasons.join("、")}。`);
        }
      }

      if (!valid) return failForm();

      let saved;
      if (form.mode === "create") {
        saved = {
          id: nextId("cc"),
          companyId,
          code,
          name,
          parentId,
          managerId,
          budget,
          warnPct,
          orderNo,
          active,
          note,
        };
        costCenters.push(saved);
      } else {
        saved = getCost(form.id);
        if (!saved) return failForm();
        Object.assign(saved, {
          code,
          name,
          parentId,
          managerId,
          budget,
          warnPct,
          orderNo,
          active,
          note,
        });
      }

      if (parentId) state.expandedCosts.add(parentId);
      if (parentId) state.cExpandedCosts.add(parentId);
      if (state.variant === "A" && state.aScreen === "costcenters") {
        state.aCostId = saved.id;
      }
      if (state.variant === "B") {
        state.bTree = "cost";
        state.bNodeId = saved.id;
        state.bView = "detail";
        state.bTab = "overview";
      }
      if (state.variant === "C") {
        state.cScreen = "costcenters";
      }
      return finishForm(
        form.mode === "create" ? "成本中心已创建" : "成本中心已保存",
      );
    }

    // employee
    const original = form.id ? getEmployee(form.id) : null;
    const locked = Boolean(original && original.status === "resigned");
    const no = (draft.no || "").trim().toUpperCase();
    const name = (draft.name || "").trim();
    const note = (draft.note || "").trim();

    if (locked) {
      if (draft.status !== "resigned") {
        addError("status", "离职为终态，本期不支持再入职");
      }
      if (!draft.resignDate) addError("resignDate", "请选择离职日期");
      else if (draft.resignDate < original.hireDate)
        addError("resignDate", "离职日期不能早于入职日期");
      else if (draft.resignDate > TODAY)
        addError("resignDate", "离职日期不能晚于今天");
      if (note.length > 500) addError("note", "备注不能超过 500 个字符");
      if (!valid) return failForm();

      original.resignDate = draft.resignDate;
      original.note = note;
      return finishForm("员工档案已保存");
    }

    if (!no) addError("no", "请输入工号");
    else if (!codePattern.test(no))
      addError("no", "工号只能包含大写字母、数字、下划线或短横线，1–32 位");
    else if (
      employees.some(
        (employee) =>
          employee.no.toUpperCase() === no && employee.id !== form.id,
      )
    )
      addError("no", "工号已存在");
    if (!name) addError("name", "请输入姓名");
    else if (name.length > 100) addError("name", "姓名不能超过 100 个字符");
    if (note.length > 500) addError("note", "备注不能超过 500 个字符");

    const dept = getDept(draft.deptId);
    if (!dept) addError("deptId", "请选择部门");
    else if (dept.companyId !== companyId)
      addError("deptId", "部门不属于当前公司");

    const position = getPosition(draft.positionId);
    if (!position) addError("positionId", "请选择岗位");
    else if (position.companyId !== companyId)
      addError("positionId", "岗位不属于当前公司");

    const cost = draft.costId ? getCost(draft.costId) : null;
    if (draft.costId && !cost) addError("costId", "成本中心不存在");
    else if (cost && cost.companyId !== companyId)
      addError("costId", "成本中心不属于当前公司");

    if (!draft.hireDate) addError("hireDate", "请选择入职日期");
    else if (draft.hireDate > TODAY)
      addError("hireDate", "入职日期不能晚于今天");

    if (!["active", "probation", "resigned"].includes(draft.status)) {
      addError("status", "请选择员工状态");
    }
    if (form.mode === "create" && draft.status === "resigned") {
      addError("status", "新建员工不能直接设为离职；请通过办理离职产生");
    }
    if (original) {
      if (original.status === "active" && draft.status === "probation") {
        addError("status", "在职不能改回试用期");
      }
      if (original.status === "resigned" && draft.status !== "resigned") {
        addError("status", "离职为终态，本期不支持再入职");
      }
    }

    if (draft.status === "resigned") {
      if (!draft.resignDate) addError("resignDate", "请选择离职日期");
      else if (draft.hireDate && draft.resignDate < draft.hireDate)
        addError("resignDate", "离职日期不能早于入职日期");
      else if (draft.resignDate > TODAY)
        addError("resignDate", "离职日期不能晚于今天");
    }

    if (!draft.contract) addError("contract", "请选择合同类型");

    if (!["active", "probation", "resigned"].includes(draft.status)) {
      // already handled above
    }

    const effectiveStatus = draft.status;
    if (dept && !dept.active && effectiveStatus !== "resigned" && original?.deptId !== dept.id) {
      addError("deptId", "部门已停用，不能用于新归属");
    }
    if (
      position &&
      !position.active &&
      effectiveStatus !== "resigned" &&
      original?.positionId !== position.id
    ) {
      addError("positionId", "岗位已停用，不能用于新归属");
    }
    if (
      cost &&
      !cost.active &&
      effectiveStatus !== "resigned" &&
      original?.costId !== cost.id
    ) {
      addError("costId", "成本中心已停用，不能用于新归属");
    }

    if (draft.managerId) {
      const manager = getEmployee(draft.managerId);
      if (!manager || inferCompanyFromDept(manager.deptId) !== companyId) {
        addError("managerId", "直属上级不存在或不属于当前公司");
      } else if (manager.id === form.id) {
        addError("managerId", "直属上级不能是自己");
      } else if (managerCycle(form.id, manager.id)) {
        addError("managerId", "直属上级会造成汇报线成环");
      } else if (
        manager.status === "resigned" &&
        manager.id !== original?.managerId
      ) {
        addError("managerId", "已离职员工不能成为新上级");
      }
    }

    if (draft.dailyHours !== "" && draft.dailyHours !== null) {
      const hours = Number(draft.dailyHours);
      if (!Number.isFinite(hours) || hours <= 0 || hours > 24) {
        addError("dailyHours", "每日工时应大于 0 且不超过 24");
      }
    }
    if (draft.monthlyRest !== "" && draft.monthlyRest !== null) {
      const rest = Number(draft.monthlyRest);
      if (!Number.isInteger(rest) || rest < 0) {
        addError("monthlyRest", "月休天数必须是不小于 0 的整数");
      }
    }
    if (draft.confidentiality !== "" && draft.confidentiality !== null) {
      const level = Number(draft.confidentiality);
      if (!Number.isInteger(level) || level < 1 || level > 5) {
        addError("confidentiality", "保密等级必须是 1–5 的整数");
      }
    }

    if (!valid) return failForm();

    const record = {
      no,
      name,
      gender: draft.gender || "unknown",
      deptId: dept.id,
      positionId: position.id,
      costId: cost ? cost.id : null,
      managerId: draft.managerId || null,
      status: draft.status,
      hireDate: draft.hireDate,
      resignDate: draft.status === "resigned" ? draft.resignDate : null,
      contract: draft.contract,
      dailyHours:
        draft.dailyHours === "" || draft.dailyHours === null
          ? null
          : String(draft.dailyHours),
      monthlyRest:
        draft.monthlyRest === "" || draft.monthlyRest === null
          ? null
          : Number(draft.monthlyRest),
      confidentiality:
        draft.confidentiality === "" || draft.confidentiality === null
          ? null
          : Number(draft.confidentiality),
      note,
    };

    let saved;
    if (form.mode === "create") {
      saved = { id: nextId("e"), ...record };
      employees.push(saved);
    } else {
      saved = original;
      if (!saved) return failForm();
      Object.assign(saved, record);
    }

    if (state.variant === "A") {
      state.aEmpDeptId = saved.deptId;
      state.aEmpStatus = "active";
      state.aEmpSearch = "";
      state.aEmpSub = true;
    }
    if (state.variant === "B") {
      state.bTree = "dept";
      state.bNodeId = saved.deptId;
      state.bView = "detail";
      state.bTab = "employees";
      state.bEmpSearch = "";
      state.bEmpStatus = "active";
      state.bEmpSub = true;
    }
    if (state.variant === "C") {
      state.cEmpDept = saved.deptId;
      state.cEmpStatus = "active";
      state.cEmpSearch = "";
      state.cEmpSub = true;
    }
    return finishForm(
      form.mode === "create" ? "员工已创建" : "员工档案已保存",
    );
  }

  /* ================================================================ delete */

  function listNames(items, suffix = "") {
    if (!items.length) return "";
    const names = items
      .slice(0, 5)
      .map((item) => item.name)
      .join("、");
    return `${names}${items.length > 5 ? " 等" : ""}${suffix}`;
  }

  function attemptDelete(entity, id) {
    if (entity === "company") {
      const company = getCompany(id);
      if (!company) return;
      const depts = deptsOfCompany(id);
      const positionList = positionsOfCompany(id);
      const costList = costsOfCompany(id);
      const employeeList = employeesOfCompany(id);
      if (depts.length || positionList.length || costList.length || employeeList.length) {
        state.overlay = {
          type: "blocked",
          title: "无法删除公司",
          message: `公司「${company.name}」下仍有组织与员工数据，必须先清空后才能删除。`,
          details: [
            `部门 ${depts.length} 个${depts.length ? `：${listNames(depts)}` : ""}`,
            `岗位 ${positionList.length} 个`,
            `成本中心 ${costList.length} 个`,
            `员工 ${employeeList.length} 人（含离职）`,
          ],
        };
        render();
        return;
      }
      state.overlay = {
        type: "confirm-delete",
        entity: "company",
        id,
        title: "删除公司？",
        message: `将永久删除公司「${company.name}」。该操作不可恢复。`,
      };
      render();
      return;
    }

    if (entity === "dept") {
      const dept = getDept(id);
      if (!dept) return;
      const children = departments.filter((item) => item.parentId === id);
      const employeeList = employees.filter((item) => item.deptId === id);
      if (children.length || employeeList.length) {
        state.overlay = {
          type: "blocked",
          title: "无法删除部门",
          message: `部门「${dept.name}」仍被下级部门或员工引用。请先调整员工归属并删除下级部门。`,
          details: [
            `下级部门 ${children.length} 个${
              children.length ? `：${listNames(children)}` : ""
            }`,
            `员工 ${employeeList.length} 人（含离职）${
              employeeList.length ? `：${listNames(employeeList)}` : ""
            }`,
            "默认部门指向该部门的岗位会被置空，不阻止删除",
          ],
        };
        render();
        return;
      }
      state.overlay = {
        type: "confirm-delete",
        entity: "dept",
        id,
        title: "删除部门？",
        message: `将永久删除部门「${dept.name}」。默认部门指向该部门的岗位会被置空。`,
      };
      render();
      return;
    }

    if (entity === "position") {
      const position = getPosition(id);
      if (!position) return;
      const employeeList = employees.filter(
        (item) => item.positionId === id,
      );
      if (employeeList.length) {
        state.overlay = {
          type: "blocked",
          title: "无法删除岗位",
          message: `岗位「${position.name}」仍被员工引用。请先把员工调整到其他岗位。`,
          details: [
            `员工 ${employeeList.length} 人（含离职）${
              employeeList.length ? `：${listNames(employeeList)}` : ""
            }`,
          ],
        };
        render();
        return;
      }
      state.overlay = {
        type: "confirm-delete",
        entity: "position",
        id,
        title: "删除岗位？",
        message: `将永久删除岗位「${position.name}」。`,
      };
      render();
      return;
    }

    const cost = getCost(id);
    if (!cost) return;
    const children = costCenters.filter((item) => item.parentId === id);
    const employeeList = employees.filter((item) => item.costId === id);
    if (children.length || employeeList.length) {
      state.overlay = {
        type: "blocked",
        title: "无法删除成本中心",
        message: `成本中心「${cost.name}」仍被下级成本中心或员工引用。请先迁移员工成本归属并删除下级。`,
        details: [
          `下级成本中心 ${children.length} 个${
            children.length ? `：${listNames(children)}` : ""
          }`,
          `员工 ${employeeList.length} 人（含离职）${
            employeeList.length ? `：${listNames(employeeList)}` : ""
          }`,
        ],
      };
      render();
      return;
    }
    state.overlay = {
      type: "confirm-delete",
      entity: "cost",
      id,
      title: "删除成本中心？",
      message: `将永久删除成本中心「${cost.name}」。`,
    };
    render();
  }

  function performDelete(entity, id) {
    if (entity === "company") {
      const index = companies.findIndex((item) => item.id === id);
      if (index < 0) return;
      companies.splice(index, 1);
      if (state.companyId === id) {
        state.companyId = companies[0]?.id || "";
        resetCompanyScopedState();
      }
      state.overlay = null;
      syncUrl();
      render();
      showToast("公司已删除");
      return;
    }

    if (entity === "dept") {
      const index = departments.findIndex((item) => item.id === id);
      if (index < 0) return;
      departments.splice(index, 1);
      positions.forEach((position) => {
        if (position.deptId === id) position.deptId = null;
      });
      if (state.aDeptId === id) {
        state.aDeptId = deptChildren(state.companyId, null)[0]?.id || null;
      }
      if (state.bNodeId === id) {
        state.bNodeId = deptChildren(state.companyId, null)[0]?.id || "all";
        state.bView = "detail";
        state.bTab = "overview";
      }
      if (state.cDeptId === id) {
        state.cDeptId = deptChildren(state.companyId, null)[0]?.id || null;
      }
      state.overlay = null;
      render();
      showToast("部门已删除");
      return;
    }

    if (entity === "position") {
      const index = positions.findIndex((item) => item.id === id);
      if (index < 0) return;
      positions.splice(index, 1);
      state.overlay = null;
      render();
      showToast("岗位已删除");
      return;
    }

    const index = costCenters.findIndex((item) => item.id === id);
    if (index < 0) return;
    costCenters.splice(index, 1);
    if (state.aCostId === id) {
      state.aCostId = costChildren(state.companyId, null)[0]?.id || "all";
    }
    if (state.bNodeId === id) {
      state.bNodeId = costChildren(state.companyId, null)[0]?.id || "all";
      state.bView = "detail";
      state.bTab = "overview";
    }
    state.overlay = null;
    render();
    showToast("成本中心已删除");
  }

  /* ================================================================ flow / diff */

  function renderFlowOverlay() {
    const names = {
      A: "方案 A · 五模块独立",
      B: "方案 B · 组织工作台",
      C: "方案 C · 顶栏导航",
    };
    return `<div class="overlay-backdrop" data-action="close-overlay"></div>
      <div class="overlay-card" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div><h2 class="modal-title">页面流程 · ${names[state.variant]}</h2><p class="modal-sub">这是一张讨论用的流程图，不是最终信息架构。</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon(
            "x",
          )}</button>
        </div>
        <div class="modal-body">${renderFlowContent()}</div>
        <div class="modal-foot"><button class="btn btn-outline" data-action="close-overlay">关闭</button></div>
      </div>`;
  }

  function renderFlowContent() {
    if (state.variant === "A") {
      return `<div class="flow-grid">
        <div>
          <div class="flow-section-title">导航与入口</div>
          <div class="flow-row">
            <span class="flow-node soft">登录</span><span class="flow-arrow">→</span>
            <span class="flow-node soft">仪表盘</span><span class="flow-arrow">→</span>
            <span class="flow-node primary">基础管理（侧边栏分组）</span>
          </div>
          <p class="flow-note">侧边栏保留「仪表盘 / 管理后台」，移除 Items；基础管理下五个独立入口。</p>
        </div>
        <div>
          <div class="flow-section-title">主路径</div>
          <div class="flow-row">
            <span class="flow-node">公司</span><span class="flow-arrow">→</span>
            <span class="flow-node">切换当前公司</span><span class="flow-arrow">→</span>
            <span class="flow-node">部门树</span><span class="flow-arrow">→</span>
            <span class="flow-node">岗位</span><span class="flow-arrow">→</span>
            <span class="flow-node primary">员工列表</span><span class="flow-arrow">→</span>
            <span class="flow-node">员工详情 / 编辑</span><span class="flow-arrow">→</span>
            <span class="flow-node">成本中心</span>
          </div>
          <p class="flow-note">公司切换器在顶栏，作用于部门、岗位、员工、成本中心四个页面；公司页管理全部公司。</p>
        </div>
        <div>
          <div class="flow-section-title">员工页关键交互</div>
          <div class="flow-row">
            <span class="flow-node">左侧部门树</span><span class="flow-arrow">→</span>
            <span class="flow-node">状态 / 关键字筛选</span><span class="flow-arrow">→</span>
            <span class="flow-node">全宽表格</span><span class="flow-arrow">→</span>
            <span class="flow-node primary">右侧详情 / 编辑抽屉</span>
          </div>
          <p class="flow-note">新建/编辑员工按「基本信息 / 行政归属 / 成本归属 / 汇报关系」分组；离职在员工详情或表格行内发起。</p>
        </div>
        <div>
          <div class="flow-section-title">删除与异常</div>
          <div class="flow-row">
            <span class="flow-node">删除部门 / 岗位 / 成本中心 / 公司</span><span class="flow-arrow">→</span>
            <span class="flow-node primary">引用检查</span><span class="flow-arrow">→</span>
            <span class="flow-node soft">阻止弹窗（列出引用）</span>
          </div>
          <p class="flow-note">无引用时进入确认删除；有下级或员工（含离职）时展示中文阻止原因。</p>
        </div>
      </div>`;
    }

    if (state.variant === "B") {
      return `<div class="flow-grid">
        <div>
          <div class="flow-section-title">导航与入口</div>
          <div class="flow-row">
            <span class="flow-node soft">登录</span><span class="flow-arrow">→</span>
            <span class="flow-node primary">基础管理（侧边栏单入口）</span><span class="flow-arrow">→</span>
            <span class="flow-node">选择当前公司</span>
          </div>
          <p class="flow-note">侧边栏只保留一个基础管理入口；公司切换与公司管理都在工作台顶部。</p>
        </div>
        <div>
          <div class="flow-section-title">工作台主路径</div>
          <div class="flow-row">
            <span class="flow-node">行政架构 / 成本架构</span><span class="flow-arrow">→</span>
            <span class="flow-node">选择节点</span><span class="flow-arrow">→</span>
            <span class="flow-node primary">右侧概览</span><span class="flow-arrow">→</span>
            <span class="flow-node">员工 / 岗位 / 下级</span><span class="flow-arrow">→</span>
            <span class="flow-node">就地表单</span>
          </div>
          <p class="flow-note">左树常驻；右侧用标签页切换概览、员工、岗位、下级，避免五个独立页面之间跳转。</p>
        </div>
        <div>
          <div class="flow-section-title">员工</div>
          <div class="flow-row">
            <span class="flow-node">节点员工标签</span><span class="flow-arrow">→</span>
            <span class="flow-node primary">右侧就地展开表单</span><span class="flow-arrow">→</span>
            <span class="flow-node">保存后回到员工列表</span>
          </div>
          <p class="flow-note">员工表单不离开工作台；部门、岗位、成本中心与公司档案使用居中弹窗。</p>
        </div>
        <div>
          <div class="flow-section-title">公司与成本</div>
          <div class="flow-row">
            <span class="flow-node">管理公司</span><span class="flow-arrow">→</span>
            <span class="flow-node">公司弹窗</span><span class="flow-arrow">→</span>
            <span class="flow-node">切换 / 新增 / 编辑 / 删除</span>
          </div>
          <p class="flow-note">成本架构通过左侧树切换；未分配作为树尾部入口，不建独立实体。</p>
        </div>
      </div>`;
    }

    return `<div class="flow-grid">
      <div>
        <div class="flow-section-title">导航与入口</div>
        <div class="flow-row">
          <span class="flow-node soft">登录</span><span class="flow-arrow">→</span>
          <span class="flow-node primary">顶部导航</span><span class="flow-arrow">→</span>
          <span class="flow-node">员工</span><span class="flow-arrow">/</span>
          <span class="flow-node">组织</span><span class="flow-arrow">/</span>
          <span class="flow-node">成本中心</span><span class="flow-arrow">/</span>
          <span class="flow-node">公司</span>
        </div>
        <p class="flow-note">无侧边栏；公司切换器在顶栏右侧；管理后台保留为顶栏文本入口，不扩展。</p>
      </div>
      <div>
        <div class="flow-section-title">员工</div>
        <div class="flow-row">
          <span class="flow-node">全宽列表</span><span class="flow-arrow">→</span>
          <span class="flow-node">部门下拉 / 状态 / 关键字</span><span class="flow-arrow">→</span>
          <span class="flow-node primary">居中弹窗详情 / 编辑</span>
        </div>
        <p class="flow-note">部门树不常驻；部门筛选放在工具栏下拉中，换取表格横向空间。</p>
      </div>
      <div>
        <div class="flow-section-title">组织</div>
        <div class="flow-row">
          <span class="flow-node">组织页签：部门 / 岗位</span><span class="flow-arrow">→</span>
          <span class="flow-node">部门：左树 + 右详情</span><span class="flow-arrow">/</span>
          <span class="flow-node">岗位：全宽表格</span>
        </div>
        <p class="flow-note">部门与岗位合并到一个一级入口，减少顶栏项目；岗位仍是公司级档案。</p>
      </div>
      <div>
        <div class="flow-section-title">成本中心</div>
        <div class="flow-row">
          <span class="flow-node">汇总卡片</span><span class="flow-arrow">→</span>
          <span class="flow-node primary">树形表格</span><span class="flow-arrow">→</span>
          <span class="flow-node">居中弹窗详情</span>
        </div>
        <p class="flow-note">「未分配」作为汇总卡片和筛选入口，不建独立实体；预算与预警线在表格列与详情中展示。</p>
      </div>
    </div>`;
  }

  function renderDiffOverlay() {
    const rows = [
      [
        "公司层级",
        "支持集团 / 多公司层级",
        "多公司，但公司之间扁平，不设上级公司",
      ],
      [
        "部门层级",
        "公司 → 部门两级为主，部门内可再分级",
        "部门支持任意多级",
      ],
      [
        "部门成本中心",
        "department.cost_center 文本字段",
        "移除；成本归属统一走 employee.cost_org_id",
      ],
      [
        "岗位绑定",
        "岗位绑定薪酬构成、计算方案、工作日参数",
        "本期只保留岗位档案与可选默认部门，不绑定计算配置",
      ],
      [
        "员工标识",
        "employee_id 业务主键",
        "UUID v7 主键 + 独立 employee_no 业务编码（ADR-0003）",
      ],
      [
        "调岗历史",
        "保留调岗/生效日期/审批流",
        "直接编辑当前归属，不保留历史",
      ],
      [
        "再入职",
        "未明确",
        "离职为终态，本期不做再入职",
      ],
      [
        "权限",
        "RBAC + 部门数据可见范围",
        "沿用现有登录；所有登录用户拥有基础管理全部权限",
      ],
      [
        "Excel 导入",
        "人员/组织、岗位、成本架构批量导入",
        "本期不做导入与导出模板",
      ],
      [
        "成本中心预算",
        "工资支出统计、预算对比、预警三态",
        "只录入 budget / warn_pct，不做统计与预警",
      ],
      [
        "其他模块",
        "考勤、薪酬、账号角色、员工端 H5",
        "均不在本期；Items 演示页移除，Admin 保留不扩展",
      ],
    ];
    return `<div class="overlay-backdrop" data-action="close-overlay"></div>
      <div class="overlay-card" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div><h2 class="modal-title">与需求文档的差异（本期范围）</h2><p class="modal-sub">原型只覆盖基础管理；差异来自已确认的 map 边界，不是遗漏。</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon(
            "x",
          )}</button>
        </div>
        <div class="modal-body">
          <table class="diff-table">
            <thead><tr><th>主题</th><th>需求文档</th><th>本期原型 / 范围</th></tr></thead>
            <tbody>${rows
              .map(
                (row) =>
                  `<tr><td>${row[0]}</td><td class="old">${row[1]}</td><td>${row[2]}</td></tr>`,
              )
              .join("")}</tbody>
          </table>
          <div class="notice info mt-12">${icon(
            "info",
          )}<div>术语以 <code>GLOSSARY.md</code> 为准；主键与双标识见 <code>docs/adr/0003-uuid-v7-with-business-codes.md</code>。</div></div>
        </div>
        <div class="modal-foot"><button class="btn btn-outline" data-action="close-overlay">关闭</button></div>
      </div>`;
  }

  /* ================================================================ events */

  function switchVariant(delta) {
    const order = ["A", "B", "C"];
    let index = order.indexOf(state.variant);
    index = (index + delta + order.length) % order.length;
    state.variant = order[index];
    state.companyMenuOpen = false;
    state.overlay = null;
    state.form = null;
    state.preview = "normal";
    state.toast = null;
    state.aDeptSearch = "";
    state.aEmpSearch = "";
    state.aEmpStatus = "active";
    state.aEmpDeptId = "all";
    state.aEmpSub = true;
    state.aCostSearch = "";
    state.aPosSearch = "";
    state.aPosStatus = "all";
    state.bTreeSearch = "";
    state.bEmpSearch = "";
    state.bEmpStatus = "active";
    state.bEmpSub = true;
    state.bView = "detail";
    state.bTab = "overview";
    state.cEmpSearch = "";
    state.cEmpStatus = "active";
    state.cEmpDept = "all";
    state.cEmpSub = true;
    state.cDeptSearch = "";
    state.cPosSearch = "";
    state.cCostSearch = "";
    if (
      !["companies", "departments", "employees", "positions", "costcenters"].includes(
        state.aScreen,
      )
    ) {
      state.aScreen = "employees";
    }
    if (
      !["employees", "organization", "costcenters", "companies"].includes(
        state.cScreen,
      )
    ) {
      state.cScreen = "employees";
    }
    normalizeBNode();
    syncUrl();
    render();
  }

  function companyContextForEmployeeForm(actionEl) {
    let deptId = actionEl.dataset.dept || "";
    let costId = actionEl.dataset.cost || "";
    if (!deptId) {
      if (state.variant === "A" && state.aEmpDeptId !== "all") {
        deptId = state.aEmpDeptId;
      } else if (state.variant === "B") {
        if (
          state.bTree === "dept" &&
          state.bNodeId !== "all" &&
          state.bNodeId !== "unassigned" &&
          getDept(state.bNodeId)
        ) {
          deptId = state.bNodeId;
        }
      } else if (state.variant === "C" && state.cEmpDept !== "all") {
        deptId = state.cEmpDept;
      }
    }
    if (
      !costId &&
      state.variant === "B" &&
      state.bTree === "cost" &&
      state.bNodeId !== "all" &&
      state.bNodeId !== "unassigned" &&
      getCost(state.bNodeId)
    ) {
      costId = state.bNodeId;
    }
    return { deptId, costId };
  }

  function openResignForm(id) {
    openForm("employee", "edit", id);
    if (!state.form) return;
    state.form.draft.status = "resigned";
    if (!state.form.draft.resignDate) state.form.draft.resignDate = TODAY;
    render();
  }

  document.addEventListener("click", (event) => {
    const actionEl = event.target.closest("[data-action]");
    if (!actionEl) {
      if (
        state.companyMenuOpen &&
        !event.target.closest(".company-switch-wrap")
      ) {
        state.companyMenuOpen = false;
        render();
      }
      return;
    }

    const action = actionEl.dataset.action;
    const id = actionEl.dataset.id;

    if (
      state.companyMenuOpen &&
      !actionEl.closest(".company-switch-wrap")
    ) {
      state.companyMenuOpen = false;
    }

    switch (action) {
      case "stub":
        showToast(
          `${actionEl.dataset.label || "该功能"}不在本次原型范围`,
        );
        break;

      case "variant-prev":
        switchVariant(-1);
        break;

      case "variant-next":
        switchVariant(1);
        break;

      case "open-flow":
        state.companyMenuOpen = false;
        state.overlay = { type: "flow" };
        render();
        break;

      case "open-diff":
        state.companyMenuOpen = false;
        state.overlay = { type: "diff" };
        render();
        break;

      case "toggle-theme":
        state.theme = state.theme === "dark" ? "light" : "dark";
        syncUrl();
        render();
        break;

      case "reset-prototype":
        window.location.href = `${window.location.pathname}?variant=${state.variant}&company=${state.companyId}&theme=${state.theme}`;
        break;

      case "nav-a":
        state.aScreen = actionEl.dataset.screen;
        state.companyMenuOpen = false;
        syncUrl();
        render();
        break;

      case "nav-c":
        state.cScreen = actionEl.dataset.screen;
        state.companyMenuOpen = false;
        syncUrl();
        render();
        break;

      case "toggle-company-menu":
        state.companyMenuOpen = !state.companyMenuOpen;
        render();
        break;

      case "select-company":
      case "switch-company": {
        const companyId = actionEl.dataset.company;
        if (!getCompany(companyId)) return;
        state.companyId = companyId;
        state.companyMenuOpen = false;
        resetCompanyScopedState();
        if (action === "switch-company") {
          state.overlay = null;
          state.form = null;
        }
        syncUrl();
        render();
        break;
      }

      case "manage-companies":
        state.companyMenuOpen = false;
        state.overlay = null;
        if (state.variant === "A") {
          state.aScreen = "companies";
          syncUrl();
        } else if (state.variant === "B") {
          state.overlay = { type: "company-modal" };
        } else {
          state.cScreen = "companies";
          syncUrl();
        }
        render();
        break;

      case "open-company-modal":
        state.companyMenuOpen = false;
        state.overlay = { type: "company-modal" };
        render();
        break;

      case "a-select-dept":
      case "select-dept":
        state.aDeptId = id;
        render();
        break;

      case "a-select-emp-dept":
        state.aEmpDeptId = id;
        render();
        break;

      case "a-select-cost":
      case "select-cost":
        state.aCostId = id;
        render();
        break;

      case "toggle-dept-expand":
        if (state.expandedDepts.has(id)) state.expandedDepts.delete(id);
        else state.expandedDepts.add(id);
        render();
        break;

      case "toggle-cost-expand":
        if (state.expandedCosts.has(id)) state.expandedCosts.delete(id);
        else state.expandedCosts.add(id);
        render();
        break;

      case "b-select-node":
        state.bNodeId = id;
        state.bView = "detail";
        state.bTab = "overview";
        state.bEmpSearch = "";
        state.bEmpStatus = "active";
        state.bEmpSub = true;
        render();
        break;

      case "b-tree-mode": {
        const mode = actionEl.dataset.mode;
        state.bTree = mode;
        state.bTreeSearch = "";
        state.bView = "detail";
        state.bTab = "overview";
        state.bNodeId =
          mode === "dept"
            ? deptChildren(state.companyId, null)[0]?.id || "all"
            : costChildren(state.companyId, null)[0]?.id || "all";
        render();
        break;
      }

      case "b-tab":
        state.bTab = actionEl.dataset.tab;
        state.bView = "detail";
        render();
        break;

      case "b-home":
        state.bTree = "dept";
        state.bNodeId = "all";
        state.bView = "detail";
        state.bTab = "overview";
        render();
        break;

      case "b-back":
        state.bView = "detail";
        state.bEmployeeId = null;
        render();
        break;

      case "b-add-employee": {
        const context = companyContextForEmployeeForm(actionEl);
        openForm("employee", "create", null, context);
        break;
      }

      case "b-view-employee":
        state.bView = "employee-detail";
        state.bEmployeeId = id;
        render();
        break;

      case "b-edit-employee":
        openForm("employee", "edit", id);
        break;

      case "b-resign-employee":
        openResignForm(id);
        break;

      case "c-select-dept":
        state.cDeptId = id;
        render();
        break;

      case "c-org-tab":
        state.cOrgTab = actionEl.dataset.tab;
        syncUrl();
        render();
        break;

      case "c-toggle-cost":
        if (state.cExpandedCosts.has(id)) state.cExpandedCosts.delete(id);
        else state.cExpandedCosts.add(id);
        render();
        break;

      case "c-view-cost":
        state.overlay = { type: "cost-detail", id };
        render();
        break;

      case "c-view-employee":
      case "a-view-employee":
      case "view-employee":
        if (state.variant === "B") {
          state.bView = "employee-detail";
          state.bEmployeeId = id;
          render();
        } else {
          state.overlay = { type: "employee-detail", id };
          render();
        }
        break;

      case "open-unassigned":
      case "open-unassigned-employees":
        state.overlay = { type: "unassigned" };
        render();
        break;

      case "add-company":
        state.companyMenuOpen = false;
        openForm("company", "create");
        break;

      case "edit-company":
        openForm("company", "edit", id);
        break;

      case "delete-company":
        attemptDelete("company", id);
        break;

      case "add-dept":
        openForm("dept", "create", null, {
          parentId: actionEl.dataset.parent || "",
        });
        break;

      case "edit-dept":
        openForm("dept", "edit", id);
        break;

      case "delete-dept":
        attemptDelete("dept", id);
        break;

      case "add-position":
        openForm("position", "create", null, {
          deptId: actionEl.dataset.dept || "",
        });
        break;

      case "edit-position":
        openForm("position", "edit", id);
        break;

      case "delete-position":
        attemptDelete("position", id);
        break;

      case "add-cost":
        openForm("cost", "create", null, {
          parentId: actionEl.dataset.parent || "",
        });
        break;

      case "edit-cost":
        openForm("cost", "edit", id);
        break;

      case "delete-cost":
        attemptDelete("cost", id);
        break;

      case "add-employee": {
        const context = companyContextForEmployeeForm(actionEl);
        openForm("employee", "create", null, context);
        break;
      }

      case "edit-employee":
        openForm("employee", "edit", id);
        break;

      case "resign-employee":
        openResignForm(id);
        break;

      case "close-overlay":
        state.overlay = null;
        state.form = null;
        render();
        break;

      case "save-form":
        saveForm();
        break;

      case "cancel-form":
        cancelForm();
        break;

      case "confirm-delete":
        performDelete(actionEl.dataset.entity, actionEl.dataset.id);
        break;

      case "retry-preview":
        state.preview = "normal";
        render();
        break;

      case "clear-emp-filters":
        state.aEmpSearch = "";
        state.aEmpStatus = "active";
        state.aEmpDeptId = "all";
        state.aEmpSub = true;
        render();
        break;

      case "clear-b-emp-filters":
        state.bEmpSearch = "";
        state.bEmpStatus = "active";
        state.bEmpSub = true;
        render();
        break;

      case "clear-c-emp-filters":
        state.cEmpSearch = "";
        state.cEmpStatus = "active";
        state.cEmpDept = "all";
        state.cEmpSub = true;
        render();
        break;

      case "clear-c-cost-filter":
        state.cCostSearch = "";
        render();
        break;

      case "goto-positions":
        state.form = null;
        state.overlay = null;
        if (state.variant === "A") {
          state.aScreen = "positions";
          syncUrl();
        } else if (state.variant === "B") {
          state.bTree = "dept";
          state.bNodeId = deptChildren(state.companyId, null)[0]?.id || "all";
          state.bView = "detail";
          state.bTab = "positions";
        } else {
          state.cScreen = "organization";
          state.cOrgTab = "positions";
          syncUrl();
        }
        render();
        break;

      default:
        break;
    }
  });

  document.addEventListener("input", (event) => {
    const target = event.target;
    const key = target.dataset.input;
    if (!key) return;

    if (key.startsWith("form:")) {
      if (!state.form) return;
      const field = key.slice(5);
      if (target.type === "checkbox") {
        state.form.draft[field] = target.checked;
        const switchLabel = target
          .closest(".switch")
          ?.querySelector(".switch-label");
        if (switchLabel) {
          switchLabel.textContent = target.checked ? "启用" : "停用";
        }
      } else {
        state.form.draft[field] = target.value;
      }
      if (state.form.errors[field]) {
        delete state.form.errors[field];
        const errorEl = document.querySelector(
          `[data-error-for="${field}"]`,
        );
        if (errorEl) errorEl.remove();
      }
      return;
    }

    switch (key) {
      case "a-dept-search":
        state.aDeptSearch = target.value;
        rerenderPreservingFocus();
        break;
      case "a-emp-search":
        state.aEmpSearch = target.value;
        rerenderPreservingFocus();
        break;
      case "a-emp-sub":
        state.aEmpSub = target.checked;
        render();
        break;
      case "a-cost-search":
        state.aCostSearch = target.value;
        rerenderPreservingFocus();
        break;
      case "a-pos-search":
        state.aPosSearch = target.value;
        rerenderPreservingFocus();
        break;
      case "b-tree-search":
        state.bTreeSearch = target.value;
        rerenderPreservingFocus();
        break;
      case "b-emp-search":
        state.bEmpSearch = target.value;
        rerenderPreservingFocus();
        break;
      case "b-emp-sub":
        state.bEmpSub = target.checked;
        render();
        break;
      case "c-emp-search":
        state.cEmpSearch = target.value;
        rerenderPreservingFocus();
        break;
      case "c-emp-sub":
        state.cEmpSub = target.checked;
        render();
        break;
      case "c-dept-search":
        state.cDeptSearch = target.value;
        rerenderPreservingFocus();
        break;
      case "c-pos-search":
        state.cPosSearch = target.value;
        rerenderPreservingFocus();
        break;
      case "c-cost-search":
        state.cCostSearch = target.value;
        rerenderPreservingFocus();
        break;
      default:
        break;
    }
  });

  document.addEventListener("change", (event) => {
    const target = event.target;
    const key = target.dataset.select;
    if (!key) return;

    if (key === "preview") {
      state.preview = target.value;
      render();
      return;
    }

    if (key.startsWith("form:")) {
      if (!state.form) return;
      const field = key.slice(5);
      state.form.draft[field] = target.value;
      if (field === "status") render();
      return;
    }

    switch (key) {
      case "a-emp-status":
        state.aEmpStatus = target.value;
        render();
        break;
      case "a-pos-status":
        state.aPosStatus = target.value;
        render();
        break;
      case "b-emp-status":
        state.bEmpStatus = target.value;
        render();
        break;
      case "c-emp-status":
        state.cEmpStatus = target.value;
        render();
        break;
      case "c-emp-dept":
        state.cEmpDept = target.value;
        render();
        break;
      default:
        break;
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (state.overlay) {
        state.overlay = null;
        state.form = null;
        render();
        return;
      }
      if (state.variant === "B" && state.bView === "employee-form") {
        cancelForm();
        return;
      }
      if (state.companyMenuOpen) {
        state.companyMenuOpen = false;
        render();
        return;
      }
    }

    if (event.metaKey || event.ctrlKey || event.altKey) return;
    const active = document.activeElement;
    const tag = active?.tagName;
    if (
      ["INPUT", "TEXTAREA", "SELECT"].includes(tag) ||
      active?.isContentEditable
    ) {
      return;
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      switchVariant(-1);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      switchVariant(1);
    }
  });

  /* ================================================================ init */

  syncUrl();
  render();
})();
