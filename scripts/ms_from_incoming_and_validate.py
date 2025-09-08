#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from core.pipeline.orchestrator import PipelineOrchestrator


async def main() -> int:
    config = {
        'paths': {'ms_stage1_dir': 'data/ms', 'log_dir': 'logs'},
        'ms_creation': {
            'same_timestamp_tolerance': 30.0,
            'min_data_quality': 0.7,
            'max_missing_subbands': 6,
            'min_integration_time': 10.0,
        },
    }

    orchestrator = PipelineOrchestrator(config)
    ms_files = await orchestrator.process_hdf5_to_ms('/data/incoming_test')
    print("\nCreated MS files:", ms_files)

    # Find newest MS
    ms_dir = Path('data/ms')
    ms_candidates = sorted(ms_dir.glob('*.ms'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not ms_candidates:
        print('No MS found in data/ms')
        return 2
    newest = str(ms_candidates[0])
    print(f'Newest MS: {newest}')

    # Run validator
    from scripts.validate_uvw import UVWValidator
    report = UVWValidator().validate_ms(newest)
    print(report.to_dict())
    return 0 if report.success else 2


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))


