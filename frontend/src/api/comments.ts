/**
 * Comments API - User comments on sources, images, observations
 *
 * Provides hooks for managing user-generated comments throughout the system.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

// ============================================================================
// Types
// ============================================================================

export type CommentTarget = "source" | "image" | "observation" | "job" | "ms";

export interface Comment {
  id: string;
  target_type: CommentTarget;
  target_id: string;
  user_id: string;
  username: string;
  content: string;
  is_pinned: boolean;
  is_resolved: boolean;
  parent_id: string | null; // For threaded replies
  reply_count: number;
  created_at: string;
  updated_at: string;
}

export interface CreateCommentRequest {
  target_type: CommentTarget;
  target_id: string;
  content: string;
  parent_id?: string; // For replies
}

export interface UpdateCommentRequest {
  content?: string;
  is_pinned?: boolean;
  is_resolved?: boolean;
}

export interface CommentThread {
  comment: Comment;
  replies: Comment[];
}

export interface CommentStats {
  total_comments: number;
  pinned_comments: number;
  resolved_comments: number;
  active_threads: number;
  comments_today: number;
  comments_this_week: number;
  top_commenters: Array<{
    user_id: string;
    username: string;
    comment_count: number;
  }>;
  target_distribution: Record<CommentTarget, number>;
}

export interface CommentSearchParams {
  target_type?: CommentTarget;
  target_id?: string;
  user_id?: string;
  search?: string;
  is_pinned?: boolean;
  is_resolved?: boolean;
  parent_id?: string | null; // null for top-level only
  sort_by?: "created_at" | "updated_at";
  sort_order?: "asc" | "desc";
  limit?: number;
  offset?: number;
}

export interface MentionedUser {
  user_id: string;
  username: string;
  email?: string;
}

// ============================================================================
// Query Keys
// ============================================================================

export const commentKeys = {
  all: ["comments"] as const,
  lists: () => [...commentKeys.all, "list"] as const,
  list: (params: CommentSearchParams) =>
    [...commentKeys.lists(), params] as const,
  details: () => [...commentKeys.all, "detail"] as const,
  detail: (id: string) => [...commentKeys.details(), id] as const,
  thread: (commentId: string) =>
    [...commentKeys.all, "thread", commentId] as const,
  forTarget: (targetType: CommentTarget, targetId: string) =>
    [...commentKeys.all, "target", targetType, targetId] as const,
  stats: () => [...commentKeys.all, "stats"] as const,
  users: () => [...commentKeys.all, "users"] as const,
};

// ============================================================================
// API Functions
// ============================================================================

async function getComments(params: CommentSearchParams = {}): Promise<Comment[]> {
  const response = await apiClient.get("/api/comments", { params });
  return response.data;
}

async function getComment(id: string): Promise<Comment> {
  const response = await apiClient.get(`/api/comments/${id}`);
  return response.data;
}

async function getCommentThread(commentId: string): Promise<CommentThread> {
  const response = await apiClient.get(`/api/comments/${commentId}/thread`);
  return response.data;
}

async function getCommentsForTarget(
  targetType: CommentTarget,
  targetId: string
): Promise<Comment[]> {
  const response = await apiClient.get(
    `/api/${targetType}s/${targetId}/comments`
  );
  return response.data;
}

async function createComment(data: CreateCommentRequest): Promise<Comment> {
  const response = await apiClient.post("/api/comments", data);
  return response.data;
}

async function updateComment(
  id: string,
  data: UpdateCommentRequest
): Promise<Comment> {
  const response = await apiClient.patch(`/api/comments/${id}`, data);
  return response.data;
}

async function deleteComment(id: string): Promise<void> {
  await apiClient.delete(`/api/comments/${id}`);
}

async function pinComment(id: string): Promise<Comment> {
  const response = await apiClient.post(`/api/comments/${id}/pin`);
  return response.data;
}

async function unpinComment(id: string): Promise<Comment> {
  const response = await apiClient.post(`/api/comments/${id}/unpin`);
  return response.data;
}

async function resolveComment(id: string): Promise<Comment> {
  const response = await apiClient.post(`/api/comments/${id}/resolve`);
  return response.data;
}

async function unresolveComment(id: string): Promise<Comment> {
  const response = await apiClient.post(`/api/comments/${id}/unresolve`);
  return response.data;
}

async function getCommentStats(): Promise<CommentStats> {
  const response = await apiClient.get("/api/comments/stats");
  return response.data;
}

async function getMentionableUsers(): Promise<MentionedUser[]> {
  const response = await apiClient.get("/api/comments/users");
  return response.data;
}

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Fetch comments with optional filtering
 */
export function useComments(params: CommentSearchParams = {}) {
  return useQuery({
    queryKey: commentKeys.list(params),
    queryFn: () => getComments(params),
  });
}

/**
 * Fetch a single comment by ID
 */
export function useComment(id: string) {
  return useQuery({
    queryKey: commentKeys.detail(id),
    queryFn: () => getComment(id),
    enabled: !!id,
  });
}

/**
 * Fetch a comment thread (comment + replies)
 */
export function useCommentThread(commentId: string) {
  return useQuery({
    queryKey: commentKeys.thread(commentId),
    queryFn: () => getCommentThread(commentId),
    enabled: !!commentId,
  });
}

/**
 * Fetch comments for a specific target (source, image, etc.)
 */
export function useCommentsForTarget(
  targetType: CommentTarget,
  targetId: string
) {
  return useQuery({
    queryKey: commentKeys.forTarget(targetType, targetId),
    queryFn: () => getCommentsForTarget(targetType, targetId),
    enabled: !!targetType && !!targetId,
  });
}

/**
 * Fetch comment statistics
 */
export function useCommentStats() {
  return useQuery({
    queryKey: commentKeys.stats(),
    queryFn: getCommentStats,
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Fetch mentionable users for @mentions
 */
export function useMentionableUsers() {
  return useQuery({
    queryKey: commentKeys.users(),
    queryFn: getMentionableUsers,
    staleTime: 60000, // 1 minute
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Create a new comment
 */
export function useCreateComment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createComment,
    onSuccess: (newComment) => {
      // Invalidate comment lists
      queryClient.invalidateQueries({ queryKey: commentKeys.lists() });
      // Invalidate target-specific comments
      queryClient.invalidateQueries({
        queryKey: commentKeys.forTarget(
          newComment.target_type,
          newComment.target_id
        ),
      });
      // Invalidate stats
      queryClient.invalidateQueries({ queryKey: commentKeys.stats() });
      // If this is a reply, invalidate the thread
      if (newComment.parent_id) {
        queryClient.invalidateQueries({
          queryKey: commentKeys.thread(newComment.parent_id),
        });
      }
    },
  });
}

/**
 * Update an existing comment
 */
export function useUpdateComment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateCommentRequest }) =>
      updateComment(id, data),
    onSuccess: (updatedComment) => {
      // Update the comment in cache
      queryClient.setQueryData(
        commentKeys.detail(updatedComment.id),
        updatedComment
      );
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: commentKeys.lists() });
      // Invalidate target-specific comments
      queryClient.invalidateQueries({
        queryKey: commentKeys.forTarget(
          updatedComment.target_type,
          updatedComment.target_id
        ),
      });
    },
  });
}

/**
 * Delete a comment
 */
export function useDeleteComment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteComment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: commentKeys.all });
    },
  });
}

/**
 * Pin a comment
 */
export function usePinComment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: pinComment,
    onSuccess: (updatedComment) => {
      queryClient.setQueryData(
        commentKeys.detail(updatedComment.id),
        updatedComment
      );
      queryClient.invalidateQueries({ queryKey: commentKeys.lists() });
    },
  });
}

/**
 * Unpin a comment
 */
export function useUnpinComment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: unpinComment,
    onSuccess: (updatedComment) => {
      queryClient.setQueryData(
        commentKeys.detail(updatedComment.id),
        updatedComment
      );
      queryClient.invalidateQueries({ queryKey: commentKeys.lists() });
    },
  });
}

/**
 * Mark a comment as resolved
 */
export function useResolveComment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: resolveComment,
    onSuccess: (updatedComment) => {
      queryClient.setQueryData(
        commentKeys.detail(updatedComment.id),
        updatedComment
      );
      queryClient.invalidateQueries({ queryKey: commentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: commentKeys.stats() });
    },
  });
}

/**
 * Mark a comment as unresolved
 */
export function useUnresolveComment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: unresolveComment,
    onSuccess: (updatedComment) => {
      queryClient.setQueryData(
        commentKeys.detail(updatedComment.id),
        updatedComment
      );
      queryClient.invalidateQueries({ queryKey: commentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: commentKeys.stats() });
    },
  });
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Format comment timestamp for display
 */
export function formatCommentTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

/**
 * Parse @mentions from comment content
 */
export function parseMentions(content: string): string[] {
  const mentionRegex = /@(\w+)/g;
  const mentions: string[] = [];
  let match;
  while ((match = mentionRegex.exec(content)) !== null) {
    mentions.push(match[1]);
  }
  return mentions;
}

/**
 * Render comment content with highlighted mentions
 */
export function renderCommentContent(content: string): string {
  return content.replace(
    /@(\w+)/g,
    '<span class="text-blue-600 font-medium">@$1</span>'
  );
}

/**
 * Get target type display label
 */
export function getTargetTypeLabel(targetType: CommentTarget): string {
  const labels: Record<CommentTarget, string> = {
    source: "Source",
    image: "Image",
    observation: "Observation",
    job: "Job",
    ms: "Measurement Set",
  };
  return labels[targetType];
}

/**
 * Get target type emoji
 */
export function getTargetTypeEmoji(targetType: CommentTarget): string {
  const emojis: Record<CommentTarget, string> = {
    source: "🔭",
    image: "🖼️",
    observation: "📡",
    job: "⚙️",
    ms: "📊",
  };
  return emojis[targetType];
}
