/**
 * Event Statistics Schema
 * Validates /api/events/stats responses
 */
import { z } from "zod";
import { countNumber } from "./common";
import type { EventStatistics, EventTypesResponse } from "../types";

export const EventStatisticsSchema: z.ZodType<EventStatistics> = z.object({
  total_events: countNumber,
  events_in_history: countNumber,
  events_per_type: z.record(z.string(), countNumber),
  events_last_minute: countNumber,
  events_last_hour: countNumber,
  subscribers: z.record(z.string(), countNumber),
  event_types: z.array(z.string()).optional(),
});

export const EventTypeSchema = z.object({
  value: z.string(),
  name: z.string(),
});

export const EventTypesResponseSchema: z.ZodType<EventTypesResponse> = z.object({
  event_types: z.array(EventTypeSchema),
});

/**
 * Validate event statistics response
 * @throws ZodError if validation fails
 */
export const validateEventStatistics = (payload: unknown): EventStatistics => {
  return EventStatisticsSchema.parse(payload);
};

/**
 * Validate event types response
 * @throws ZodError if validation fails
 */
export const validateEventTypesResponse = (payload: unknown): EventTypesResponse => {
  return EventTypesResponseSchema.parse(payload);
};
