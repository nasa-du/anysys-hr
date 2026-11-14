import type { ErrorDetail } from "@/client"
import { DeleteBlockedDialog } from "@/components/BasicManagement/shared/DeleteBlockedDialog"

type ShiftBlockedAction = "deactivate" | "delete"

const DIALOG_COPY: Record<
  ShiftBlockedAction,
  { title: string; confirmLabel: string }
> = {
  deactivate: { title: "无法停用班次", confirmLabel: "无法停用" },
  delete: { title: "无法删除班次", confirmLabel: "无法删除" },
}

interface ReferenceBlockedDialogProps {
  detail: ErrorDetail | null
  action: ShiftBlockedAction
  onDismiss: () => void
}

/** Explains the plan or roster references that block a shift operation. */
export function ReferenceBlockedDialog({
  detail,
  action,
  onDismiss,
}: ReferenceBlockedDialogProps) {
  return (
    <DeleteBlockedDialog
      open={detail !== null}
      onOpenChange={(open) => {
        if (!open) onDismiss()
      }}
      title={DIALOG_COPY[action].title}
      confirmLabel={DIALOG_COPY[action].confirmLabel}
      detail={detail}
    />
  )
}
