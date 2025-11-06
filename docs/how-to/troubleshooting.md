# Troubleshooting

- CASA open errors → use direct-subband writer; ensure imaging columns
- .fuse_hidden files → clean after confirming no open FDs
- Stale groups → API reprocess, housekeeping utility, scheduler
- Performance → adjust workers, OMP/MKL threads, use fast scratch
