import { Building2, Home, Network, Users } from "lucide-react"

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
