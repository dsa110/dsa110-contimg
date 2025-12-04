/**
 * Jupyter Integration Page
 *
 * Provides:
 * - Kernel management (start, stop, restart)
 * - Notebook browser and launcher
 * - Session monitoring
 * - Template-based notebook creation for sources/images
 */

import React, { useState } from "react";
import {
  useKernels,
  useNotebooks,
  useSessions,
  useNotebookTemplates,
  useJupyterStats,
  useJupyterUrl,
  useStartKernel,
  useRestartKernel,
  useInterruptKernel,
  useShutdownKernel,
  useDeleteNotebook,
  useCreateSession,
  useDeleteSession,
  useLaunchNotebook,
  type JupyterKernel,
  type JupyterNotebook,
  type JupyterSession,
  type NotebookTemplate,
  type JupyterStats,
} from "../api/jupyter";

// Kernel status badge component
function KernelStatusBadge({ status }: { status: JupyterKernel["status"] }) {
  const colors: Record<JupyterKernel["status"], string> = {
    idle: "text-green-600 bg-green-100 dark:bg-green-900/30",
    busy: "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30",
    starting: "text-blue-600 bg-blue-100 dark:bg-blue-900/30",
    error: "text-red-600 bg-red-100 dark:bg-red-900/30",
    dead: "text-gray-600 bg-gray-100 dark:bg-gray-900/30",
  };

  return (
    <span
      className={`px-2 py-1 text-xs font-medium rounded-full capitalize ${colors[status]}`}
    >
      {status}
    </span>
  );
}

// Kernel card component
interface KernelCardProps {
  kernel: JupyterKernel;
  onRestart: () => void;
  onInterrupt: () => void;
  onShutdown: () => void;
}

function KernelCard({
  kernel,
  onRestart,
  onInterrupt,
  onShutdown,
}: KernelCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <span className="text-2xl">🐍</span>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-gray-100">
              {kernel.display_name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {kernel.language} • {kernel.connections} connection
              {kernel.connections !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
        <KernelStatusBadge status={kernel.status} />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="text-gray-500 dark:text-gray-400">Executions</div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {kernel.execution_count}
          </div>
        </div>
        <div>
          <div className="text-gray-500 dark:text-gray-400">Last Activity</div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {new Date(kernel.last_activity).toLocaleTimeString()}
          </div>
        </div>
      </div>
      <div className="mt-4 flex gap-2">
        {kernel.status === "busy" && (
          <button
            onClick={onInterrupt}
            className="flex-1 px-3 py-1.5 text-sm text-yellow-700 bg-yellow-100 hover:bg-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 rounded-lg"
          >
            Interrupt
          </button>
        )}
        <button
          onClick={onRestart}
          className="flex-1 px-3 py-1.5 text-sm text-blue-700 bg-blue-100 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg"
        >
          Restart
        </button>
        <button
          onClick={onShutdown}
          className="flex-1 px-3 py-1.5 text-sm text-red-700 bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 rounded-lg"
        >
          Shutdown
        </button>
      </div>
    </div>
  );
}

// Notebook card component
interface NotebookCardProps {
  notebook: JupyterNotebook;
  onOpen: () => void;
  onDelete: () => void;
}

function NotebookCard({ notebook, onOpen, onDelete }: NotebookCardProps) {
  const icon = notebook.type === "notebook" ? "📓" : "📁";
  const modified = new Date(notebook.last_modified);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <span className="text-2xl">{icon}</span>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-gray-100">
              {notebook.name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {notebook.path}
            </p>
          </div>
        </div>
        {notebook.kernel_id && (
          <span className="px-2 py-1 text-xs font-medium rounded-full text-green-600 bg-green-100 dark:bg-green-900/30">
            Active
          </span>
        )}
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="text-gray-500 dark:text-gray-400">Modified</div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {modified.toLocaleDateString()}
          </div>
        </div>
        {notebook.size && (
          <div>
            <div className="text-gray-500 dark:text-gray-400">Size</div>
            <div className="font-medium text-gray-900 dark:text-gray-100">
              {(notebook.size / 1024).toFixed(1)} KB
            </div>
          </div>
        )}
      </div>
      <div className="mt-4 flex gap-2">
        <button
          onClick={onOpen}
          className="flex-1 px-3 py-1.5 text-sm text-blue-700 bg-blue-100 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg"
        >
          Open
        </button>
        <button
          onClick={onDelete}
          className="flex-1 px-3 py-1.5 text-sm text-red-700 bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 rounded-lg"
        >
          Delete
        </button>
      </div>
    </div>
  );
}

// Session card component
interface SessionCardProps {
  session: JupyterSession;
  onOpen: () => void;
  onClose: () => void;
}

function SessionCard({ session, onOpen, onClose }: SessionCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <span className="text-2xl">⚡</span>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-gray-100">
              {session.notebook.name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {session.kernel.display_name}
            </p>
          </div>
        </div>
        <KernelStatusBadge status={session.kernel.status} />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="text-gray-500 dark:text-gray-400">Started</div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {new Date(session.created).toLocaleTimeString()}
          </div>
        </div>
        <div>
          <div className="text-gray-500 dark:text-gray-400">Executions</div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {session.kernel.execution_count}
          </div>
        </div>
      </div>
      <div className="mt-4 flex gap-2">
        <button
          onClick={onOpen}
          className="flex-1 px-3 py-1.5 text-sm text-blue-700 bg-blue-100 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg"
        >
          Open
        </button>
        <button
          onClick={onClose}
          className="flex-1 px-3 py-1.5 text-sm text-red-700 bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 rounded-lg"
        >
          Close
        </button>
      </div>
    </div>
  );
}

// Template card component
interface TemplateCardProps {
  template: NotebookTemplate;
  onLaunch: () => void;
}

function TemplateCard({ template, onLaunch }: TemplateCardProps) {
  const categoryIcons: Record<NotebookTemplate["category"], string> = {
    source_analysis: "🔭",
    image_inspection: "🖼️",
    data_exploration: "📊",
    custom: "📝",
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-start gap-3">
        <span className="text-2xl">{categoryIcons[template.category]}</span>
        <div>
          <h3 className="font-medium text-gray-900 dark:text-gray-100">
            {template.name}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {template.description}
          </p>
        </div>
      </div>
      <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
        {template.parameters.length} parameter
        {template.parameters.length !== 1 ? "s" : ""} required
      </div>
      <button
        onClick={onLaunch}
        className="mt-4 w-full px-3 py-1.5 text-sm text-blue-700 bg-blue-100 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg"
      >
        Launch Notebook
      </button>
    </div>
  );
}

// Stats panel component
interface StatsPanelProps {
  stats: JupyterStats;
}

function StatsPanel({ stats }: StatsPanelProps) {
  const diskPercent = (stats.disk_usage_mb / stats.max_disk_mb) * 100;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Jupyter Statistics
      </h2>
      <div className="grid grid-cols-2 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {stats.total_notebooks}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Notebooks
          </div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            {stats.active_kernels}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Active Kernels
          </div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
            {stats.total_sessions}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Sessions
          </div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
            {stats.kernel_usage.python3}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Python Kernels
          </div>
        </div>
      </div>
      <div className="mt-4">
        <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400 mb-1">
          <span>Disk Usage</span>
          <span>
            {stats.disk_usage_mb.toFixed(0)} / {stats.max_disk_mb} MB
          </span>
        </div>
        <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${
              diskPercent > 90
                ? "bg-red-500"
                : diskPercent > 70
                ? "bg-yellow-500"
                : "bg-green-500"
            }`}
            style={{ width: `${Math.min(diskPercent, 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// Launch notebook modal
interface LaunchNotebookModalProps {
  template: NotebookTemplate;
  isOpen: boolean;
  onClose: () => void;
  onLaunch: (name: string, params: Record<string, string | number>) => void;
  isPending: boolean;
}

function LaunchNotebookModal({
  template,
  isOpen,
  onClose,
  onLaunch,
  isPending,
}: LaunchNotebookModalProps) {
  const [name, setName] = useState(() => `${template.name}-${Date.now()}`);
  const [params, setParams] = useState<Record<string, string | number>>({});

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onLaunch(name, params);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Launch {template.name}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            >
              ✕
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="notebook-name-input"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Notebook Name
              </label>
              <input
                id="notebook-name-input"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                required
              />
            </div>

            {template.parameters.map((param) => (
              <div key={param.name}>
                <label
                  htmlFor={`param-${param.name}`}
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  {param.name}
                  {param.required && <span className="text-red-500">*</span>}
                </label>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                  {param.description}
                </p>
                <input
                  id={`param-${param.name}`}
                  type={param.type === "number" ? "number" : "text"}
                  value={params[param.name] || ""}
                  onChange={(e) =>
                    setParams({
                      ...params,
                      [param.name]:
                        param.type === "number"
                          ? Number(e.target.value)
                          : e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  required={param.required}
                />
              </div>
            ))}

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
                disabled={isPending}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isPending ? "Launching..." : "Launch"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// Start kernel modal
interface StartKernelModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStart: (kernelName: string) => void;
  isPending: boolean;
}

function StartKernelModal({
  isOpen,
  onClose,
  onStart,
  isPending,
}: StartKernelModalProps) {
  const [kernelName, setKernelName] = useState("python3");

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onStart(kernelName);
  };

  const kernelOptions = [
    { value: "python3", label: "Python 3" },
    { value: "julia-1.9", label: "Julia 1.9" },
    { value: "ir", label: "R" },
  ];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Start New Kernel
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            >
              ✕
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="kernel-type-select"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Kernel Type
              </label>
              <select
                id="kernel-type-select"
                value={kernelName}
                onChange={(e) => setKernelName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                {kernelOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
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
                disabled={isPending}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isPending ? "Starting..." : "Start Kernel"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// Main page component
export default function JupyterPage() {
  const [activeTab, setActiveTab] = useState<
    "kernels" | "notebooks" | "sessions" | "templates"
  >("kernels");
  const [showStartKernelModal, setShowStartKernelModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] =
    useState<NotebookTemplate | null>(null);

  // Queries
  const kernelsQuery = useKernels();
  const notebooksQuery = useNotebooks();
  const sessionsQuery = useSessions();
  const templatesQuery = useNotebookTemplates();
  const statsQuery = useJupyterStats();
  const jupyterUrlQuery = useJupyterUrl();

  // Check if Jupyter service is unavailable (all queries failed with 404)
  const isJupyterUnavailable =
    kernelsQuery.error &&
    notebooksQuery.error &&
    sessionsQuery.error &&
    !kernelsQuery.isPending;

  // Mutations
  const startKernel = useStartKernel();
  const restartKernel = useRestartKernel();
  const interruptKernel = useInterruptKernel();
  const shutdownKernel = useShutdownKernel();
  const deleteNotebook = useDeleteNotebook();
  const _createSession = useCreateSession();
  const deleteSession = useDeleteSession();
  const launchNotebook = useLaunchNotebook();

  const handleOpenJupyter = (notebookPath?: string) => {
    if (jupyterUrlQuery.data) {
      const url = notebookPath
        ? `${jupyterUrlQuery.data}/notebooks/${encodeURIComponent(
            notebookPath
          )}`
        : jupyterUrlQuery.data;
      window.open(url, "_blank");
    }
  };

  const handleStartKernel = async (kernelName: string) => {
    await startKernel.mutateAsync(kernelName);
    setShowStartKernelModal(false);
  };

  const handleLaunchNotebook = async (
    name: string,
    params: Record<string, string | number>
  ) => {
    if (!selectedTemplate) return;
    await launchNotebook.mutateAsync({
      template_id: selectedTemplate.id,
      name,
      parameters: params,
    });
    setSelectedTemplate(null);
  };

  // Show helpful message when Jupyter is not configured
  if (isJupyterUnavailable) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        <div className="max-w-3xl mx-auto">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 text-center">
            <span className="text-6xl mb-4 block">🪐</span>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Jupyter Integration Not Available
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              The Jupyter service is not currently configured or running. To
              enable Jupyter integration:
            </p>

            <div className="bg-gray-100 dark:bg-gray-700 rounded-lg p-6 text-left mb-6">
              <h2 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">
                Setup Instructions
              </h2>
              <ol className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
                <li className="flex gap-2">
                  <span className="font-bold">1.</span>
                  <span>Start a Jupyter server on the backend host:</span>
                </li>
                <li className="ml-6">
                  <code className="bg-gray-200 dark:bg-gray-600 px-2 py-1 rounded text-xs">
                    jupyter lab --no-browser --port=8888
                  </code>
                </li>
                <li className="flex gap-2">
                  <span className="font-bold">2.</span>
                  <span>
                    Configure the backend to proxy Jupyter API requests
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="font-bold">3.</span>
                  <span>Refresh this page to connect</span>
                </li>
              </ol>
            </div>

            <div className="flex justify-center gap-4">
              <button
                onClick={() => {
                  kernelsQuery.refetch();
                  notebooksQuery.refetch();
                  sessionsQuery.refetch();
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Retry Connection
              </button>
              <a
                href="http://localhost:8888"
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
              >
                Open Jupyter Directly
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: "kernels", label: "Kernels", count: kernelsQuery.data?.length },
    { id: "notebooks", label: "Notebooks", count: notebooksQuery.data?.length },
    { id: "sessions", label: "Sessions", count: sessionsQuery.data?.length },
    {
      id: "templates",
      label: "Templates",
      count: templatesQuery.data?.length,
    },
  ] as const;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <span className="text-3xl">🪐</span>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Jupyter Integration
              </h1>
              <p className="text-gray-500 dark:text-gray-400">
                Manage notebooks and kernels for data analysis
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowStartKernelModal(true)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
            >
              <span>+</span>
              Start Kernel
            </button>
            <button
              onClick={() => handleOpenJupyter()}
              disabled={!jupyterUrlQuery.data}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              <span>🔗</span>
              Open JupyterLab
            </button>
          </div>
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
            {activeTab === "kernels" && (
              <div>
                {kernelsQuery.isPending ? (
                  <div className="text-center py-8 text-gray-500">
                    Loading kernels...
                  </div>
                ) : kernelsQuery.error ? (
                  <div className="text-center py-8 text-red-500">
                    Error loading kernels
                  </div>
                ) : kernelsQuery.data?.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No active kernels. Start one to begin.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {kernelsQuery.data?.map((kernel) => (
                      <KernelCard
                        key={kernel.id}
                        kernel={kernel}
                        onRestart={() => restartKernel.mutate(kernel.id)}
                        onInterrupt={() => interruptKernel.mutate(kernel.id)}
                        onShutdown={() => shutdownKernel.mutate(kernel.id)}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "notebooks" && (
              <div>
                {notebooksQuery.isPending ? (
                  <div className="text-center py-8 text-gray-500">
                    Loading notebooks...
                  </div>
                ) : notebooksQuery.error ? (
                  <div className="text-center py-8 text-red-500">
                    Error loading notebooks
                  </div>
                ) : notebooksQuery.data?.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No notebooks found. Create one from a template.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {notebooksQuery.data?.map((notebook) => (
                      <NotebookCard
                        key={notebook.id}
                        notebook={notebook}
                        onOpen={() => handleOpenJupyter(notebook.path)}
                        onDelete={() => deleteNotebook.mutate(notebook.id)}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "sessions" && (
              <div>
                {sessionsQuery.isPending ? (
                  <div className="text-center py-8 text-gray-500">
                    Loading sessions...
                  </div>
                ) : sessionsQuery.error ? (
                  <div className="text-center py-8 text-red-500">
                    Error loading sessions
                  </div>
                ) : sessionsQuery.data?.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No active sessions. Open a notebook to start a session.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {sessionsQuery.data?.map((session) => (
                      <SessionCard
                        key={session.id}
                        session={session}
                        onOpen={() => handleOpenJupyter(session.notebook.path)}
                        onClose={() => deleteSession.mutate(session.id)}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "templates" && (
              <div>
                {templatesQuery.isPending ? (
                  <div className="text-center py-8 text-gray-500">
                    Loading templates...
                  </div>
                ) : templatesQuery.error ? (
                  <div className="text-center py-8 text-red-500">
                    Error loading templates
                  </div>
                ) : templatesQuery.data?.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No templates available.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {templatesQuery.data?.map((template) => (
                      <TemplateCard
                        key={template.id}
                        template={template}
                        onLaunch={() => setSelectedTemplate(template)}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Stats */}
            {statsQuery.data && <StatsPanel stats={statsQuery.data} />}

            {/* Quick actions */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Quick Actions
              </h2>
              <div className="space-y-2">
                <button
                  onClick={() => handleOpenJupyter()}
                  disabled={!jupyterUrlQuery.data}
                  className="w-full px-4 py-2 text-left text-sm text-blue-700 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg disabled:opacity-50"
                >
                  🔗 Open JupyterLab
                </button>
                <button
                  onClick={() => setShowStartKernelModal(true)}
                  className="w-full px-4 py-2 text-left text-sm text-green-700 bg-green-50 hover:bg-green-100 dark:bg-green-900/30 dark:text-green-400 rounded-lg"
                >
                  ➕ Start New Kernel
                </button>
                <button
                  onClick={() => setActiveTab("templates")}
                  className="w-full px-4 py-2 text-left text-sm text-purple-700 bg-purple-50 hover:bg-purple-100 dark:bg-purple-900/30 dark:text-purple-400 rounded-lg"
                >
                  📝 Create from Template
                </button>
              </div>
            </div>

            {/* Tips */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                💡 Tips
              </h2>
              <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <li>
                  • Use templates for source/image analysis with pre-configured
                  code
                </li>
                <li>• Idle kernels are automatically shut down after 1 hour</li>
                <li>• Click on a notebook to open it in JupyterLab</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Modals */}
      <StartKernelModal
        isOpen={showStartKernelModal}
        onClose={() => setShowStartKernelModal(false)}
        onStart={handleStartKernel}
        isPending={startKernel.isPending}
      />

      {selectedTemplate && (
        <LaunchNotebookModal
          template={selectedTemplate}
          isOpen={true}
          onClose={() => setSelectedTemplate(null)}
          onLaunch={handleLaunchNotebook}
          isPending={launchNotebook.isPending}
        />
      )}
    </div>
  );
}
