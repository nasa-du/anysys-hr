import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  AttendanceImportsService,
  type AttendanceMonthPublic,
  AttendanceMonthsService,
  type Body_attendance_imports_preview_imports,
  type ImportBatchErrorsPublic,
  type ImportBatchesPublic,
  type ImportBatchPublic,
  type ImportBatchRecordsPublic,
  type ImportCommitPublic,
  type ImportMappingTemplatePublic,
  type ImportPreviewPublic,
  type ImportSeverity,
} from "@/client"
import type {
  AttendanceImportBatchStatus,
  AttendanceImportDataType,
} from "@/lib/enums"

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

export type ImportDataTypeFilter = AttendanceImportDataType | "all"
export type ImportStatusFilter = AttendanceImportBatchStatus | "all"

export type ImportBatchFilters = {
  dataType: ImportDataTypeFilter
  status: ImportStatusFilter
  skip: number
  limit: number
}

export function importListQueryKey(
  companyId: string,
  month: string,
  filters: ImportBatchFilters,
) {
  return [
    "attendance",
    "imports",
    "list",
    companyId,
    month,
    {
      dataType: filters.dataType,
      status: filters.status,
      skip: filters.skip,
      limit: filters.limit,
    },
  ] as const
}

export function importDetailQueryKey(batchId: string) {
  return ["attendance", "imports", "detail", batchId] as const
}

export function importErrorsQueryKey(
  batchId: string,
  severity: ImportSeverity | "all",
  skip: number,
  limit: number,
) {
  return [
    "attendance",
    "imports",
    "errors",
    batchId,
    { severity, skip, limit },
  ] as const
}

export function importRecordsQueryKey(
  batchId: string,
  skip: number,
  limit: number,
) {
  return ["attendance", "imports", "records", batchId, { skip, limit }] as const
}

/** Import changes invalidate batches, month state, and results (spec 8.9). */
export function invalidateImportQueries(
  queryClient: ReturnType<typeof useQueryClient>,
): void {
  void queryClient.invalidateQueries({ queryKey: ["attendance", "imports"] })
  void queryClient.invalidateQueries({ queryKey: ["attendance", "months"] })
  void queryClient.invalidateQueries({ queryKey: ["attendance", "results"] })
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
    onSuccess: () => invalidateImportQueries(queryClient),
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

/** Month status and staleness used by the import center's stale/closed states. */
export function useAttendanceMonthOverview(companyId: string, month: string) {
  const year = Number(month.slice(0, 4))
  return useQuery({
    queryKey: ["attendance", "months", "list", companyId, year],
    queryFn: async (): Promise<AttendanceMonthPublic | null> => {
      const response = await AttendanceMonthsService.readMonths({
        query: { company_id: companyId, year },
      })
      return response.data.data.find((item) => item.month === month) ?? null
    },
    enabled: Boolean(companyId && month),
  })
}

/** Paginated batch history for one company/month. */
export function useImportBatches(
  companyId: string,
  month: string,
  filters: ImportBatchFilters,
) {
  return useQuery({
    queryKey: importListQueryKey(companyId, month, filters),
    queryFn: async (): Promise<ImportBatchesPublic> => {
      const response = await AttendanceImportsService.readImportBatches({
        query: {
          company_id: companyId,
          month,
          skip: filters.skip,
          limit: filters.limit,
          ...(filters.dataType === "all"
            ? {}
            : { data_type: filters.dataType }),
          ...(filters.status === "all" ? {} : { status: filters.status }),
        },
      })
      return response.data
    },
    enabled: Boolean(companyId && month),
  })
}

export function useImportBatch(batchId: string) {
  return useQuery({
    queryKey: importDetailQueryKey(batchId),
    queryFn: async (): Promise<ImportBatchPublic> => {
      const response = await AttendanceImportsService.readImportBatch({
        path: { batch_id: batchId },
      })
      return response.data
    },
  })
}

export function useImportBatchErrors(
  batchId: string,
  severity: ImportSeverity | "all",
  skip: number,
  limit: number,
) {
  return useQuery({
    queryKey: importErrorsQueryKey(batchId, severity, skip, limit),
    queryFn: async (): Promise<ImportBatchErrorsPublic> => {
      const response = await AttendanceImportsService.readImportBatchErrors({
        path: { batch_id: batchId },
        query: {
          severity: severity === "all" ? undefined : severity,
          skip,
          limit,
        },
      })
      return response.data
    },
  })
}

export function useImportBatchRecords(
  batchId: string,
  skip: number,
  limit: number,
) {
  return useQuery({
    queryKey: importRecordsQueryKey(batchId, skip, limit),
    queryFn: async (): Promise<ImportBatchRecordsPublic> => {
      const response = await AttendanceImportsService.readImportBatchRecords({
        path: { batch_id: batchId },
        query: { skip, limit },
      })
      return response.data
    },
  })
}

export function useCommitImport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (batchId: string): Promise<ImportCommitPublic> => {
      const response = await AttendanceImportsService.commitImport({
        path: { batch_id: batchId },
      })
      return response.data
    },
    onSuccess: () => invalidateImportQueries(queryClient),
  })
}

export function useDiscardImport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (batchId: string): Promise<ImportBatchPublic> => {
      const response = await AttendanceImportsService.discardImport({
        path: { batch_id: batchId },
      })
      return response.data
    },
    onSuccess: () => invalidateImportQueries(queryClient),
  })
}

export function useRevokeImport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (batchId: string): Promise<ImportBatchPublic> => {
      const response = await AttendanceImportsService.revokeImport({
        path: { batch_id: batchId },
      })
      return response.data
    },
    onSuccess: () => invalidateImportQueries(queryClient),
  })
}
