/**
 * Workflow Context - Manages workflow state and context-aware navigation
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import type {
  WorkflowType,
  WorkflowContext as WorkflowContextType,
  NavigationItem,
  QuickAction,
  BreadcrumbItem,
} from "../types/workflow";
import { NAVIGATION_RULES } from "../types/workflow";

interface WorkflowContextValue {
  currentWorkflow: WorkflowType | null;
  setCurrentWorkflow: (workflow: WorkflowType | null) => void;
  suggestedNextSteps: NavigationItem[];
  quickActions: QuickAction[];
  breadcrumbs: BreadcrumbItem[];
  addBreadcrumb: (item: BreadcrumbItem) => void;
  clearBreadcrumbs: () => void;
  getWorkflowForPage: (path: string) => WorkflowType | null;
}

const WorkflowContext = createContext<WorkflowContextValue | undefined>(undefined);

// Map pages to workflows
const PAGE_TO_WORKFLOW: Record<string, WorkflowType> = {
  "/dashboard": "monitoring",
  "/sources": "investigation",
  "/sources/": "investigation",
  "/data": "analysis",
  "/qa": "analysis",
  "/control": "control",
  "/operations": "debugging",
  "/health": "debugging",
  "/pipeline": "monitoring",
};

// Detect workflow from current page and context
function detectWorkflow(path: string, previousWorkflow: WorkflowType | null): WorkflowType | null {
  // Check if we're in a specific workflow context
  if (path.includes("/sources/")) {
    return "investigation";
  }
  if (path === "/operations" || path === "/health") {
    return "debugging";
  }
  if (path === "/control") {
    return "control";
  }
  if (path === "/data" || path === "/qa") {
    return "analysis";
  }

  // Use page-based detection
  for (const [pagePath, workflow] of Object.entries(PAGE_TO_WORKFLOW)) {
    if (path.startsWith(pagePath)) {
      return workflow;
    }
  }

  return previousWorkflow;
}

export function WorkflowProvider({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [currentWorkflow, setCurrentWorkflow] = useState<WorkflowType | null>(null);
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([]);

  // Detect workflow from current page
  useEffect(() => {
    const workflow = detectWorkflow(location.pathname, currentWorkflow);
    if (workflow !== currentWorkflow) {
      setCurrentWorkflow(workflow);
    }
  }, [location.pathname]);

  // Generate breadcrumbs from path
  useEffect(() => {
    const pathParts = location.pathname.split("/").filter(Boolean);
    const newBreadcrumbs: BreadcrumbItem[] = [{ label: "Dashboard", path: "/dashboard" }];

    if (pathParts.length > 0) {
      const pageMap: Record<string, string> = {
        sources: "Sources",
        data: "Data Browser",
        qa: "QA Visualization",
        control: "Control",
        streaming: "Streaming",
        operations: "Operations",
        health: "Health",
        pipeline: "Pipeline",
        sky: "Sky View",
        events: "Events",
        cache: "Cache",
      };

      pathParts.forEach((part, index) => {
        const fullPath = "/" + pathParts.slice(0, index + 1).join("/");
        const label = pageMap[part] || part;
        newBreadcrumbs.push({
          label,
          path: index < pathParts.length - 1 ? fullPath : undefined,
        });
      });
    }

    setBreadcrumbs(newBreadcrumbs);
  }, [location.pathname]);

  // Generate suggested next steps based on context
  const suggestedNextSteps = React.useMemo(() => {
    const context: WorkflowContextType = {
      currentWorkflow,
      currentPage: location.pathname,
      suggestedNextSteps: [],
      quickActions: [],
      breadcrumbs,
    };

    // Find matching navigation rules
    for (const rule of NAVIGATION_RULES) {
      if (rule.condition(context)) {
        return rule.suggestions;
      }
    }

    return [];
  }, [currentWorkflow, location.pathname, breadcrumbs]);

  // Generate quick actions based on context
  const quickActions = React.useMemo(() => {
    const actions: QuickAction[] = [];

    if (currentWorkflow === "discovery") {
      actions.push({
        id: "view-sources",
        label: "View Sources",
        action: () => navigate("/sources"),
      });
    }

    if (currentWorkflow === "debugging") {
      actions.push({
        id: "check-dlq",
        label: "Check DLQ",
        action: () => navigate("/operations"),
      });
    }

    return actions;
  }, [currentWorkflow, navigate]);

  const addBreadcrumb = useCallback((item: BreadcrumbItem) => {
    setBreadcrumbs((prev) => [...prev, item]);
  }, []);

  const clearBreadcrumbs = useCallback(() => {
    setBreadcrumbs([]);
  }, []);

  const getWorkflowForPage = useCallback((path: string): WorkflowType | null => {
    return detectWorkflow(path, null);
  }, []);

  return (
    <WorkflowContext.Provider
      value={{
        currentWorkflow,
        setCurrentWorkflow,
        suggestedNextSteps,
        quickActions,
        breadcrumbs,
        addBreadcrumb,
        clearBreadcrumbs,
        getWorkflowForPage,
      }}
    >
      {children}
    </WorkflowContext.Provider>
  );
}

export function useWorkflow() {
  const context = useContext(WorkflowContext);
  if (context === undefined) {
    throw new Error("useWorkflow must be used within a WorkflowProvider");
  }
  return context;
}
