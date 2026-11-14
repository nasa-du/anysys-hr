import {
  Briefcase,
  Building2,
  CalendarClock,
  ClipboardCheck,
  Clock3,
  Home,
  Network,
  SlidersHorizontal,
  Upload,
  UserRound,
  Users,
  Wallet,
} from "lucide-react"

import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { Main, type NavGroup } from "./Main"
import { User } from "./User"

export function AppSidebar() {
  const { user: currentUser } = useAuth()

  const groups: NavGroup[] = [
    { items: [{ icon: Home, title: "仪表盘", path: "/" }] },
    {
      label: "基础管理",
      items: [
        { icon: Building2, title: "公司", path: "/companies" },
        { icon: Network, title: "部门", path: "/departments" },
        { icon: UserRound, title: "员工", path: "/employees" },
        { icon: Briefcase, title: "岗位", path: "/positions" },
        { icon: Wallet, title: "成本中心", path: "/cost-centers" },
      ],
    },
    {
      label: "考勤管理",
      items: [
        {
          icon: CalendarClock,
          title: "排班工作台",
          path: "/attendance/schedule",
        },
        { icon: Upload, title: "导入中心", path: "/attendance/imports" },
        {
          icon: ClipboardCheck,
          title: "考勤结果",
          path: "/attendance/results",
        },
        {
          icon: SlidersHorizontal,
          title: "规则与节假日",
          path: "/attendance/rules",
        },
        { icon: Clock3, title: "班次", path: "/attendance/shifts" },
      ],
    },
  ]

  if (currentUser?.is_superuser) {
    groups.push({
      label: "系统",
      items: [{ icon: Users, title: "管理后台", path: "/admin" }],
    })
  }

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main groups={groups} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
