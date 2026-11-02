import { useQuery } from "@tanstack/react-query"

import { type DepartmentPublic, PositionsService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { getErrorMessage } from "@/lib/api-error"

interface DepartmentPositionsProps {
  department: DepartmentPublic
}

/** Positions that use this department as their default department. */
export function DepartmentPositions({ department }: DepartmentPositionsProps) {
  const positionsQuery = useQuery({
    queryKey: [
      "basic",
      "positions",
      "list",
      department.company_id,
      { dept_id: department.id },
    ],
    queryFn: async () => {
      const response = await PositionsService.readPositions({
        query: {
          company_id: department.company_id,
          dept_id: department.id,
          skip: 0,
          limit: 500,
        },
      })
      return response.data
    },
  })

  const positions = positionsQuery.data?.data ?? []
  const count = positionsQuery.data?.count ?? 0

  return (
    <div className="space-y-3" data-testid="department-positions">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">使用此默认部门的岗位</h3>
        <span className="text-xs text-muted-foreground">共 {count} 个</span>
      </div>
      {positionsQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">正在加载岗位…</p>
      ) : positionsQuery.isError ? (
        <p className="text-sm text-destructive">
          {getErrorMessage(positionsQuery.error)}
        </p>
      ) : positions.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          暂无岗位使用此部门作为默认部门。
        </p>
      ) : (
        <ul className="divide-y rounded-md border">
          {positions.map((position) => (
            <li
              key={position.id}
              className="flex flex-wrap items-center gap-2 px-3 py-2 text-sm"
            >
              <span className="font-mono text-xs text-muted-foreground">
                {position.position_code}
              </span>
              <span>{position.position_name}</span>
              {!position.is_active && (
                <Badge variant="secondary" className="text-xs">
                  停用
                </Badge>
              )}
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-muted-foreground">
        默认部门仅用于员工建档时带出部门，员工的实际部门可以不同。
      </p>
    </div>
  )
}
