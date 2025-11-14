# Anticipatory Dashboard Implementation Plan

**Vision:** A unified command center that anticipates user needs, eliminates unnecessary steps, and guides users seamlessly through complex workflows. The dashboard serves as the primary interface for monitoring and controlling the autonomous streaming pipeline, with manual override capabilities when needed.

**Philosophy:** Combine Jony Ive's minimalism with Steve Jobs' workflow-focused UX - "It just works."

**Core Principle:** The streaming pipeline operates autonomously, but the dashboard provides complete visibility and control. When everything runs smoothly, the dashboard stays quiet. When intervention is needed, it anticipates what you'll want to do.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Streaming Pipeline Integration](#streaming-pipeline-integration)
3. [State Management System](#state-management-system)
4. [Pre-fetching & Anticipation Engine](#pre-fetching--anticipation-engine)
5. [Contextual Intelligence](#contextual-intelligence)
6. [Workflow State Machine](#workflow-state-machine)
7. [UI Components](#ui-components)
8. [Autonomous Operation Monitoring](#autonomous-operation-monitoring)
9. [Manual Override & Control](#manual-override--control)
10. [Analysis & Exploration Workspace](#analysis--exploration-workspace)
11. [Implementation Phases](#implementation-phases)
12. [Code Examples](#code-examples)

---

## Architecture Overview

### Core Principles

1. **Unified Command Center** - Single interface for all pipeline operations
2. **Autonomous-First** - Dashboard monitors autonomous operations, intervenes only when needed
3. **State-Driven UI** - Interface adapts to current context (autonomous vs manual vs analysis)
4. **Predictive Loading** - Data loads before it's requested
5. **Contextual Actions** - Only show relevant actions
6. **Workflow Guidance** - Guide users through complex tasks
7. **Zero Configuration** - Smart defaults, optional overrides
8. **Manual Override** - Full control when autonomous operations need intervention
9. **Flexible Analysis** - Powerful yet trustworthy exploratory tools for data products
10. **Deterministic Results** - All analysis operations are reproducible and traceable

### System Components

```
┌─────────────────────────────────────────────────────────┐
│              Unified Command Center                      │
│  (Dashboard Shell - Adapts to autonomous/manual state)  │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
│ Streaming    │  │ State         │  │ Pre-fetch     │
│ Pipeline     │  │ Machine       │  │ Engine        │
│ Monitor      │  │               │  │               │
└──────────────┘  └───────────────┘  └───────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
│ Autonomous   │  │ Manual       │  │ Contextual   │
│ Operations   │  │ Override     │  │ Intelligence │
│ Tracker      │  │ Controller   │  │               │
└──────────────┘  └───────────────┘  └──────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
│ React Query  │  │ WebSocket     │  │ UI           │
│ Cache        │  │ Updates       │  │ Components   │
└──────────────┘  └───────────────┘  └──────────────┘
```

### Streaming Pipeline Integration

The dashboard integrates deeply with the streaming pipeline:

- **Autonomous Operation Monitoring** - Track what the pipeline is doing autonomously
- **Manual Override Capabilities** - Take control when needed
- **Unified Status View** - Single view of autonomous + manual operations
- **Intervention Detection** - Automatically detect when manual intervention is needed
- **Control Handoff** - Seamless transition between autonomous and manual modes

---

## State Management System

### Dashboard State Types

```typescript
// frontend/src/stores/dashboardState.ts

export type DashboardMode = 
  | 'idle'           // Normal monitoring, autonomous operations running smoothly
  | 'autonomous'     // Streaming pipeline operating autonomously (monitoring mode)
  | 'discovery'      // ESE candidate detected
  | 'investigation'  // User investigating something
  | 'debugging'      // System issue detected
  | 'manual-control' // User has taken manual control (override mode)
  | 'analysis';      // Analysis/exploration workspace for data products

export type SystemStatus = 
  | 'healthy'        // Everything operational
  | 'attention'      // Something needs looking at
  | 'action-required'; // Immediate action needed

export interface IdleState {
  mode: 'idle';
  status: SystemStatus;
  lastUpdate: Date;
  streamingPipeline: {
    status: 'running' | 'stopped' | 'error';
    autonomous: boolean; // Is pipeline operating autonomously?
    lastActivity: Date;
  };
}

export interface AutonomousState {
  mode: 'autonomous';
  streamingPipeline: {
    status: 'running';
    currentOperations: AutonomousOperation[];
    metrics: StreamingMetrics;
    config: StreamingConfig;
  };
  lastUpdate: Date;
}

export interface AutonomousOperation {
  id: string;
  type: 'conversion' | 'calibration' | 'imaging' | 'mosaicking' | 'qa';
  status: 'pending' | 'in-progress' | 'completed' | 'failed';
  progress?: number; // 0-100
  startedAt: Date;
  estimatedCompletion?: Date;
  resourceUsage?: {
    cpu: number;
    memory: number;
  };
  details?: Record<string, unknown>;
}

export interface DiscoveryState {
  mode: 'discovery';
  candidate: ESECandidate;
  investigationData: PreloadedInvestigationData;
  autoExpanded: boolean; // Auto-expand investigation panel
}

export interface InvestigationState {
  mode: 'investigation';
  context: {
    sourceId?: string;
    msPath?: string;
    imageId?: string;
    focus: 'light-curve' | 'calibration' | 'catalog' | 'imaging';
  };
  preloadedData: Record<string, unknown>;
}

export interface DebuggingState {
  mode: 'debugging';
  issue: {
    type: 'failed-job' | 'pipeline-error' | 'system-warning';
    id: string;
    severity: 'warning' | 'error' | 'critical';
  };
  diagnosticData: DiagnosticData;
  suggestedFixes: SuggestedFix[];
}

export interface ManualControlState {
  mode: 'manual-control';
  reason: 'user-initiated' | 'autonomous-failure' | 'intervention-required';
  previousState: DashboardState; // State before manual takeover
  controlScope: {
    streaming?: boolean; // Controlling streaming service
    calibration?: boolean; // Controlling calibration
    imaging?: boolean; // Controlling imaging
    mosaicking?: boolean; // Controlling mosaicking
  };
  operations: ManualOperation[];
}

export interface AnalysisState {
  mode: 'analysis';
  workspace: AnalysisWorkspace;
  activeTools: AnalysisTool[];
  dataProducts: DataProduct[];
  trustIndicators: TrustIndicator[];
  reproducibility: ReproducibilityInfo;
}

export interface AnalysisWorkspace {
  id: string;
  name: string;
  createdAt: Date;
  dataProducts: {
    images: ImageProduct[];
    mosaics: MosaicProduct[];
    catalogs: CatalogProduct[];
  };
  activeComparisons: CatalogComparison[];
  activeInvestigations: SourceInvestigation[];
  savedViews: SavedView[];
}

export interface AnalysisTool {
  id: string;
  type: 'catalog-comparison' | 'image-analysis' | 'source-investigation' | 'mosaic-analysis' | 'qa-review';
  name: string;
  state: Record<string, unknown>;
  results: AnalysisResult[];
  trustScore: number; // 0-1, indicates reliability
  deterministic: boolean; // Is this operation deterministic?
}

export interface TrustIndicator {
  type: 'qa-metric' | 'calibration-status' | 'catalog-match' | 'reproducibility';
  label: string;
  value: number | string;
  status: 'trusted' | 'warning' | 'untrusted';
  details?: string;
}

export interface ReproducibilityInfo {
  analysisId: string;
  parameters: Record<string, unknown>;
  dataVersions: {
    image: string;
    catalog: string;
    calibration: string;
  };
  codeVersion: string;
  timestamp: Date;
  canReproduce: boolean;
  reproductionScript?: string;
}

export type DashboardState = 
  | IdleState 
  | AutonomousState
  | DiscoveryState 
  | InvestigationState 
  | DebuggingState
  | ManualControlState
  | AnalysisState;

export interface DashboardContext {
  state: DashboardState;
  userIntent: UserIntent | null;
  recentActions: Action[];
  workflowHistory: WorkflowStep[];
}
```

### State Store (Zustand)

```typescript
// frontend/src/stores/dashboardStore.ts

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

interface DashboardStore {
  state: DashboardState;
  context: DashboardContext;
  
  // Actions
  setState: (state: DashboardState) => void;
  transitionTo: (mode: DashboardMode, data?: unknown) => void;
  updateContext: (updates: Partial<DashboardContext>) => void;
  
  // State helpers
  isIdle: () => boolean;
  isDiscovery: () => boolean;
  isInvestigation: () => boolean;
  isDebugging: () => boolean;
  
  // Context helpers
  getSuggestedActions: () => Action[];
  getPreloadTargets: () => string[];
}

export const useDashboardStore = create<DashboardStore>()(
  immer((set, get) => ({
    state: { mode: 'idle', status: 'healthy', lastUpdate: new Date() },
    context: {
      state: { mode: 'idle', status: 'healthy', lastUpdate: new Date() },
      userIntent: null,
      recentActions: [],
      workflowHistory: [],
    },
    
    setState: (newState) => set((draft) => {
      draft.state = newState;
      draft.context.state = newState;
    }),
    
    transitionTo: (mode, data) => set((draft) => {
      switch (mode) {
        case 'idle':
          draft.state = { 
            mode: 'idle', 
            status: data?.status || 'healthy',
            lastUpdate: new Date() 
          };
          break;
        case 'discovery':
          draft.state = {
            mode: 'discovery',
            candidate: data.candidate,
            investigationData: data.investigationData,
            autoExpanded: true,
          };
          break;
        case 'investigation':
          draft.state = {
            mode: 'investigation',
            context: data.context,
            preloadedData: data.preloadedData || {},
          };
          break;
        case 'debugging':
          draft.state = {
            mode: 'debugging',
            issue: data.issue,
            diagnosticData: data.diagnosticData,
            suggestedFixes: data.suggestedFixes || [],
          };
          break;
        case 'autonomous':
          draft.state = {
            mode: 'autonomous',
            streamingPipeline: data.streamingPipeline,
            lastUpdate: new Date(),
          };
          break;
        case 'manual-control':
          draft.state = {
            mode: 'manual-control',
            reason: data.reason,
            previousState: data.previousState || get().state,
            controlScope: data.controlScope || {},
            operations: data.operations || [],
          };
          break;
        case 'analysis':
          draft.state = {
            mode: 'analysis',
            workspace: data.workspace,
            activeTools: data.activeTools || [],
            dataProducts: data.dataProducts || [],
            trustIndicators: data.trustIndicators || [],
            reproducibility: data.reproducibility,
          };
          break;
      }
      draft.context.state = draft.state;
    }),
    
    updateContext: (updates) => set((draft) => {
      Object.assign(draft.context, updates);
    }),
    
    isIdle: () => get().state.mode === 'idle',
    isAutonomous: () => get().state.mode === 'autonomous',
    isDiscovery: () => get().state.mode === 'discovery',
    isInvestigation: () => get().state.mode === 'investigation',
    isDebugging: () => get().state.mode === 'debugging',
    isManualControl: () => get().state.mode === 'manual-control',
    isAnalysis: () => get().state.mode === 'analysis',
    
    getSuggestedActions: () => {
      const state = get().state;
      const context = get().context;
      return suggestActions(state, context);
    },
    
    getPreloadTargets: () => {
      const state = get().state;
      const context = get().context;
      return getPreloadTargets(state, context);
    },
  }))
);
```

---

## Pre-fetching & Anticipation Engine

### Pre-fetch Strategy

```typescript
// frontend/src/hooks/useAnticipatoryPrefetch.ts

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useDashboardStore } from '../stores/dashboardStore';

export function useAnticipatoryPrefetch() {
  const queryClient = useQueryClient();
  const state = useDashboardStore((s) => s.state);
  const preloadTargets = useDashboardStore((s) => s.getPreloadTargets());
  
  useEffect(() => {
    // Pre-fetch based on current state
    const prefetchPromises: Promise<unknown>[] = [];
    
    switch (state.mode) {
      case 'idle':
        // Pre-fetch likely next steps
        if (state.status === 'attention') {
          // Something needs attention, pre-fetch diagnostic data
          prefetchPromises.push(
            queryClient.prefetchQuery(['pipeline-status']),
            queryClient.prefetchQuery(['system-metrics']),
          );
        }
        break;
        
      case 'discovery':
        // Pre-fetch everything needed for investigation
        const candidate = state.candidate;
        prefetchPromises.push(
          queryClient.prefetchQuery(['light-curve', candidate.source_id]),
          queryClient.prefetchQuery(['calibration-qa', candidate.ms_path]),
          queryClient.prefetchQuery(['catalog-comparison', candidate.source_id]),
          queryClient.prefetchQuery(['historical-context', candidate.source_id]),
        );
        break;
        
      case 'investigation':
        // Pre-fetch related data based on focus
        const { context } = state;
        if (context.focus === 'light-curve' && context.sourceId) {
          prefetchPromises.push(
            queryClient.prefetchQuery(['light-curve', context.sourceId]),
            queryClient.prefetchQuery(['source-metadata', context.sourceId]),
          );
        }
        if (context.msPath) {
          prefetchPromises.push(
            queryClient.prefetchQuery(['ms-metadata', context.msPath]),
            queryClient.prefetchQuery(['calibration-qa', context.msPath]),
            queryClient.prefetchQuery(['image-qa', context.msPath]),
          );
        }
        break;
        
      case 'debugging':
        // Pre-fetch diagnostic and fix data
        const { issue } = state;
        prefetchPromises.push(
          queryClient.prefetchQuery(['job-details', issue.id]),
          queryClient.prefetchQuery(['diagnostic-data', issue.id]),
        );
        break;
    }
    
    // Pre-fetch based on preload targets
    preloadTargets.forEach((target) => {
      const [key, ...args] = target.split(':');
      prefetchPromises.push(
        queryClient.prefetchQuery([key, ...args])
      );
    });
    
    Promise.all(prefetchPromises).catch((error) => {
      console.warn('Prefetch failed:', error);
      // Don't show errors for prefetch failures
    });
  }, [state, preloadTargets, queryClient]);
}
```

### Preload Target Calculator

```typescript
// frontend/src/utils/preloadTargets.ts

export function getPreloadTargets(
  state: DashboardState,
  context: DashboardContext
): string[] {
  const targets: string[] = [];
  
  // If viewing MS, pre-fetch related data
  if (context.userIntent?.type === 'view-ms' && context.userIntent.msPath) {
    targets.push(`calibration-status:${context.userIntent.msPath}`);
    targets.push(`imaging-status:${context.userIntent.msPath}`);
    targets.push(`qa-results:${context.userIntent.msPath}`);
  }
  
  // If viewing calibration, pre-fetch imaging and QA
  if (context.userIntent?.type === 'view-calibration' && context.userIntent.msPath) {
    targets.push(`imaging-status:${context.userIntent.msPath}`);
    targets.push(`qa-results:${context.userIntent.msPath}`);
  }
  
  // If viewing image, pre-fetch QA
  if (context.userIntent?.type === 'view-image' && context.userIntent.imageId) {
    targets.push(`qa-results:${context.userIntent.imageId}`);
    targets.push(`catalog-overlay:${context.userIntent.imageId}`);
  }
  
  // Based on recent actions, predict next steps
  const lastAction = context.recentActions[context.recentActions.length - 1];
  if (lastAction?.type === 'calibration-completed') {
    targets.push(`apply-calibration:${lastAction.msPath}`);
  }
  
  if (lastAction?.type === 'imaging-completed') {
    targets.push(`qa-results:${lastAction.msPath}`);
  }
  
  return targets;
}
```

---

## Contextual Intelligence

### Action Suggestion Engine

```typescript
// frontend/src/utils/suggestActions.ts

export interface Action {
  id: string;
  label: string;
  description?: string;
  primary: boolean;
  icon?: React.ReactNode;
  onClick: () => void;
  category: 'investigation' | 'control' | 'analysis' | 'export';
}

export function suggestActions(
  state: DashboardState,
  context: DashboardContext
): Action[] {
  const actions: Action[] = [];
  
  switch (state.mode) {
    case 'idle':
      if (state.status === 'attention') {
        actions.push({
          id: 'view-details',
          label: 'View Details',
          description: 'See what needs attention',
          primary: true,
          onClick: () => {
            // Transition to debugging mode
            useDashboardStore.getState().transitionTo('debugging', {
              issue: { type: 'system-warning', id: 'attention', severity: 'warning' },
            });
          },
          category: 'investigation',
        });
      }
      break;
      
    case 'discovery':
      const candidate = state.candidate;
      actions.push(
        {
          id: 'investigate',
          label: 'Investigate',
          description: 'View full investigation data',
          primary: true,
          onClick: () => {
            useDashboardStore.getState().transitionTo('investigation', {
              context: {
                sourceId: candidate.source_id,
                focus: 'light-curve',
              },
            });
          },
          category: 'investigation',
        },
        {
          id: 'view-light-curve',
          label: 'View Light Curve',
          description: 'See flux over time',
          primary: false,
          onClick: () => {
            // Data already pre-loaded
            navigate(`/sources/${candidate.source_id}/light-curve`);
          },
          category: 'analysis',
        },
        {
          id: 'compare-catalog',
          label: 'Compare Catalog',
          description: 'Compare with NVSS/VLASS',
          primary: false,
          onClick: () => {
            navigate(`/sources/${candidate.source_id}/catalog-comparison`);
          },
          category: 'analysis',
        },
        {
          id: 'export-report',
          label: 'Export Report',
          description: 'Generate investigation report',
          primary: false,
          onClick: () => {
            generateReport(candidate);
          },
          category: 'export',
        }
      );
      break;
      
    case 'investigation':
      const { context: invContext } = state;
      
      if (invContext.msPath) {
        actions.push({
          id: 'view-calibration-qa',
          label: 'View Calibration QA',
          description: 'Check calibration quality',
          primary: invContext.focus === 'calibration',
          onClick: () => {
            // Data already pre-loaded
            navigate(`/qa/calibration/${invContext.msPath}`);
          },
          category: 'analysis',
        });
      }
      
      if (invContext.sourceId) {
        actions.push({
          id: 'view-light-curve',
          label: 'View Light Curve',
          description: 'See flux over time',
          primary: invContext.focus === 'light-curve',
          onClick: () => {
            navigate(`/sources/${invContext.sourceId}/light-curve`);
          },
          category: 'analysis',
        });
      }
      break;
      
    case 'debugging':
      const { issue, suggestedFixes } = state;
      
      suggestedFixes.forEach((fix, idx) => {
        actions.push({
          id: `fix-${idx}`,
          label: fix.label,
          description: fix.description,
          primary: idx === 0, // First fix is primary
          onClick: () => {
            applyFix(fix);
          },
          category: 'control',
        });
      });
      
      actions.push({
        id: 'view-details',
        label: 'View Details',
        description: 'See full diagnostic information',
        primary: false,
        onClick: () => {
          navigate(`/debug/${issue.id}`);
        },
        category: 'investigation',
      });
      break;
  }
  
  // Add workflow-based suggestions
  const workflowSuggestions = getWorkflowSuggestions(context);
  actions.push(...workflowSuggestions);
  
  return actions;
}

function getWorkflowSuggestions(context: DashboardContext): Action[] {
  const suggestions: Action[] = [];
  const lastAction = context.recentActions[context.recentActions.length - 1];
  
  // If calibration just completed, suggest applying it
  if (lastAction?.type === 'calibration-completed') {
    suggestions.push({
      id: 'apply-calibration',
      label: 'Apply Calibration',
      description: 'Apply to target observations',
      primary: true,
      onClick: () => {
        applyCalibration(lastAction.msPath);
      },
      category: 'control',
    });
  }
  
  // If imaging completed, suggest viewing QA
  if (lastAction?.type === 'imaging-completed') {
    suggestions.push({
      id: 'view-qa',
      label: 'View QA Results',
      description: 'Check image quality',
      primary: true,
      onClick: () => {
        navigate(`/qa/image/${lastAction.msPath}`);
      },
      category: 'analysis',
    });
  }
  
  return suggestions;
}
```

### State Transition Logic

```typescript
// frontend/src/hooks/useStateTransitions.ts

import { useEffect } from 'react';
import { useDashboardStore } from '../stores/dashboardStore';
import { useESECandidates } from '../api/queries';
import { usePipelineStatus } from '../api/queries';

export function useStateTransitions() {
  const transitionTo = useDashboardStore((s) => s.transitionTo);
  const currentState = useDashboardStore((s) => s.state);
  
  const { data: eseCandidates } = useESECandidates();
  const { data: pipelineStatus } = usePipelineStatus();
  
  useEffect(() => {
    // Auto-transition to discovery mode if ESE detected
    if (
      currentState.mode === 'idle' &&
      eseCandidates?.candidates &&
      eseCandidates.candidates.length > 0
    ) {
      const activeCandidate = eseCandidates.candidates.find(
        (c) => c.status === 'active'
      );
      
      if (activeCandidate) {
        // Pre-load investigation data
        preloadInvestigationData(activeCandidate).then((investigationData) => {
          transitionTo('discovery', {
            candidate: activeCandidate,
            investigationData,
          });
        });
      }
    }
    
    // Auto-transition to debugging if issues detected
    if (currentState.mode === 'idle' && pipelineStatus) {
      const hasFailures = pipelineStatus.queue.failed > 0;
      const hasAttention = pipelineStatus.queue.in_progress > 10; // Queue backing up
      
      if (hasFailures || hasAttention) {
        transitionTo('debugging', {
          issue: {
            type: hasFailures ? 'failed-job' : 'system-warning',
            id: 'pipeline-issue',
            severity: hasFailures ? 'error' : 'warning',
          },
          diagnosticData: await getDiagnosticData(pipelineStatus),
          suggestedFixes: await getSuggestedFixes(pipelineStatus),
        });
      }
    }
  }, [eseCandidates, pipelineStatus, currentState.mode, transitionTo]);
}
```

---

## Workflow State Machine

### Workflow Definition

```typescript
// frontend/src/workflows/types.ts

export type WorkflowType = 
  | 'ese-investigation'
  | 'pipeline-debugging'
  | 'calibration-workflow'
  | 'imaging-workflow';

export interface WorkflowStep {
  id: string;
  label: string;
  description: string;
  component: React.ComponentType;
  required: boolean;
  completed: boolean;
  data?: unknown;
}

export interface Workflow {
  id: WorkflowType;
  label: string;
  steps: WorkflowStep[];
  currentStep: number;
  completed: boolean;
}

export const WORKFLOWS: Record<WorkflowType, Workflow> = {
  'ese-investigation': {
    id: 'ese-investigation',
    label: 'ESE Investigation',
    steps: [
      {
        id: 'view-discovery',
        label: 'Review Discovery',
        description: 'Examine ESE candidate details',
        component: DiscoveryReviewStep,
        required: true,
        completed: false,
      },
      {
        id: 'analyze-light-curve',
        label: 'Analyze Light Curve',
        description: 'Review flux variability over time',
        component: LightCurveAnalysisStep,
        required: true,
        completed: false,
      },
      {
        id: 'verify-calibration',
        label: 'Verify Calibration',
        description: 'Ensure calibration quality',
        component: CalibrationVerificationStep,
        required: false,
        completed: false,
      },
      {
        id: 'compare-catalog',
        label: 'Compare Catalog',
        description: 'Compare with known sources',
        component: CatalogComparisonStep,
        required: false,
        completed: false,
      },
      {
        id: 'generate-report',
        label: 'Generate Report',
        description: 'Create investigation report',
        component: ReportGenerationStep,
        required: false,
        completed: false,
      },
    ],
    currentStep: 0,
    completed: false,
  },
  // ... other workflows
};
```

### Workflow Manager

```typescript
// frontend/src/workflows/WorkflowManager.tsx

export function WorkflowManager() {
  const state = useDashboardStore((s) => s.state);
  const workflow = useWorkflowStore((s) => s.currentWorkflow);
  
  if (!workflow) return null;
  
  const currentStep = workflow.steps[workflow.currentStep];
  const CurrentStepComponent = currentStep.component;
  
  return (
    <Box>
      {/* Progress indicator */}
      <WorkflowProgress workflow={workflow} />
      
      {/* Current step */}
      <CurrentStepComponent 
        step={currentStep}
        workflow={workflow}
        onComplete={() => {
          // Auto-advance to next step
          useWorkflowStore.getState().advanceStep();
        }}
        onSkip={() => {
          // Skip optional step
          useWorkflowStore.getState().skipStep();
        }}
      />
      
      {/* Suggested next actions */}
      <WorkflowActions workflow={workflow} />
    </Box>
  );
}
```

---

## UI Components

### Adaptive Dashboard Shell

```typescript
// frontend/src/components/DashboardShell.tsx

export function DashboardShell() {
  const state = useDashboardStore((s) => s.state);
  const suggestedActions = useDashboardStore((s) => s.getSuggestedActions());
  
  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Adaptive header */}
      <DashboardHeader state={state} />
      
      {/* Main content - adapts to state */}
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        {state.mode === 'idle' && <IdleView state={state} />}
        {state.mode === 'autonomous' && <AutonomousView state={state} />}
        {state.mode === 'discovery' && <DiscoveryView state={state} />}
        {state.mode === 'investigation' && <InvestigationView state={state} />}
        {state.mode === 'debugging' && <DebuggingView state={state} />}
        {state.mode === 'manual-control' && <ManualControlView state={state} />}
        {state.mode === 'analysis' && <AnalysisView state={state} />}
      </Box>
      
      {/* Contextual action bar */}
      {suggestedActions.length > 0 && (
        <ActionBar actions={suggestedActions} />
      )}
    </Box>
  );
}
```

### Idle View (Minimal)

```typescript
// frontend/src/components/views/IdleView.tsx

export function IdleView({ state }: { state: IdleState }) {
  const getStatusColor = (status: SystemStatus) => {
    switch (status) {
      case 'healthy': return '#4CAF50';
      case 'attention': return '#FFC107';
      case 'action-required': return '#F44336';
    }
  };
  
  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#0A0E27',
      }}
    >
      <Typography
        variant="h1"
        sx={{
          fontSize: '72px',
          fontWeight: 300,
          color: getStatusColor(state.status),
          mb: 2,
        }}
      >
        {state.status === 'healthy' && 'All Quiet'}
        {state.status === 'attention' && 'Attention'}
        {state.status === 'action-required' && 'Action Required'}
      </Typography>
      
      <Typography
        variant="h6"
        sx={{
          color: '#F5F5F5',
          fontWeight: 300,
          mb: 4,
        }}
      >
        Monitoring the universe
      </Typography>
      
      {state.status !== 'healthy' && (
        <Button
          variant="contained"
          onClick={() => {
            useDashboardStore.getState().transitionTo('debugging', {
              issue: {
                type: 'system-warning',
                id: 'attention',
                severity: state.status === 'action-required' ? 'error' : 'warning',
              },
            });
          }}
          sx={{ mt: 2 }}
        >
          View Details
        </Button>
      )}
      
      <Typography
        variant="caption"
        sx={{
          color: '#888',
          mt: 4,
        }}
      >
        Last update: {formatTimeAgo(state.lastUpdate)}
      </Typography>
    </Box>
  );
}
```

### Discovery View (Focused)

```typescript
// frontend/src/components/views/DiscoveryView.tsx

export function DiscoveryView({ state }: { state: DiscoveryState }) {
  const { candidate, investigationData } = state;
  
  return (
    <Box sx={{ p: 4 }}>
      {/* Discovery header */}
      <Box sx={{ mb: 4, textAlign: 'center' }}>
        <Typography variant="h2" sx={{ mb: 1 }}>
          ⭐ Discovery
        </Typography>
        <Typography variant="h4" sx={{ fontFamily: 'monospace', mb: 2 }}>
          {candidate.source_id}
        </Typography>
        <Typography variant="h6" sx={{ color: '#FFD700' }}>
          {candidate.max_sigma_dev.toFixed(1)}σ deviation detected
        </Typography>
      </Box>
      
      {/* Pre-loaded investigation data */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Light Curve" />
            <CardContent>
              {/* Data already loaded */}
              <LightCurveChart data={investigationData.lightCurve} />
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Calibration Quality" />
            <CardContent>
              {/* Data already loaded */}
              <CalibrationQA data={investigationData.calibrationQA} />
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Catalog Comparison" />
            <CardContent>
              {/* Data already loaded */}
              <CatalogComparison data={investigationData.catalogComparison} />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      
      {/* Action buttons */}
      <Box sx={{ mt: 4, display: 'flex', gap: 2, justifyContent: 'center' }}>
        <Button
          variant="contained"
          size="large"
          onClick={() => {
            useDashboardStore.getState().transitionTo('investigation', {
              context: {
                sourceId: candidate.source_id,
                focus: 'light-curve',
              },
            });
          }}
        >
          Full Investigation
        </Button>
        <Button
          variant="outlined"
          size="large"
          onClick={() => {
            generateReport(candidate);
          }}
        >
          Export Report
        </Button>
      </Box>
    </Box>
  );
}
```

### Action Bar (Contextual)

```typescript
// frontend/src/components/ActionBar.tsx

export function ActionBar({ actions }: { actions: Action[] }) {
  return (
    <Paper
      sx={{
        p: 2,
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        backgroundColor: '#1A1E2E',
      }}
    >
      <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
        {actions.map((action) => (
          <Button
            key={action.id}
            variant={action.primary ? 'contained' : 'outlined'}
            startIcon={action.icon}
            onClick={action.onClick}
            sx={{
              minWidth: 200,
            }}
          >
            {action.label}
            {action.description && (
              <Tooltip title={action.description}>
                <InfoIcon sx={{ ml: 1, fontSize: 16 }} />
              </Tooltip>
            )}
          </Button>
        ))}
      </Box>
    </Paper>
  );
}
```

---

## VAST-Inspired Patterns Integration

### Overview

The VAST pipeline provides proven patterns for radio astronomy data analysis interfaces. This section integrates VAST's successful patterns into the DSA-110 dashboard implementation.

### Key VAST Patterns to Adopt

#### 1. Generic Table Component Pattern

**VAST Approach:** Single reusable template for all table views with dynamic column configuration.

**DSA-110 Implementation:**
```typescript
// frontend/src/components/GenericTable.tsx
// Inspired by VAST's generic_table.html

interface GenericTableProps {
  apiEndpoint: string;
  columns: TableColumn[];
  title?: string;
  searchable?: boolean;
  exportable?: boolean;
  // ... other props
}

export function GenericTable(props: GenericTableProps) {
  // Server-side pagination (like DataTables)
  // Dynamic column configuration
  // Export functionality (CSV, Excel)
  // Column visibility toggle
  // Search/filter
}
```

**Benefits:**
- Consistent table UI across all views
- Reduced code duplication
- Easy to add new table views
- Built-in export functionality

#### 2. Detail Page Pattern

**VAST Approach:** Three-column layout: Details card, Visualization, Comments/Annotations.

**DSA-110 Implementation:**
```typescript
// frontend/src/pages/SourceDetailPage.tsx
// Inspired by VAST's source_detail.html

export function SourceDetailPage({ sourceId }: { sourceId: string }) {
  return (
    <Grid container spacing={3}>
      {/* Column 1: Details */}
      <Grid item xs={12} md={4}>
        <SourceDetailsCard />
      </Grid>
      
      {/* Column 2: Visualization (Aladin Lite) */}
      <Grid item xs={12} md={4}>
        <AladinSkyViewer />
      </Grid>
      
      {/* Column 3: Comments */}
      <Grid item xs={12} md={4}>
        <CommentsPanel />
      </Grid>
      
      {/* Full width: Collapsible sections */}
      <Grid item xs={12}>
        <CollapsibleSection title="Light Curve">
          <SourceLightCurve />
        </CollapsibleSection>
      </Grid>
    </Grid>
  );
}
```

**Benefits:**
- Familiar layout for radio astronomers
- Efficient use of screen space
- Easy to scan information
- Consistent navigation patterns

#### 3. Query Interface Pattern

**VAST Approach:** Complex query builder with multiple filter criteria, saved queries, export.

**DSA-110 Implementation:**
```typescript
// frontend/src/components/SourceQueryBuilder.tsx
// Inspired by VAST's sources_query.html

export function SourceQueryBuilder() {
  // Filter by:
  // - Position (RA/Dec, radius)
  // - Flux range
  // - Variability metrics (v, eta)
  // - ESE candidate flag
  // - Date range
  // - Run selection
  // - Tags
  
  // Use React JSON Schema Form for dynamic forms
  // Save queries for reuse
  // Export results
}
```

**Benefits:**
- Powerful filtering capabilities
- Reusable queries
- Easy to extend with new filters
- Familiar to VAST users

#### 4. Measurement Pair Metrics

**VAST Approach:** Calculate 2-epoch variability metrics (Vs, m) for all measurement pairs.

**DSA-110 Backend Implementation:**
```python
# src/dsa110_contimg/pipeline/pairs.py
# Inspired by VAST's pairs.py

def calculate_vs_metric(
    flux_a: float, flux_b: float,
    flux_err_a: float, flux_err_b: float
) -> float:
    """T-statistic for variability (Mooley et al. 2016)."""
    return (flux_a - flux_b) / np.hypot(flux_err_a, flux_err_b)

def calculate_m_metric(flux_a: float, flux_b: float) -> float:
    """Modulation index (fractional variability)."""
    return 2 * ((flux_a - flux_b) / (flux_a + flux_b))

def calculate_measurement_pair_metrics(
    detections_df: pd.DataFrame,
    n_cpu: int = 0,
    max_partition_mb: int = 15,
) -> pd.DataFrame:
    """Calculate 2-epoch variability metrics for all detection pairs."""
    # Use Dask for parallel processing
    # Group by source
    # Generate all pairs
    # Calculate metrics
    # Return DataFrame with vs_peak, vs_int, m_peak, m_int
```

**Benefits:**
- Proven variability metrics
- Parallel processing for performance
- Essential for ESE detection
- Can aggregate per source

#### 5. Forced Extraction Pattern

**VAST Approach:** Fill gaps in light curves by extracting flux at known positions.

**DSA-110 Backend Implementation:**
```python
# src/dsa110_contimg/pipeline/forced_extraction.py
# Inspired by VAST's forced_extraction.py

def forced_extraction(
    sources: pd.DataFrame,
    image_path: str,
    background_path: str,
    noise_path: str,
    edge_buffer: float = 1.0,
) -> pd.DataFrame:
    """
    Extract flux for sources at known positions.
    Critical for ESE detection - need complete light curves.
    """
    # Handle edge cases
    # Check for NaN values
    # Use forced_phot library or custom implementation
```

**Benefits:**
- Complete light curves for analysis
- Essential for ESE detection
- Handles edge cases properly
- Parallel processing support

#### 6. Source Statistics Calculation

**VAST Approach:** Parallel groupby for aggregate metrics, weighted averages, nearest neighbor.

**DSA-110 Backend Implementation:**
```python
# src/dsa110_contimg/pipeline/finalise.py
# Inspired by VAST's finalise.py

def calculate_source_statistics(
    detections_df: pd.DataFrame,
    sources_df: pd.DataFrame,
    n_cpu: int = 0,
) -> pd.DataFrame:
    """
    Calculate aggregate statistics for sources:
    - Weighted averages (position, uncertainties)
    - Aggregate flux metrics (avg, max, min)
    - Variability metrics (v, eta)
    - Nearest neighbor distance
    - Pair metrics aggregates
    """
    # Use Dask for parallel groupby
    # Calculate weighted averages
    # Calculate variability metrics
    # Find nearest neighbors
    # Aggregate pair metrics
```

**Benefits:**
- Efficient parallel processing
- Comprehensive source metrics
- Proven algorithms
- Memory-efficient

#### 7. Visualization Patterns

**VAST → DSA-110 Mapping:**
- Bokeh plots → Plotly.js (already using)
- JS9 image viewer → JS9 integration (planned)
- Aladin Lite → Aladin Lite integration (planned)
- Datashader → Plotly with WebGL (for large datasets)

**Implementation:**
```typescript
// frontend/src/components/visualizations/

// Eta-V Plot (inspired by VAST's sources_etav_plot.html)
export function EtaVPlot({ sources }: { sources: Source[] }) {
  // Use Plotly.js
  // Color by ESE probability
  // Interactive selection
}

// Light Curve (inspired by VAST's source detail light curve)
export function SourceLightCurve({ sourceId }: { sourceId: string }) {
  // Use Plotly.js
  // Show forced vs detected differently
  // Interactive hover with cutouts
  // Link to measurement details
}
```

#### 8. Data Storage Patterns

**VAST Approach:**
- Parquet files for measurements per image
- Arrow format for very large datasets
- Parquet for sources, associations, relations

**DSA-110 Implementation:**
- Already using Parquet for some data
- Continue with Parquet for measurements
- Consider Arrow for measurement pairs if needed
- Store sources, associations in Parquet

#### 9. Bulk Operations Pattern

**VAST Approach:** Batch creation/update for performance.

**DSA-110 Implementation:**
```python
# src/dsa110_contimg/pipeline/loading.py
# Inspired by VAST's loading.py

def bulk_upload_detections(
    detections_df: pd.DataFrame,
    batch_size: int = 10000,
) -> List[int]:
    """Bulk create detections with batch processing."""
    # Use Django/FastAPI bulk_create equivalent
    # Process in batches
    # Return IDs
```

**Benefits:**
- Much faster than individual inserts
- Memory efficient
- Transaction safe

#### 10. Configuration Management

**VAST Approach:** YAML config with schema validation, Jinja2 templates.

**DSA-110 Implementation:**
- Already using YAML configs
- Add schema validation (like VAST's StrictYAML)
- Use templates for common configurations
- Validate inputs (file existence, matching files)

### Integration into Implementation Phases

These VAST patterns will be integrated into the existing implementation phases:

- **Phase 1**: Add generic table component, detail page pattern
- **Phase 2**: Implement measurement pair metrics, forced extraction
- **Phase 3**: Add query interface, visualization patterns
- **Phase 4**: Integrate bulk operations, source statistics
- **Phase 5**: Add analysis tools inspired by VAST patterns

See individual phase sections for detailed integration.

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Goal:** Set up state management and basic state transitions

**Tasks:**
1. Install Zustand for state management
2. Create dashboard state store
3. Implement basic state types (idle, autonomous, discovery, investigation, debugging, manual-control)
4. Create state transition functions
5. Add state transition hooks
6. Integrate streaming pipeline status monitoring

**Deliverables:**
- `dashboardStore.ts` - State management
- `useStateTransitions.ts` - Auto-transitions
- `useStreamingPipelineMonitor.ts` - Streaming pipeline monitoring
- Basic state machine working

### Phase 2: Pre-fetching Engine (Weeks 3-4)

**Goal:** Implement predictive data loading

**Tasks:**
1. Create pre-fetch hook
2. Implement preload target calculator
3. Add pre-fetch to React Query
4. Test pre-fetch performance

**Deliverables:**
- `useAnticipatoryPrefetch.ts` - Pre-fetch hook
- `preloadTargets.ts` - Target calculator
- Pre-fetch working for all states

### Phase 3: Contextual Intelligence (Weeks 5-6)

**Goal:** Implement action suggestions and workflow guidance

**Tasks:**
1. Create action suggestion engine
2. Implement workflow state machine
3. Add workflow manager component
4. Create workflow definitions

**Deliverables:**
- `suggestActions.ts` - Action engine
- `WorkflowManager.tsx` - Workflow UI
- Workflow definitions
- Action suggestions working

### Phase 4: UI Components (Weeks 7-8)

**Goal:** Build adaptive UI components

**Tasks:**
1. Create DashboardShell component
2. Build IdleView (minimal)
3. Build AutonomousView (streaming pipeline monitoring)
4. Build ManualControlView (override interface)
5. Build DiscoveryView (focused)
6. Build InvestigationView (detailed)
7. Build DebuggingView (diagnostic)
8. Build AnalysisView (exploratory workspace)
9. Create ActionBar component

**Deliverables:**
- All view components
- Adaptive shell
- Action bar
- Autonomous operations display
- Manual control interface
- Analysis workspace foundation
- Complete UI working

### Phase 4.5: Analysis Workspace Foundation (Weeks 9-10)

**Goal:** Build flexible, trustworthy, deterministic analysis workspace foundation

**Tasks:**
1. Install and configure Golden Layout
2. Install core analysis tools:
   - Monaco Editor (code viewing/editing)
   - React JSON Schema Form (parameter configuration)
   - React Split Pane (comparisons)
   - React Markdown (documentation)
   - React Hotkeys Hook (keyboard shortcuts)
3. Implement TrustIndicatorBar
4. Implement ReproducibilitySystem foundation
5. Build deterministic operation framework
6. Create basic workspace shell with Golden Layout
7. Test workspace persistence and layout saving

**Deliverables:**
- Golden Layout integrated
- Core analysis tools installed and configured
- Trust indicator system working
- Reproducibility foundation in place
- Basic workspace shell functional
- Layout persistence working

### Phase 4.6: Analysis Tools Implementation (Weeks 11-12)

**Goal:** Build core analysis tools with trust and reproducibility

**Tasks:**
1. Build CatalogComparisonTool
   - React JSON Schema Form for parameters
   - TanStack Table for results (install if needed)
   - React Diff Viewer for comparison (install)
   - Trust indicators integration
   - Reproducibility script generation
2. Build ImageAnalysisTool
   - Image selection with QA indicators
   - Parameter configuration form
   - Analysis results display
   - Trust score calculation
3. Build SourceInvestigationTool
   - Light curve visualization (Plotly)
   - Catalog comparison view
   - Image stack viewer
   - Profile fitting interface
   - Reproducibility info panel
4. Build MosaicAnalysisTool
   - Mosaic properties display
   - Comparison capabilities
   - Quality metrics
5. Integrate Monaco Editor for reproduction scripts
6. Test all tools with real data

**Deliverables:**
- All core analysis tools functional
- Trust indicators integrated in all tools
- Reproducibility scripts generated for all operations
- Tools tested with real data products

### Phase 4.7: Analysis Workspace Enhancement (Weeks 13-14)

**Goal:** Enhance workspace with advanced features and polish

**Tasks:**
1. Install and integrate additional tools:
   - React Flow (workflow visualization)
   - React Context Menu (right-click menus)
   - @dnd-kit (drag and drop)
2. Build workflow visualization
   - Visualize analysis pipelines
   - Show data lineage
   - Interactive workflow editor
3. Implement context menus
   - Right-click on images → "Open in JS9", "Compare", "Export"
   - Right-click on tools → "Close", "Duplicate", "Save template"
   - Right-click on workspace → "Save", "Export", "Share"
4. Add drag and drop
   - Drag data products into tools
   - Reorder analysis steps
   - Organize workspace layout
5. Create analysis workflow templates
6. Build workspace export/import
7. Add keyboard shortcuts for all common actions
8. Polish UI and interactions

**Deliverables:**
- Workflow visualization working
- Context menus functional
- Drag and drop integrated
- Analysis workflow templates
- Workspace export/import
- Keyboard shortcuts implemented
- Polished UI

### Phase 5: Integration & Polish (Weeks 15-16)

**Goal:** Integrate everything and polish UX

**Tasks:**
1. Integrate with existing API
2. Connect all analysis tools to backend
3. Integrate with existing components (JS9, Plotly, AG Grid)
4. Add animations and transitions
5. Polish visual design
6. Test all workflows (including analysis)
7. Performance optimization
8. Reproducibility testing and verification
9. User acceptance testing
10. Documentation and training materials

**Deliverables:**
- Fully integrated dashboard
- Analysis workspace fully functional
- All tools connected to backend
- Smooth animations
- Polished UI
- Performance optimized
- Reproducibility verified
- Documentation complete

---

## Streaming Pipeline Integration

### Autonomous Operation Tracking

```typescript
// frontend/src/hooks/useStreamingPipelineMonitor.ts

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useDashboardStore } from '../stores/dashboardStore';
import { useStreamingStatus, useStreamingMetrics } from '../api/queries';

export function useStreamingPipelineMonitor() {
  const queryClient = useQueryClient();
  const transitionTo = useDashboardStore((s) => s.transitionTo);
  const currentState = useDashboardStore((s) => s.state);
  
  const { data: streamingStatus } = useStreamingStatus();
  const { data: streamingMetrics } = useStreamingMetrics();
  
  useEffect(() => {
    if (!streamingStatus) return;
    
    // If streaming is running and we're in idle, transition to autonomous mode
    if (
      streamingStatus.running &&
      (currentState.mode === 'idle' || currentState.mode === 'autonomous')
    ) {
      // Fetch current operations from pipeline
      fetchAutonomousOperations().then((operations) => {
        transitionTo('autonomous', {
          streamingPipeline: {
            status: 'running',
            currentOperations: operations,
            metrics: streamingMetrics,
            config: streamingStatus.config,
          },
        });
      });
    }
    
    // If streaming stops and we're in autonomous mode, transition back to idle
    if (!streamingStatus.running && currentState.mode === 'autonomous') {
      transitionTo('idle', {
        status: streamingStatus.error ? 'attention' : 'healthy',
        streamingPipeline: {
          status: 'stopped',
          autonomous: false,
          lastActivity: new Date(),
        },
      });
    }
    
    // If streaming has errors, suggest manual intervention
    if (streamingStatus.error && currentState.mode === 'autonomous') {
      transitionTo('debugging', {
        issue: {
          type: 'pipeline-error',
          id: 'streaming-error',
          severity: 'error',
        },
        diagnosticData: {
          error: streamingStatus.error,
          status: streamingStatus,
        },
        suggestedFixes: [
          {
            label: 'Take Manual Control',
            description: 'Switch to manual control mode to diagnose issue',
            action: () => {
              transitionTo('manual-control', {
                reason: 'autonomous-failure',
                controlScope: { streaming: true },
              });
            },
          },
          {
            label: 'Restart Streaming Service',
            description: 'Restart the streaming service',
            action: () => {
              restartStreamingService();
            },
          },
        ],
      });
    }
  }, [streamingStatus, streamingMetrics, currentState.mode, transitionTo]);
}

async function fetchAutonomousOperations(): Promise<AutonomousOperation[]> {
  // Fetch current operations from pipeline API
  const response = await fetch('/api/streaming/operations');
  const data = await response.json();
  return data.operations;
}
```

### Manual Override Controller

```typescript
// frontend/src/hooks/useManualOverride.ts

import { useCallback } from 'react';
import { useDashboardStore } from '../stores/dashboardStore';
import { useStopStreaming, useStartStreaming } from '../api/queries';

export function useManualOverride() {
  const state = useDashboardStore((s) => s.state);
  const transitionTo = useDashboardStore((s) => s.transitionTo);
  const stopStreaming = useStopStreaming();
  const startStreaming = useStartStreaming();
  
  const takeManualControl = useCallback((scope: {
    streaming?: boolean;
    calibration?: boolean;
    imaging?: boolean;
    mosaicking?: boolean;
  }) => {
    const previousState = state;
    
    // Stop autonomous operations in scope
    if (scope.streaming && state.mode === 'autonomous') {
      stopStreaming.mutate(undefined, {
        onSuccess: () => {
          transitionTo('manual-control', {
            reason: 'user-initiated',
            previousState,
            controlScope: scope,
            operations: [],
          });
        },
      });
    } else {
      transitionTo('manual-control', {
        reason: 'user-initiated',
        previousState,
        controlScope: scope,
        operations: [],
      });
    }
  }, [state, transitionTo, stopStreaming]);
  
  const returnToAutonomous = useCallback(() => {
    if (state.mode === 'manual-control') {
      const { previousState } = state;
      
      // Restart autonomous operations
      if (state.controlScope.streaming) {
        startStreaming.mutate(undefined, {
          onSuccess: () => {
            // Return to previous state or autonomous mode
            if (previousState.mode === 'autonomous' || previousState.mode === 'idle') {
              transitionTo('autonomous', {
                streamingPipeline: {
                  status: 'running',
                  currentOperations: [],
                  metrics: null,
                  config: null,
                },
              });
            } else {
              transitionTo(previousState.mode, previousState);
            }
          },
        });
      } else {
        // No streaming restart needed, just return to previous state
        transitionTo(previousState.mode, previousState);
      }
    }
  }, [state, transitionTo, startStreaming]);
  
  return {
    takeManualControl,
    returnToAutonomous,
    isManualControl: state.mode === 'manual-control',
  };
}
```

### Autonomous Operations Display

```typescript
// frontend/src/components/views/AutonomousView.tsx

export function AutonomousView({ state }: { state: AutonomousState }) {
  const { streamingPipeline } = state;
  const { takeManualControl } = useManualOverride();
  
  return (
    <Box sx={{ p: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 1 }}>
            Autonomous Operations
          </Typography>
          <Typography variant="body2" sx={{ color: '#888' }}>
            Streaming pipeline operating autonomously
          </Typography>
        </Box>
        <Button
          variant="outlined"
          onClick={() => takeManualControl({ streaming: true })}
          sx={{ minWidth: 200 }}
        >
          Take Manual Control
        </Button>
      </Box>
      
      {/* Current Operations */}
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Active Operations" />
            <CardContent>
              {streamingPipeline.currentOperations.length > 0 ? (
                <List>
                  {streamingPipeline.currentOperations.map((op) => (
                    <ListItem key={op.id}>
                      <ListItemIcon>
                        {getOperationIcon(op.type)}
                      </ListItemIcon>
                      <ListItemText
                        primary={op.type}
                        secondary={`${op.status} - ${op.progress || 0}%`}
                      />
                      {op.progress !== undefined && (
                        <LinearProgress
                          variant="determinate"
                          value={op.progress}
                          sx={{ width: 200, ml: 2 }}
                        />
                      )}
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" sx={{ color: '#888', textAlign: 'center', py: 4 }}>
                  No active operations
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
        
        {/* Metrics */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Pipeline Metrics" />
            <CardContent>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  CPU Usage
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={streamingPipeline.metrics?.cpu_percent || 0}
                  sx={{ mt: 1 }}
                />
                <Typography variant="caption">
                  {streamingPipeline.metrics?.cpu_percent?.toFixed(1) || 0}%
                </Typography>
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Memory Usage
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={streamingPipeline.metrics?.memory_mb || 0}
                  sx={{ mt: 1 }}
                />
                <Typography variant="caption">
                  {streamingPipeline.metrics?.memory_mb?.toFixed(0) || 0} MB
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Configuration */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Configuration" />
            <CardContent>
              <Typography variant="body2">
                <strong>Input Directory:</strong> {streamingPipeline.config?.input_dir}
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                <strong>Output Directory:</strong> {streamingPipeline.config?.output_dir}
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                <strong>Max Workers:</strong> {streamingPipeline.config?.max_workers}
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                <strong>Expected Subbands:</strong> {streamingPipeline.config?.expected_subbands}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
```

### Manual Control View

```typescript
// frontend/src/components/views/ManualControlView.tsx

export function ManualControlView({ state }: { state: ManualControlState }) {
  const { returnToAutonomous } = useManualOverride();
  
  return (
    <Box sx={{ p: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 1 }}>
            Manual Control Mode
          </Typography>
          <Typography variant="body2" sx={{ color: '#888' }}>
            {state.reason === 'user-initiated' && 'You have taken manual control'}
            {state.reason === 'autonomous-failure' && 'Manual control activated due to autonomous failure'}
            {state.reason === 'intervention-required' && 'Manual intervention required'}
          </Typography>
        </Box>
        <Button
          variant="contained"
          onClick={returnToAutonomous}
          sx={{ minWidth: 200 }}
        >
          Return to Autonomous
        </Button>
      </Box>
      
      {/* Control Panels */}
      <Grid container spacing={3}>
        {state.controlScope.streaming && (
          <Grid item xs={12}>
            <Card>
              <CardHeader title="Streaming Service Control" />
              <CardContent>
                <StreamingControlPanel />
              </CardContent>
            </Card>
          </Grid>
        )}
        
        {state.controlScope.calibration && (
          <Grid item xs={12}>
            <Card>
              <CardHeader title="Calibration Control" />
              <CardContent>
                <CalibrationControlPanel />
              </CardContent>
            </Card>
          </Grid>
        )}
        
        {state.controlScope.imaging && (
          <Grid item xs={12}>
            <Card>
              <CardHeader title="Imaging Control" />
              <CardContent>
                <ImagingControlPanel />
              </CardContent>
            </Card>
          </Grid>
        )}
        
        {state.controlScope.mosaicking && (
          <Grid item xs={12}>
            <Card>
              <CardHeader title="Mosaicking Control" />
              <CardContent>
                <MosaickingControlPanel />
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
      
      {/* Manual Operations */}
      {state.operations.length > 0 && (
        <Box sx={{ mt: 4 }}>
          <Card>
            <CardHeader title="Manual Operations" />
            <CardContent>
              <List>
                {state.operations.map((op) => (
                  <ListItem key={op.id}>
                    <ListItemText
                      primary={op.label}
                      secondary={op.status}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Box>
      )}
    </Box>
  );
}
```

## Autonomous Operation Monitoring

### Operation Types

The dashboard tracks all autonomous operations performed by the streaming pipeline:

1. **UVH5 to MS Conversion** - Automatic conversion of incoming UVH5 files
2. **Calibration** - Automatic calibration using registry lookups
3. **Imaging** - Automatic imaging of calibrated data
4. **Mosaicking** - Automatic mosaicking of images
5. **QA** - Automatic quality assurance checks

### Real-time Operation Updates

```typescript
// frontend/src/hooks/useAutonomousOperations.ts

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useDashboardStore } from '../stores/dashboardStore';

export function useAutonomousOperations() {
  const queryClient = useQueryClient();
  const state = useDashboardStore((s) => s.state);
  
  useEffect(() => {
    if (state.mode !== 'autonomous') return;
    
    // Subscribe to WebSocket updates for autonomous operations
    const ws = new WebSocket('/api/ws/streaming-operations');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'operation-update') {
        // Update operation in state
        const currentState = useDashboardStore.getState().state;
        if (currentState.mode === 'autonomous') {
          const updatedOperations = currentState.streamingPipeline.currentOperations.map(
            (op) => op.id === data.operation.id ? data.operation : op
          );
          
          useDashboardStore.getState().setState({
            ...currentState,
            streamingPipeline: {
              ...currentState.streamingPipeline,
              currentOperations: updatedOperations,
            },
          });
        }
      }
      
      if (data.type === 'operation-completed') {
        // Remove completed operation, add to history
        const currentState = useDashboardStore.getState().state;
        if (currentState.mode === 'autonomous') {
          const filteredOperations = currentState.streamingPipeline.currentOperations.filter(
            (op) => op.id !== data.operation.id
          );
          
          useDashboardStore.getState().setState({
            ...currentState,
            streamingPipeline: {
              ...currentState.streamingPipeline,
              currentOperations: filteredOperations,
            },
          });
        }
      }
    };
    
    return () => {
      ws.close();
    };
  }, [state.mode, queryClient]);
}
```

### Operation History

```typescript
// frontend/src/components/AutonomousOperationHistory.tsx

export function AutonomousOperationHistory() {
  const { data: history } = useQuery({
    queryKey: ['autonomous-operations', 'history'],
    queryFn: async () => {
      const response = await fetch('/api/streaming/operations/history');
      return response.json();
    },
  });
  
  return (
    <Card>
      <CardHeader title="Recent Operations" />
      <CardContent>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Started</TableCell>
              <TableCell>Duration</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {history?.operations?.map((op) => (
              <TableRow key={op.id}>
                <TableCell>{op.type}</TableCell>
                <TableCell>
                  <Chip
                    label={op.status}
                    color={op.status === 'completed' ? 'success' : 'error'}
                    size="small"
                  />
                </TableCell>
                <TableCell>{formatDate(op.startedAt)}</TableCell>
                <TableCell>{formatDuration(op.duration)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
```

## Manual Override & Control

### Override Triggers

Manual control can be triggered in several ways:

1. **User-Initiated** - User explicitly takes control
2. **Autonomous Failure** - Pipeline error requires intervention
3. **Intervention Required** - System detects need for manual intervention

### Control Scope

When taking manual control, users can specify what they want to control:

- **Streaming Service** - Control UVH5 to MS conversion
- **Calibration** - Control calibration operations
- **Imaging** - Control imaging operations
- **Mosaicking** - Control mosaicking operations

### Override Workflow

```typescript
// frontend/src/workflows/manualOverrideWorkflow.ts

export const manualOverrideWorkflow: Workflow = {
  id: 'manual-override',
  label: 'Manual Override',
  steps: [
    {
      id: 'confirm-override',
      label: 'Confirm Override',
      description: 'Confirm you want to take manual control',
      component: ConfirmOverrideStep,
      required: true,
      completed: false,
    },
    {
      id: 'select-scope',
      label: 'Select Control Scope',
      description: 'Choose what to control manually',
      component: SelectControlScopeStep,
      required: true,
      completed: false,
    },
    {
      id: 'stop-autonomous',
      label: 'Stop Autonomous Operations',
      description: 'Stopping autonomous operations in selected scope',
      component: StopAutonomousStep,
      required: true,
      completed: false,
    },
    {
      id: 'manual-control',
      label: 'Manual Control',
      description: 'You now have manual control',
      component: ManualControlStep,
      required: true,
      completed: false,
    },
  ],
  currentStep: 0,
  completed: false,
};
```

### Return to Autonomous

When returning to autonomous mode, the dashboard:

1. Validates that manual operations are complete
2. Restarts autonomous operations in the control scope
3. Transitions back to autonomous or idle state
4. Resumes monitoring

## Analysis & Exploration Workspace

### Design Principles

The analysis workspace follows three core principles:

1. **Flexibility** - Support diverse analysis workflows without constraints
2. **Trustworthiness** - Clear indicators of data quality and result reliability
3. **Determinism** - All operations are reproducible and traceable

### Workspace Architecture

```typescript
// frontend/src/components/analysis/AnalysisWorkspace.tsx

import { GoldenLayout } from 'golden-layout';
import { HotkeysProvider } from 'react-hotkeys-hook';

export function AnalysisWorkspace() {
  const state = useDashboardStore((s) => s.state);
  const workspace = state.mode === 'analysis' ? state.workspace : null;
  
  if (!workspace) return null;
  
  return (
    <HotkeysProvider>
      <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
        {/* Trust & Reproducibility Bar */}
        <TrustIndicatorBar indicators={state.trustIndicators} />
        
        {/* Main Workspace - Golden Layout */}
        <GoldenLayout
          config={workspace.layout}
          onStateChange={(layout) => {
            saveWorkspaceLayout(workspace.id, layout);
          }}
        >
          {/* Tool Panels - Registered Components */}
          {workspace.activeTools.map((tool) => (
            <ToolPanel key={tool.id} tool={tool} />
          ))}
        </GoldenLayout>
        
        {/* Analysis Toolbar */}
        <AnalysisToolbar workspace={workspace} />
      </Box>
    </HotkeysProvider>
  );
}

// Register Golden Layout components
GoldenLayout.registerComponent('CatalogComparisonTool', CatalogComparisonTool);
GoldenLayout.registerComponent('ImageAnalysisTool', ImageAnalysisTool);
GoldenLayout.registerComponent('SourceInvestigationTool', SourceInvestigationTool);
GoldenLayout.registerComponent('MosaicAnalysisTool', MosaicAnalysisTool);
GoldenLayout.registerComponent('ReproductionScript', ReproductionScriptViewer);
GoldenLayout.registerComponent('DataBrowser', DataBrowser);
GoldenLayout.registerComponent('WorkflowVisualization', WorkflowVisualization);
```

### Trust Indicators

```typescript
// frontend/src/components/analysis/TrustIndicatorBar.tsx

export function TrustIndicatorBar({ indicators }: { indicators: TrustIndicator[] }) {
  const overallTrust = calculateOverallTrust(indicators);
  
  return (
    <Paper
      sx={{
        p: 1,
        backgroundColor: getTrustColor(overallTrust),
        borderBottom: '2px solid',
        borderColor: getTrustColor(overallTrust),
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <TrustIcon trust={overallTrust} />
        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
          {overallTrust === 'trusted' && '✓ All indicators trusted'}
          {overallTrust === 'warning' && '⚠ Some indicators need attention'}
          {overallTrust === 'untrusted' && '✗ Trust indicators failed'}
        </Typography>
        
        {indicators.map((indicator) => (
          <Chip
            key={indicator.type}
            label={`${indicator.label}: ${indicator.value}`}
            color={indicator.status === 'trusted' ? 'success' : indicator.status === 'warning' ? 'warning' : 'error'}
            size="small"
            sx={{ ml: 1 }}
          />
        ))}
        
        <Box sx={{ ml: 'auto' }}>
          <ReproducibilityBadge />
        </Box>
      </Box>
    </Paper>
  );
}

function calculateOverallTrust(indicators: TrustIndicator[]): 'trusted' | 'warning' | 'untrusted' {
  if (indicators.every((i) => i.status === 'trusted')) return 'trusted';
  if (indicators.some((i) => i.status === 'untrusted')) return 'untrusted';
  return 'warning';
}
```

### Catalog Comparison Tool

```typescript
// frontend/src/components/analysis/CatalogComparisonTool.tsx

export function CatalogComparisonTool({ tool }: { tool: AnalysisTool }) {
  const [comparison, setComparison] = useState<CatalogComparison | null>(null);
  const [results, setResults] = useState<ComparisonResult[]>([]);
  
  return (
    <Card>
      <CardHeader
        title="Catalog Comparison"
        action={
          <Tooltip title="Deterministic operation - results are reproducible">
            <VerifiedIcon color="success" />
          </Tooltip>
        }
      />
      <CardContent>
        {/* Parameter Configuration - React JSON Schema Form */}
        <Form
          schema={catalogComparisonSchema}
          validator={validator}
          formData={comparison}
          onChange={({ formData }) => {
            setComparison(formData as CatalogComparison);
          }}
          onSubmit={async ({ formData }) => {
            const comparisonResults = await runCatalogComparison(formData as CatalogComparison);
            setResults(comparisonResults);
            
            // Update tool state for reproducibility
            updateToolState(tool.id, {
              comparison: formData,
              results: comparisonResults,
              timestamp: new Date(),
            });
            
            // Generate and display reproduction script
            const script = generateReproductionScript(tool, dataProducts);
            openReproductionScriptPanel(script, tool.id);
          }}
          uiSchema={{
            catalog: {
              'ui:widget': 'select',
            },
            radius: {
              'ui:widget': 'range',
            },
          }}
        />
        
        {/* Results - TanStack Table */}
        {results.length > 0 && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle2" gutterBottom>
              Comparison Results
            </Typography>
            <CatalogComparisonTable data={results} />
          </Box>
        )}
        
        {/* Comparison View - React Split Pane */}
        {results.length > 0 && comparison && (
          <Box sx={{ mt: 3 }}>
            <SplitPane split="vertical" defaultSize="50%">
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Our Sources
                </Typography>
                <SourceList sources={results.map((r) => r.source)} />
              </Box>
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Catalog Matches
                </Typography>
                <CatalogMatchList matches={results.filter((r) => r.catalogMatch)} />
              </Box>
            </SplitPane>
          </Box>
        )}
        
        {/* Actions */}
        <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            onClick={async () => {
              const comparisonResults = await runCatalogComparison(comparison!);
              setResults(comparisonResults);
              
              // Update tool state for reproducibility
              updateToolState(tool.id, {
                comparison,
                results: comparisonResults,
                timestamp: new Date(),
              });
              
              // Generate and display reproduction script
              const script = generateReproductionScript(tool, dataProducts);
              openReproductionScriptPanel(script, tool.id);
            }}
            disabled={!comparison}
          >
            Run Comparison
          </Button>
          <Button
            variant="outlined"
            onClick={() => {
              exportComparisonResults(results);
            }}
            disabled={results.length === 0}
          >
            Export Results
          </Button>
          <Button
            variant="outlined"
            onClick={() => {
              const script = generateReproductionScript(tool, dataProducts);
              openReproductionScriptPanel(script, tool.id);
            }}
          >
            View Script
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}
```

### Image Analysis Tool

```typescript
// frontend/src/components/analysis/ImageAnalysisTool.tsx

export function ImageAnalysisTool({ tool }: { tool: AnalysisTool }) {
  const [image, setImage] = useState<ImageProduct | null>(null);
  const [analysis, setAnalysis] = useState<ImageAnalysis | null>(null);
  
  return (
    <Card>
      <CardHeader
        title="Image Analysis"
        action={
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="QA metrics available">
              <QAIcon color="success" />
            </Tooltip>
            <Tooltip title="Deterministic operation">
              <VerifiedIcon color="success" />
            </Tooltip>
          </Box>
        }
      />
      <CardContent>
        {/* Image Selection */}
        <Box sx={{ mb: 3 }}>
          <ImageSelector
            value={image}
            onChange={setImage}
            showQAIndicators={true}
          />
        </Box>
        
        {/* Image Properties */}
        {image && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" gutterBottom>
              Image Properties
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Typography variant="body2">
                  <strong>RA:</strong> {image.ra.toFixed(4)}°
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2">
                  <strong>Dec:</strong> {image.dec.toFixed(4)}°
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2">
                  <strong>Beam:</strong> {image.beam.major.toFixed(2)}" × {image.beam.minor.toFixed(2)}"
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2">
                  <strong>RMS:</strong> {image.rms.toFixed(3)} mJy/beam
                </Typography>
              </Grid>
            </Grid>
          </Box>
        )}
        
        {/* Analysis Options */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Analysis Options
          </Typography>
          <FormGroup>
            <FormControlLabel
              control={
                <Checkbox
                  checked={analysis?.options?.sourceFinding || false}
                  onChange={(e) => {
                    setAnalysis({
                      ...analysis!,
                      options: {
                        ...analysis?.options,
                        sourceFinding: e.target.checked,
                      },
                    });
                  }}
                />
              }
              label="Source Finding"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={analysis?.options?.noiseAnalysis || false}
                  onChange={(e) => {
                    setAnalysis({
                      ...analysis!,
                      options: {
                        ...analysis?.options,
                        noiseAnalysis: e.target.checked,
                      },
                    });
                  }}
                />
              }
              label="Noise Analysis"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={analysis?.options?.beamAnalysis || false}
                  onChange={(e) => {
                    setAnalysis({
                      ...analysis!,
                      options: {
                        ...analysis?.options,
                        beamAnalysis: e.target.checked,
                      },
                    });
                  }}
                />
              }
              label="Beam Analysis"
            />
          </FormGroup>
        </Box>
        
        {/* Analysis Results */}
        {analysis?.results && (
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Analysis Results
            </Typography>
            <AnalysisResultsView results={analysis.results} />
          </Box>
        )}
        
        {/* Actions */}
        <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            onClick={async () => {
              const results = await runImageAnalysis(image!, analysis!.options);
              setAnalysis({
                ...analysis!,
                results,
                timestamp: new Date(),
              });
              
              // Update tool state
              updateToolState(tool.id, {
                image,
                analysis: {
                  ...analysis!,
                  results,
                },
              });
            }}
            disabled={!image || !analysis}
          >
            Run Analysis
          </Button>
          <Button
            variant="outlined"
            onClick={() => {
              exportAnalysisResults(analysis!.results);
            }}
            disabled={!analysis?.results}
          >
            Export Results
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}
```

### Source Investigation Tool

```typescript
// frontend/src/components/analysis/SourceInvestigationTool.tsx

export function SourceInvestigationTool({ tool }: { tool: AnalysisTool }) {
  const [source, setSource] = useState<Source | null>(null);
  const [investigation, setInvestigation] = useState<SourceInvestigation | null>(null);
  
  return (
    <Card>
      <CardHeader
        title="Source Investigation"
        action={
          <Tooltip title="All operations are deterministic and reproducible">
            <VerifiedIcon color="success" />
          </Tooltip>
        }
      />
      <CardContent>
        {/* Source Selection */}
        <Box sx={{ mb: 3 }}>
          <SourceSelector
            value={source}
            onChange={setSource}
            showCatalogMatches={true}
          />
        </Box>
        
        {/* Investigation Tabs */}
        {source && (
          <Box>
            <Tabs value={investigation?.focus || 'light-curve'}>
              <Tab
                label="Light Curve"
                onClick={() => {
                  setInvestigation({
                    ...investigation!,
                    focus: 'light-curve',
                  });
                }}
              />
              <Tab
                label="Catalog Comparison"
                onClick={() => {
                  setInvestigation({
                    ...investigation!,
                    focus: 'catalog',
                  });
                }}
              />
              <Tab
                label="Image Stack"
                onClick={() => {
                  setInvestigation({
                    ...investigation!,
                    focus: 'images',
                  });
                }}
              />
              <Tab
                label="Profile Fitting"
                onClick={() => {
                  setInvestigation({
                    ...investigation!,
                    focus: 'fitting',
                  });
                }}
              />
            </Tabs>
            
            {/* Focused View */}
            <Box sx={{ mt: 3 }}>
              {investigation?.focus === 'light-curve' && (
                <LightCurveView source={source} />
              )}
              {investigation?.focus === 'catalog' && (
                <CatalogComparisonView source={source} />
              )}
              {investigation?.focus === 'images' && (
                <ImageStackView source={source} />
              )}
              {investigation?.focus === 'fitting' && (
                <ProfileFittingView source={source} />
              )}
            </Box>
          </Box>
        )}
        
        {/* Reproducibility Info - React Markdown */}
        {investigation && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle2" gutterBottom>
              Reproducibility
            </Typography>
            <ReactMarkdown
              remarkPlugins={[remarkMath]}
              rehypePlugins={[rehypeKatex]}
            >
              {`
**Analysis ID:** \`${investigation.analysisId}\`

**Parameters:**
\`\`\`json
${JSON.stringify(investigation.parameters, null, 2)}
\`\`\`

**Data Versions:**
- Image: ${investigation.dataVersions.image || 'N/A'}
- Catalog: ${investigation.dataVersions.catalog || 'N/A'}
- Calibration: ${investigation.dataVersions.calibration || 'N/A'}

**Code Version:** \`${investigation.codeVersion}\`
              `}
            </ReactMarkdown>
            <Button
              size="small"
              variant="outlined"
              onClick={() => {
                const script = generateReproductionScript(tool, dataProducts);
                openReproductionScriptPanel(script, investigation.analysisId);
              }}
              sx={{ mt: 1 }}
            >
              View Reproduction Script
            </Button>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
```

### Reproducibility System

```typescript
// frontend/src/utils/reproducibility.ts

import Editor from '@monaco-editor/react';

export interface ReproducibilityRecord {
  analysisId: string;
  timestamp: Date;
  parameters: Record<string, unknown>;
  dataVersions: {
    image?: string;
    catalog?: string;
    calibration?: string;
  };
  codeVersion: string;
  results: unknown;
  script: string; // Generated Python script
}

export function generateReproductionScript(
  tool: AnalysisTool,
  dataProducts: DataProduct[]
): string {
  const script = `
# Reproducible Analysis Script
# Generated: ${new Date().toISOString()}
# Analysis ID: ${tool.id}

import numpy as np
from astropy.io import fits
from dsa110_contimg.analysis import catalog_comparison, image_analysis, source_investigation

# Data Products
${dataProducts.map((dp) => `# ${dp.type}: ${dp.path}`).join('\n')}

# Parameters
parameters = ${JSON.stringify(tool.state, null, 2)}

# Run Analysis
${generateAnalysisCode(tool, dataProducts)}

# Results
# Results saved to: results_${tool.id}.json
`;

  return script;
}

// Reproduction Script Viewer Component
export function ReproductionScriptViewer({ script, analysisId }: { script: string; analysisId: string }) {
  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 1, borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
        <Typography variant="subtitle2">
          Reproduction Script: {analysisId}
        </Typography>
      </Box>
      <Box sx={{ flexGrow: 1 }}>
        <Editor
          height="100%"
          language="python"
          value={script}
          theme="vs-dark"
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 14,
            wordWrap: 'on',
          }}
        />
      </Box>
      <Box sx={{ p: 1, borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
        <Button
          size="small"
          variant="outlined"
          onClick={() => {
            downloadScript(script, analysisId);
          }}
        >
          Download Script
        </Button>
        <Button
          size="small"
          variant="outlined"
          onClick={() => {
            copyToClipboard(script);
          }}
          sx={{ ml: 1 }}
        >
          Copy to Clipboard
        </Button>
      </Box>
    </Box>
  );
}

export async function saveReproducibilityRecord(
  record: ReproducibilityRecord
): Promise<void> {
  await fetch('/api/analysis/reproducibility', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(record),
  });
}

export async function loadReproducibilityRecord(
  analysisId: string
): Promise<ReproducibilityRecord> {
  const response = await fetch(`/api/analysis/reproducibility/${analysisId}`);
  return response.json();
}

export async function reproduceAnalysis(
  analysisId: string
): Promise<unknown> {
  const record = await loadReproducibilityRecord(analysisId);
  
  // Execute the script
  const response = await fetch('/api/analysis/reproduce', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ script: record.script }),
  });
  
  return response.json();
}
```

### Deterministic Operations

```typescript
// frontend/src/utils/determinism.ts

export interface DeterministicOperation {
  id: string;
  name: string;
  parameters: Record<string, unknown>;
  seed?: number; // For random operations
  version: string; // Code version
  timestamp: Date;
}

export function markAsDeterministic(
  operation: DeterministicOperation
): void {
  // Store operation parameters for reproducibility
  localStorage.setItem(
    `deterministic_${operation.id}`,
    JSON.stringify(operation)
  );
}

export function verifyDeterminism(
  operationId: string,
  results: unknown
): boolean {
  const stored = localStorage.getItem(`deterministic_${operationId}`);
  if (!stored) return false;
  
  const operation = JSON.parse(stored) as DeterministicOperation;
  
  // Verify parameters match
  // Verify code version matches
  // Verify results can be reproduced
  
  return true;
}

export function ensureDeterministic<T>(
  operation: () => Promise<T>,
  parameters: Record<string, unknown>
): Promise<T> {
  // Set random seed if needed
  if (parameters.seed !== undefined) {
    // Set seed in backend
  }
  
  // Record operation
  const deterministicOp: DeterministicOperation = {
    id: generateId(),
    name: operation.name,
    parameters,
    seed: parameters.seed as number,
    version: getCodeVersion(),
    timestamp: new Date(),
  };
  
  markAsDeterministic(deterministicOp);
  
  return operation();
}
```

### Analysis Workspace View

```typescript
// frontend/src/components/views/AnalysisView.tsx

export function AnalysisView({ state }: { state: AnalysisState }) {
  const { workspace, trustIndicators, reproducibility } = state;
  
  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h4">
            Analysis Workspace: {workspace.name}
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="outlined"
              onClick={() => {
                saveWorkspace(workspace);
              }}
            >
              Save Workspace
            </Button>
            <Button
              variant="outlined"
              onClick={() => {
                exportWorkspace(workspace);
              }}
            >
              Export
            </Button>
          </Box>
        </Box>
      </Box>
      
      {/* Trust Indicators */}
      <TrustIndicatorBar indicators={trustIndicators} />
      
      {/* Main Workspace */}
      <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
        <AnalysisWorkspace workspace={workspace} />
      </Box>
      
      {/* Toolbar */}
      <AnalysisToolbar
        workspace={workspace}
        onAddTool={(toolType) => {
          addToolToWorkspace(workspace.id, toolType);
        }}
      />
    </Box>
  );
}
```

### Transition to Analysis Mode

```typescript
// frontend/src/hooks/useAnalysisTransition.ts

import { useHotkeys } from 'react-hotkeys-hook';

export function useAnalysisTransition() {
  const transitionTo = useDashboardStore((s) => s.transitionTo);
  const currentState = useDashboardStore((s) => s.state);
  
  // Keyboard shortcut: Ctrl+Shift+A to enter analysis mode
  useHotkeys('ctrl+shift+a', () => {
    if (currentState.mode !== 'analysis') {
      // Get available data products
      const dataProducts = getAvailableDataProducts();
      if (dataProducts.length > 0) {
        enterAnalysisMode(dataProducts);
      }
    }
  }, { scopes: ['global'] });
  
  const enterAnalysisMode = useCallback(async (dataProducts: DataProduct[]) => {
    // Create new workspace with default layout
    const workspace = await createAnalysisWorkspace({
      name: `Analysis ${new Date().toLocaleString()}`,
      dataProducts,
      layout: getDefaultWorkspaceLayout(),
    });
    
    // Calculate trust indicators
    const trustIndicators = await calculateTrustIndicators(dataProducts);
    
    // Initialize reproducibility info
    const reproducibility: ReproducibilityInfo = {
      analysisId: generateId(),
      parameters: {},
      dataVersions: {
        image: dataProducts.find((dp) => dp.type === 'image')?.version || 'unknown',
        catalog: dataProducts.find((dp) => dp.type === 'catalog')?.version || 'unknown',
        calibration: dataProducts.find((dp) => dp.type === 'calibration')?.version || 'unknown',
      },
      codeVersion: getCodeVersion(),
      timestamp: new Date(),
      canReproduce: true,
    };
    
    // Transition to analysis mode
    transitionTo('analysis', {
      workspace,
      activeTools: [],
      dataProducts,
      trustIndicators,
      reproducibility,
    });
  }, [transitionTo]);
  
  return { enterAnalysisMode };
}

function getDefaultWorkspaceLayout() {
  return {
    content: [
      {
        type: 'row',
        content: [
          {
            type: 'column',
            width: 25,
            content: [
              { type: 'component', componentName: 'DataBrowser', title: 'Data Browser' },
              { type: 'component', componentName: 'ParameterForm', title: 'Parameters' },
            ],
          },
          {
            type: 'column',
            width: 75,
            content: [
              { type: 'component', componentName: 'MainAnalysis', title: 'Analysis' },
            ],
          },
        ],
      },
    ],
  };
}
```

## Code Examples

### Complete Dashboard Page

```typescript
// frontend/src/pages/AnticipatoryDashboardPage.tsx

import { useEffect } from 'react';
import { DashboardShell } from '../components/DashboardShell';
import { useAnticipatoryPrefetch } from '../hooks/useAnticipatoryPrefetch';
import { useStateTransitions } from '../hooks/useStateTransitions';
import { useDashboardStore } from '../stores/dashboardStore';

export default function AnticipatoryDashboardPage() {
  // Initialize anticipatory systems
  useAnticipatoryPrefetch();
  useStateTransitions();
  useStreamingPipelineMonitor(); // Monitor streaming pipeline
  useAutonomousOperations(); // Track autonomous operations
  
  // Get current state
  const state = useDashboardStore((s) => s.state);
  
  return (
    <DashboardShell />
  );
}
```

### Pre-load Investigation Data

```typescript
// frontend/src/utils/preloadInvestigationData.ts

export async function preloadInvestigationData(
  candidate: ESECandidate
): Promise<PreloadedInvestigationData> {
  const queryClient = useQueryClient();
  
  // Pre-fetch all investigation data in parallel
  const [lightCurve, calibrationQA, catalogComparison, historicalContext] = await Promise.all([
    queryClient.fetchQuery(['light-curve', candidate.source_id]),
    queryClient.fetchQuery(['calibration-qa', candidate.ms_path]),
    queryClient.fetchQuery(['catalog-comparison', candidate.source_id]),
    queryClient.fetchQuery(['historical-context', candidate.source_id]),
  ]);
  
  return {
    lightCurve,
    calibrationQA,
    catalogComparison,
    historicalContext,
  };
}
```

---

## Key Metrics for Success

1. **Zero clicks for normal operation** - Dashboard shows nothing when autonomous operations run smoothly
2. **One click for common tasks** - Most actions are one click away
3. **Autonomous operation visibility** - 100% visibility into what the pipeline is doing autonomously
4. **Manual override time** - <5 seconds from decision to manual control
5. **Pre-fetch hit rate** - >80% of user requests should be pre-fetched
6. **Workflow completion rate** - >90% of workflows completed without guidance
7. **Time to insight** - <2 seconds from discovery to investigation view
8. **User satisfaction** - Dashboard feels "magical" and intuitive
9. **Control handoff** - Seamless transition between autonomous and manual modes
10. **Analysis flexibility** - Support diverse analysis workflows without constraints
11. **Trust indicators** - 100% of analysis operations show trust indicators
12. **Reproducibility** - 100% of analysis operations are reproducible
13. **Deterministic operations** - All analysis operations produce consistent results

---

## Tool Dependencies Summary

### Phase 4.5 (Foundation)
- `golden-layout` - Layout system
- `@monaco-editor/react` - Code editor
- `@rjsf/core`, `@rjsf/mui`, `@rjsf/validator-ajv8` - Form generation
- `react-split-pane` - Side-by-side comparisons
- `react-markdown`, `remark-math`, `rehype-katex` - Documentation
- `react-hotkeys-hook` - Keyboard shortcuts

### Phase 4.6 (Core Tools)
- `@tanstack/react-table` - Advanced tables
- `react-diff-viewer` - Result comparison
- `plotly.js`, `react-plotly.js` - Already installed ✓
- `d3` - Already installed ✓

### Phase 4.7 (Enhancements)
- `reactflow` - Workflow visualization
- `react-contextmenu` - Right-click menus
- `@dnd-kit/core`, `@dnd-kit/sortable` - Drag and drop

### Already Available
- `ag-grid-community`, `ag-grid-react` - Data grids ✓
- `plotly.js`, `react-plotly.js` - Visualization ✓
- `d3` - Custom visualizations ✓

## Next Steps

1. **Review and approve** this implementation plan
2. **Set up project structure** for new components
3. **Install Phase 4.5 dependencies** - Foundation tools
4. **Begin Phase 1** - Foundation
5. **Iterate based on feedback** - Adjust as we learn

---

**This dashboard will feel magical - it will anticipate needs, eliminate steps, and guide users seamlessly through complex workflows. The complexity is hidden; the simplicity is revealed.**

**The streaming pipeline operates autonomously, but the dashboard provides complete visibility and control. When everything runs smoothly, the dashboard stays quiet. When intervention is needed, it anticipates what you'll want to do - seamlessly transitioning from autonomous monitoring to manual control and back again.**

**Once data products are ready, the analysis workspace provides flexible, trustworthy, and deterministic tools for exploration. Every analysis operation is reproducible, every result is traceable, and trust indicators ensure you know the reliability of your findings. The complexity of scientific analysis is made simple, but never at the cost of rigor.**

