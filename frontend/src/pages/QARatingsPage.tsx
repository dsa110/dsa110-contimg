/**
 * QA Ratings Page
 *
 * Provides:
 * - Star rating interface for sources and images
 * - Quality flag assignment
 * - Review queue management
 * - Rating statistics dashboard
 */

import React, { useState } from "react";
import {
  useRatingStats,
  useRatingQueue,
  useUserRatings,
  useSubmitRating,
  useRemoveFromQueue,
  type Rating,
  type RatingTarget,
  type RatingCategory,
  type QualityFlag,
  type QueueItem,
  type RatingStats,
} from "../api/ratings";

// Star rating component
interface StarRatingProps {
  value: number;
  onChange?: (value: number) => void;
  readonly?: boolean;
  size?: "sm" | "md" | "lg";
}

function StarRating({
  value,
  onChange,
  readonly = false,
  size = "md",
}: StarRatingProps) {
  const [hoverValue, setHoverValue] = useState(0);

  const sizeClasses = {
    sm: "text-lg",
    md: "text-2xl",
    lg: "text-3xl",
  };

  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={readonly}
          className={`${sizeClasses[size]} ${
            readonly ? "cursor-default" : "cursor-pointer hover:scale-110"
          } transition-transform`}
          onMouseEnter={() => !readonly && setHoverValue(star)}
          onMouseLeave={() => !readonly && setHoverValue(0)}
          onClick={() => onChange?.(star)}
        >
          {(hoverValue || value) >= star ? "⭐" : "☆"}
        </button>
      ))}
    </div>
  );
}

// Quality flag badge
function QualityFlagBadge({ flag }: { flag: QualityFlag }) {
  const colors: Record<QualityFlag, string> = {
    good: "text-green-600 bg-green-100 dark:bg-green-900/30",
    uncertain: "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30",
    bad: "text-red-600 bg-red-100 dark:bg-red-900/30",
    needs_review: "text-blue-600 bg-blue-100 dark:bg-blue-900/30",
  };

  const labels: Record<QualityFlag, string> = {
    good: "Good",
    uncertain: "Uncertain",
    bad: "Bad",
    needs_review: "Needs Review",
  };

  return (
    <span
      className={`px-2 py-1 text-xs font-medium rounded-full ${colors[flag]}`}
    >
      {labels[flag]}
    </span>
  );
}

// Rating card component
interface RatingCardProps {
  rating: Rating;
}

function RatingCard({ rating }: RatingCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <span className="text-2xl">
            {rating.target_type === "source" ? "🔭" : "🖼️"}
          </span>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-gray-100">
              {rating.target_type === "source" ? "Source" : "Image"}{" "}
              {rating.target_id}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {rating.category} • by {rating.username}
            </p>
          </div>
        </div>
        <QualityFlagBadge flag={rating.flag} />
      </div>
      <div className="mt-4 flex items-center gap-4">
        <StarRating value={rating.value} readonly size="sm" />
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {new Date(rating.created_at).toLocaleDateString()}
        </span>
      </div>
      {rating.comment && (
        <p className="mt-3 text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50 p-2 rounded">
          {rating.comment}
        </p>
      )}
    </div>
  );
}

// Queue item card
interface QueueItemCardProps {
  item: QueueItem;
  onRate: () => void;
  onRemove: () => void;
}

function QueueItemCard({ item, onRate, onRemove }: QueueItemCardProps) {
  const priorityColors: Record<QueueItem["priority"], string> = {
    high: "text-red-600 bg-red-100 dark:bg-red-900/30",
    medium: "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30",
    low: "text-green-600 bg-green-100 dark:bg-green-900/30",
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <span className="text-2xl">
            {item.target_type === "source" ? "🔭" : "🖼️"}
          </span>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-gray-100">
              {item.name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {item.reason}
            </p>
          </div>
        </div>
        <span
          className={`px-2 py-1 text-xs font-medium rounded-full capitalize ${
            priorityColors[item.priority]
          }`}
        >
          {item.priority}
        </span>
      </div>
      <div className="mt-4 flex gap-2">
        <button
          onClick={onRate}
          className="flex-1 px-3 py-1.5 text-sm text-blue-700 bg-blue-100 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg"
        >
          Rate Now
        </button>
        <button
          onClick={onRemove}
          className="flex-1 px-3 py-1.5 text-sm text-gray-700 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 rounded-lg"
        >
          Remove
        </button>
      </div>
    </div>
  );
}

// Stats panel
interface StatsPanelProps {
  stats: RatingStats;
}

function StatsPanel({ stats }: StatsPanelProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Rating Statistics
      </h2>
      <div className="grid grid-cols-2 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {stats.total_ratings}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Total Ratings
          </div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            {stats.average_rating.toFixed(1)}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Average Rating
          </div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
            {stats.sources_rated}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Sources Rated
          </div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
            {stats.images_rated}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Images Rated
          </div>
        </div>
      </div>
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500 dark:text-gray-400">Today</span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {stats.ratings_today} ratings
          </span>
        </div>
        <div className="flex justify-between text-sm mt-2">
          <span className="text-gray-500 dark:text-gray-400">This Week</span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {stats.ratings_this_week} ratings
          </span>
        </div>
      </div>
    </div>
  );
}

// Submit rating modal
interface SubmitRatingModalProps {
  isOpen: boolean;
  onClose: () => void;
  targetType?: RatingTarget;
  targetId?: string;
  targetName?: string;
}

function SubmitRatingModal({
  isOpen,
  onClose,
  targetType: initialTargetType,
  targetId: initialTargetId,
  targetName,
}: SubmitRatingModalProps) {
  const [targetType, setTargetType] = useState<RatingTarget>(
    initialTargetType || "source"
  );
  const [targetId, setTargetId] = useState(initialTargetId || "");
  const [category, setCategory] = useState<RatingCategory>("overall");
  const [value, setValue] = useState(0);
  const [flag, setFlag] = useState<QualityFlag>("good");
  const [comment, setComment] = useState("");

  const submitRating = useSubmitRating();

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await submitRating.mutateAsync({
      target_type: targetType,
      target_id: targetId,
      category,
      value,
      flag,
      comment: comment || undefined,
    });
    onClose();
  };

  const categories: RatingCategory[] = [
    "overall",
    "flux",
    "morphology",
    "position",
    "calibration",
  ];

  const flags: QualityFlag[] = ["good", "uncertain", "bad", "needs_review"];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Submit Rating
              {targetName && (
                <span className="text-sm font-normal text-gray-500 ml-2">
                  for {targetName}
                </span>
              )}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            >
              ✕
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {!initialTargetType && (
              <div>
                <label
                  htmlFor="target-type-select"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Target Type
                </label>
                <select
                  id="target-type-select"
                  value={targetType}
                  onChange={(e) =>
                    setTargetType(e.target.value as RatingTarget)
                  }
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                >
                  <option value="source">Source</option>
                  <option value="image">Image</option>
                </select>
              </div>
            )}

            {!initialTargetId && (
              <div>
                <label
                  htmlFor="target-id-input"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Target ID
                </label>
                <input
                  id="target-id-input"
                  type="text"
                  value={targetId}
                  onChange={(e) => setTargetId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder={`Enter ${targetType} ID`}
                  required
                />
              </div>
            )}

            <div>
              <label
                htmlFor="category-select"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Category
              </label>
              <select
                id="category-select"
                value={category}
                onChange={(e) => setCategory(e.target.value as RatingCategory)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat.charAt(0).toUpperCase() + cat.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Rating
              </label>
              <div className="flex items-center gap-4">
                <StarRating value={value} onChange={setValue} size="lg" />
                <span className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  {value > 0 ? `${value}/5` : "Select rating"}
                </span>
              </div>
            </div>

            <div>
              <label
                htmlFor="flag-select"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Quality Flag
              </label>
              <select
                id="flag-select"
                value={flag}
                onChange={(e) => setFlag(e.target.value as QualityFlag)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                {flags.map((f) => (
                  <option key={f} value={f}>
                    {f
                      .split("_")
                      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                      .join(" ")}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="comment-input"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Comment (optional)
              </label>
              <textarea
                id="comment-input"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                placeholder="Add notes about this rating..."
              />
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={value === 0 || submitRating.isPending}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {submitRating.isPending ? "Submitting..." : "Submit Rating"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// Top raters panel
interface TopRatersPanelProps {
  topRaters: RatingStats["top_raters"];
}

function TopRatersPanel({ topRaters }: TopRatersPanelProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        🏆 Top Raters
      </h2>
      <div className="space-y-3">
        {topRaters.map((rater, index) => (
          <div key={rater.user_id} className="flex items-center gap-3">
            <span className="text-lg font-bold text-gray-400">
              #{index + 1}
            </span>
            <div className="flex-1">
              <div className="font-medium text-gray-900 dark:text-gray-100">
                {rater.username}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {rater.rating_count} ratings
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Main page component
export default function QARatingsPage() {
  const [activeTab, setActiveTab] = useState<"queue" | "my-ratings" | "all">(
    "queue"
  );
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [selectedQueueItem, setSelectedQueueItem] = useState<QueueItem | null>(
    null
  );

  // Queries
  const statsQuery = useRatingStats();
  const queueQuery = useRatingQueue();
  const userRatingsQuery = useUserRatings();

  // Mutations
  const removeFromQueue = useRemoveFromQueue();

  const handleRateFromQueue = (item: QueueItem) => {
    setSelectedQueueItem(item);
    setShowSubmitModal(true);
  };

  const handleRemoveFromQueue = async (item: QueueItem) => {
    await removeFromQueue.mutateAsync({
      targetType: item.target_type,
      targetId: item.target_id,
    });
  };

  const tabs = [
    { id: "queue", label: "Review Queue", count: queueQuery.data?.length },
    {
      id: "my-ratings",
      label: "My Ratings",
      count: userRatingsQuery.data?.length,
    },
    { id: "all", label: "All Activity" },
  ] as const;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <span className="text-3xl">⭐</span>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                QA Ratings
              </h1>
              <p className="text-gray-500 dark:text-gray-400">
                Rate sources and images for quality assessment
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              setSelectedQueueItem(null);
              setShowSubmitModal(true);
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
          >
            <span>+</span>
            Submit Rating
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main content */}
          <div className="lg:col-span-3">
            {/* Tabs */}
            <div className="flex gap-2 mb-6">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    activeTab === tab.id
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
                  }`}
                >
                  {tab.label}
                  {tab.count !== undefined && (
                    <span className="ml-2 px-2 py-0.5 text-xs bg-white/20 rounded-full">
                      {tab.count}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Tab content */}
            {activeTab === "queue" && (
              <div>
                {queueQuery.isPending ? (
                  <div className="text-center py-8 text-gray-500">
                    Loading queue...
                  </div>
                ) : queueQuery.error ? (
                  <div className="text-center py-8 text-red-500">
                    Error loading queue
                  </div>
                ) : queueQuery.data?.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No items in review queue. Great job! 🎉
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {queueQuery.data?.map((item) => (
                      <QueueItemCard
                        key={`${item.target_type}-${item.target_id}`}
                        item={item}
                        onRate={() => handleRateFromQueue(item)}
                        onRemove={() => handleRemoveFromQueue(item)}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "my-ratings" && (
              <div>
                {userRatingsQuery.isPending ? (
                  <div className="text-center py-8 text-gray-500">
                    Loading your ratings...
                  </div>
                ) : userRatingsQuery.error ? (
                  <div className="text-center py-8 text-red-500">
                    Error loading ratings
                  </div>
                ) : userRatingsQuery.data?.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    You haven&apos;t submitted any ratings yet.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {userRatingsQuery.data?.map((rating) => (
                      <RatingCard key={rating.id} rating={rating} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "all" && (
              <div className="text-center py-8 text-gray-500">
                All activity view coming soon...
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Stats */}
            {statsQuery.data && <StatsPanel stats={statsQuery.data} />}

            {/* Top raters */}
            {statsQuery.data?.top_raters && (
              <TopRatersPanel topRaters={statsQuery.data.top_raters} />
            )}

            {/* Flag distribution */}
            {statsQuery.data && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                  Quality Distribution
                </h2>
                <div className="space-y-2">
                  {(
                    Object.entries(statsQuery.data.flag_distribution) as [
                      QualityFlag,
                      number
                    ][]
                  ).map(([flag, count]) => (
                    <div
                      key={flag}
                      className="flex items-center justify-between"
                    >
                      <QualityFlagBadge flag={flag} />
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {count}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tips */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                💡 Rating Tips
              </h2>
              <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <li>• Rate overall quality first, then specific aspects</li>
                <li>• Use flags to quickly mark data quality</li>
                <li>• Add comments for unusual cases</li>
                <li>• Check the queue regularly for priority items</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Submit Rating Modal */}
      <SubmitRatingModal
        isOpen={showSubmitModal}
        onClose={() => {
          setShowSubmitModal(false);
          setSelectedQueueItem(null);
        }}
        targetType={selectedQueueItem?.target_type}
        targetId={selectedQueueItem?.target_id}
        targetName={selectedQueueItem?.name}
      />
    </div>
  );
}
