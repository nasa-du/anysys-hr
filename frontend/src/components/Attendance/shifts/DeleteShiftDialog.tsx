import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import {
  AttendanceShiftsService,
  type ErrorDetail,
  type ShiftPublic,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorDetail, getErrorMessage } from "@/lib/api-error"
import { invalidateShiftQueries } from "./queries"
import { ReferenceBlockedDialog } from "./ReferenceBlockedDialog"

interface DeleteShiftDialogProps {
  shift: ShiftPublic | null
  onOpenChange: (open: boolean) => void
  onDeleted: (shiftId: string) => void
}

export function DeleteShiftDialog({
  shift,
  onOpenChange,
  onDeleted,
}: DeleteShiftDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [blocked, setBlocked] = useState<ErrorDetail | null>(null)

  const mutation = useMutation({
    mutationFn: (shiftId: string) =>
      AttendanceShiftsService.deleteShift({ path: { shift_id: shiftId } }),
    onSuccess: () => {
      showSuccessToast("班次删除成功")
      if (shift) onDeleted(shift.id)
      onOpenChange(false)
    },
    onError: (error) => {
      const detail = getErrorDetail(error)
      if (detail?.code === "referenced") {
        onOpenChange(false)
        setBlocked(detail)
        return
      }
      showErrorToast(getErrorMessage(error))
    },
    onSettled: () => {
      invalidateShiftQueries(queryClient)
    },
  })

  return (
    <>
      <Dialog open={shift !== null} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>删除班次</DialogTitle>
            <DialogDescription>
              将永久删除班次「{shift?.shift_name}
              」。任何排班方案（含已归档）或排班明细快照引用该班次时都无法删除。确定要继续吗？此操作无法撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              disabled={mutation.isPending}
              onClick={() => onOpenChange(false)}
            >
              取消
            </Button>
            <LoadingButton
              variant="destructive"
              loading={mutation.isPending}
              onClick={() => {
                if (shift) mutation.mutate(shift.id)
              }}
            >
              删除
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ReferenceBlockedDialog
        detail={blocked}
        action="delete"
        onDismiss={() => setBlocked(null)}
      />
    </>
  )
}
