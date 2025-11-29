import React, { useState } from "react";

export interface TagFilterProps {
  /** Available tags */
  availableTags: string[];
  /** Currently included tags */
  includeTags: string[];
  /** Currently excluded tags */
  excludeTags: string[];
  /** Callback when include tags change */
  onIncludeChange: (tags: string[]) => void;
  /** Callback when exclude tags change */
  onExcludeChange: (tags: string[]) => void;
  /** Custom class name */
  className?: string;
}

/**
 * Tag include/exclude filter with autocomplete.
 */
const TagFilter: React.FC<TagFilterProps> = ({
  availableTags,
  includeTags,
  excludeTags,
  onIncludeChange,
  onExcludeChange,
  className = "",
}) => {
  const [includeInput, setIncludeInput] = useState("");
  const [excludeInput, setExcludeInput] = useState("");
  const [showIncludeSuggestions, setShowIncludeSuggestions] = useState(false);
  const [showExcludeSuggestions, setShowExcludeSuggestions] = useState(false);

  const getFilteredSuggestions = (input: string, currentTags: string[]) => {
    if (!input.trim()) return [];
    const lower = input.toLowerCase();
    return availableTags
      .filter((tag) => tag.toLowerCase().includes(lower) && !currentTags.includes(tag))
      .slice(0, 10);
  };

  const addTag = (
    tag: string,
    currentTags: string[],
    onChange: (tags: string[]) => void,
    setInput: (val: string) => void
  ) => {
    if (!currentTags.includes(tag)) {
      onChange([...currentTags, tag]);
    }
    setInput("");
  };

  const removeTag = (tag: string, currentTags: string[], onChange: (tags: string[]) => void) => {
    onChange(currentTags.filter((t) => t !== tag));
  };

  const renderTagInput = (
    label: string,
    input: string,
    setInput: (val: string) => void,
    tags: string[],
    onChange: (tags: string[]) => void,
    showSuggestions: boolean,
    setShowSuggestions: (show: boolean) => void,
    tooltip: string
  ) => {
    const suggestions = getFilteredSuggestions(input, tags);

    return (
      <div className="form-group">
        <div className="flex items-center gap-2 mb-1">
          <label className="form-label mb-0 font-semibold">{label}</label>
          <span className="text-gray-400 cursor-help" title={tooltip}>
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
                clipRule="evenodd"
              />
            </svg>
          </span>
        </div>

        {/* Selected tags */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {tags.map((tag) => (
              <span key={tag} className="badge badge-secondary flex items-center gap-1">
                {tag}
                <button
                  onClick={() => removeTag(tag, tags, onChange)}
                  className="hover:text-red-500"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Input with suggestions */}
        <div className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && input.trim()) {
                e.preventDefault();
                if (suggestions.length > 0) {
                  addTag(suggestions[0], tags, onChange, setInput);
                } else if (availableTags.includes(input.trim())) {
                  addTag(input.trim(), tags, onChange, setInput);
                }
              }
            }}
            placeholder="Type to search tags..."
            className="form-control w-full"
          />

          {/* Suggestions dropdown */}
          {showSuggestions && suggestions.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-48 overflow-auto">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => addTag(suggestion, tags, onChange, setInput)}
                  className="w-full text-left px-3 py-2 hover:bg-gray-100 text-sm"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {renderTagInput(
        "Include Tags",
        includeInput,
        setIncludeInput,
        includeTags,
        onIncludeChange,
        showIncludeSuggestions,
        setShowIncludeSuggestions,
        "Only return sources that have the given tags."
      )}
      {renderTagInput(
        "Exclude Tags",
        excludeInput,
        setExcludeInput,
        excludeTags,
        onExcludeChange,
        showExcludeSuggestions,
        setShowExcludeSuggestions,
        "Only return sources that do NOT have the given tags."
      )}
    </div>
  );
};

export default TagFilter;
