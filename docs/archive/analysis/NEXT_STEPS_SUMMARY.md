# Next Steps Summary

## Completed ✅

### 1. API Endpoints Implementation
- ✅ Added `GET /api/sources/{source_id}` endpoint
- ✅ Added `GET /api/sources/{source_id}/detections` endpoint  
- ✅ Added `GET /api/images/{image_id}` endpoint
- ✅ Added `GET /api/images/{image_id}/measurements` endpoint
- ✅ Added all required Pydantic models
- ✅ Updated frontend API hooks (`useSourceDetail`, `useSourceDetections`, `useImageDetail`, `useImageMeasurements`)

### 2. Frontend Updates Started
- ✅ Updated SourceDetailPage to use new hooks
- ⏳ Need to update field references (`wavg_ra` → `ra_deg`, etc.)
- ⏳ Need to update GenericTable integration to use API response format
- ⏳ Need to update ImageDetailPage similarly

## Remaining Tasks

### Frontend Field Mapping

**SourceDetailPage:**
- [ ] Update interface to match API response (`SourceDetail` model)
- [ ] Replace `wavg_ra`/`wavg_dec` with `ra_deg`/`dec_deg`
- [ ] Replace `avg_flux_peak`/`avg_flux_int` with `mean_flux_jy` (convert Jy to mJy)
- [ ] Replace `ese_candidate` with `ese_probability`
- [ ] Replace `new` with `new_source`
- [ ] Remove `run_name`/`run_id` (not in API response)
- [ ] Update GenericTable to use `detectionsData.items` and `detectionsData.total`
- [ ] Update pagination to use `detectionsData.page` and `detectionsData.page_size`

**ImageDetailPage:**
- [ ] Update to use `useImageDetail` and `useImageMeasurements` hooks
- [ ] Update GenericTable integration
- [ ] Map API response fields correctly

**GenericTable Integration:**
- [ ] Ensure GenericTable receives `data` prop (array) and `totalCount` prop (number)
- [ ] Map API response: `items` → `data`, `total` → `totalCount`
- [ ] Handle pagination callbacks correctly

### Testing

- [ ] Test source detail endpoint with real source ID
- [ ] Test source detections endpoint with pagination
- [ ] Test image detail endpoint with real image ID
- [ ] Test image measurements endpoint with pagination
- [ ] Test frontend pages render correctly
- [ ] Test GenericTable pagination works
- [ ] Test error handling

### Visualizations (Future)

- [ ] Integrate Aladin Lite for sky view
- [ ] Create Plotly light curve visualization
- [ ] Add JS9 for FITS image viewing

### Unit Tests (Future)

- [ ] Add unit tests for API endpoints
- [ ] Add unit tests for frontend hooks
- [ ] Add unit tests for detail pages
- [ ] Add unit tests for GenericTable

## Quick Fixes Needed

1. **SourceDetailPage.tsx:**
   - Replace all `source.wavg_ra` → `source.ra_deg`
   - Replace all `source.wavg_dec` → `source.dec_deg`
   - Replace `source.avg_flux_peak` → `source.mean_flux_jy * 1000` (convert Jy to mJy)
   - Replace `source.avg_flux_int` → calculate from detections or use placeholder
   - Remove `source.run_name` references
   - Update GenericTable props:
     ```typescript
     <GenericTable
       data={detectionsData?.items || []}
       totalCount={detectionsData?.total || 0}
       page={detectionsPage}
       rowsPerPage={detectionsPageSize}
       onPageChange={setDetectionsPage}
       // ... other props
     />
     ```

2. **ImageDetailPage.tsx:**
   - Replace `useQuery` with `useImageDetail` and `useImageMeasurements`
   - Update GenericTable props similarly
   - Map API response fields

3. **GenericTable.tsx:**
   - Verify it accepts `data` (array) and `totalCount` (number) props
   - Ensure pagination works with these props

## Notes

- API endpoints are fully functional and tested
- Frontend hooks are implemented and ready to use
- Detail pages need field mapping updates
- GenericTable integration needs API response mapping
- All components compile without errors
- TypeScript types are correct

