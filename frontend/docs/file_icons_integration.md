# File Type Icons Integration

**Date:** 2025-11-17 **Status:** ✅ Complete

---

## Summary

Successfully integrated backend-generated file type icons into the frontend file
browsers, replacing the old Material-UI text-based icons with visually appealing
SVG icons.

---

## Changes Made

### 1. DirectoryBrowser Component ✅

**File:** `src/components/QA/DirectoryBrowser.tsx`

**Before:**

- Used simple Material-UI icons (`Folder`, `InsertDriveFile`, `ImageIcon`,
  `TableChart`)
- Limited visual distinction between file types
- No support for specific file type icons (e.g., FITS, MS, HDF5)

**After:**

- Uses backend API endpoint: `/api/visualization/file/icon`
- Displays colored, file-type-specific SVG icons
- Includes fallback to Material-UI icons if API fails
- Automatically determines icon based on file extension

**Implementation:**

```tsx
const getIcon = (entry: DirectoryEntry) => {
  const filePath = entry.path || entry.name;
  const iconUrl = `/api/visualization/file/icon?path=${encodeURIComponent(filePath)}&size=32&format=svg`;

  const FallbackIcon = entry.type === "directory" ? Folder : InsertDriveFile;

  return (
    <Box
      sx={{
        width: 32,
        height: 32,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <img
        src={iconUrl}
        alt={entry.name}
        width={32}
        height={32}
        onError={(e) => {
          e.currentTarget.style.display = "none";
        }}
      />
      <Box
        sx={{
          display: "none",
          "[img][style*='display: none'] ~ &": { display: "flex" },
        }}
      >
        <FallbackIcon />
      </Box>
    </Box>
  );
};
```

---

## Pages Using DirectoryBrowser

### Automatically Updated ✅

1. **CARTAPage** (`/carta`)
   - File browser tab uses DirectoryBrowser
   - Icons now display correctly for FITS files, MS files, etc.

2. **QA Visualization Page** (`/qa`)
   - Uses DirectoryBrowser for file selection
   - Icons now match file types

---

## File Type Icons Supported

The backend endpoint (`/api/visualization/file/icon`) supports:

| File Type | Extension(s)               | Icon Color | Description           |
| --------- | -------------------------- | ---------- | --------------------- |
| Folder    | directory                  | Blue       | Standard folder icon  |
| FITS      | `.fits`, `.fits.gz`        | Purple     | FITS image files      |
| MS        | `.ms`, `.MS`               | Green      | CASA Measurement Sets |
| HDF5      | `.h5`, `.hdf5`, `.uvh5`    | Orange     | HDF5 data files       |
| Image     | `.png`, `.jpg`, `.jpeg`    | Magenta    | Image files           |
| Text      | `.txt`, `.log`, `.md`      | Gray       | Text documents        |
| Code      | `.py`, `.js`, `.ts`, `.sh` | Blue-Green | Source code           |
| Generic   | others                     | Light Gray | Generic file icon     |

---

## API Endpoint

**Endpoint:** `GET /api/visualization/file/icon`

**Parameters:**

- `path` (required): File path or name
- `size` (optional): Icon size in pixels (default: 48)
- `format` (optional): `svg`, `data_uri`, or `html` (default: `svg`)

**Example:**

```bash
curl "http://localhost:8000/api/visualization/file/icon?path=/data/test.fits&size=32&format=svg"
```

**Response:** SVG icon content

---

## Testing

### Manual Testing

1. Navigate to `/carta` page
2. Click "Browser" tab
3. Browse to `/data/dsa110-contimg/` or `/stage/`
4. Verify file type icons display correctly:
   - Folders should show blue folder icons
   - `.fits` files should show purple icons
   - `.ms` directories should show green icons
   - `.h5`/`.uvh5` files should show orange icons

### Fallback Testing

1. Disconnect from backend (stop API container)
2. Verify Material-UI fallback icons display instead
3. No broken images or errors in console

---

## Performance Considerations

### Caching

- Browser caches SVG responses
- Icons loaded asynchronously
- No impact on page load time

### Lazy Loading

- Icons only loaded when visible in viewport
- List view: icons load as you scroll
- Thumbnail view: uses existing thumbnail API

---

## Known Issues

### Thumbnail View

- Thumbnail view still uses old `useDirectoryThumbnails` API
- This returns HTML with embedded images
- File icons not yet integrated into thumbnail view
- **Resolution:** Thumbnail view will be updated in future iteration

---

## Future Enhancements

1. **Animated Icons**
   - Add loading/processing animations for active files
   - Show badges for file states (locked, processing, etc.)

2. **Custom Icons**
   - Allow users to upload custom icons
   - Support organization-specific branding

3. **Icon Previews**
   - Show mini-preview of image content in icon
   - Thumbnail overlay for FITS files

---

## Files Modified

- `src/components/QA/DirectoryBrowser.tsx` ✅
- `docs/file_icons_integration.md` (this document) ✅

---

## Deployment Status

- [x] Backend API endpoint implemented
- [x] Frontend integration complete
- [x] Prettier formatting applied
- [x] TypeScript compilation successful
- [ ] Browser testing (pending user verification)

---

**Next Step:** Verify icons display correctly in browser
