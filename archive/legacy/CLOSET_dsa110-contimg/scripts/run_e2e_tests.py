#!/usr/bin/env python3
"""
End-to-End Test Runner for DSA-110 Pipeline

This script runs comprehensive end-to-end tests to validate
the entire pipeline functionality and science product quality.
"""

import asyncio
import os
import sys
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.e2e.test_pipeline_e2e import E2ETestFramework, TestConfig
from tests.science.validation_framework import ScienceValidator, ValidationCriteria
from dsa110.automation.pipeline_automation import PipelineAutomation, AutomationConfig
from dsa110.utils.logging import get_logger

logger = get_logger(__name__)


class TestRunner:
    """
    Comprehensive test runner for DSA-110 pipeline.
    
    Orchestrates end-to-end testing, science validation,
    and automation testing.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the test runner.
        
        Args:
            config: Test configuration
        """
        self.config = config or self._get_default_config()
        self.test_results = []
        self.start_time = time.time()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default test configuration."""
        return {
            'test_data_dir': '/tmp/dsa110_test_data',
            'output_dir': '/tmp/dsa110_test_output',
            'run_e2e_tests': True,
            'run_science_validation': True,
            'run_automation_tests': True,
            'run_performance_tests': True,
            'cleanup_after_tests': True,
            'generate_reports': True,
            'report_format': 'markdown'  # 'markdown', 'json', 'html'
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all configured tests.
        
        Returns:
            Dictionary with test results and summary
        """
        logger.info("Starting comprehensive DSA-110 pipeline testing")
        
        test_summary = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_results': [],
            'overall_success': False,
            'duration': 0.0
        }
        
        try:
            # 1. End-to-End Pipeline Tests
            if self.config.get('run_e2e_tests', True):
                logger.info("Running end-to-end pipeline tests...")
                e2e_result = await self._run_e2e_tests()
                test_summary['test_results'].append(e2e_result)
                test_summary['total_tests'] += 1
                if e2e_result['success']:
                    test_summary['passed_tests'] += 1
                else:
                    test_summary['failed_tests'] += 1
            
            # 2. Science Validation Tests
            if self.config.get('run_science_validation', True):
                logger.info("Running science validation tests...")
                science_result = await self._run_science_validation()
                test_summary['test_results'].append(science_result)
                test_summary['total_tests'] += 1
                if science_result['success']:
                    test_summary['passed_tests'] += 1
                else:
                    test_summary['failed_tests'] += 1
            
            # 3. Automation Tests
            if self.config.get('run_automation_tests', True):
                logger.info("Running automation tests...")
                automation_result = await self._run_automation_tests()
                test_summary['test_results'].append(automation_result)
                test_summary['total_tests'] += 1
                if automation_result['success']:
                    test_summary['passed_tests'] += 1
                else:
                    test_summary['failed_tests'] += 1
            
            # 4. Performance Tests
            if self.config.get('run_performance_tests', True):
                logger.info("Running performance tests...")
                performance_result = await self._run_performance_tests()
                test_summary['test_results'].append(performance_result)
                test_summary['total_tests'] += 1
                if performance_result['success']:
                    test_summary['passed_tests'] += 1
                else:
                    test_summary['failed_tests'] += 1
            
            # Calculate overall success
            test_summary['overall_success'] = test_summary['failed_tests'] == 0
            test_summary['duration'] = time.time() - self.start_time
            
            # Generate reports
            if self.config.get('generate_reports', True):
                await self._generate_reports(test_summary)
            
            # Cleanup
            if self.config.get('cleanup_after_tests', True):
                await self._cleanup_test_environment()
            
            logger.info(f"Testing completed - Success: {test_summary['overall_success']}")
            return test_summary
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            test_summary['overall_success'] = False
            test_summary['duration'] = time.time() - self.start_time
            return test_summary
    
    async def _run_e2e_tests(self) -> Dict[str, Any]:
        """Run end-to-end pipeline tests."""
        start_time = time.time()
        
        try:
            # Create test configuration
            test_config = TestConfig(
                test_data_dir=self.config['test_data_dir'],
                output_dir=self.config['output_dir']
            )
            
            # Initialize test framework
            framework = E2ETestFramework(test_config)
            
            # Run full pipeline test
            result = await framework.run_full_pipeline_test()
            
            # Run performance benchmark
            perf_result = await framework.run_performance_benchmark()
            
            # Combine results
            success = result.success and perf_result.success
            duration = time.time() - start_time
            
            return {
                'test_name': 'End-to-End Pipeline Tests',
                'success': success,
                'duration': duration,
                'details': {
                    'pipeline_test': {
                        'success': result.success,
                        'quality_metrics': result.quality_metrics,
                        'performance_metrics': result.performance_metrics
                    },
                    'performance_test': {
                        'success': perf_result.success,
                        'performance_metrics': perf_result.performance_metrics
                    }
                },
                'errors': result.errors + perf_result.errors,
                'warnings': result.warnings + perf_result.warnings
            }
            
        except Exception as e:
            return {
                'test_name': 'End-to-End Pipeline Tests',
                'success': False,
                'duration': time.time() - start_time,
                'details': {},
                'errors': [str(e)],
                'warnings': []
            }
    
    async def _run_science_validation(self) -> Dict[str, Any]:
        """Run science validation tests."""
        start_time = time.time()
        
        try:
            # Create validation criteria
            criteria = ValidationCriteria()
            validator = ScienceValidator(criteria)
            
            # Create mock test files for validation
            test_files = await self._create_mock_test_files()
            
            # Run validation tests
            validation_results = []
            
            for test_file in test_files:
                if test_file.endswith('.fits'):
                    # Image quality validation
                    result = validator.validate_image_quality(test_file)
                    validation_results.append(result)
                    
                    # Astrometric validation
                    result = validator.validate_astrometry(test_file)
                    validation_results.append(result)
                    
                    # Spectral quality validation
                    result = validator.validate_spectral_quality(test_file)
                    validation_results.append(result)
                    
                    # Mosaic quality validation
                    result = validator.validate_mosaic_quality(test_file)
                    validation_results.append(result)
            
            # Calculate overall success
            passed_tests = sum(1 for r in validation_results if r.passed)
            total_tests = len(validation_results)
            success = passed_tests == total_tests
            
            duration = time.time() - start_time
            
            return {
                'test_name': 'Science Validation Tests',
                'success': success,
                'duration': duration,
                'details': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': total_tests - passed_tests,
                    'validation_results': [
                        {
                            'test_name': r.test_name,
                            'passed': r.passed,
                            'score': r.score,
                            'issues': r.issues,
                            'recommendations': r.recommendations
                        }
                        for r in validation_results
                    ]
                },
                'errors': [r.issues for r in validation_results if not r.passed],
                'warnings': [r.recommendations for r in validation_results if r.recommendations]
            }
            
        except Exception as e:
            return {
                'test_name': 'Science Validation Tests',
                'success': False,
                'duration': time.time() - start_time,
                'details': {},
                'errors': [str(e)],
                'warnings': []
            }
    
    async def _run_automation_tests(self) -> Dict[str, Any]:
        """Run automation system tests."""
        start_time = time.time()
        
        try:
            # Create automation configuration
            automation_config = AutomationConfig(
                schedule_type="manual",
                max_concurrent_jobs=1,
                job_timeout=300  # 5 minutes for testing
            )
            
            # Initialize automation system
            automation = PipelineAutomation(automation_config)
            
            # Test automation system startup
            await automation.start_automation()
            
            # Test job execution
            job_status = await automation._trigger_pipeline_execution()
            
            # Wait for job completion
            max_wait_time = 300  # 5 minutes
            wait_time = 0
            while automation.active_jobs and wait_time < max_wait_time:
                await asyncio.sleep(5)
                wait_time += 5
            
            # Test automation system shutdown
            await automation.stop_automation()
            
            # Get job statistics
            stats = automation.get_job_statistics()
            
            # Calculate success
            success = stats['total_jobs'] > 0 and stats['success_rate'] > 0
            duration = time.time() - start_time
            
            return {
                'test_name': 'Automation System Tests',
                'success': success,
                'duration': duration,
                'details': {
                    'job_statistics': stats,
                    'automation_config': automation_config.__dict__
                },
                'errors': [],
                'warnings': []
            }
            
        except Exception as e:
            return {
                'test_name': 'Automation System Tests',
                'success': False,
                'duration': time.time() - start_time,
                'details': {},
                'errors': [str(e)],
                'warnings': []
            }
    
    async def _run_performance_tests(self) -> Dict[str, Any]:
        """Run performance benchmarking tests."""
        start_time = time.time()
        
        try:
            # Performance test configuration
            test_config = TestConfig(
                test_data_dir=self.config['test_data_dir'],
                output_dir=self.config['output_dir']
            )
            
            # Initialize test framework
            framework = E2ETestFramework(test_config)
            
            # Run performance benchmark
            result = await framework.run_performance_benchmark()
            
            # Additional performance tests
            memory_usage = framework.data_ingestion.get_memory_usage()
            cpu_usage = self._get_cpu_usage()
            
            # Calculate success based on performance thresholds
            success = (
                result.success and
                memory_usage['memory_mb'] < 8000 and  # 8 GB limit
                cpu_usage < 80.0  # 80% CPU limit
            )
            
            duration = time.time() - start_time
            
            return {
                'test_name': 'Performance Tests',
                'success': success,
                'duration': duration,
                'details': {
                    'performance_metrics': result.performance_metrics,
                    'memory_usage': memory_usage,
                    'cpu_usage': cpu_usage
                },
                'errors': result.errors if not success else [],
                'warnings': result.warnings
            }
            
        except Exception as e:
            return {
                'test_name': 'Performance Tests',
                'success': False,
                'duration': time.time() - start_time,
                'details': {},
                'errors': [str(e)],
                'warnings': []
            }
    
    async def _create_mock_test_files(self) -> List[str]:
        """Create mock test files for validation."""
        test_files = []
        
        # Create mock FITS file
        fits_file = os.path.join(self.config['test_data_dir'], 'test_image.fits')
        os.makedirs(os.path.dirname(fits_file), exist_ok=True)
        
        # Create a simple FITS file
        import astropy.io.fits as fits
        import numpy as np
        
        # Create mock image data
        data = np.random.normal(0, 0.01, (100, 100))
        data[50, 50] = 1.0  # Add a bright source
        
        # Create header with WCS
        header = fits.Header()
        header['CTYPE1'] = 'RA---SIN'
        header['CTYPE2'] = 'DEC--SIN'
        header['CRVAL1'] = 180.0
        header['CRVAL2'] = 37.0
        header['CRPIX1'] = 50.0
        header['CRPIX2'] = 50.0
        header['CDELT1'] = -0.001
        header['CDELT2'] = 0.001
        header['CUNIT1'] = 'deg'
        header['CUNIT2'] = 'deg'
        
        # Write FITS file
        hdu = fits.PrimaryHDU(data, header)
        hdu.writeto(fits_file, overwrite=True)
        test_files.append(fits_file)
        
        return test_files
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            import psutil
            return psutil.cpu_percent()
        except:
            return 0.0
    
    async def _generate_reports(self, test_summary: Dict[str, Any]):
        """Generate test reports."""
        try:
            # Generate markdown report
            if self.config.get('report_format') == 'markdown':
                report = self._generate_markdown_report(test_summary)
                report_path = os.path.join(self.config['output_dir'], 'test_report.md')
                with open(report_path, 'w') as f:
                    f.write(report)
                logger.info(f"Markdown report saved to: {report_path}")
            
            # Generate JSON report
            elif self.config.get('report_format') == 'json':
                report_path = os.path.join(self.config['output_dir'], 'test_report.json')
                with open(report_path, 'w') as f:
                    import json
                    json.dump(test_summary, f, indent=2, default=str)
                logger.info(f"JSON report saved to: {report_path}")
            
            # Generate HTML report
            elif self.config.get('report_format') == 'html':
                report = self._generate_html_report(test_summary)
                report_path = os.path.join(self.config['output_dir'], 'test_report.html')
                with open(report_path, 'w') as f:
                    f.write(report)
                logger.info(f"HTML report saved to: {report_path}")
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
    
    def _generate_markdown_report(self, test_summary: Dict[str, Any]) -> str:
        """Generate markdown test report."""
        report = []
        report.append("# DSA-110 Pipeline Test Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        report.append("## Summary")
        report.append(f"- **Total Tests**: {test_summary['total_tests']}")
        report.append(f"- **Passed**: {test_summary['passed_tests']}")
        report.append(f"- **Failed**: {test_summary['failed_tests']}")
        report.append(f"- **Success Rate**: {test_summary['passed_tests'] / test_summary['total_tests'] * 100:.1f}%")
        report.append(f"- **Duration**: {test_summary['duration']:.2f}s")
        report.append(f"- **Overall Success**: {'✅ PASS' if test_summary['overall_success'] else '❌ FAIL'}")
        report.append("")
        
        # Individual test results
        report.append("## Test Results")
        for result in test_summary['test_results']:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            report.append(f"### {result['test_name']} - {status}")
            report.append(f"- **Duration**: {result['duration']:.2f}s")
            
            if result.get('details'):
                report.append("- **Details**:")
                for key, value in result['details'].items():
                    if isinstance(value, dict):
                        report.append(f"  - **{key}**:")
                        for sub_key, sub_value in value.items():
                            report.append(f"    - {sub_key}: {sub_value}")
                    else:
                        report.append(f"  - **{key}**: {value}")
            
            if result.get('errors'):
                report.append("- **Errors**:")
                for error in result['errors']:
                    report.append(f"  - {error}")
            
            if result.get('warnings'):
                report.append("- **Warnings**:")
                for warning in result['warnings']:
                    report.append(f"  - {warning}")
            
            report.append("")
        
        return "\n".join(report)
    
    def _generate_html_report(self, test_summary: Dict[str, Any]) -> str:
        """Generate HTML test report."""
        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html>")
        html.append("<head>")
        html.append("<title>DSA-110 Pipeline Test Report</title>")
        html.append("<style>")
        html.append("body { font-family: Arial, sans-serif; margin: 20px; }")
        html.append(".pass { color: green; }")
        html.append(".fail { color: red; }")
        html.append(".summary { background-color: #f0f0f0; padding: 15px; border-radius: 5px; }")
        html.append(".test-result { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }")
        html.append("</style>")
        html.append("</head>")
        html.append("<body>")
        
        html.append("<h1>DSA-110 Pipeline Test Report</h1>")
        html.append(f"<p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>")
        
        # Summary
        html.append("<div class='summary'>")
        html.append("<h2>Summary</h2>")
        html.append(f"<p><strong>Total Tests:</strong> {test_summary['total_tests']}</p>")
        html.append(f"<p><strong>Passed:</strong> {test_summary['passed_tests']}</p>")
        html.append(f"<p><strong>Failed:</strong> {test_summary['failed_tests']}</p>")
        html.append(f"<p><strong>Success Rate:</strong> {test_summary['passed_tests'] / test_summary['total_tests'] * 100:.1f}%</p>")
        html.append(f"<p><strong>Duration:</strong> {test_summary['duration']:.2f}s</p>")
        html.append(f"<p><strong>Overall Success:</strong> <span class={'pass' if test_summary['overall_success'] else 'fail'}>{'✅ PASS' if test_summary['overall_success'] else '❌ FAIL'}</span></p>")
        html.append("</div>")
        
        # Test results
        html.append("<h2>Test Results</h2>")
        for result in test_summary['test_results']:
            status_class = "pass" if result['success'] else "fail"
            status_text = "✅ PASS" if result['success'] else "❌ FAIL"
            
            html.append(f"<div class='test-result'>")
            html.append(f"<h3 class='{status_class}'>{result['test_name']} - {status_text}</h3>")
            html.append(f"<p><strong>Duration:</strong> {result['duration']:.2f}s</p>")
            
            if result.get('details'):
                html.append("<h4>Details</h4>")
                html.append("<ul>")
                for key, value in result['details'].items():
                    if isinstance(value, dict):
                        html.append(f"<li><strong>{key}:</strong>")
                        html.append("<ul>")
                        for sub_key, sub_value in value.items():
                            html.append(f"<li>{sub_key}: {sub_value}</li>")
                        html.append("</ul></li>")
                    else:
                        html.append(f"<li><strong>{key}:</strong> {value}</li>")
                html.append("</ul>")
            
            if result.get('errors'):
                html.append("<h4>Errors</h4>")
                html.append("<ul>")
                for error in result['errors']:
                    html.append(f"<li class='fail'>{error}</li>")
                html.append("</ul>")
            
            if result.get('warnings'):
                html.append("<h4>Warnings</h4>")
                html.append("<ul>")
                for warning in result['warnings']:
                    html.append(f"<li>{warning}</li>")
                html.append("</ul>")
            
            html.append("</div>")
        
        html.append("</body>")
        html.append("</html>")
        
        return "\n".join(html)
    
    async def _cleanup_test_environment(self):
        """Cleanup test environment."""
        try:
            import shutil
            
            # Cleanup test directories
            if os.path.exists(self.config['test_data_dir']):
                shutil.rmtree(self.config['test_data_dir'])
            
            if os.path.exists(self.config['output_dir']):
                shutil.rmtree(self.config['output_dir'])
            
            logger.info("Test environment cleanup completed")
            
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")


async def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description='Run DSA-110 Pipeline Tests')
    parser.add_argument('--test-data-dir', default='/tmp/dsa110_test_data',
                       help='Directory for test data')
    parser.add_argument('--output-dir', default='/tmp/dsa110_test_output',
                       help='Directory for test output')
    parser.add_argument('--report-format', choices=['markdown', 'json', 'html'],
                       default='markdown', help='Report format')
    parser.add_argument('--no-cleanup', action='store_true',
                       help='Do not cleanup test environment')
    parser.add_argument('--skip-e2e', action='store_true',
                       help='Skip end-to-end tests')
    parser.add_argument('--skip-science', action='store_true',
                       help='Skip science validation tests')
    parser.add_argument('--skip-automation', action='store_true',
                       help='Skip automation tests')
    parser.add_argument('--skip-performance', action='store_true',
                       help='Skip performance tests')
    
    args = parser.parse_args()
    
    # Create test configuration
    config = {
        'test_data_dir': args.test_data_dir,
        'output_dir': args.output_dir,
        'report_format': args.report_format,
        'cleanup_after_tests': not args.no_cleanup,
        'run_e2e_tests': not args.skip_e2e,
        'run_science_validation': not args.skip_science,
        'run_automation_tests': not args.skip_automation,
        'run_performance_tests': not args.skip_performance
    }
    
    # Create and run test runner
    runner = TestRunner(config)
    results = await runner.run_all_tests()
    
    # Print summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed_tests']}")
    print(f"Failed: {results['failed_tests']}")
    print(f"Success Rate: {results['passed_tests'] / results['total_tests'] * 100:.1f}%")
    print(f"Duration: {results['duration']:.2f}s")
    print(f"Overall Success: {'✅ PASS' if results['overall_success'] else '❌ FAIL'}")
    print("="*50)
    
    # Exit with appropriate code
    sys.exit(0 if results['overall_success'] else 1)


if __name__ == "__main__":
    asyncio.run(main())
