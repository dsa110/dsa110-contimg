/**
 * QA Ratings API
 *
 * Provides hooks for:
 * - Rating sources and images (1-5 stars)
 * - Quality assessment categories
 * - Flagging problematic data
 * - Rating statistics and summaries
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

// Types
export type RatingTarget = "source" | "image";
export type RatingCategory =
  | "overall"
  | "flux"
  | "morphology"
  | "position"
  | "calibration";
export type QualityFlag = "good" | "uncertain" | "bad" | "needs_review";

export interface Rating {
  id: string;
  target_type: RatingTarget;
  target_id: string;
  user_id: string;
  username: string;
  category: RatingCategory;
  value: number; // 1-5 stars
  flag: QualityFlag;
  comment?: string;
  created_at: string;
  updated_at: string;
}

export interface RatingSubmission {
  target_type: RatingTarget;
  target_id: string;
  category: RatingCategory;
  value: number;
  flag?: QualityFlag;
  comment?: string;
}

export interface RatingSummary {
  target_type: RatingTarget;
  target_id: string;
  category: RatingCategory;
  average_rating: number;
  rating_count: number;
  flag_distribution: Record<QualityFlag, number>;
  recent_ratings: Rating[];
}

export interface TargetRatingSummary {
  target_type: RatingTarget;
  target_id: string;
  overall_average: number;
  total_ratings: number;
  categories: Record<RatingCategory, { average: number; count: number }>;
  primary_flag: QualityFlag;
  needs_attention: boolean;
}

export interface RatingStats {
  total_ratings: number;
  sources_rated: number;
  images_rated: number;
  average_rating: number;
  ratings_today: number;
  ratings_this_week: number;
  top_raters: Array<{
    user_id: string;
    username: string;
    rating_count: number;
  }>;
  flag_distribution: Record<QualityFlag, number>;
}

export interface QueueItem {
  target_type: RatingTarget;
  target_id: string;
  name: string;
  priority: "high" | "medium" | "low";
  reason: string;
  created_at: string;
}

// Query keys
const ratingKeys = {
  all: ["ratings"] as const,
  lists: () => [...ratingKeys.all, "list"] as const,
  list: (targetType: RatingTarget, targetId: string) =>
    [...ratingKeys.lists(), targetType, targetId] as const,
  summaries: () => [...ratingKeys.all, "summaries"] as const,
  summary: (targetType: RatingTarget, targetId: string) =>
    [...ratingKeys.summaries(), targetType, targetId] as const,
  targetSummary: (targetType: RatingTarget, targetId: string) =>
    [...ratingKeys.all, "target-summary", targetType, targetId] as const,
  stats: () => [...ratingKeys.all, "stats"] as const,
  queue: () => [...ratingKeys.all, "queue"] as const,
  userRatings: (userId?: string) =>
    [...ratingKeys.all, "user", userId] as const,
};

// Get ratings for a specific target
export function useRatings(targetType: RatingTarget, targetId: string) {
  return useQuery({
    queryKey: ratingKeys.list(targetType, targetId),
    queryFn: async (): Promise<Rating[]> => {
      const response = await apiClient.get(
        `/ratings/${targetType}/${targetId}`
      );
      return response.data;
    },
    enabled: !!targetId,
  });
}

// Get rating summary for a specific target and category
export function useRatingSummary(
  targetType: RatingTarget,
  targetId: string,
  category: RatingCategory = "overall"
) {
  return useQuery({
    queryKey: [...ratingKeys.summary(targetType, targetId), category],
    queryFn: async (): Promise<RatingSummary> => {
      const response = await apiClient.get(
        `/ratings/${targetType}/${targetId}/summary`,
        { params: { category } }
      );
      return response.data;
    },
    enabled: !!targetId,
  });
}

// Get complete rating summary for a target (all categories)
export function useTargetRatingSummary(
  targetType: RatingTarget,
  targetId: string
) {
  return useQuery({
    queryKey: ratingKeys.targetSummary(targetType, targetId),
    queryFn: async (): Promise<TargetRatingSummary> => {
      const response = await apiClient.get(
        `/ratings/${targetType}/${targetId}/complete-summary`
      );
      return response.data;
    },
    enabled: !!targetId,
  });
}

// Submit a rating
export function useSubmitRating() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (submission: RatingSubmission): Promise<Rating> => {
      const response = await apiClient.post("/ratings", submission);
      return response.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ratingKeys.list(variables.target_type, variables.target_id),
      });
      queryClient.invalidateQueries({
        queryKey: ratingKeys.summary(
          variables.target_type,
          variables.target_id
        ),
      });
      queryClient.invalidateQueries({
        queryKey: ratingKeys.targetSummary(
          variables.target_type,
          variables.target_id
        ),
      });
      queryClient.invalidateQueries({ queryKey: ratingKeys.stats() });
    },
  });
}

// Update a rating
export function useUpdateRating() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      ratingId,
      ...update
    }: Partial<RatingSubmission> & { ratingId: string }): Promise<Rating> => {
      const response = await apiClient.patch(`/ratings/${ratingId}`, update);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: ratingKeys.list(data.target_type, data.target_id),
      });
      queryClient.invalidateQueries({
        queryKey: ratingKeys.summary(data.target_type, data.target_id),
      });
      queryClient.invalidateQueries({
        queryKey: ratingKeys.targetSummary(data.target_type, data.target_id),
      });
      queryClient.invalidateQueries({ queryKey: ratingKeys.stats() });
    },
  });
}

// Delete a rating
export function useDeleteRating() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      ratingId,
      targetType: _targetType,
      targetId: _targetId,
    }: {
      ratingId: string;
      targetType: RatingTarget;
      targetId: string;
    }): Promise<void> => {
      await apiClient.delete(`/ratings/${ratingId}`);
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ratingKeys.list(variables.targetType, variables.targetId),
      });
      queryClient.invalidateQueries({
        queryKey: ratingKeys.summary(variables.targetType, variables.targetId),
      });
      queryClient.invalidateQueries({
        queryKey: ratingKeys.targetSummary(
          variables.targetType,
          variables.targetId
        ),
      });
      queryClient.invalidateQueries({ queryKey: ratingKeys.stats() });
    },
  });
}

// Get rating statistics
export function useRatingStats() {
  return useQuery({
    queryKey: ratingKeys.stats(),
    queryFn: async (): Promise<RatingStats> => {
      const response = await apiClient.get("/ratings/stats");
      return response.data;
    },
    refetchInterval: 60000,
  });
}

// Get QA review queue
export function useRatingQueue(priority?: QueueItem["priority"]) {
  return useQuery({
    queryKey: [...ratingKeys.queue(), priority],
    queryFn: async (): Promise<QueueItem[]> => {
      const response = await apiClient.get("/ratings/queue", {
        params: priority ? { priority } : {},
      });
      return response.data;
    },
  });
}

// Get user's ratings
export function useUserRatings(userId?: string) {
  return useQuery({
    queryKey: ratingKeys.userRatings(userId),
    queryFn: async (): Promise<Rating[]> => {
      const url = userId ? `/ratings/user/${userId}` : "/ratings/user/me";
      const response = await apiClient.get(url);
      return response.data;
    },
  });
}

// Add item to review queue
export function useAddToQueue() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      item: Omit<QueueItem, "created_at">
    ): Promise<QueueItem> => {
      const response = await apiClient.post("/ratings/queue", item);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ratingKeys.queue() });
    },
  });
}

// Remove item from queue
export function useRemoveFromQueue() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      targetType,
      targetId,
    }: {
      targetType: RatingTarget;
      targetId: string;
    }): Promise<void> => {
      await apiClient.delete(`/ratings/queue/${targetType}/${targetId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ratingKeys.queue() });
    },
  });
}
