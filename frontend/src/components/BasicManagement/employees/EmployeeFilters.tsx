import { Search } from "lucide-react"

import type { CostCenterPublic, PositionPublic } from "@/client"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  EMPLOYEE_STATUS_FILTER_OPTIONS,
  type EmployeeStatusFilter,
} from "@/lib/enums"

export const ALL_POSITIONS = "__all_positions__"
export const ALL_COST_CENTERS = "__all_cost_centers__"
export const UNASSIGNED_COST_CENTER = "__unassigned__"

interface EmployeeFiltersProps {
  keyword: string
  onKeywordChange: (value: string) => void
  status: EmployeeStatusFilter
  onStatusChange: (value: EmployeeStatusFilter) => void
  positionId: string
  onPositionIdChange: (value: string) => void
  positions: PositionPublic[]
  costCenterValue: string
  onCostCenterChange: (value: string) => void
  costCenters: CostCenterPublic[]
}

export function EmployeeFilters({
  keyword,
  onKeywordChange,
  status,
  onStatusChange,
  positionId,
  onPositionIdChange,
  positions,
  costCenterValue,
  onCostCenterChange,
  costCenters,
}: EmployeeFiltersProps) {
  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
      <div className="relative lg:w-64">
        <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          className="pl-9"
          placeholder="搜索工号或姓名"
          aria-label="搜索员工"
          value={keyword}
          onChange={(event) => onKeywordChange(event.target.value)}
        />
      </div>
      <Select
        value={status}
        onValueChange={(value) => onStatusChange(value as EmployeeStatusFilter)}
      >
        <SelectTrigger className="w-full lg:w-[160px]" aria-label="状态筛选">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {EMPLOYEE_STATUS_FILTER_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={positionId} onValueChange={onPositionIdChange}>
        <SelectTrigger className="w-full lg:w-[200px]" aria-label="岗位筛选">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_POSITIONS}>全部岗位</SelectItem>
          {positions.map((position) => (
            <SelectItem key={position.id} value={position.id}>
              {position.position_name}（{position.position_code}）
              {!position.is_active ? " 停用" : ""}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={costCenterValue} onValueChange={onCostCenterChange}>
        <SelectTrigger
          className="w-full lg:w-[220px]"
          aria-label="成本中心筛选"
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_COST_CENTERS}>全部成本中心</SelectItem>
          <SelectItem value={UNASSIGNED_COST_CENTER}>未分配</SelectItem>
          {costCenters.map((costCenter) => (
            <SelectItem key={costCenter.id} value={costCenter.id}>
              {costCenter.cost_org_name}（{costCenter.cost_org_code}）
              {!costCenter.is_active ? " 停用" : ""}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
