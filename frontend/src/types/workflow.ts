/**
 * Workflow Types and Interfaces
 */

export type WorkflowType = 
  | 'monitoring' 
  | 'discovery' 
  | 'investigation' 
  | 'debugging' 
  | 'analysis'
  | 'control';

export interface NavigationItem {
  path: string;
  label: string;
  icon?: React.ComponentType;
  description?: string;
  category?: 'page' | 'action' | 'source' | 'image' | 'observation';
}

export interface QuickAction {
  id: string;
  label: string;
  icon?: React.ComponentType;
  action: () => void;
  shortcut?: string;
  category?: string;
}

export interface WorkflowContext {
  currentWorkflow: WorkflowType | null;
  currentPage: string;
  suggestedNextSteps: NavigationItem[];
  quickActions: QuickAction[];
  breadcrumbs: BreadcrumbItem[];
}

export interface BreadcrumbItem {
  label: string;
  path?: string;
  icon?: React.ComponentType;
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  steps: NavigationItem[];
  icon?: React.ComponentType;
}

// Workflow definitions
export const WORKFLOW_TEMPLATES: WorkflowTemplate[] = [
  {
    id: 'ese-discovery',
    name: 'ESE Discovery Investigation',
    description: 'Investigate an Extreme Scattering Event candidate',
    steps: [
      { path: '/dashboard', label: 'Dashboard', description: 'View ESE alert' },
      { path: '/sources', label: 'Sources', description: 'View source details' },
      { path: '/qa', label: 'QA', description: 'Check data quality' },
      { path: '/data', label: 'Data Browser', description: 'View images' },
    ],
  },
  {
    id: 'pipeline-debug',
    name: 'Pipeline Debugging',
    description: 'Debug pipeline issues',
    steps: [
      { path: '/dashboard', label: 'Dashboard', description: 'View errors' },
      { path: '/operations', label: 'Operations', description: 'Check DLQ' },
      { path: '/control', label: 'Control', description: 'Manual intervention' },
      { path: '/health', label: 'Health', description: 'View metrics' },
    ],
  },
  {
    id: 'data-exploration',
    name: 'Data Exploration',
    description: 'Explore observations and images',
    steps: [
      { path: '/sky', label: 'Sky View', description: 'View coverage' },
      { path: '/sources', label: 'Sources', description: 'Browse catalog' },
      { path: '/data', label: 'Data Browser', description: 'View images' },
      { path: '/qa', label: 'QA', description: 'Check quality' },
    ],
  },
];

// Context-aware navigation rules
export interface NavigationRule {
  condition: (context: WorkflowContext) => boolean;
  suggestions: NavigationItem[];
  quickActions: QuickAction[];
}

export const NAVIGATION_RULES: NavigationRule[] = [
  {
    condition: (ctx) => ctx.currentPage === '/dashboard' && ctx.currentWorkflow === 'discovery',
    suggestions: [
      { path: '/sources', label: 'View Sources', description: 'Investigate ESE candidates' },
      { path: '/qa', label: 'Check QA', description: 'Validate data quality' },
    ],
    quickActions: [],
  },
  {
    condition: (ctx) => ctx.currentPage.startsWith('/sources/') && ctx.currentWorkflow === 'investigation',
    suggestions: [
      { path: '/data', label: 'View Images', description: 'See images for this source' },
      { path: '/qa', label: 'Check QA', description: 'Validate calibration' },
    ],
    quickActions: [],
  },
  {
    condition: (ctx) => ctx.currentPage === '/dashboard' && ctx.currentWorkflow === 'debugging',
    suggestions: [
      { path: '/operations', label: 'Check DLQ', description: 'View failed operations' },
      { path: '/health', label: 'System Health', description: 'View metrics' },
    ],
    quickActions: [],
  },
];

