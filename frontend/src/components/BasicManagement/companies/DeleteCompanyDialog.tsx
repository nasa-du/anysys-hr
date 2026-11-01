import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import {
  CompaniesService,
  type CompanyPublic,
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

interface DeleteCompanyDialogProps {
  company: CompanyPublic | null
  onOpenChange: (open: boolean) => void
}

export function DeleteCompanyDialog({
  company,
  onOpenChange,
}: DeleteCompanyDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [blocked, setBlocked] = useState<ErrorDetail | null>(null)

  const mutation = useMutation({
    mutationFn: (companyId: string) =>
      CompaniesService.deleteCompany({ path: { company_id: companyId } }),
    onSuccess: () => {
      showSuccessToast("公司删除成功")
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
      queryClient.invalidateQueries({ queryKey: ["basic", "companies"] })
    },
  })

  return (
    <>
      <Dialog open={company !== null} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>删除公司</DialogTitle>
            <DialogDescription>
              将永久删除公司「{company?.company_name}
              」。删除前必须先清空该公司的部门、
              岗位、成本中心与员工。确定要继续吗？此操作无法撤销。
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
                if (company) mutation.mutate(company.id)
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
        title="无法删除公司"
        detail={blocked}
      />
    </>
  )
}
