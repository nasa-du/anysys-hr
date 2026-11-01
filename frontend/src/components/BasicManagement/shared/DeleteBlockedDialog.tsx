import { AlertTriangle } from "lucide-react"

import type { Blocker, ErrorDetail } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

const BLOCKER_TYPE_LABELS: Record<Blocker["type"], string> = {
  company: "公司",
  department: "部门",
  position: "岗位",
  cost_center: "成本中心",
  employee: "员工",
}

interface DeleteBlockedDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  detail: ErrorDetail | null
  confirmLabel?: string
}

/** Explains why a delete or deactivation is blocked; confirmation is disabled. */
export function DeleteBlockedDialog({
  open,
  onOpenChange,
  title,
  detail,
  confirmLabel = "无法删除",
}: DeleteBlockedDialogProps) {
  const blockers = detail?.blockers ?? []
  const blockerCount = detail?.blocker_count ?? blockers.length

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg" data-testid="blocked-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="size-5 text-destructive" />
            {title}
          </DialogTitle>
          <DialogDescription>{detail?.message ?? ""}</DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            共{" "}
            <span className="font-medium text-foreground">{blockerCount}</span>{" "}
            项引用
            {blockers.length < blockerCount
              ? `，以下显示前 ${blockers.length} 项`
              : ""}
            。
          </p>
          <ul className="max-h-64 space-y-2 overflow-y-auto rounded-md border p-3">
            {blockers.map((blocker) => (
              <li
                key={`${blocker.type}-${blocker.id}`}
                className="flex items-center gap-2 text-sm"
              >
                <Badge variant="secondary" className="shrink-0">
                  {BLOCKER_TYPE_LABELS[blocker.type]}
                </Badge>
                <span className="truncate">{blocker.label}</span>
              </li>
            ))}
          </ul>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            知道了
          </Button>
          <Button variant="destructive" disabled>
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
