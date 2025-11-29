#!/bin/bash
# Organize test files into proper subdirectories
# This script moves test files from tests/ and tests/unit/ into organized subdirectories

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Create necessary subdirectories
mkdir -p tests/unit/api
mkdir -p tests/unit/calibration
mkdir -p tests/unit/catalog
mkdir -p tests/unit/database
mkdir -p tests/unit/imaging
mkdir -p tests/unit/mosaic
mkdir -p tests/unit/photometry
mkdir -p tests/unit/pipeline
mkdir -p tests/unit/qa
mkdir -p tests/unit/visualization

echo "Organizing test files..."

# Move files from tests/ root to appropriate subdirectories
echo "Moving files from tests/ root..."

# API tests
[ -f tests/test_api_endpoints.py ] && mv tests/test_api_endpoints.py tests/unit/api/ && echo "  Moved test_api_endpoints.py :arrow_right: tests/unit/api/"

# Catalog tests
[ -f tests/test_catalog_query_fix.py ] && mv tests/test_catalog_query_fix.py tests/unit/catalog/ && echo "  Moved test_catalog_query_fix.py :arrow_right: tests/unit/catalog/"

# QA/Validation tests
[ -f tests/test_completeness_analysis.py ] && mv tests/test_completeness_analysis.py tests/unit/qa/ && echo "  Moved test_completeness_analysis.py :arrow_right: tests/unit/qa/"
[ -f tests/test_completeness_mock.py ] && mv tests/test_completeness_mock.py tests/unit/qa/ && echo "  Moved test_completeness_mock.py :arrow_right: tests/unit/qa/"
[ -f tests/test_html_reports.py ] && mv tests/test_html_reports.py tests/unit/qa/ && echo "  Moved test_html_reports.py :arrow_right: tests/unit/qa/"
[ -f tests/test_html_reports_simple.py ] && mv tests/test_html_reports_simple.py tests/unit/qa/ && echo "  Moved test_html_reports_simple.py :arrow_right: tests/unit/qa/"
[ -f tests/test_qa_visualization.py ] && mv tests/test_qa_visualization.py tests/unit/qa/ && echo "  Moved test_qa_visualization.py :arrow_right: tests/unit/qa/"
[ -f tests/test_validation_plots.py ] && mv tests/test_validation_plots.py tests/unit/qa/ && echo "  Moved test_validation_plots.py :arrow_right: tests/unit/qa/"
[ -f tests/test_validation_real_data.py ] && mv tests/test_validation_real_data.py tests/unit/qa/ && echo "  Moved test_validation_real_data.py :arrow_right: tests/unit/qa/"
[ -f tests/test_validation_real_observations.py ] && mv tests/test_validation_real_observations.py tests/unit/qa/ && echo "  Moved test_validation_real_observations.py :arrow_right: tests/unit/qa/"

# Visualization tests
[ -f tests/test_fits_visualization.py ] && mv tests/test_fits_visualization.py tests/unit/visualization/ && echo "  Moved test_fits_visualization.py :arrow_right: tests/unit/visualization/"
[ -f tests/test_visualization_logic.py ] && mv tests/test_visualization_logic.py tests/unit/visualization/ && echo "  Moved test_visualization_logic.py :arrow_right: tests/unit/visualization/"

# Photometry tests
[ -f tests/test_forced_photometry.py ] && mv tests/test_forced_photometry.py tests/unit/photometry/ && echo "  Moved test_forced_photometry.py :arrow_right: tests/unit/photometry/"

# Pipeline tests
[ -f tests/test_pipeline.py ] && mv tests/test_pipeline.py tests/unit/pipeline/ && echo "  Moved test_pipeline.py :arrow_right: tests/unit/pipeline/"

# Note: test_priority1_quick.py stays in root as it's a quick check script

# Move files from tests/unit/ root to appropriate subdirectories
echo ""
echo "Moving files from tests/unit/ root..."

# Calibration tests
[ -f tests/unit/test_calibration_comprehensive.py ] && mv tests/unit/test_calibration_comprehensive.py tests/unit/calibration/ && echo "  Moved test_calibration_comprehensive.py :arrow_right: tests/unit/calibration/"
[ -f tests/unit/test_caltable_paths.py ] && mv tests/unit/test_caltable_paths.py tests/unit/calibration/ && echo "  Moved test_caltable_paths.py :arrow_right: tests/unit/calibration/"
[ -f tests/unit/test_cli_calibration_args.py ] && mv tests/unit/test_cli_calibration_args.py tests/unit/calibration/ && echo "  Moved test_cli_calibration_args.py :arrow_right: tests/unit/calibration/"

# Catalog tests
[ -f tests/unit/test_catalog_validation.py ] && mv tests/unit/test_catalog_validation.py tests/unit/catalog/ && echo "  Moved test_catalog_validation.py :arrow_right: tests/unit/catalog/"
[ -f tests/unit/test_crossmatch.py ] && mv tests/unit/test_crossmatch.py tests/unit/catalog/ && echo "  Moved test_crossmatch.py :arrow_right: tests/unit/catalog/"

# Database tests
[ -f tests/unit/test_data_registry_publish.py ] && mv tests/unit/test_data_registry_publish.py tests/unit/database/ && echo "  Moved test_data_registry_publish.py :arrow_right: tests/unit/database/"
[ -f tests/unit/test_eta_metric_migration.py ] && mv tests/unit/test_eta_metric_migration.py tests/unit/database/ && echo "  Moved test_eta_metric_migration.py :arrow_right: tests/unit/database/"

# Imaging tests
[ -f tests/unit/test_imaging_mocked.py ] && mv tests/unit/test_imaging_mocked.py tests/unit/imaging/ && echo "  Moved test_imaging_mocked.py :arrow_right: tests/unit/imaging/"
[ -f tests/unit/test_casaimage_api.py ] && mv tests/unit/test_casaimage_api.py tests/unit/imaging/ && echo "  Moved test_casaimage_api.py :arrow_right: tests/unit/imaging/"

# Mosaic tests
[ -f tests/unit/test_mosaic_bounds_calculation.py ] && mv tests/unit/test_mosaic_bounds_calculation.py tests/unit/mosaic/ && echo "  Moved test_mosaic_bounds_calculation.py :arrow_right: tests/unit/mosaic/"
[ -f tests/unit/test_mosaic_coordinate_system.py ] && mv tests/unit/test_mosaic_coordinate_system.py tests/unit/mosaic/ && echo "  Moved test_mosaic_coordinate_system.py :arrow_right: tests/unit/mosaic/"
[ -f tests/unit/test_mosaic_orchestrator.py ] && mv tests/unit/test_mosaic_orchestrator.py tests/unit/mosaic/ && echo "  Moved test_mosaic_orchestrator.py :arrow_right: tests/unit/mosaic/"
[ -f tests/unit/test_mosaic_overlap_filtering.py ] && mv tests/unit/test_mosaic_overlap_filtering.py tests/unit/mosaic/ && echo "  Moved test_mosaic_overlap_filtering.py :arrow_right: tests/unit/mosaic/"
[ -f tests/unit/test_mosaic_shape_handling.py ] && mv tests/unit/test_mosaic_shape_handling.py tests/unit/mosaic/ && echo "  Moved test_mosaic_shape_handling.py :arrow_right: tests/unit/mosaic/"
[ -f tests/unit/test_mosaic_weight_image_init.py ] && mv tests/unit/test_mosaic_weight_image_init.py tests/unit/mosaic/ && echo "  Moved test_mosaic_weight_image_init.py :arrow_right: tests/unit/mosaic/"

# Photometry tests
[ -f tests/unit/test_forced_photometry_enhanced.py ] && mv tests/unit/test_forced_photometry_enhanced.py tests/unit/photometry/ && echo "  Moved test_forced_photometry_enhanced.py :arrow_right: tests/unit/photometry/"
[ -f tests/unit/test_forced_photometry_failures.py ] && mv tests/unit/test_forced_photometry_failures.py tests/unit/photometry/ && echo "  Moved test_forced_photometry_failures.py :arrow_right: tests/unit/photometry/"

# Pipeline tests
[ -f tests/unit/test_pipeline_stages_comprehensive.py ] && mv tests/unit/test_pipeline_stages_comprehensive.py tests/unit/pipeline/ && echo "  Moved test_pipeline_stages_comprehensive.py :arrow_right: tests/unit/pipeline/"

# QA tests
[ -f tests/unit/test_qa_base.py ] && mv tests/unit/test_qa_base.py tests/unit/qa/ && echo "  Moved test_qa_base.py :arrow_right: tests/unit/qa/"
[ -f tests/unit/test_qa_config.py ] && mv tests/unit/test_qa_config.py tests/unit/qa/ && echo "  Moved test_qa_config.py :arrow_right: tests/unit/qa/"
[ -f tests/unit/test_qa_fast_validation.py ] && mv tests/unit/test_qa_fast_validation.py tests/unit/qa/ && echo "  Moved test_qa_fast_validation.py :arrow_right: tests/unit/qa/"
[ -f tests/unit/test_qa_photometry_validation.py ] && mv tests/unit/test_qa_photometry_validation.py tests/unit/qa/ && echo "  Moved test_qa_photometry_validation.py :arrow_right: tests/unit/qa/"
[ -f tests/unit/test_qa_validation_mode.py ] && mv tests/unit/test_qa_validation_mode.py tests/unit/qa/ && echo "  Moved test_qa_validation_mode.py :arrow_right: tests/unit/qa/"
[ -f tests/unit/test_validation_functions.py ] && mv tests/unit/test_validation_functions.py tests/unit/qa/ && echo "  Moved test_validation_functions.py :arrow_right: tests/unit/qa/"

# Other utility tests (keep in unit root for now)
# test_casa_lazy_imports.py - CASA-specific, could go to tests/unit/casa/ if we create it
# test_masking.py - could go to tests/unit/masking/ if we create it
# test_mermaid_diagram_helpers.py - utility, keep in root
# test_monitoring_script.py - utility, keep in root
# test_nvss_seeding.py - catalog-related, move to catalog
# test_optimizations.py - keep in root
# test_parallel.py - keep in root
# test_products_pointing.py - could go to tests/unit/pointing/ if we create it
# test_quality_tier.py - QA-related, move to qa
# test_source_class.py - keep in root
# test_subband_ordering.py - conversion-related, move to conversion

# Additional moves
[ -f tests/unit/test_nvss_seeding.py ] && mv tests/unit/test_nvss_seeding.py tests/unit/catalog/ && echo "  Moved test_nvss_seeding.py :arrow_right: tests/unit/catalog/"
[ -f tests/unit/test_quality_tier.py ] && mv tests/unit/test_quality_tier.py tests/unit/qa/ && echo "  Moved test_quality_tier.py :arrow_right: tests/unit/qa/"
[ -f tests/unit/test_subband_ordering.py ] && mv tests/unit/test_subband_ordering.py tests/unit/conversion/ && echo "  Moved test_subband_ordering.py :arrow_right: tests/unit/conversion/"

echo ""
echo "Test organization complete!"
echo ""
echo "Remaining files in tests/ root:"
ls -1 tests/test_*.py 2>/dev/null | wc -l | xargs echo "  Count:"
echo ""
echo "Remaining files in tests/unit/ root:"
ls -1 tests/unit/test_*.py 2>/dev/null | wc -l | xargs echo "  Count:"

