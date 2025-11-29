import React, { useState, useCallback } from "react";

export type ConfidenceLevel = "true" | "false" | "unsure";

export interface RatingTag {
  id: string;
  name: string;
  color?: string;
  description?: string;
}

export interface PreviousRating {
  id: string;
  confidence: ConfidenceLevel;
  tag: RatingTag;
  notes?: string;
  user: string;
  date: string;
}

export interface RatingCardProps {
  /** ID of the item being rated */
  itemId: string;
  /** Display name for the item */
  itemName: string;
  /** Available classification tags */
  tags: RatingTag[];
  /** Previous rating if exists */
  previousRating?: PreviousRating;
  /** Callback when rating is submitted */
  onSubmit: (rating: {
    itemId: string;
    confidence: ConfidenceLevel;
    tagId: string;
    notes: string;
  }) => Promise<void>;
  /** Callback to navigate to next unrated item */
  onNextUnrated?: () => void;
  /** Callback to create a new tag */
  onCreateTag?: (name: string, description: string) => Promise<RatingTag>;
  /** Loading state */
  isLoading?: boolean;
  /** Custom class name */
  className?: string;
}

const CONFIDENCE_OPTIONS: { value: ConfidenceLevel; label: string; color: string }[] = [
  { value: "true", label: "True", color: "bg-green-500" },
  { value: "false", label: "False", color: "bg-red-500" },
  { value: "unsure", label: "Unsure", color: "bg-yellow-500" },
];

/**
 * Rating card component for classifying candidates.
 * Displays previous rating if exists and allows updating.
 */
const RatingCard: React.FC<RatingCardProps> = ({
  itemId,
  itemName,
  tags,
  previousRating,
  onSubmit,
  onNextUnrated,
  onCreateTag,
  isLoading = false,
  className = "",
}) => {
  const [confidence, setConfidence] = useState<ConfidenceLevel>(
    previousRating?.confidence || "false"
  );
  const [selectedTagId, setSelectedTagId] = useState<string>(
    previousRating?.tag.id || tags[0]?.id || ""
  );
  const [notes, setNotes] = useState<string>(previousRating?.notes || "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showNewTagForm, setShowNewTagForm] = useState(false);
  const [newTagName, setNewTagName] = useState("");
  const [newTagDescription, setNewTagDescription] = useState("");

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!selectedTagId) return;

      setIsSubmitting(true);
      try {
        await onSubmit({
          itemId,
          confidence,
          tagId: selectedTagId,
          notes,
        });
      } finally {
        setIsSubmitting(false);
      }
    },
    [itemId, confidence, selectedTagId, notes, onSubmit]
  );

  const handleCreateTag = useCallback(async () => {
    if (!newTagName.trim() || !onCreateTag) return;

    try {
      const newTag = await onCreateTag(newTagName.trim(), newTagDescription.trim());
      setSelectedTagId(newTag.id);
      setNewTagName("");
      setNewTagDescription("");
      setShowNewTagForm(false);
    } catch (error) {
      console.error("Failed to create tag:", error);
    }
  }, [newTagName, newTagDescription, onCreateTag]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className={`card ${className}`}>
      <div className="card-header">
        <h4 className="text-lg font-semibold">Rate: {itemName}</h4>
      </div>

      <div className="card-body space-y-4">
        {/* Previous Rating Display */}
        {previousRating && (
          <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
            <p className="text-sm text-gray-600 mb-2">Your previous rating:</p>
            <div className="space-y-1 text-sm">
              <div className="flex gap-2">
                <span className="font-medium">Real variable?</span>
                <span
                  className={`badge ${
                    previousRating.confidence === "true"
                      ? "badge-success"
                      : previousRating.confidence === "false"
                      ? "badge-error"
                      : "badge-warning"
                  }`}
                >
                  {previousRating.confidence.charAt(0).toUpperCase() +
                    previousRating.confidence.slice(1)}
                </span>
              </div>
              <div className="flex gap-2">
                <span className="font-medium">Tag:</span>
                <span className="badge badge-info">{previousRating.tag.name}</span>
              </div>
              <div className="flex gap-2">
                <span className="font-medium">Date:</span>
                <span>{formatDate(previousRating.date)}</span>
              </div>
              {previousRating.notes && (
                <div>
                  <span className="font-medium">Notes:</span>
                  <p className="mt-1 text-gray-600 bg-white p-2 rounded border max-h-24 overflow-y-auto">
                    {previousRating.notes}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        <hr className="border-gray-200" />

        {/* Rating Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Confidence Selection */}
          <div className="form-group">
            <label className="form-label">Real variable?</label>
            <div className="flex gap-2">
              {CONFIDENCE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setConfidence(option.value)}
                  className={`flex-1 py-2 px-3 rounded-md font-medium transition-all ${
                    confidence === option.value
                      ? `${option.color} text-white shadow-md`
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tag Selection */}
          <div className="form-group">
            <label className="form-label">Classification Tag</label>
            <div className="flex gap-2">
              <select
                value={selectedTagId}
                onChange={(e) => setSelectedTagId(e.target.value)}
                className="form-select flex-1"
              >
                <option value="">Select a tag...</option>
                {tags.map((tag) => (
                  <option key={tag.id} value={tag.id}>
                    {tag.name}
                  </option>
                ))}
              </select>
              {onCreateTag && (
                <button
                  type="button"
                  onClick={() => setShowNewTagForm(!showNewTagForm)}
                  className="btn btn-success btn-sm"
                  title="Create new tag"
                >
                  +
                </button>
              )}
            </div>
          </div>

          {/* New Tag Form */}
          {showNewTagForm && onCreateTag && (
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-200 space-y-2">
              <input
                type="text"
                value={newTagName}
                onChange={(e) => setNewTagName(e.target.value)}
                placeholder="Tag name"
                className="form-control"
              />
              <textarea
                value={newTagDescription}
                onChange={(e) => setNewTagDescription(e.target.value)}
                placeholder="Description (optional)"
                rows={2}
                className="form-control"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowNewTagForm(false)}
                  className="btn btn-secondary btn-sm"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleCreateTag}
                  disabled={!newTagName.trim()}
                  className="btn btn-primary btn-sm"
                >
                  Add Tag
                </button>
              </div>
            </div>
          )}

          {/* Notes */}
          <div className="form-group">
            <label className="form-label">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any observations or notes..."
              rows={4}
              className="form-control"
            />
          </div>

          {/* Action Buttons */}
          <div className="space-y-2">
            <button
              type="submit"
              disabled={isSubmitting || isLoading || !selectedTagId}
              className="btn btn-primary w-full"
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Saving...
                </span>
              ) : previousRating ? (
                "Update Rating"
              ) : (
                "Submit Rating"
              )}
            </button>

            {onNextUnrated && (
              <button type="button" onClick={onNextUnrated} className="btn btn-success w-full">
                Next Unrated Candidate :arrow_right:
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};

export default RatingCard;
