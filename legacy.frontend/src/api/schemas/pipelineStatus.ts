import { z } from "zod";
import type {
  CalibrationSet,
  CalibratorMatch,
  PipelineStatus,
  QueueGroup,
  QueueStats,
} from "../types";

const countNumber = z.number().finite().min(0);

const CalibratorMatchSchema: z.ZodType<CalibratorMatch> = z.object({
  name: z.string(),
  ra_deg: z.number().finite(),
  dec_deg: z.number().finite(),
  sep_deg: z.number().finite(),
  weighted_flux: z.number().finite().nullable().optional(),
});

const QueueGroupSchema: z.ZodType<QueueGroup> = z.object({
  group_id: z.string().min(1),
  state: z.string().min(1),
  received_at: z.string().min(1),
  last_update: z.string().min(1),
  subbands_present: countNumber,
  expected_subbands: countNumber,
  has_calibrator: z.boolean().nullable().optional(),
  matches: z.array(CalibratorMatchSchema).nullable().optional(),
});

const QueueStatsSchema: z.ZodType<QueueStats> = z.object({
  total: countNumber,
  pending: countNumber,
  in_progress: countNumber,
  failed: countNumber,
  completed: countNumber,
  collecting: countNumber,
});

const CalibrationSetSchema: z.ZodType<CalibrationSet> = z.object({
  set_name: z.string().min(1),
  tables: z.array(z.string()).default([]),
  active: countNumber,
  total: countNumber,
});

export const PipelineStatusSchema: z.ZodType<PipelineStatus> = z.object({
  queue: QueueStatsSchema,
  recent_groups: z.array(QueueGroupSchema),
  calibration_sets: z.array(CalibrationSetSchema),
  matched_recent: countNumber.optional(),
});

export const validatePipelineStatus = (payload: unknown): PipelineStatus => {
  return PipelineStatusSchema.parse(payload);
};
