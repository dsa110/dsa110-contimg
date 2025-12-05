"""Initial schema baseline

Revision ID: 001
Revises:
Create Date: 2025-11-30

This migration documents the existing database schema as of the
initial Alembic integration. No actual changes are made - this
serves as a baseline for future migrations.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Document the existing schema - no changes needed.

    The existing tables are:

    - images: Stores image metadata (path, ms_path, type, beam info, etc.)
    - ms_index: Measurement Set processing status and metadata
    - photometry: Source photometry measurements
    - sources: Source catalog entries
    - batch_jobs: Batch job tracking
    - batch_job_items: Individual items within batch jobs
    - ese_events: Extreme Scattering Event detections
    - variability_metrics: Source variability statistics
    """
    # Check if tables exist, create if not (for new databases)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "images" not in existing_tables:
        op.create_table(
            "images",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("path", sa.Text(), nullable=False, unique=True),
            sa.Column("ms_path", sa.Text(), nullable=False),
            sa.Column("created_at", sa.Float(), nullable=False),
            sa.Column("type", sa.Text(), nullable=False),
            sa.Column("beam_major_arcsec", sa.Float()),
            sa.Column("beam_minor_arcsec", sa.Float()),
            sa.Column("beam_pa_deg", sa.Float()),
            sa.Column("noise_jy", sa.Float()),
            sa.Column("dynamic_range", sa.Float()),
            sa.Column("pbcor", sa.Integer(), default=0),
            sa.Column("format", sa.Text(), default="fits"),
            sa.Column("field_name", sa.Text()),
            sa.Column("center_ra_deg", sa.Float()),
            sa.Column("center_dec_deg", sa.Float()),
            sa.Column("imsize_x", sa.Integer()),
            sa.Column("imsize_y", sa.Integer()),
            sa.Column("cellsize_arcsec", sa.Float()),
            sa.Column("freq_ghz", sa.Float()),
            sa.Column("bandwidth_mhz", sa.Float()),
            sa.Column("integration_sec", sa.Float()),
        )
        op.create_index("idx_images_ms_path", "images", ["ms_path"])
        op.create_index("idx_images_created_at", "images", ["created_at"])

    if "ms_index" not in existing_tables:
        op.create_table(
            "ms_index",
            sa.Column("path", sa.Text(), primary_key=True),
            sa.Column("start_mjd", sa.Float()),
            sa.Column("end_mjd", sa.Float()),
            sa.Column("mid_mjd", sa.Float()),
            sa.Column("processed_at", sa.Float()),
            sa.Column("status", sa.Text()),
            sa.Column("stage", sa.Text()),
            sa.Column("stage_updated_at", sa.Float()),
            sa.Column("cal_applied", sa.Integer(), default=0),
            sa.Column("imagename", sa.Text()),
            sa.Column("ra_deg", sa.Float()),
            sa.Column("dec_deg", sa.Float()),
            sa.Column("field_name", sa.Text()),
            sa.Column("pointing_ra_deg", sa.Float()),
            sa.Column("pointing_dec_deg", sa.Float()),
        )
        op.create_index("idx_ms_index_stage", "ms_index", ["stage"])
        op.create_index("idx_ms_index_mid_mjd", "ms_index", ["mid_mjd"])

    if "photometry" not in existing_tables:
        op.create_table(
            "photometry",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source_id", sa.Text(), nullable=False),
            sa.Column("image_path", sa.Text(), nullable=False),
            sa.Column("ra_deg", sa.Float(), nullable=False),
            sa.Column("dec_deg", sa.Float(), nullable=False),
            sa.Column("mjd", sa.Float()),
            sa.Column("flux_jy", sa.Float()),
            sa.Column("flux_err_jy", sa.Float()),
            sa.Column("peak_jyb", sa.Float()),
            sa.Column("peak_err_jyb", sa.Float()),
            sa.Column("snr", sa.Float()),
            sa.Column("local_rms", sa.Float()),
        )
        op.create_index("idx_photometry_source_id", "photometry", ["source_id"])
        op.create_index("idx_photometry_mjd", "photometry", ["mjd"])

    if "batch_jobs" not in existing_tables:
        op.create_table(
            "batch_jobs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("type", sa.Text(), nullable=False),
            sa.Column("created_at", sa.Float(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("total_items", sa.Integer(), nullable=False),
            sa.Column("completed_items", sa.Integer(), default=0),
            sa.Column("failed_items", sa.Integer(), default=0),
            sa.Column("params", sa.Text()),
        )

    if "batch_job_items" not in existing_tables:
        op.create_table(
            "batch_job_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("batch_id", sa.Integer(), nullable=False),
            sa.Column("ms_path", sa.Text(), nullable=False),
            sa.Column("job_id", sa.Integer()),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("error", sa.Text()),
            sa.Column("started_at", sa.Float()),
            sa.Column("completed_at", sa.Float()),
            sa.Column("data_id", sa.Text()),
            sa.ForeignKeyConstraint(["batch_id"], ["batch_jobs.id"]),
        )
        op.create_index("idx_batch_job_items_batch_id", "batch_job_items", ["batch_id"])


def downgrade():
    """
    Remove tables created by this migration.

    Note: This should only be used on fresh databases, not production.
    """
    op.drop_table("batch_job_items")
    op.drop_table("batch_jobs")
    op.drop_table("photometry")
    op.drop_table("ms_index")
    op.drop_table("images")
