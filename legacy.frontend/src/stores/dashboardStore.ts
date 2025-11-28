/**
 * Dashboard State Store
 *
 * Zustand store for managing dashboard state and transitions.
 *
 * NOTE: Requires Zustand to be installed:
 *   npm install zustand
 *
 * @module stores/dashboardStore
 */

import { create } from "zustand";
import type {
  DashboardState,
  DashboardMode,
  DashboardContext,
  IdleState,
  AutonomousState,
  DiscoveryState,
  InvestigationState,
  DebuggingState,
  ManualControlState,
  AnalysisState,
} from "./dashboardState";

interface DashboardStore {
  state: DashboardState;
  context: DashboardContext;

  // Actions
  setState: (state: DashboardState) => void;
  transitionTo: (mode: DashboardMode, data?: Record<string, unknown>) => void;
  updateContext: (updates: Partial<DashboardContext>) => void;

  // State helpers
  isIdle: () => boolean;
  isAutonomous: () => boolean;
  isDiscovery: () => boolean;
  isInvestigation: () => boolean;
  isDebugging: () => boolean;
  isManualControl: () => boolean;
  isAnalysis: () => boolean;

  // Context helpers
  setUserIntent: (intent: DashboardContext["userIntent"]) => void;
  addRecentAction: (action: DashboardContext["recentActions"][0]) => void;
  addWorkflowStep: (step: DashboardContext["workflowHistory"][0]) => void;
}

// Initial state
const initialIdleState: IdleState = {
  mode: "idle",
  status: "healthy",
  lastUpdate: new Date(),
};

const initialContext: DashboardContext = {
  state: initialIdleState,
  userIntent: null,
  recentActions: [],
  workflowHistory: [],
};

// Zustand store implementation
export const useDashboardStore = create<DashboardStore>((set, get) => ({
  state: initialIdleState,
  context: initialContext,

  setState: (newState) =>
    set({
      state: newState,
      context: { ...get().context, state: newState },
    }),

  transitionTo: (mode, data = {}) => {
    const now = new Date();
    let newState: DashboardState;

    switch (mode) {
      case "idle":
        newState = {
          mode: "idle",
          status: (data.status as IdleState["status"]) || "healthy",
          lastUpdate: now,
          streamingPipeline: data.streamingPipeline as IdleState["streamingPipeline"],
        };
        break;

      case "autonomous":
        newState = {
          mode: "autonomous",
          streamingPipeline: data.streamingPipeline as AutonomousState["streamingPipeline"],
          lastUpdate: now,
        };
        break;

      case "discovery":
        newState = {
          mode: "discovery",
          candidate: data.candidate as DiscoveryState["candidate"],
          investigationData: data.investigationData as DiscoveryState["investigationData"],
          autoExpanded: (data.autoExpanded as boolean) ?? true,
        };
        break;

      case "investigation":
        newState = {
          mode: "investigation",
          context: data.context as InvestigationState["context"],
          preloadedData: (data.preloadedData as Record<string, unknown>) || {},
        };
        break;

      case "debugging":
        newState = {
          mode: "debugging",
          issue: data.issue as DebuggingState["issue"],
          diagnosticData: (data.diagnosticData as Record<string, unknown>) || {},
          suggestedFixes: (data.suggestedFixes as DebuggingState["suggestedFixes"]) || [],
        };
        break;

      case "manual-control":
        newState = {
          mode: "manual-control",
          reason: data.reason as string,
          previousState: (data.previousState as DashboardState) || get().state,
          controlScope: (data.controlScope as ManualControlState["controlScope"]) || {},
          operations: (data.operations as ManualControlState["operations"]) || [],
        };
        break;

      case "analysis":
        newState = {
          mode: "analysis",
          workspace: data.workspace as AnalysisState["workspace"],
          activeTools: (data.activeTools as AnalysisState["activeTools"]) || [],
          dataProducts: (data.dataProducts as AnalysisState["dataProducts"]) || [],
          trustIndicators: (data.trustIndicators as AnalysisState["trustIndicators"]) || [],
          reproducibility: data.reproducibility as AnalysisState["reproducibility"],
        };
        break;

      default:
        newState = get().state;
    }

    set({
      state: newState,
      context: { ...get().context, state: newState },
    });
  },

  updateContext: (updates) =>
    set((state) => ({
      context: { ...state.context, ...updates },
    })),

  isIdle: () => get().state.mode === "idle",
  isAutonomous: () => get().state.mode === "autonomous",
  isDiscovery: () => get().state.mode === "discovery",
  isInvestigation: () => get().state.mode === "investigation",
  isDebugging: () => get().state.mode === "debugging",
  isManualControl: () => get().state.mode === "manual-control",
  isAnalysis: () => get().state.mode === "analysis",

  setUserIntent: (intent) =>
    set((state) => ({
      context: { ...state.context, userIntent: intent },
    })),

  addRecentAction: (action) =>
    set((state) => ({
      context: {
        ...state.context,
        recentActions: [action, ...state.context.recentActions.slice(0, 9)],
      },
    })),

  addWorkflowStep: (step) =>
    set((state) => ({
      context: {
        ...state.context,
        workflowHistory: [step, ...state.context.workflowHistory.slice(0, 49)],
      },
    })),
}));
