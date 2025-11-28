/**
 * Workflow Status Schema
 * Validates /api/workflow/status responses
 */
import { z } from "zod";
import { countNumber, isoTimestamp } from "./common";
import type { WorkflowStatus, WorkflowStageStatus } from "../types";

export const WorkflowStageStatusSchema: z.ZodType<WorkflowStageStatus> = z.object({
  name: z.string(),
  display_name: z.string(),
  pending: countNumber,
  processing: countNumber,
  completed_today: countNumber,
  failed_today: countNumber,
});

export const WorkflowStatusSchema: z.ZodType<WorkflowStatus> = z.object({
  stages: z.array(WorkflowStageStatusSchema),
  bottleneck: z.string().nullable(),
  estimated_completion: z.string().nullable(),
  overall_health: z.enum(["healthy", "degraded", "stalled"]),
  total_pending: countNumber,
  total_completed_today: countNumber,
  total_failed_today: countNumber,
  updated_at: isoTimestamp,
});

/**
 * Validate workflow status response
 * @throws ZodError if validation fails
 */
export const validateWorkflowStatus = (payload: unknown): WorkflowStatus => {
  return WorkflowStatusSchema.parse(payload);
};

/**
 * Safe validation that returns null instead of throwing
 */
export const safeValidateWorkflowStatus = (
  payload: unknown
): { success: true; data: WorkflowStatus } | { success: false; error: z.ZodError } => {
  const result = WorkflowStatusSchema.safeParse(payload);
  return result;
};
