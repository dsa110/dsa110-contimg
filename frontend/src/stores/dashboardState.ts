/**
 * Dashboard State Types
 * 
 * Defines the state structure for the anticipatory dashboard.
 * Inspired by VAST's state management patterns and the anticipatory dashboard design.
 * 
 * @module stores/dashboardState
 */

export type DashboardMode = 
  | 'idle'           // Normal monitoring, autonomous operations running smoothly
  | 'autonomous'     // Streaming pipeline operating autonomously (monitoring mode)
  | 'discovery'      // ESE candidate detected - focused investigation
  | 'investigation'  // Deep dive into specific source/issue
  | 'debugging'      // Diagnostic mode for troubleshooting
  | 'manual-control' // Manual override of autonomous operations
  | 'analysis';      // Analysis workspace mode

export interface IdleState {
  mode: 'idle';
  status: 'healthy' | 'attention' | 'warning';
  lastUpdate: Date;
  streamingPipeline?: {
    status: 'running' | 'stopped' | 'error';
    lastCheck: Date;
  };
}

export interface AutonomousState {
  mode: 'autonomous';
  streamingPipeline: {
    status: 'running' | 'stopped' | 'error';
    currentOperations: AutonomousOperation[];
    metrics: {
      throughput: number;
      latency: number;
      errorRate: number;
    };
    config: Record<string, unknown>;
  };
  lastUpdate: Date;
}

export interface AutonomousOperation {
  id: string;
  type: 'conversion' | 'calibration' | 'imaging' | 'mosaicking';
  status: 'pending' | 'running' | 'completed' | 'failed';
  startTime: Date;
  endTime?: Date;
  progress?: number;
  error?: string;
}

export interface DiscoveryState {
  mode: 'discovery';
  candidate: {
    sourceId: string;
    ra: number;
    dec: number;
    significance: number;
    detectedAt: Date;
  };
  investigationData?: {
    lightCurve?: unknown;
    catalogMatches?: unknown;
    calibrationQA?: unknown;
  };
  autoExpanded: boolean;
}

export interface InvestigationState {
  mode: 'investigation';
  context: {
    sourceId?: string;
    msPath?: string;
    imagePath?: string;
    focus: 'light-curve' | 'calibration' | 'imaging' | 'catalog' | 'general';
  };
  preloadedData: Record<string, unknown>;
}

export interface DebuggingState {
  mode: 'debugging';
  issue: {
    id: string;
    type: 'pipeline-error' | 'calibration-failure' | 'imaging-error' | 'system-error';
    severity: 'low' | 'medium' | 'high' | 'critical';
    description: string;
    timestamp: Date;
  };
  diagnosticData: Record<string, unknown>;
  suggestedFixes: Array<{
    action: string;
    description: string;
    confidence: number;
  }>;
}

export interface ManualControlState {
  mode: 'manual-control';
  reason: string;
  previousState: DashboardState;
  controlScope: {
    streaming?: boolean;
    calibration?: boolean;
    imaging?: boolean;
    mosaicking?: boolean;
  };
  operations: Array<{
    id: string;
    type: string;
    status: string;
  }>;
}

export interface AnalysisState {
  mode: 'analysis';
  workspace: {
    id: string;
    name: string;
    createdAt: Date;
    layout: unknown; // Golden Layout config
  };
  activeTools: Array<{
    id: string;
    type: string;
    state: Record<string, unknown>;
  }>;
  dataProducts: Array<{
    type: string;
    path: string;
    metadata: Record<string, unknown>;
  }>;
  trustIndicators: Array<{
    type: string;
    label: string;
    status: 'trusted' | 'warning' | 'untrusted';
  }>;
  reproducibility: {
    analysisId: string;
    canReproduce: boolean;
  };
}

export type DashboardState = 
  | IdleState 
  | AutonomousState
  | DiscoveryState 
  | InvestigationState 
  | DebuggingState
  | ManualControlState
  | AnalysisState;

export interface UserIntent {
  type: 'view-source' | 'view-ms' | 'view-image' | 'investigate-candidate' | 'debug-issue' | 'analyze-data';
  targetId?: string;
  msPath?: string;
  sourceId?: string;
  imagePath?: string;
}

export interface Action {
  id: string;
  label: string;
  description: string;
  icon?: string;
  onClick: () => void;
  priority: number;
}

export interface WorkflowStep {
  id: string;
  type: string;
  timestamp: Date;
  data: Record<string, unknown>;
}

export interface DashboardContext {
  state: DashboardState;
  userIntent: UserIntent | null;
  recentActions: Action[];
  workflowHistory: WorkflowStep[];
}

