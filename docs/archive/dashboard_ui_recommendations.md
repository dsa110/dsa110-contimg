# Dashboard UI Development Recommendations

## Current Stack Analysis

You're already using excellent libraries:
- ✅ **Material-UI (MUI) v7** - Comprehensive component library
- ✅ **React Query (TanStack Query)** - Data fetching & caching
- ✅ **AG Grid** - Enterprise-grade tables
- ✅ **Plotly.js** - Scientific plotting
- ✅ **React Router** - Navigation

**The problem**: Building custom components from scratch instead of leveraging these libraries' built-in solutions.

## Recommended Approach: Leverage Existing Libraries

### 1. Material-UI Components (You Already Have This!)

**Stop building custom components** - MUI has pre-built, tested components for almost everything:

#### File Browser → Use MUI DataGrid or TreeView
```typescript
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { TreeView, TreeItem } from '@mui/x-tree-view';

// Instead of custom file list, use DataGrid
const columns: GridColDef[] = [
  { field: 'name', headerName: 'Name', width: 300 },
  { field: 'type', headerName: 'Type', width: 150 },
  { field: 'size', headerName: 'Size', width: 120 },
  { field: 'modified', headerName: 'Modified', width: 180 },
];

<DataGrid
  rows={files}
  columns={columns}
  onRowClick={(params) => handleFileClick(params.row)}
  getRowId={(row) => row.path}
  // Built-in: sorting, filtering, pagination, selection
/>
```

#### Forms → Use MUI Form Components
```typescript
import { TextField, Select, MenuItem, Button } from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers';

// Instead of custom form inputs
<TextField
  label="MS Path"
  value={msPath}
  onChange={(e) => setMsPath(e.target.value)}
  error={!!errors.msPath}
  helperText={errors.msPath}
  fullWidth
/>
```

#### Loading States → Use MUI Skeleton/Backdrop
```typescript
import { Skeleton, Backdrop, CircularProgress } from '@mui/material';

// Instead of custom loading spinners
{loading ? (
  <Skeleton variant="rectangular" height={400} />
) : (
  <FileList files={files} />
)}

<Backdrop open={isLoading} sx={{ zIndex: 9999 }}>
  <CircularProgress />
</Backdrop>
```

#### Dialogs/Modals → Use MUI Dialog
```typescript
import { Dialog, DialogTitle, DialogContent, DialogActions } from '@mui/material';

// Instead of custom modals
<Dialog open={open} onClose={handleClose} maxWidth="lg" fullWidth>
  <DialogTitle>View FITS File</DialogTitle>
  <DialogContent>
    <FITSViewer path={selectedFile} />
  </DialogContent>
  <DialogActions>
    <Button onClick={handleClose}>Close</Button>
  </DialogActions>
</Dialog>
```

### 2. React Query Patterns (You Already Have This!)

**Stop manually managing loading/error states** - React Query handles it:

```typescript
import { useQuery, useMutation } from '@tanstack/react-query';

// Instead of useState + useEffect + manual error handling
function useDirectoryListing(path: string) {
  return useQuery({
    queryKey: ['directory', path],
    queryFn: () => apiClient.get(`/api/visualization/browse?path=${path}`),
    staleTime: 30000, // Cache for 30 seconds
    // Built-in: loading, error, refetch, caching, deduplication
  });
}

function useQARun() {
  return useMutation({
    mutationFn: (data: QARunRequest) => 
      apiClient.post('/api/visualization/qa/run', data),
    onSuccess: () => {
      // Invalidate queries to refetch
      queryClient.invalidateQueries({ queryKey: ['qa-runs'] });
    },
  });
}

// Usage
function FileBrowser({ path }: { path: string }) {
  const { data, isLoading, error, refetch } = useDirectoryListing(path);
  
  if (isLoading) return <Skeleton />;
  if (error) return <Alert severity="error">{error.message}</Alert>;
  
  return <DataGrid rows={data.entries} columns={columns} />;
}
```

### 3. AG Grid for Tables (You Already Have This!)

**Stop building custom tables** - AG Grid handles everything:

```typescript
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-material.css';

// Instead of custom table component
<AgGridReact
  rowData={tableData}
  columnDefs={columnDefs}
  defaultColDef={{
    sortable: true,
    filter: true,
    resizable: true,
  }}
  pagination={true}
  paginationPageSize={50}
  onRowClicked={(event) => handleRowClick(event.data)}
  // Built-in: sorting, filtering, pagination, column resizing, 
  // row selection, export, grouping, etc.
/>
```

### 4. Add These Missing Libraries

#### Form Validation: React Hook Form + Zod
```bash
npm install react-hook-form zod @hookform/resolvers
```

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const qaRunSchema = z.object({
  ms_path: z.string().min(1, 'MS path is required'),
  qa_root: z.string().min(1, 'QA root is required'),
  thresholds: z.object({
    min_snr: z.number().min(0).optional(),
  }).optional(),
});

function QARunForm() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(qaRunSchema),
  });
  
  const mutation = useQARun();
  
  return (
    <form onSubmit={handleSubmit(mutation.mutate)}>
      <TextField
        {...register('ms_path')}
        error={!!errors.ms_path}
        helperText={errors.ms_path?.message}
      />
      {/* Automatic validation, error handling */}
    </form>
  );
}
```

#### File Viewer: react-file-viewer or react-pdf
```bash
npm install react-file-viewer react-pdf
```

```typescript
import FileViewer from 'react-file-viewer';
import { Document, Page } from 'react-pdf';

// For images, PDFs, etc.
<FileViewer
  fileType={fileExtension}
  filePath={fileUrl}
  onError={handleError}
/>
```

#### Code/Text Viewer: react-syntax-highlighter
```bash
npm install react-syntax-highlighter @types/react-syntax-highlighter
```

```typescript
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

<SyntaxHighlighter
  language="python"
  style={vscDarkPlus}
  showLineNumbers
  wrapLines
>
  {code}
</SyntaxHighlighter>
```

#### Virtual Scrolling for Large Lists: react-window
```bash
npm install react-window @types/react-window
```

```typescript
import { FixedSizeList } from 'react-window';

// For large file lists (thousands of files)
<FixedSizeList
  height={600}
  itemCount={files.length}
  itemSize={50}
  width="100%"
>
  {({ index, style }) => (
    <div style={style}>
      <FileItem file={files[index]} />
    </div>
  )}
</FixedSizeList>
```

#### Toast Notifications: notistack (MUI-compatible)
```bash
npm install notistack
```

```typescript
import { SnackbarProvider, useSnackbar } from 'notistack';

function App() {
  return (
    <SnackbarProvider maxSnack={3}>
      <YourApp />
    </SnackbarProvider>
  );
}

function MyComponent() {
  const { enqueueSnackbar } = useSnackbar();
  
  const handleSuccess = () => {
    enqueueSnackbar('QA run started successfully', { variant: 'success' });
  };
}
```

#### Drag & Drop: react-beautiful-dnd or @dnd-kit
```bash
npm install @dnd-kit/core @dnd-kit/sortable
```

### 5. Component Architecture Pattern

#### Create Reusable Wrapper Components

```typescript
// components/common/QueryWrapper.tsx
import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { Skeleton, Alert, AlertTitle } from '@mui/material';

interface QueryWrapperProps<T> {
  query: UseQueryResult<T>;
  children: (data: T) => React.ReactNode;
  skeleton?: React.ReactNode;
}

export function QueryWrapper<T>({ query, children, skeleton }: QueryWrapperProps<T>) {
  if (query.isLoading) {
    return skeleton || <Skeleton variant="rectangular" height={400} />;
  }
  
  if (query.isError) {
    return (
      <Alert severity="error">
        <AlertTitle>Error</AlertTitle>
        {query.error instanceof Error ? query.error.message : 'An error occurred'}
      </Alert>
    );
  }
  
  if (!query.data) {
    return <Alert severity="info">No data available</Alert>;
  }
  
  return <>{children(query.data)}</>;
}

// Usage
function FileBrowser({ path }: { path: string }) {
  const query = useDirectoryListing(path);
  
  return (
    <QueryWrapper query={query}>
      {(data) => <DataGrid rows={data.entries} columns={columns} />}
    </QueryWrapper>
  );
}
```

#### Create Specialized Viewer Components

```typescript
// components/viewers/FITSViewer.tsx
import { useState } from 'react';
import { Box, Select, MenuItem, FormControl, InputLabel, ToggleButtonGroup, ToggleButton } from '@mui/material';
import { useQuery } from '@tanstack/react-query';

export function FITSViewer({ path }: { path: string }) {
  const [scale, setScale] = useState('linear');
  const [colormap, setColormap] = useState('grey');
  const [dualWindow, setDualWindow] = useState(false);
  
  const { data: html } = useQuery({
    queryKey: ['fits-view', path, scale, colormap, dualWindow],
    queryFn: () => 
      apiClient.get(`/api/visualization/fits/view`, {
        params: { path, scale, colormap, dual_window: dualWindow },
      }),
  });
  
  return (
    <Box>
      <Box sx={{ mb: 2, display: 'flex', gap: 2 }}>
        <FormControl size="small">
          <InputLabel>Scale</InputLabel>
          <Select value={scale} onChange={(e) => setScale(e.target.value)}>
            <MenuItem value="linear">Linear</MenuItem>
            <MenuItem value="log">Log</MenuItem>
            <MenuItem value="sqrt">Square Root</MenuItem>
          </Select>
        </FormControl>
        
        <FormControl size="small">
          <InputLabel>Colormap</InputLabel>
          <Select value={colormap} onChange={(e) => setColormap(e.target.value)}>
            <MenuItem value="grey">Grey</MenuItem>
            <MenuItem value="heat">Heat</MenuItem>
            <MenuItem value="cool">Cool</MenuItem>
          </Select>
        </FormControl>
        
        <ToggleButtonGroup
          value={dualWindow}
          exclusive
          onChange={(_, value) => setDualWindow(value)}
        >
          <ToggleButton value={false}>Single</ToggleButton>
          <ToggleButton value={true}>Dual</ToggleButton>
        </ToggleButtonGroup>
      </Box>
      
      <Box dangerouslySetInnerHTML={{ __html: html }} />
    </Box>
  );
}
```

### 6. Error Handling Pattern

```typescript
// hooks/useErrorHandler.ts
import { useSnackbar } from 'notistack';
import { useQueryErrorResetBoundary } from '@tanstack/react-query';
import { ErrorBoundary } from 'react-error-boundary';

export function useErrorHandler() {
  const { enqueueSnackbar } = useSnackbar();
  
  return {
    handleError: (error: unknown) => {
      const message = error instanceof Error ? error.message : 'An error occurred';
      enqueueSnackbar(message, { variant: 'error' });
    },
  };
}

// components/common/ErrorFallback.tsx
export function ErrorFallback({ error, resetErrorBoundary }: any) {
  return (
    <Alert severity="error" action={<Button onClick={resetErrorBoundary}>Retry</Button>}>
      <AlertTitle>Something went wrong</AlertTitle>
      {error.message}
    </Alert>
  );
}

// Usage in App
<ErrorBoundary FallbackComponent={ErrorFallback}>
  <YourComponent />
</ErrorBoundary>
```

### 7. State Management Pattern

**For simple state**: Use React Query + local state
**For complex state**: Consider Zustand (lightweight, no boilerplate)

```bash
npm install zustand
```

```typescript
// stores/qaStore.ts
import { create } from 'zustand';

interface QAStore {
  selectedFile: string | null;
  viewerSettings: {
    scale: string;
    colormap: string;
  };
  setSelectedFile: (path: string | null) => void;
  setViewerSettings: (settings: Partial<QAStore['viewerSettings']>) => void;
}

export const useQAStore = create<QAStore>((set) => ({
  selectedFile: null,
  viewerSettings: { scale: 'linear', colormap: 'grey' },
  setSelectedFile: (path) => set({ selectedFile: path }),
  setViewerSettings: (settings) => 
    set((state) => ({ viewerSettings: { ...state.viewerSettings, ...settings } })),
}));
```

## Recommended Package Additions

```bash
# Form handling & validation
npm install react-hook-form zod @hookform/resolvers

# File viewing
npm install react-file-viewer react-pdf

# Code/text viewing
npm install react-syntax-highlighter @types/react-syntax-highlighter

# Performance (large lists)
npm install react-window @types/react-window

# Notifications
npm install notistack

# State management (if needed)
npm install zustand

# Drag & drop (if needed)
npm install @dnd-kit/core @dnd-kit/sortable

# Date/time utilities (you have dayjs, but consider)
# dayjs is already installed - use it!
```

## Quick Wins: Replace Custom Components

1. **Custom file list** → MUI DataGrid or AG Grid
2. **Custom loading spinner** → MUI Skeleton/CircularProgress
3. **Custom modal** → MUI Dialog
4. **Custom form inputs** → MUI TextField/Select/etc.
5. **Custom error display** → MUI Alert
6. **Custom table** → AG Grid
7. **Manual API calls** → React Query hooks
8. **Custom toast** → notistack

## Example: Complete File Browser Component

```typescript
import { useQuery } from '@tanstack/react-query';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import { IconButton, Chip, Box } from '@mui/material';
import { Visibility, Download } from '@mui/icons-material';
import { QueryWrapper } from './QueryWrapper';
import { FITSViewer } from './viewers/FITSViewer';
import { Dialog } from '@mui/material';

const columns: GridColDef[] = [
  { field: 'name', headerName: 'Name', width: 300 },
  { 
    field: 'type', 
    headerName: 'Type', 
    width: 150,
    renderCell: (params) => (
      <Chip label={params.value} size="small" color="primary" />
    ),
  },
  { field: 'size', headerName: 'Size', width: 120 },
  {
    field: 'actions',
    type: 'actions',
    width: 100,
    getActions: (params) => [
      <GridActionsCellItem
        icon={<Visibility />}
        label="View"
        onClick={() => handleView(params.row)}
      />,
      <GridActionsCellItem
        icon={<Download />}
        label="Download"
        onClick={() => handleDownload(params.row)}
      />,
    ],
  },
];

export function FileBrowser({ path }: { path: string }) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  
  const query = useQuery({
    queryKey: ['directory', path],
    queryFn: () => apiClient.get(`/api/visualization/browse?path=${path}`),
  });
  
  return (
    <>
      <QueryWrapper query={query}>
        {(data) => (
          <DataGrid
            rows={data.entries}
            columns={columns}
            onRowClick={(params) => setSelectedFile(params.row.path)}
            getRowId={(row) => row.path}
            pageSizeOptions={[25, 50, 100]}
            initialState={{ pagination: { paginationModel: { pageSize: 50 } } }}
          />
        )}
      </QueryWrapper>
      
      <Dialog open={!!selectedFile} onClose={() => setSelectedFile(null)} maxWidth="lg" fullWidth>
        <DialogTitle>{selectedFile}</DialogTitle>
        <DialogContent>
          {selectedFile && <FileViewer path={selectedFile} />}
        </DialogContent>
      </Dialog>
    </>
  );
}
```

## Benefits

1. **Less code** - Use pre-built components instead of custom ones
2. **Fewer bugs** - Components are battle-tested by thousands of users
3. **Better UX** - Components follow Material Design principles
4. **Accessibility** - MUI components are WCAG compliant
5. **Performance** - Optimized by library authors
6. **Maintainability** - Standard patterns, easier to understand

## Migration Strategy

1. **Start with one component** - Pick your most problematic custom component
2. **Replace with MUI equivalent** - Use MUI docs to find matching component
3. **Test thoroughly** - Ensure all edge cases are handled
4. **Repeat** - Gradually replace other custom components

## Resources

- [MUI Component Library](https://mui.com/components/)
- [React Query Docs](https://tanstack.com/query/latest)
- [AG Grid Docs](https://www.ag-grid.com/react-data-grid/)
- [React Hook Form](https://react-hook-form.com/)
- [Zod Validation](https://zod.dev/)

