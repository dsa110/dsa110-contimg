# Workflow-Optimized Navigation Implementation

**Date:** 2025-11-12  
**Status:** ✅ Implemented  
**Phase:** Workflow Navigation Improvements

---

## Summary

Implemented workflow-optimized navigation features to improve user experience and reduce context switching. The implementation includes context-aware navigation, unified workspace mode, command palette, and workflow breadcrumbs.

---

## Components Implemented

### 1. Workflow Context (`contexts/WorkflowContext.tsx`)

**Purpose:** Manages workflow state and provides context-aware navigation suggestions.

**Features:**
- Automatically detects workflow type based on current page
- Generates breadcrumbs from URL path
- Provides suggested next steps based on navigation rules
- Tracks current workflow state (monitoring, discovery, investigation, debugging, analysis, control)

**Workflow Detection:**
- `/dashboard` → `monitoring`
- `/sources` or `/sources/:id` → `investigation`
- `/data` or `/qa` → `analysis`
- `/operations` or `/health` → `debugging`
- `/control` → `control`

**Usage:**
```typescript
import { useWorkflow } from '../contexts/WorkflowContext';

function MyComponent() {
  const { currentWorkflow, suggestedNextSteps, breadcrumbs } = useWorkflow();
  // Use workflow context...
}
```

### 2. Workflow Breadcrumbs (`components/WorkflowBreadcrumbs.tsx`)

**Purpose:** Shows current navigation path with clickable breadcrumbs.

**Features:**
- Automatically generated from URL path
- Clickable navigation to parent pages
- Shows current workflow type as chip
- Only displays when not on dashboard (reduces clutter)

**Visual:**
```
Dashboard > Sources > NVSS J1234+5678  [Investigation]
```

### 3. Command Palette (`components/CommandPalette.tsx`)

**Purpose:** Quick access to all pages, actions, and workflows via Cmd+K / Ctrl+K.

**Features:**
- Fuzzy search across all pages and actions
- Keyboard navigation (↑↓ arrows, Enter to select, Esc to close)
- Groups commands by category (Pages, Actions, Workflows)
- Shows suggested next steps
- Displays workflow templates

**Keyboard Shortcuts:**
- `Cmd+K` / `Ctrl+K` - Open command palette
- `↑` / `↓` - Navigate results
- `Enter` - Select command
- `Esc` - Close palette

**Command Categories:**
- **Pages** - All navigation pages (Dashboard, Sources, Data, etc.)
- **Suggested Actions** - Context-aware suggestions
- **Workflows** - Pre-defined workflow templates

**Workflow Templates:**
1. **ESE Discovery Investigation** - Dashboard → Sources → QA → Data Browser
2. **Pipeline Debugging** - Dashboard → Operations → Control → Health
3. **Data Exploration** - Sky View → Sources → Data Browser → QA

### 4. Context-Aware Navigation (`components/ContextAwareNavigation.tsx`)

**Purpose:** Shows suggested next steps and quick actions based on current workflow.

**Features:**
- Displays suggested navigation steps
- Shows quick action buttons
- Only appears when suggestions are available
- Adapts to current workflow context

**Example:**
When on Dashboard with discovery workflow:
- Suggested: "View Sources", "Check QA"
- Quick Actions: "View ESE Candidates"

### 5. Unified Workspace (`components/UnifiedWorkspace.tsx`)

**Purpose:** Multi-pane layout for viewing multiple related views simultaneously.

**Features:**
- **Split Horizontal** - Side-by-side views
- **Split Vertical** - Stacked views
- **Grid/Tabs** - Tabbed interface for multiple views
- **Fullscreen Mode** - Expand any view to fullscreen
- **Closable Views** - Remove views from workspace

**Use Cases:**
- ESE Investigation: Source details + Light curve + Image viewer
- Pipeline Debug: DLQ + Error logs + System metrics
- Data Analysis: Multiple images side-by-side

**Usage:**
```typescript
import UnifiedWorkspace, { WorkspaceView } from '../components/UnifiedWorkspace';

const views: WorkspaceView[] = [
  {
    id: 'source-detail',
    title: 'Source Details',
    component: <SourceDetailComponent />,
    closable: true,
  },
  {
    id: 'light-curve',
    title: 'Light Curve',
    component: <LightCurveComponent />,
    closable: true,
  },
];

<UnifiedWorkspace views={views} defaultLayout="split-horizontal" />
```

### 6. Command Palette Hook (`hooks/useCommandPalette.ts`)

**Purpose:** Manages command palette open/close state with keyboard shortcuts.

**Features:**
- Global keyboard shortcut handling (Cmd+K / Ctrl+K)
- Escape key to close
- State management for open/close

---

## Integration

### Updated Components

1. **Navigation.tsx**
   - Added command palette trigger button (keyboard icon)
   - Shows current workflow chip
   - Integrated command palette component

2. **App.tsx**
   - Wrapped app with `WorkflowProvider`
   - Added `WorkflowBreadcrumbs` component below navigation

---

## Workflow Types

### Monitoring
- **Pages:** Dashboard, Pipeline
- **Purpose:** Monitor pipeline health and status
- **Next Steps:** View metrics, check health

### Discovery
- **Pages:** Dashboard (with ESE alerts)
- **Purpose:** Investigate new ESE candidates
- **Next Steps:** View sources, check QA, view images

### Investigation
- **Pages:** Sources, Source Detail
- **Purpose:** Investigate specific sources
- **Next Steps:** View images, check calibration, view QA

### Debugging
- **Pages:** Operations, Health
- **Purpose:** Debug pipeline issues
- **Next Steps:** Check DLQ, view logs, check metrics

### Analysis
- **Pages:** Data Browser, QA Visualization
- **Purpose:** Analyze data products
- **Next Steps:** View related images, check quality

### Control
- **Pages:** Control, Streaming
- **Purpose:** Manual pipeline control
- **Next Steps:** View status, check operations

---

## Navigation Rules

Navigation rules define when to show suggestions based on context:

```typescript
{
  condition: (ctx) => ctx.currentPage === '/dashboard' && ctx.currentWorkflow === 'discovery',
  suggestions: [
    { path: '/sources', label: 'View Sources' },
    { path: '/qa', label: 'Check QA' },
  ],
}
```

---

## Usage Examples

### Example 1: ESE Discovery Workflow

1. User sees ESE alert on Dashboard
2. Workflow automatically switches to `discovery`
3. Breadcrumbs show: `Dashboard [Discovery]`
4. Context-aware navigation suggests: "View Sources", "Check QA"
5. User presses `Cmd+K` → Command palette shows workflow template
6. User selects "ESE Discovery Investigation" → Navigates to Sources page

### Example 2: Pipeline Debugging

1. User sees error on Dashboard
2. Workflow switches to `debugging`
3. Breadcrumbs show: `Dashboard > Operations [Debugging]`
4. Context-aware navigation suggests: "Check DLQ", "View Health"
5. User opens unified workspace with DLQ + Error logs side-by-side

### Example 3: Source Investigation

1. User navigates to `/sources/NVSS J1234+5678`
2. Workflow switches to `investigation`
3. Breadcrumbs show: `Dashboard > Sources > NVSS J1234+5678 [Investigation]`
4. Context-aware navigation suggests: "View Images", "Check QA"
5. User can open unified workspace with source details + light curve + images

---

## Future Enhancements

1. **Workflow Persistence** - Save workflow state across sessions
2. **Custom Workflows** - Allow users to create custom workflow templates
3. **Workflow Analytics** - Track common workflow patterns
4. **Smart Suggestions** - ML-based suggestions based on user behavior
5. **Workspace Templates** - Pre-configured workspace layouts for common tasks
6. **Keyboard Shortcuts** - More keyboard shortcuts for power users
7. **Workflow History** - Navigate back through workflow steps

---

## Testing

### Manual Testing Checklist

- [ ] Command palette opens with Cmd+K / Ctrl+K
- [ ] Command palette search filters correctly
- [ ] Keyboard navigation works (↑↓, Enter, Esc)
- [ ] Breadcrumbs appear on non-dashboard pages
- [ ] Breadcrumbs navigate correctly when clicked
- [ ] Workflow chip shows correct workflow type
- [ ] Context-aware navigation shows suggestions
- [ ] Unified workspace renders multiple views
- [ ] Unified workspace layout switching works
- [ ] Fullscreen mode works in unified workspace

### Test Scenarios

1. **ESE Discovery Flow**
   - Navigate to dashboard with ESE alert
   - Verify workflow is `discovery`
   - Verify suggestions appear
   - Use command palette to navigate

2. **Source Investigation Flow**
   - Navigate to `/sources/:id`
   - Verify workflow is `investigation`
   - Verify breadcrumbs show path
   - Open unified workspace with multiple views

3. **Pipeline Debug Flow**
   - Navigate to `/operations`
   - Verify workflow is `debugging`
   - Verify suggestions appear
   - Use command palette to navigate to health page

---

## Files Created

1. `frontend/src/types/workflow.ts` - Type definitions
2. `frontend/src/contexts/WorkflowContext.tsx` - Workflow context provider
3. `frontend/src/components/WorkflowBreadcrumbs.tsx` - Breadcrumbs component
4. `frontend/src/components/CommandPalette.tsx` - Command palette component
5. `frontend/src/components/ContextAwareNavigation.tsx` - Context-aware suggestions
6. `frontend/src/components/UnifiedWorkspace.tsx` - Multi-pane workspace
7. `frontend/src/hooks/useCommandPalette.ts` - Command palette hook

## Files Modified

1. `frontend/src/components/Navigation.tsx` - Added command palette integration
2. `frontend/src/App.tsx` - Added WorkflowProvider and breadcrumbs

---

## Next Steps

1. **Integrate Unified Workspace** - Add workspace mode to source detail pages
2. **Enhance Suggestions** - Add more navigation rules based on user feedback
3. **Add More Workflows** - Create additional workflow templates
4. **User Testing** - Gather feedback from radio astronomers
5. **Performance Optimization** - Optimize command palette search for large datasets
6. **Accessibility** - Ensure keyboard navigation works for all users

---

## References

- Design Document: `docs/analysis/DASHBOARD_DESIGN_IMPROVEMENTS.md`
- Workflow Types: `frontend/src/types/workflow.ts`
- Navigation Rules: `frontend/src/contexts/WorkflowContext.tsx`

