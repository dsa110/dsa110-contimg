"""Integration tests for CrossMatchStage."""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile
import sqlite3

from dsa110_contimg.pipeline.config import PipelineConfig, PathsConfig, CrossMatchConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages_impl import CrossMatchStage
from dsa110_contimg.database.products import ensure_products_db


@pytest.fixture
def temp_state_dir():
    """Create temporary state directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_state_dir):
    """Create test pipeline configuration."""
    paths = PathsConfig(
        input_dir=temp_state_dir / "input",
        output_dir=temp_state_dir / "output",
        state_dir=temp_state_dir / "state",
    )
    config = PipelineConfig(
        paths=paths,
        crossmatch=CrossMatchConfig(
            enabled=True,
            catalog_types=["nvss"],
            radius_arcsec=10.0,
            method="basic",
            store_in_database=True,
        ),
    )
    return config


@pytest.fixture
def test_context(test_config):
    """Create test pipeline context."""
    return PipelineContext(config=test_config)


@pytest.fixture
def mock_detected_sources():
    """Create mock detected sources DataFrame."""
    return pd.DataFrame(
        {
            "ra_deg": [10.0, 20.0, 30.0],
            "dec_deg": [0.0, 5.0, 10.0],
            "flux_jy": [1.0, 2.0, 3.0],
            "flux_err_jy": [0.1, 0.2, 0.3],
            "snr": [10.0, 10.0, 10.0],
        }
    )


@pytest.fixture
def mock_catalog_sources():
    """Create mock catalog sources DataFrame."""
    return pd.DataFrame(
        {
            "ra_deg": [10.1, 20.1, 30.1],
            "dec_deg": [0.1, 5.1, 10.1],
            "flux_mjy": [1000.0, 2000.0, 3000.0],
            "flux_err_mjy": [100.0, 200.0, 300.0],
        }
    )


class TestCrossMatchStage:
    """Test CrossMatchStage integration."""

    def test_stage_validation_enabled(self, test_config, test_context):
        """Test stage validation when enabled."""
        stage = CrossMatchStage(test_config)
        test_context = test_context.with_output(
            "detected_sources",
            pd.DataFrame({"ra_deg": [10.0], "dec_deg": [0.0]}),
        )

        valid, msg = stage.validate(test_context)
        assert valid is True

    def test_stage_validation_disabled(self, test_config, test_context):
        """Test stage validation when disabled."""
        test_config.crossmatch.enabled = False
        stage = CrossMatchStage(test_config)

        valid, msg = stage.validate(test_context)
        assert valid is False
        assert "disabled" in msg.lower()

    def test_stage_validation_no_sources(self, test_config, test_context):
        """Test stage validation when no sources available."""
        stage = CrossMatchStage(test_config)

        valid, msg = stage.validate(test_context)
        assert valid is False
        assert "no detected sources" in msg.lower()

    def test_stage_execution_with_mock_sources(
        self, test_config, test_context, mock_detected_sources, temp_state_dir
    ):
        """Test stage execution with mock sources."""
        # Mock catalog query by creating a simple catalog database
        from dsa110_contimg.catalog.query import resolve_catalog_path
        import shutil

        # Create mock catalog database
        catalog_dir = temp_state_dir / "catalogs"
        catalog_dir.mkdir(parents=True, exist_ok=True)
        catalog_db = catalog_dir / "nvss_strip_dec0.0.db"

        conn = sqlite3.connect(catalog_db)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE sources (
                ra_deg REAL,
                dec_deg REAL,
                flux_mjy REAL,
                flux_err_mjy REAL
            )
        """
        )
        cursor.executemany(
            "INSERT INTO sources VALUES (?, ?, ?, ?)",
            [
                (10.1, 0.1, 1000.0, 100.0),
                (20.1, 5.1, 2000.0, 200.0),
                (30.1, 10.1, 3000.0, 300.0),
            ],
        )
        conn.commit()
        conn.close()

        # Update config to use mock catalog directory
        # Note: This is a simplified test - in practice, catalog paths are resolved differently

        stage = CrossMatchStage(test_config)
        test_context = test_context.with_output(
            "detected_sources", mock_detected_sources
        )

        # Mock the catalog query to return our mock sources
        import dsa110_contimg.catalog.query as query_module

        original_query = query_module.query_sources

        def mock_query_sources(*args, **kwargs):
            # Use sources very close to detected sources (within 10 arcsec = ~0.0028 degrees)
            return pd.DataFrame(
                {
                    "ra_deg": [10.0 + 0.001, 20.0 + 0.001, 30.0 + 0.001],
                    "dec_deg": [0.0 + 0.001, 5.0 + 0.001, 10.0 + 0.001],
                    "flux_mjy": [1000.0, 2000.0, 3000.0],
                }
            )

        query_module.query_sources = mock_query_sources

        try:
            result_context = stage.execute(test_context)

            assert "crossmatch_results" in result_context.outputs
            results = result_context.outputs["crossmatch_results"]

            assert results["n_catalogs"] > 0
            assert "matches" in results
            assert "offsets" in results

        finally:
            query_module.query_sources = original_query

    def test_stage_execution_no_matches(
        self, test_config, test_context, temp_state_dir
    ):
        """Test stage execution when no matches found."""
        # Create detected sources far from catalog
        detected_sources = pd.DataFrame(
            {
                "ra_deg": [100.0, 200.0],
                "dec_deg": [50.0, 60.0],
                "flux_jy": [1.0, 2.0],
            }
        )

        stage = CrossMatchStage(test_config)
        test_context = test_context.with_output("detected_sources", detected_sources)

        # Mock catalog query to return sources far away
        import dsa110_contimg.catalog.query as query_module

        original_query = query_module.query_sources

        def mock_query_sources(*args, **kwargs):
            return pd.DataFrame(
                {
                    "ra_deg": [10.0, 20.0],
                    "dec_deg": [0.0, 5.0],
                    "flux_mjy": [1000.0, 2000.0],
                }
            )

        query_module.query_sources = mock_query_sources

        try:
            result_context = stage.execute(test_context)

            # Should still complete but with no matches
            assert "crossmatch_results" in result_context.outputs
            results = result_context.outputs["crossmatch_results"]
            assert results["n_catalogs"] == 0 or len(results.get("matches", {})) == 0

        finally:
            query_module.query_sources = original_query

    def test_database_storage(
        self, test_config, test_context, mock_detected_sources, temp_state_dir
    ):
        """Test that cross-matches are stored in database."""
        # Ensure products database exists and schema is evolved
        products_db = test_config.paths.products_db
        ensure_products_db(products_db)
        # Run schema evolution to create cross_matches table
        from dsa110_contimg.database.schema_evolution import evolve_products_schema

        evolve_products_schema(products_db, verbose=False)

        # Create mock matches
        matches = pd.DataFrame(
            {
                "detected_idx": [0, 1],
                "catalog_idx": [0, 1],
                "separation_arcsec": [5.0, 6.0],
                "dra_arcsec": [1.0, 2.0],
                "ddec_arcsec": [0.5, 1.0],
                "detected_flux": [1.0, 2.0],
                "catalog_flux": [1.1, 2.1],
                "flux_ratio": [0.91, 0.95],
            }
        )

        stage = CrossMatchStage(test_config)
        stage._store_matches_in_database(
            matches=matches,
            catalog_type="nvss",
            method="basic",
            context=test_context,
        )

        # Verify matches were stored
        conn = sqlite3.connect(products_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cross_matches")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 2

    def test_match_quality_classification(self, test_config, temp_state_dir):
        """Test match quality classification."""
        # Ensure products database exists and schema is evolved
        products_db = test_config.paths.products_db
        ensure_products_db(products_db)
        from dsa110_contimg.database.schema_evolution import evolve_products_schema

        evolve_products_schema(products_db, verbose=False)

        stage = CrossMatchStage(test_config)

        # Test excellent match
        matches_excellent = pd.DataFrame(
            {
                "detected_idx": [0],
                "catalog_idx": [0],
                "separation_arcsec": [1.0],
            }
        )
        stage._store_matches_in_database(
            matches=matches_excellent,
            catalog_type="nvss",
            method="basic",
            context=PipelineContext(config=test_config),
        )

        # Verify quality was set
        conn = sqlite3.connect(test_config.paths.products_db)
        cursor = conn.cursor()
        cursor.execute("SELECT match_quality FROM cross_matches LIMIT 1")
        quality = cursor.fetchone()[0]
        conn.close()

        assert quality == "excellent"

    def test_master_catalog_id_storage(
        self, test_config, test_context, mock_detected_sources, temp_state_dir
    ):
        """Test that master catalog IDs are stored in database."""
        from dsa110_contimg.database.products import ensure_products_db
        from dsa110_contimg.database.schema_evolution import evolve_products_schema
        import sqlite3

        products_db = test_config.paths.products_db
        ensure_products_db(products_db)
        evolve_products_schema(products_db, verbose=False)

        # Create matches with master catalog IDs
        matches = pd.DataFrame(
            {
                "detected_idx": [0, 1],
                "catalog_idx": [0, 1],
                "separation_arcsec": [5.0, 6.0],
                "dra_arcsec": [1.0, 2.0],
                "ddec_arcsec": [0.5, 1.0],
                "detected_flux": [1.0, 2.0],
                "catalog_flux": [1.1, 2.1],
                "flux_ratio": [0.91, 0.95],
                "catalog_source_id": ["nvss_1", "nvss_2"],
            }
        )

        master_catalog_ids = {
            "nvss:nvss_1": "nvss:nvss_1",
            "nvss:nvss_2": "nvss:nvss_2",
        }

        stage = CrossMatchStage(test_config)
        stage._store_matches_in_database(
            matches=matches,
            catalog_type="nvss",
            method="basic",
            context=test_context,
            master_catalog_ids=master_catalog_ids,
        )

        # Verify master catalog IDs were stored
        conn = sqlite3.connect(products_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT master_catalog_id FROM cross_matches WHERE catalog_source_id = 'nvss_1'"
        )
        master_id = cursor.fetchone()[0]
        conn.close()

        assert master_id == "nvss:nvss_1"

    def test_unique_constraint(
        self, test_config, test_context, mock_detected_sources, temp_state_dir
    ):
        """Test that UNIQUE constraint prevents duplicate entries."""
        from dsa110_contimg.database.products import ensure_products_db
        from dsa110_contimg.database.schema_evolution import evolve_products_schema
        import sqlite3

        products_db = test_config.paths.products_db
        ensure_products_db(products_db)
        evolve_products_schema(products_db, verbose=False)

        # Create matches
        matches = pd.DataFrame(
            {
                "detected_idx": [0],
                "catalog_idx": [0],
                "separation_arcsec": [5.0],
                "dra_arcsec": [1.0],
                "ddec_arcsec": [0.5],
                "catalog_source_id": ["nvss_1"],
            }
        )

        stage = CrossMatchStage(test_config)

        # Store first match
        stage._store_matches_in_database(
            matches=matches,
            catalog_type="nvss",
            method="basic",
            context=test_context,
        )

        # Store same match again (should replace, not duplicate)
        stage._store_matches_in_database(
            matches=matches,
            catalog_type="nvss",
            method="basic",
            context=test_context,
        )

        # Verify only one entry exists
        conn = sqlite3.connect(products_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cross_matches WHERE catalog_type = 'nvss'")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1  # Should be 1, not 2 (UNIQUE constraint)
