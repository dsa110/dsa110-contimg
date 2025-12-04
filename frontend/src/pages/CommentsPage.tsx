/**
 * Comments Page
 *
 * Dashboard for viewing, creating, and managing user comments on
 * sources, images, observations, jobs, and measurement sets.
 */

import React, { useState, useMemo } from "react";
import {
  useComments,
  useCommentStats,
  useCreateComment,
  useDeleteComment,
  usePinComment,
  useUnpinComment,
  useResolveComment,
  useUnresolveComment,
  useMentionableUsers,
  formatCommentTime,
  getTargetTypeLabel,
  getTargetTypeEmoji,
  type Comment,
  type CommentTarget,
  type CommentSearchParams,
} from "../api/comments";

// ============================================================================
// Types
// ============================================================================

type TabType = "all" | "mine" | "pinned" | "unresolved";

// ============================================================================
// Sub-Components
// ============================================================================

interface CommentCardProps {
  comment: Comment;
  isOwner: boolean;
  onPin: (id: string) => void;
  onUnpin: (id: string) => void;
  onResolve: (id: string) => void;
  onUnresolve: (id: string) => void;
  onDelete: (id: string) => void;
  onReply: (comment: Comment) => void;
}

function CommentCard({
  comment,
  isOwner,
  onPin,
  onUnpin,
  onResolve,
  onUnresolve,
  onDelete,
  onReply,
}: CommentCardProps) {
  const [showActions, setShowActions] = useState(false);

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${
        comment.is_pinned ? "ring-2 ring-yellow-400" : ""
      } ${comment.is_resolved ? "opacity-75" : ""}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <span className="text-2xl">
            {getTargetTypeEmoji(comment.target_type)}
          </span>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {comment.username}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {formatCommentTime(comment.created_at)}
              </span>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              on {getTargetTypeLabel(comment.target_type)} {comment.target_id}
            </p>
          </div>
        </div>

        {/* Status badges */}
        <div className="flex items-center gap-2">
          {comment.is_pinned && (
            <span className="px-2 py-1 text-xs font-medium rounded-full text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30">
              📌 Pinned
            </span>
          )}
          {comment.is_resolved && (
            <span className="px-2 py-1 text-xs font-medium rounded-full text-green-600 bg-green-100 dark:bg-green-900/30">
              ✓ Resolved
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="mt-3 text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
        {comment.content}
      </div>

      {/* Thread indicator */}
      {comment.reply_count > 0 && (
        <div className="mt-3 text-sm text-blue-600 dark:text-blue-400">
          💬 {comment.reply_count}{" "}
          {comment.reply_count === 1 ? "reply" : "replies"}
        </div>
      )}

      {/* Actions */}
      {showActions && (
        <div className="mt-3 flex items-center gap-2 border-t border-gray-200 dark:border-gray-700 pt-3">
          <button
            onClick={() => onReply(comment)}
            className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            Reply
          </button>
          {comment.is_pinned ? (
            <button
              onClick={() => onUnpin(comment.id)}
              className="px-3 py-1 text-sm text-yellow-600 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 rounded"
            >
              Unpin
            </button>
          ) : (
            <button
              onClick={() => onPin(comment.id)}
              className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              Pin
            </button>
          )}
          {comment.is_resolved ? (
            <button
              onClick={() => onUnresolve(comment.id)}
              className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              Unresolve
            </button>
          ) : (
            <button
              onClick={() => onResolve(comment.id)}
              className="px-3 py-1 text-sm text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
            >
              Resolve
            </button>
          )}
          {isOwner && (
            <button
              onClick={() => onDelete(comment.id)}
              className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded ml-auto"
            >
              Delete
            </button>
          )}
        </div>
      )}
    </div>
  );
}

interface CreateCommentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: {
    target_type: CommentTarget;
    target_id: string;
    content: string;
    parent_id?: string;
  }) => Promise<void>;
  replyTo?: Comment | null;
  isPending: boolean;
}

function CreateCommentModal({
  isOpen,
  onClose,
  onSubmit,
  replyTo,
  isPending,
}: CreateCommentModalProps) {
  const [targetType, setTargetType] = useState<CommentTarget>("source");
  const [targetId, setTargetId] = useState("");
  const [content, setContent] = useState("");

  const { data: users } = useMentionableUsers();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit({
      target_type: replyTo ? replyTo.target_type : targetType,
      target_id: replyTo ? replyTo.target_id : targetId,
      content,
      parent_id: replyTo?.id,
    });
    setContent("");
    setTargetId("");
    onClose();
  };

  const handleInsertMention = (username: string) => {
    setContent((prev) => prev + `@${username} `);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full mx-4">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {replyTo ? (
              <span>Reply to {replyTo.username}'s comment</span>
            ) : (
              "New Comment"
            )}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {!replyTo && (
            <>
              <div>
                <label
                  htmlFor="comment-target-type"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Target Type
                </label>
                <select
                  id="comment-target-type"
                  value={targetType}
                  onChange={(e) =>
                    setTargetType(e.target.value as CommentTarget)
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                >
                  <option value="source">Source</option>
                  <option value="image">Image</option>
                  <option value="observation">Observation</option>
                  <option value="job">Job</option>
                  <option value="ms">Measurement Set</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="comment-target-id"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Target ID
                </label>
                <input
                  id="comment-target-id"
                  type="text"
                  value={targetId}
                  onChange={(e) => setTargetId(e.target.value)}
                  placeholder="e.g., J1234+5678"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  required
                />
              </div>
            </>
          )}

          <div>
            <label
              htmlFor="comment-content"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Comment
            </label>
            <textarea
              id="comment-content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Write your comment... Use @username to mention someone"
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              required
            />
          </div>

          {/* Mention suggestions */}
          {users && users.length > 0 && (
            <div>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Mention:
              </span>
              <div className="flex flex-wrap gap-1 mt-1">
                {users.slice(0, 5).map((user) => (
                  <button
                    key={user.user_id}
                    type="button"
                    onClick={() => handleInsertMention(user.username)}
                    className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
                  >
                    @{user.username}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending || !content.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPending ? "Posting..." : replyTo ? "Reply" : "Post Comment"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function StatsPanel({
  stats,
}: {
  stats: import("../api/comments").CommentStats | undefined;
}) {
  if (!stats) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        📊 Comment Statistics
      </h3>

      <div className="grid grid-cols-2 gap-4">
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {stats.total_comments}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Total Comments
          </div>
        </div>
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {stats.active_threads}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Active Threads
          </div>
        </div>
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-yellow-600">
            {stats.pinned_comments}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">Pinned</div>
        </div>
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-green-600">
            {stats.resolved_comments}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Resolved
          </div>
        </div>
      </div>

      {/* Activity */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500 dark:text-gray-400">Today</span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {stats.comments_today} comments
          </span>
        </div>
        <div className="flex justify-between text-sm mt-2">
          <span className="text-gray-500 dark:text-gray-400">This Week</span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {stats.comments_this_week} comments
          </span>
        </div>
      </div>
    </div>
  );
}

function TopCommentersPanel({
  commenters,
}: {
  commenters: Array<{
    user_id: string;
    username: string;
    comment_count: number;
  }>;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        🏆 Top Commenters
      </h3>

      <div className="space-y-3">
        {commenters.map((commenter, index) => (
          <div
            key={commenter.user_id}
            className="flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <span className="text-gray-500 dark:text-gray-400 font-medium">
                #{index + 1}
              </span>
              <span className="text-gray-900 dark:text-gray-100">
                {commenter.username}
              </span>
            </div>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {commenter.comment_count} comments
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TargetDistributionPanel({
  distribution,
}: {
  distribution: Record<CommentTarget, number>;
}) {
  const entries = Object.entries(distribution) as Array<
    [CommentTarget, number]
  >;
  const total = entries.reduce((sum, [, count]) => sum + count, 0);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        📈 Comments by Target
      </h3>

      <div className="space-y-3">
        {entries.map(([type, count]) => {
          const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
          return (
            <div key={type}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {getTargetTypeEmoji(type)} {getTargetTypeLabel(type)}
                </span>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {count}
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full"
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function CommentsPage() {
  const [activeTab, setActiveTab] = useState<TabType>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState<CommentTarget | "">("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [replyTo, setReplyTo] = useState<Comment | null>(null);

  // Build search params based on active tab and filters
  const searchParams: CommentSearchParams = useMemo(() => {
    const params: CommentSearchParams = {
      sort_by: "created_at",
      sort_order: "desc",
    };

    if (searchTerm) {
      params.search = searchTerm;
    }

    if (filterType) {
      params.target_type = filterType;
    }

    switch (activeTab) {
      case "mine":
        params.user_id = "me"; // Backend will resolve to current user
        break;
      case "pinned":
        params.is_pinned = true;
        break;
      case "unresolved":
        params.is_resolved = false;
        break;
    }

    return params;
  }, [activeTab, searchTerm, filterType]);

  // Queries
  const {
    data: comments,
    isPending: isLoadingComments,
    error: commentsError,
  } = useComments(searchParams);
  const { data: stats } = useCommentStats();

  // Mutations
  const createComment = useCreateComment();
  const deleteComment = useDeleteComment();
  const pinComment = usePinComment();
  const unpinComment = useUnpinComment();
  const resolveComment = useResolveComment();
  const unresolveComment = useUnresolveComment();

  // Handlers
  const handleCreateComment = async (data: {
    target_type: CommentTarget;
    target_id: string;
    content: string;
    parent_id?: string;
  }) => {
    await createComment.mutateAsync(data);
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this comment?")) {
      await deleteComment.mutateAsync(id);
    }
  };

  const handleReply = (comment: Comment) => {
    setReplyTo(comment);
    setIsModalOpen(true);
  };

  const handleOpenNewComment = () => {
    setReplyTo(null);
    setIsModalOpen(true);
  };

  const tabs: Array<{ key: TabType; label: string; count?: number }> = [
    { key: "all", label: "All Comments", count: stats?.total_comments },
    { key: "mine", label: "My Comments" },
    { key: "pinned", label: "📌 Pinned", count: stats?.pinned_comments },
    {
      key: "unresolved",
      label: "Unresolved",
      count: stats ? stats.total_comments - stats.resolved_comments : undefined,
    },
  ];

  // Current user ID (would come from auth context in real app)
  const currentUserId = "me";

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            💬 Comments
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Discuss and annotate sources, images, and observations
          </p>
        </div>
        <button
          onClick={handleOpenNewComment}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <span>✏️</span>
          New Comment
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-3 space-y-4">
          {/* Tabs */}
          <div className="flex items-center gap-2 border-b border-gray-200 dark:border-gray-700">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.key
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
                }`}
              >
                {tab.label}
                {tab.count !== undefined && (
                  <span className="ml-2 text-xs bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <input
                type="text"
                placeholder="Search comments..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </div>
            <select
              value={filterType}
              onChange={(e) =>
                setFilterType(e.target.value as CommentTarget | "")
              }
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              aria-label="Filter by target type"
            >
              <option value="">All Types</option>
              <option value="source">Sources</option>
              <option value="image">Images</option>
              <option value="observation">Observations</option>
              <option value="job">Jobs</option>
              <option value="ms">Measurement Sets</option>
            </select>
          </div>

          {/* Comments List */}
          {isLoadingComments ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              Loading comments...
            </div>
          ) : commentsError ? (
            <div className="text-center py-8 text-red-500">
              Error loading comments
            </div>
          ) : comments?.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              {activeTab === "mine"
                ? "You haven't posted any comments yet."
                : activeTab === "pinned"
                ? "No pinned comments."
                : activeTab === "unresolved"
                ? "No unresolved comments. Great work! 🎉"
                : "No comments found."}
            </div>
          ) : (
            <div className="space-y-4">
              {comments?.map((comment) => (
                <CommentCard
                  key={comment.id}
                  comment={comment}
                  isOwner={comment.user_id === currentUserId}
                  onPin={(id) => pinComment.mutate(id)}
                  onUnpin={(id) => unpinComment.mutate(id)}
                  onResolve={(id) => resolveComment.mutate(id)}
                  onUnresolve={(id) => unresolveComment.mutate(id)}
                  onDelete={handleDelete}
                  onReply={handleReply}
                />
              ))}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <StatsPanel stats={stats} />
          {stats?.top_commenters && (
            <TopCommentersPanel commenters={stats.top_commenters} />
          )}
          {stats?.target_distribution && (
            <TargetDistributionPanel distribution={stats.target_distribution} />
          )}

          {/* Tips */}
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">
              💡 Comment Tips
            </h4>
            <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
              <li>• Use @username to mention team members</li>
              <li>• Pin important comments for visibility</li>
              <li>• Mark resolved when discussion is complete</li>
              <li>• Reply to keep discussions organized</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Create Comment Modal */}
      <CreateCommentModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setReplyTo(null);
        }}
        onSubmit={handleCreateComment}
        replyTo={replyTo}
        isPending={createComment.isPending}
      />
    </div>
  );
}
