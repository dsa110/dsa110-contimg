/**
 * useFeatureFlag - React hook for feature flag state
 *
 * Provides reactive access to feature flags that updates
 * when features are toggled at runtime.
 */
import { useState, useEffect, useCallback } from "react";
import type { FeatureFlags } from "../config/features";
import { getFeatures, isFeatureEnabled, getFeatureFallbackMessage } from "../config/features";

interface FeatureFlagState {
  /** Whether the feature is enabled */
  enabled: boolean;
  /** Fallback message to display when disabled */
  fallbackMessage: string;
}

/**
 * Hook to check feature flag status
 *
 * @param featureName - The feature to check
 * @returns Object with enabled status and fallback message
 *
 * @example
 * const { enabled, fallbackMessage } = useFeatureFlag('absurd');
 * if (!enabled) return <Alert>{fallbackMessage}</Alert>;
 */
export function useFeatureFlag(featureName: keyof FeatureFlags): FeatureFlagState {
  const [state, setState] = useState<FeatureFlagState>(() => ({
    enabled: isFeatureEnabled(featureName),
    fallbackMessage: getFeatureFallbackMessage(featureName),
  }));

  // Periodically check for runtime changes (every 5 seconds)
  useEffect(() => {
    const checkFeature = () => {
      const enabled = isFeatureEnabled(featureName);
      const fallbackMessage = getFeatureFallbackMessage(featureName);

      setState((prev) => {
        if (prev.enabled !== enabled || prev.fallbackMessage !== fallbackMessage) {
          return { enabled, fallbackMessage };
        }
        return prev;
      });
    };

    const interval = setInterval(checkFeature, 5000);
    return () => clearInterval(interval);
  }, [featureName]);

  return state;
}

/**
 * Hook to get all feature flags
 */
export function useFeatureFlags(): FeatureFlags {
  const [features, setFeatures] = useState<FeatureFlags>(() => getFeatures());

  useEffect(() => {
    const interval = setInterval(() => {
      setFeatures(getFeatures());
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return features;
}

/**
 * Hook that returns a component wrapper for feature-gated content
 */
export function useFeatureGate(featureName: keyof FeatureFlags) {
  const { enabled, fallbackMessage } = useFeatureFlag(featureName);

  const FeatureGate = useCallback(
    ({ children, fallback }: { children: React.ReactNode; fallback?: React.ReactNode }) => {
      if (!enabled) {
        return fallback ?? null;
      }
      return <>{children}</>;
    },
    [enabled]
  );

  return { enabled, fallbackMessage, FeatureGate };
}
