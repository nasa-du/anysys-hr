import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import {
  type DepartmentPublic,
  DepartmentsService,
  type ErrorDetail,
} from "@/client"
import { DeleteBlockedDialog } from "@/components/BasicManagement/shared/DeleteBlockedDialog"
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

interface DeleteDepartmentDialogProps {
  department: DepartmentPublic | null
  onOpenChange: (open: boolean) => void
  onDeleted: (departmentId: string) => void
}

export function DeleteDepartmentDialog({
  department,
  onOpenChange,
  onDeleted,
}: DeleteDepartmentDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [blocked, setBlocked] = useState<ErrorDetail | null>(null)

  const mutation = useMutation({
    mutationFn: (departmentId: string) =>
      DepartmentsService.deleteDepartment({
        path: { department_id: departmentId },
      }),
    onSuccess: () => {
      showSuccessToast("部门删除成功")
      if (department) onDeleted(department.id)
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
      queryClient.invalidateQueries({ queryKey: ["basic", "departments"] })
    },
  })

  return (
    <>
      <Dialog open={department !== null} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>删除部门</DialogTitle>
            <DialogDescription>
              将永久删除部门「{department?.dept_name}
              」。存在下级部门或员工引用时无法删除；岗位的默认部门会被清空。
              确定要继续吗？此操作无法撤销。
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
                if (department) mutation.mutate(department.id)
              }}
            >
              删除
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <DeleteBlockedDialog
        open={blocked !== null}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) setBlocked(null)
        }}
        title="无法删除部门"
        detail={blocked}
      />
    </>
  )
}
