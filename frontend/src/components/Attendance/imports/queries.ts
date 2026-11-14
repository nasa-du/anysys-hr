import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  AttendanceImportsService,
  type Body_attendance_imports_preview_imports,
  type ImportMappingTemplatePublic,
  type ImportPreviewPublic,
} from "@/client"
import type { AttendanceImportDataType } from "@/lib/enums"

export type ImportColumnMapping = Record<string, number | null>

export type PreviewRequest = {
  companyId: string
  dataType: AttendanceImportDataType
  month: string
  file: File | null
  text: string | null
  sheetName: string | null
  columnMapping: ImportColumnMapping | null
}

/** Parse an upload or paste into a persisted preview batch. */
export function usePreviewImport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (
      request: PreviewRequest,
    ): Promise<ImportPreviewPublic> => {
      const body: Body_attendance_imports_preview_imports = {
        company_id: request.companyId,
        data_type: request.dataType,
        month: request.month,
      }
      if (request.file) body.file = request.file
      if (request.text !== null) body.text = request.text
      if (request.sheetName) body.sheet_name = request.sheetName
      if (request.columnMapping) {
        body.column_mapping = JSON.stringify(request.columnMapping)
      }
      const response = await AttendanceImportsService.previewImports({ body })
      return response.data
    },
    onSuccess: () => {
      // Spec 8.9: import changes invalidate batches, month state, and results.
      void queryClient.invalidateQueries({
        queryKey: ["attendance", "imports"],
      })
      void queryClient.invalidateQueries({ queryKey: ["attendance", "months"] })
      void queryClient.invalidateQueries({
        queryKey: ["attendance", "results"],
      })
    },
  })
}

/** The last successfully committed mapping, or null when none exists yet. */
export function useMappingTemplate(
  companyId: string,
  dataType: AttendanceImportDataType,
) {
  return useQuery({
    queryKey: [
      "attendance",
      "imports",
      "mapping-template",
      companyId,
      dataType,
    ],
    queryFn: async (): Promise<ImportMappingTemplatePublic | null> => {
      const response = await AttendanceImportsService.readMappingTemplate({
        query: { company_id: companyId, data_type: dataType },
        throwOnError: false,
      })
      return response.data ?? null
    },
  })
}
