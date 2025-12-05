# Development Roadmap & Status

**Last Updated:** December 4, 2025

This document tracks the high-level progress of the DSA-110 Continuum Imaging
Pipeline development.

---

## Current State (December 2025)

| Layer              | Status                                          |
| ------------------ | ----------------------------------------------- |
| **Frontend UI**    | ✅ 9/9 major features implemented with tests    |
| **Backend API**    | ⚠️ ~70% coverage - some features lack endpoints |
| **Database**       | ✅ Unified SQLite with WAL mode                 |
| **Pipeline Core**  | ✅ Streaming converter operational              |
| **Monitoring/Ops** | ✅ Prometheus + Grafana ready                   |
| **Documentation**  | ✅ Consolidated and organized                   |

---

## ✅ Completed Milestones

### December 2025: Documentation & Visualization

- **Documentation Consolidation**: Merged fragmented docs into topic-based guides
- **Visualization Module**: Unified plotting for calibration, imaging, mosaics
- **Nightly Mosaic Infrastructure**: Systemd service/timer for automated mosaics
- **Subband Filename Normalization**: Automatic grouping of correlator output

### November 2025: Browser Testing & Reliability

- **Playwright Test Suite**: End-to-end browser testing
- **Pipeline Health Checks**: Automated monitoring and alerting
- **Timeout Handling**: Graceful handling of long-running operations

### October 2025: Streaming Pipeline

- **Streaming Converter**: Real-time UVH5 → MS conversion daemon
- **SQLite-backed Queue**: Checkpoint recovery and state management
- **Performance Tracking**: Load/phase/write timing per observation

### Earlier 2025

- **Event Bus Monitor**: Real-time pipeline event streaming
- **Cache Statistics**: API for monitoring cache performance
- **Pipeline Stage Dashboard**: Visual monitoring of pipeline stages

---

## 🚧 Active Development (Q4 2025)

### 1. Complexity Reduction Refactoring

- **Goal**: Simplify codebase architecture per complexity reduction guide
- **Status**: In Progress
- **Docs**: [Complexity Reduction Guide](../dsa110-contimg-complexity-reduction-guide.md)

### 2. Backend API Completion

Missing endpoints identified in [Production Readiness Roadmap](design/PRODUCTION_READINESS_ROADMAP.md):

| Feature             | Status     | Priority |
| ------------------- | ---------- | -------- |
| Saved Queries       | ❌ Missing | Medium   |
| Backup/Restore      | ⚠️ Partial | High     |
| Pipeline Triggers   | ⚠️ Partial | Medium   |
| Jupyter Integration | ❌ Missing | Low      |
| VO Export           | ⚠️ Partial | Medium   |

### 3. GPU Acceleration

- **Goal**: 10-20x performance improvement via GPU
- **Status**: Planning complete, implementation starting
- **Docs**: [GPU Implementation Plan](design/GPU_implementation_plan.md)

---

## 🔮 Future Roadmap

### Q1 2026

1. **GPU Calibration**: CUDA-accelerated bandpass calibration
2. **Automated QA**: Catalog-based validation against NVSS/VLASS
3. **Self-Healing Pipeline**: Automatic recovery from common failures

### Q2 2026

1. **GPU Imaging**: Accelerated imaging with cuFFT
2. **Production Hardening**: Complete backend API coverage
3. **Performance Monitoring**: Grafana dashboards for throughput tracking

### Long-term

1. **Real-time Processing**: Sub-minute latency from observation to image
2. **Distributed Processing**: Multi-node parallelization
3. **ML-based RFI Detection**: Machine learning for interference flagging

---

## Key Metrics

| Metric             | Current      | Target (12 months) |
| ------------------ | ------------ | ------------------ |
| Calibration time   | ~41s         | ~4s (GPU)          |
| Imaging time       | ~60s         | ~6s (GPU)          |
| Overall throughput | ~28 MS/hour  | ~360 MS/hour       |
| API test coverage  | ~72%         | >90%               |
| Documentation      | Consolidated | Maintained         |

---

## Related Documents

- [Architecture](ARCHITECTURE.md) - System design overview
- [Developer Guide](DEVELOPER_GUIDE.md) - Contributing guidelines
- [Production Readiness](design/PRODUCTION_READINESS_ROADMAP.md) - Detailed backend gaps
- [GPU Implementation](design/GPU_implementation_plan.md) - GPU acceleration plan
- [Complexity Reduction](../dsa110-contimg-complexity-reduction-guide.md) - Refactoring guide
