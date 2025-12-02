import numpy as np
import pandas as pd
import pytest

from dsa110_contimg.simulation.source_models import (
    evaluate_flux_density,
    multi_source_visibility,
)
from dsa110_contimg.simulation.source_selection import (
    CatalogRegion,
    SourceSelector,
    SyntheticSource,
    summarize_sources,
)


def _synthetic_df():
    return pd.DataFrame(
        [
            {
                "source_id": "J0000+0000",
                "ra_deg": 10.0,
                "dec_deg": 20.0,
                "flux_mjy": 250.0,
                "maj_arcsec": 5.0,
                "min_arcsec": 3.0,
                "pa_deg": 45.0,
                "spectral_index": -0.7,
                "catalog_name": "NVSS",
            },
            {
                "source_id": "J0001+0001",
                "ra_deg": 10.5,
                "dec_deg": 20.5,
                "flux_mjy": 100.0,
                "maj_arcsec": np.nan,
                "min_arcsec": np.nan,
                "pa_deg": np.nan,
                "spectral_index": np.nan,
            },
        ]
    )


def test_source_selector_converts_dataframe(monkeypatch):
    """Ensure SourceSelector converts catalog rows into SyntheticSource objects."""

    def fake_query(**kwargs):
        return _synthetic_df()

    monkeypatch.setattr(
        "dsa110_contimg.simulation.source_selection.query_sources", fake_query
    )

    region = CatalogRegion(ra_deg=10.0, dec_deg=20.0, radius_deg=1.0)
    selector = SourceSelector(region, "nvss")
    sources = selector.select_sources()

    assert len(sources) == 2

    first = sources[0]
    assert first.source_id == "J0000+0000"
    assert first.flux_ref_jy == pytest.approx(0.25)  # mJy -> Jy
    assert first.reference_freq_hz == pytest.approx(1.4e9)
    assert first.major_axis_arcsec == 5.0
    assert first.minor_axis_arcsec == 3.0
    assert first.position_angle_deg == 45.0
    assert first.spectral_index == -0.7
    assert "catalog_name" in first.metadata


def test_summarize_sources_returns_stats():
    sources = [
        SyntheticSource(
            source_id="a",
            ra_deg=0,
            dec_deg=0,
            flux_ref_jy=1.0,
            reference_freq_hz=1.0,
        ),
        SyntheticSource(
            source_id="b",
            ra_deg=0,
            dec_deg=0,
            flux_ref_jy=0.5,
            reference_freq_hz=1.0,
        ),
    ]
    summary = summarize_sources(sources)
    assert summary["count"] == 2
    assert summary["total_flux_jy"] == pytest.approx(1.5)
    assert summary["brightest_flux_jy"] == pytest.approx(1.0)
    assert summary["faintest_flux_jy"] == pytest.approx(0.5)


def test_evaluate_flux_density_with_spectral_index():
    source = SyntheticSource(
        source_id="c",
        ra_deg=0,
        dec_deg=0,
        flux_ref_jy=1.0,
        reference_freq_hz=1.0e9,
        spectral_index=-0.5,
    )
    freqs = np.array([1.0e9, 4.0e9])
    flux = evaluate_flux_density(source, freqs)
    assert flux[0] == pytest.approx(1.0)
    # (4 GHz / 1 GHz)^-0.5 = 0.5
    assert flux[1] == pytest.approx(0.5, rel=1e-6)


def test_multi_source_visibility_accumulates_flux():
    sources = [
        SyntheticSource(
            source_id="d",
            ra_deg=0.0,
            dec_deg=0.0,
            flux_ref_jy=1.0,
            reference_freq_hz=1.0e9,
        ),
        SyntheticSource(
            source_id="e",
            ra_deg=0.0,
            dec_deg=0.0,
            flux_ref_jy=0.5,
            reference_freq_hz=1.0e9,
        ),
    ]
    uvw_m = np.zeros((2, 3), dtype=float)  # two baseline-time entries, zero spacing
    freq = np.array([1.0e9], dtype=float)
    vis = multi_source_visibility(sources, uvw_m, freq, 0.0, 0.0, npols=2)

    assert vis.shape == (2, 1, 1, 2)
    # Both sources at phase center -> pure real flux. Split equally across pols.
    expected = (1.0 + 0.5) / 2.0
    assert np.allclose(vis[..., 0].real, expected)
    assert np.allclose(vis[..., 1].real, expected)
    assert np.all(vis.imag == 0)
