import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

// =============================================================================
// UI State Store - for ephemeral UI state
// =============================================================================

interface UIState {
  // Sidebar
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;

  // Loading overlay
  globalLoading: boolean;
  setGlobalLoading: (loading: boolean) => void;

  // Toast/notification queue
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, "id">) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
}

export interface Notification {
  id: string;
  type: "info" | "success" | "warning" | "error";
  title: string;
  message?: string;
  duration?: number; // ms, 0 = sticky
}

export const useUIStore = create<UIState>()(
  devtools(
    (set) => ({
      // Sidebar
      sidebarOpen: true,
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      // Loading
      globalLoading: false,
      setGlobalLoading: (loading) => set({ globalLoading: loading }),

      // Notifications
      notifications: [],
      addNotification: (notification) =>
        set((state) => ({
          notifications: [...state.notifications, { ...notification, id: crypto.randomUUID() }],
        })),
      removeNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),
      clearNotifications: () => set({ notifications: [] }),
    }),
    { name: "ui-store" }
  )
);

// =============================================================================
// User Preferences Store - persisted to localStorage
// =============================================================================

interface UserPreferences {
  // Theme
  theme: "light" | "dark" | "system";
  setTheme: (theme: "light" | "dark" | "system") => void;

  // Table settings
  defaultPageSize: number;
  setDefaultPageSize: (size: number) => void;

  // Recent items (for quick access)
  recentImages: string[];
  addRecentImage: (id: string) => void;
  recentSources: string[];
  addRecentSource: (id: string) => void;
  recentJobs: string[];
  addRecentJob: (runId: string) => void;
}

/**
 * Maximum number of recent items to track per type.
 * Rationale: 10 items provides quick access to recent work without
 * cluttering the UI or consuming excessive localStorage space.
 */
const MAX_RECENT_ITEMS = 10;

const addToRecent = (list: string[], item: string): string[] => {
  const filtered = list.filter((i) => i !== item);
  return [item, ...filtered].slice(0, MAX_RECENT_ITEMS);
};

export const usePreferencesStore = create<UserPreferences>()(
  devtools(
    persist(
      (set) => ({
        // Theme
        theme: "system",
        setTheme: (theme) => set({ theme }),

        // Table settings
        // Default page size of 25: balances between reducing API requests
        // and providing reasonable viewport scrolling on most displays
        defaultPageSize: 25,
        setDefaultPageSize: (size) => set({ defaultPageSize: size }),

        // Recent items
        recentImages: [],
        addRecentImage: (id) =>
          set((state) => ({ recentImages: addToRecent(state.recentImages, id) })),
        recentSources: [],
        addRecentSource: (id) =>
          set((state) => ({ recentSources: addToRecent(state.recentSources, id) })),
        recentJobs: [],
        addRecentJob: (runId) =>
          set((state) => ({ recentJobs: addToRecent(state.recentJobs, runId) })),
      }),
      {
        name: "dsa110-preferences",
        version: 1,
      }
    ),
    { name: "preferences-store" }
  )
);

// =============================================================================
// Selection Store - for multi-select operations
// =============================================================================

interface SelectionState {
  selectedImages: Set<string>;
  toggleImageSelection: (id: string) => void;
  selectAllImages: (ids: string[]) => void;
  clearImageSelection: () => void;

  selectedSources: Set<string>;
  toggleSourceSelection: (id: string) => void;
  selectAllSources: (ids: string[]) => void;
  clearSourceSelection: () => void;

  selectedJobs: Set<string>;
  toggleJobSelection: (runId: string) => void;
  selectAllJobs: (runIds: string[]) => void;
  clearJobSelection: () => void;

  clearAllSelections: () => void;
}

export const useSelectionStore = create<SelectionState>()(
  devtools(
    (set) => ({
      // Images
      selectedImages: new Set(),
      toggleImageSelection: (id) =>
        set((state) => {
          const newSet = new Set(state.selectedImages);
          if (newSet.has(id)) {
            newSet.delete(id);
          } else {
            newSet.add(id);
          }
          return { selectedImages: newSet };
        }),
      selectAllImages: (ids) => set({ selectedImages: new Set(ids) }),
      clearImageSelection: () => set({ selectedImages: new Set() }),

      // Sources
      selectedSources: new Set(),
      toggleSourceSelection: (id) =>
        set((state) => {
          const newSet = new Set(state.selectedSources);
          if (newSet.has(id)) {
            newSet.delete(id);
          } else {
            newSet.add(id);
          }
          return { selectedSources: newSet };
        }),
      selectAllSources: (ids) => set({ selectedSources: new Set(ids) }),
      clearSourceSelection: () => set({ selectedSources: new Set() }),

      // Jobs
      selectedJobs: new Set(),
      toggleJobSelection: (runId) =>
        set((state) => {
          const newSet = new Set(state.selectedJobs);
          if (newSet.has(runId)) {
            newSet.delete(runId);
          } else {
            newSet.add(runId);
          }
          return { selectedJobs: newSet };
        }),
      selectAllJobs: (runIds) => set({ selectedJobs: new Set(runIds) }),
      clearJobSelection: () => set({ selectedJobs: new Set() }),

      // Clear all
      clearAllSelections: () =>
        set({
          selectedImages: new Set(),
          selectedSources: new Set(),
          selectedJobs: new Set(),
        }),
    }),
    { name: "selection-store" }
  )
);
