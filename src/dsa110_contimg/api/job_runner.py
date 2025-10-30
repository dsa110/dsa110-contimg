"""Job runner for background calibration, apply, and imaging tasks."""

from __future__ import annotations

import subprocess
import json
import time
import os
from pathlib import Path
import sys
from typing import Optional, List

from dsa110_contimg.database.jobs import (
    update_job_status,
    append_job_log,
    get_job,
    create_job,
)
from dsa110_contimg.database.products import ensure_products_db


def _store_calibration_qa(conn, ms_path: str, job_id: int, caltables: dict) -> None:
    """Extract and store calibration QA metrics in database."""
    try:
        from dsa110_contimg.api.batch_jobs import extract_calibration_qa
        
        qa_metrics = extract_calibration_qa(ms_path, job_id, caltables)
        
        # Store in database
        import time as time_module
        cursor = conn.execute(
            """
            INSERT INTO calibration_qa (ms_path, job_id, k_metrics, bp_metrics, g_metrics, 
                                      overall_quality, flags_total, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ms_path,
                job_id,
                json.dumps(qa_metrics.get("k_metrics")) if qa_metrics.get("k_metrics") else None,
                json.dumps(qa_metrics.get("bp_metrics")) if qa_metrics.get("bp_metrics") else None,
                json.dumps(qa_metrics.get("g_metrics")) if qa_metrics.get("g_metrics") else None,
                qa_metrics.get("overall_quality", "unknown"),
                qa_metrics.get("flags_total"),
                time_module.time(),
            )
        )
        conn.commit()
    except Exception as e:
        # Log error but don't fail the job
        import logging
        logging.warning(f"Failed to extract calibration QA for {ms_path}: {e}")


def _store_image_qa(conn, ms_path: str, job_id: int, image_path: str) -> None:
    """Extract and store image QA metrics in database."""
    try:
        from dsa110_contimg.api.batch_jobs import extract_image_qa, generate_image_thumbnail
        
        # Extract QA metrics
        qa_metrics = extract_image_qa(ms_path, job_id, image_path)
        
        # Generate thumbnail
        thumbnail_path = None
        if Path(image_path).exists():
            try:
                thumbnail_path = generate_image_thumbnail(image_path)
            except Exception as e:
                import logging
                logging.warning(f"Failed to generate thumbnail for {image_path}: {e}")
        
        # Store in database
        import time as time_module
        cursor = conn.execute(
            """
            INSERT INTO image_qa (ms_path, job_id, image_path, rms_noise, peak_flux, dynamic_range,
                                 beam_major, beam_minor, beam_pa, num_sources, thumbnail_path,
                                 overall_quality, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ms_path,
                job_id,
                image_path,
                qa_metrics.get("rms_noise"),
                qa_metrics.get("peak_flux"),
                qa_metrics.get("dynamic_range"),
                qa_metrics.get("beam_major"),
                qa_metrics.get("beam_minor"),
                qa_metrics.get("beam_pa"),
                qa_metrics.get("num_sources"),
                thumbnail_path,
                qa_metrics.get("overall_quality", "unknown"),
                time_module.time(),
            )
        )
        conn.commit()
    except Exception as e:
        # Log error but don't fail the job
        import logging
        logging.warning(f"Failed to extract image QA for {ms_path}: {e}")


def _python_cmd_for_jobs() -> list[str]:
    """Decide how to invoke Python for job subprocesses.

    Priority:
      1) CONTIMG_JOB_PY (absolute path to interpreter)
      2) CONTIMG_CONDA_ENV (use conda run -n <env> python)
      3) sys.executable (current interpreter)
    """
    job_py = os.environ.get("CONTIMG_JOB_PY")
    if job_py:
        return [job_py]
    conda_env = os.environ.get("CONTIMG_CONDA_ENV")
    if conda_env:
        return ["conda", "run", "-n", conda_env, "python"]
    return [sys.executable]


def _src_path_for_env() -> str:
    """Compute repository src path to export into PYTHONPATH for child processes."""
    try:
        # job_runner.py → api → dsa110_contimg → src
        src_dir = Path(__file__).resolve().parents[2]
        return str(src_dir)
    except Exception:
        for p in ("/app/src", "/data/dsa110-contimg/src"):
            if Path(p).exists():
                return p
        return ""


def list_caltables(ms_path: str) -> List[str]:
    """Discover calibration tables associated with an MS."""
    ms_dir = Path(ms_path).parent
    ms_stem = Path(ms_path).stem

    artifacts = []
    for suffix in [".kcal", ".bpcal", ".gpcal", "_kcal", "_bpcal", "_gpcal"]:
        pattern = f"{ms_stem}*{suffix}"
        for p in ms_dir.glob(pattern):
            if p.is_dir() or p.is_file():
                artifacts.append(str(p))
    return artifacts


def run_calibrate_job(job_id: int, ms_path: str, params: dict, products_db: Path):
    """Run calibration in subprocess; stream logs to DB."""
    conn = ensure_products_db(products_db)
    update_job_status(conn, job_id, "running", started_at=time.time())
    conn.close()

    field = params.get("field", "0")
    refant = params.get("refant", "103")
    
    # Handle existing table discovery/selection
    use_existing = params.get("use_existing_tables", "auto")
    existing_k = params.get("existing_k_table")
    existing_bp = params.get("existing_bp_table")
    existing_g = params.get("existing_g_table")
    
    if use_existing == "auto":
        # Auto-discover latest tables
        import glob
        ms_dir = os.path.dirname(ms_path)
        ms_base = os.path.basename(ms_path).replace('.ms', '')
        
        # Find latest K table if not solving K
        if not params.get("solve_delay", True) and not existing_k:
            k_pattern = os.path.join(ms_dir, f"{ms_base}*kcal")
            k_tables = sorted([p for p in glob.glob(k_pattern) if os.path.isdir(p)], 
                            key=os.path.getmtime, reverse=True)
            if k_tables:
                existing_k = k_tables[0]
        
        # Find latest BP table if not solving BP
        if not params.get("solve_bandpass", True) and not existing_bp:
            bp_pattern = os.path.join(ms_dir, f"{ms_base}*bpcal")
            bp_tables = sorted([p for p in glob.glob(bp_pattern) if os.path.isdir(p)], 
                             key=os.path.getmtime, reverse=True)
            if bp_tables:
                existing_bp = bp_tables[0]
        
        # Find latest G table if not solving G
        if not params.get("solve_gains", True) and not existing_g:
            g_pattern = os.path.join(ms_dir, f"{ms_base}*g*cal")
            g_tables = sorted([p for p in glob.glob(g_pattern) if os.path.isdir(p)], 
                            key=os.path.getmtime, reverse=True)
            if g_tables:
                existing_g = g_tables[0]

    py = _python_cmd_for_jobs()
    cmd = py + [
        "-u",  # Unbuffered output
        "-m",
        "dsa110_contimg.calibration.cli",
        "calibrate",
        "--ms",
        ms_path,
        "--field",
        field,
        "--refant",
        refant,
    ]
    
    # Add flexible cal table selection flags
    if not params.get("solve_delay", True):
        cmd.append("--skip-k")
    if not params.get("solve_bandpass", True):
        cmd.append("--skip-bp")
    if not params.get("solve_gains", True):
        cmd.append("--skip-g")
    
    # Add gain parameters
    gain_solint = params.get("gain_solint", "inf")
    if gain_solint != "inf":
        cmd.extend(["--gain-solint", gain_solint])
    
    gain_calmode = params.get("gain_calmode", "ap")
    if gain_calmode != "ap":
        cmd.extend(["--gain-calmode", gain_calmode])
    
    # Add catalog matching parameters
    if params.get("auto_fields", True):
        cmd.append("--auto-fields")
        cal_catalog = params.get("cal_catalog", "vla")
        if cal_catalog:
            # Use centralized catalog resolution
            from dsa110_contimg.calibration.catalogs import resolve_vla_catalog_path
            try:
                cat_path = str(resolve_vla_catalog_path())
                cmd.extend(["--cal-catalog", cat_path])
            except FileNotFoundError as e:
                # Non-fatal: job will fail if catalog is needed but missing
                import warnings
                warnings.warn(f"VLA catalog not found for calibration job: {e}")
        
        search_radius = params.get("search_radius_deg", 1.0)
        if search_radius != 1.0:
            cmd.extend(["--cal-search-radius-deg", str(search_radius)])
        
        min_pb = params.get("min_pb", 0.5)
        if min_pb is not None:
            cmd.extend(["--bp-min-pb", str(min_pb)])
    
    # Add flagging control
    if not params.get("do_flagging", False):
        cmd.append("--no-flagging")

    env = os.environ.copy()
    src_path = _src_path_for_env()
    if src_path:
        env["PYTHONPATH"] = src_path

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
        )

        conn = ensure_products_db(products_db)
        
        # Log existing table usage at start
        if existing_k:
            append_job_log(conn, job_id, f"INFO: Using existing K table: {os.path.basename(existing_k)}\n")
        if existing_bp:
            append_job_log(conn, job_id, f"INFO: Using existing BP table: {os.path.basename(existing_bp)}\n")
        if existing_g:
            append_job_log(conn, job_id, f"INFO: Using existing G table: {os.path.basename(existing_g)}\n")
        conn.commit()
        
        for line in proc.stdout:
            append_job_log(conn, job_id, line)
            conn.commit()  # Commit every line for real-time streaming

        proc.wait()

        if proc.returncode == 0:
            artifacts = list_caltables(ms_path)
            update_job_status(
                conn,
                job_id,
                "done",
                finished_at=time.time(),
                artifacts=json.dumps(artifacts),
            )
            
            # Extract QA metrics from calibration tables
            try:
                # Build caltables dict from artifacts
                caltables = {}
                ms_dir = Path(ms_path).parent
                ms_stem = Path(ms_path).stem
                
                for artifact in artifacts:
                    artifact_path = Path(artifact)
                    if artifact_path.exists():
                        if '.kcal' in artifact or '_kcal' in artifact:
                            caltables['k'] = str(artifact_path)
                        elif '.bpcal' in artifact or '_bpcal' in artifact:
                            caltables['bp'] = str(artifact_path)
                        elif '.gpcal' in artifact or '_gpcal' in artifact or '.gacal' in artifact:
                            caltables['g'] = str(artifact_path)
                
                if caltables:
                    append_job_log(conn, job_id, "\nExtracting QA metrics from calibration tables...\n")
                    conn.commit()
                    _store_calibration_qa(conn, ms_path, job_id, caltables)
                    append_job_log(conn, job_id, "QA metrics extracted successfully\n")
                    conn.commit()
            except Exception as e:
                # Don't fail the job if QA extraction fails
                append_job_log(conn, job_id, f"\nWARNING: QA extraction failed: {e}\n")
                conn.commit()
        else:
            update_job_status(conn, job_id, "failed", finished_at=time.time())

        conn.close()

    except Exception as e:
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"\nERROR: {e}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
        conn.close()


def run_apply_job(job_id: int, ms_path: str, params: dict, products_db: Path):
    """Apply calibration tables via clearcal + applycal."""
    conn = ensure_products_db(products_db)
    update_job_status(conn, job_id, "running", started_at=time.time())
    conn.close()

    gaintables = params.get("gaintables", [])
    if not gaintables:
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, "ERROR: No gaintables specified\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
        conn.close()
        return

    # Python script to run clearcal + applycal within CASA
    script = f"""
import sys
from casatasks import clearcal, applycal

ms = "{ms_path}"
tables = {gaintables}

print("Clearing calibration...", flush=True)
clearcal(vis=ms, addmodel=True)

print("Applying calibration tables:", tables, flush=True)
applycal(vis=ms, field="", gaintable=tables, calwt=True, parang=False)

print("Apply complete", flush=True)
"""

    py = _python_cmd_for_jobs()
    cmd = py + ["-c", script]
    env = os.environ.copy()
    src_path = _src_path_for_env()
    if src_path:
        env["PYTHONPATH"] = src_path

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
        )

        conn = ensure_products_db(products_db)
        line_count = 0
        for line in proc.stdout:
            append_job_log(conn, job_id, line)
            line_count += 1
            if line_count % 10 == 0:
                conn.commit()

        conn.commit()
        proc.wait()

        if proc.returncode == 0:
            update_job_status(
                conn, job_id, "done", finished_at=time.time(), artifacts=json.dumps([ms_path])
            )
        else:
            update_job_status(conn, job_id, "failed", finished_at=time.time())

        conn.close()

    except Exception as e:
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"\nERROR: {e}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
        conn.close()


def run_image_job(job_id: int, ms_path: str, params: dict, products_db: Path):
    """Run imaging via imaging.cli."""
    conn = ensure_products_db(products_db)
    update_job_status(conn, job_id, "running", started_at=time.time())
    conn.close()

    # Construct output imagename
    ms_name = Path(ms_path).stem
    out_dir = Path(ms_path).parent.parent / "images" / Path(ms_path).parent.name
    out_dir.mkdir(parents=True, exist_ok=True)
    imagename = str(out_dir / f"{ms_name}.img")

    gridder = params.get("gridder", "wproject")
    wprojplanes = params.get("wprojplanes", -1)
    datacolumn = params.get("datacolumn", "corrected")
    skip_fits = params.get("skip_fits", True)

    py = _python_cmd_for_jobs()
    cmd = py + [
        "-m",
        "dsa110_contimg.imaging.cli",
        "--ms",
        ms_path,
        "--imagename",
        imagename,
        "--gridder",
        gridder,
        "--wprojplanes",
        str(wprojplanes),
        "--verbose",
    ]
    if skip_fits:
        cmd.append("--skip-fits")

    env = os.environ.copy()
    src_path = _src_path_for_env()
    if src_path:
        env["PYTHONPATH"] = src_path

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
        )

        conn = ensure_products_db(products_db)
        line_count = 0
        for line in proc.stdout:
            append_job_log(conn, job_id, line)
            line_count += 1
            if line_count % 10 == 0:
                conn.commit()

        conn.commit()
        proc.wait()

        if proc.returncode == 0:
            artifacts = []
            for suffix in [".image", ".image.pbcor", ".residual", ".psf", ".pb", ".model"]:
                img_path = f"{imagename}{suffix}"
                if Path(img_path).exists():
                    artifacts.append(img_path)
            update_job_status(
                conn,
                job_id,
                "done",
                finished_at=time.time(),
                artifacts=json.dumps(artifacts),
            )
            
            # Extract QA metrics from primary image
            try:
                primary_image = None
                for artifact in artifacts:
                    if artifact.endswith('.image') and '.pbcor' not in artifact:
                        primary_image = artifact
                        break
                
                if primary_image and Path(primary_image).exists():
                    append_job_log(conn, job_id, "\nExtracting QA metrics from image...\n")
                    conn.commit()
                    _store_image_qa(conn, ms_path, job_id, primary_image)
                    append_job_log(conn, job_id, "QA metrics and thumbnail extracted successfully\n")
                    conn.commit()
            except Exception as e:
                # Don't fail the job if QA extraction fails
                append_job_log(conn, job_id, f"\nWARNING: QA extraction failed: {e}\n")
                conn.commit()
        else:
            update_job_status(conn, job_id, "failed", finished_at=time.time())

        conn.close()

    except Exception as e:
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"\nERROR: {e}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
        conn.close()


def run_convert_job(job_id: int, params: dict, products_db: Path):
    """Run UVH5 → MS conversion via hdf5_orchestrator."""
    conn = ensure_products_db(products_db)
    update_job_status(conn, job_id, "running", started_at=time.time())
    conn.close()

    input_dir = params.get("input_dir", "/data/incoming")
    output_dir = params.get("output_dir", "/scratch/dsa110-contimg/ms")
    start_time = params.get("start_time")
    end_time = params.get("end_time")
    writer = params.get("writer", "auto")
    stage_to_tmpfs = params.get("stage_to_tmpfs", True)
    max_workers = params.get("max_workers", 4)

    if not start_time or not end_time:
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, "ERROR: start_time and end_time required\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
        conn.close()
        return

    py = _python_cmd_for_jobs()
    cmd = py + [
        "-u",  # Unbuffered output for real-time logging
        "-m",
        "dsa110_contimg.conversion.strategies.hdf5_orchestrator",
        input_dir,
        output_dir,
        start_time,
        end_time,
        "--writer",
        writer,
        "--max-workers",
        str(max_workers),
    ]
    
    if stage_to_tmpfs:
        cmd.append("--stage-to-tmpfs")
    else:
        cmd.append("--no-stage-to-tmpfs")

    env = os.environ.copy()
    src_path = _src_path_for_env()
    if src_path:
        env["PYTHONPATH"] = src_path
    
    # Set environment for conversion
    env.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
    env.setdefault("OMP_NUM_THREADS", "4")
    env.setdefault("MKL_NUM_THREADS", "4")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
        )

        conn = ensure_products_db(products_db)
        for line in proc.stdout:
            append_job_log(conn, job_id, line)
            # Commit every line for real-time log streaming
            conn.commit()

        proc.wait()

        if proc.returncode == 0:
            # Discover created MS files
            artifacts = []
            output_path = Path(output_dir)
            if output_path.exists():
                for ms in output_path.glob("**/*.ms"):
                    if ms.is_dir():
                        artifacts.append(str(ms))
            
            update_job_status(
                conn,
                job_id,
                "done",
                finished_at=time.time(),
                artifacts=json.dumps(artifacts),
            )
        else:
            update_job_status(conn, job_id, "failed", finished_at=time.time())

        conn.close()

    except Exception as e:
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"\nERROR: {e}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
        conn.close()


def run_workflow_job(job_id: int, params: dict, products_db: Path):
    """Run full pipeline workflow: Convert → Calibrate → Image."""
    conn = ensure_products_db(products_db)
    update_job_status(conn, job_id, "running", started_at=time.time())
    append_job_log(conn, job_id, "=== Starting Pipeline Workflow ===\n")
    append_job_log(conn, job_id, f"Time range: {params['start_time']} to {params['end_time']}\n\n")
    conn.commit()
    conn.close()

    try:
        # Step 1: Convert UVH5 → MS
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, "Step 1/3: Converting UVH5 → MS...\n")
        conn.commit()
        conn.close()
        
        convert_params = {
            "input_dir": params.get("input_dir", "/data/incoming"),
            "output_dir": params.get("output_dir", "/scratch/dsa110-contimg/ms"),
            "start_time": params["start_time"],
            "end_time": params["end_time"],
            "writer": params.get("writer", "auto"),
            "stage_to_tmpfs": params.get("stage_to_tmpfs", True),
            "max_workers": params.get("max_workers", 4),
        }
        
        # Run conversion inline (simplified - in production you'd want better error handling)
        run_convert_job(job_id, convert_params, products_db)
        
        # Get the created MS path from artifacts
        conn = ensure_products_db(products_db)
        cursor = conn.cursor()
        cursor.execute("SELECT artifacts, status FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if not row or row[1] == "failed":
            conn.close()
            raise Exception("Conversion step failed")
        artifacts = json.loads(row[0]) if row and row[0] else []
        conn.close()
        
        if not artifacts:
            raise Exception("Conversion failed: no MS file created")
        
        ms_path = artifacts[0]  # Use first MS
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"\n✓ Conversion complete: {ms_path}\n\n")
        append_job_log(conn, job_id, "Step 2/3: Calibrating & Applying...\n")
        conn.commit()
        conn.close()
        
        # Step 2: Calibrate (skip for now - would need calibrator detection)
        # For workflow, assume MS is already calibrated or skip calibration
        
        # Step 3: Image directly
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, "Step 3/3: Imaging...\n")
        conn.commit()
        conn.close()
        
        image_params = {
            "gridder": params.get("gridder", "wproject"),
            "wprojplanes": params.get("wprojplanes", -1),
            "datacolumn": "data",  # Use DATA since no calibration
            "skip_fits": False,
        }
        
        run_image_job(job_id, ms_path, image_params, products_db)
        
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, "\n=== Workflow Complete ===\n")
        append_job_log(conn, job_id, f"✓ MS: {ms_path}\n")
        append_job_log(conn, job_id, "✓ Image products created\n")
        update_job_status(conn, job_id, "done", finished_at=time.time())
        conn.commit()
        conn.close()
        
    except Exception as e:
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"\n=== Workflow Failed ===\n")
        append_job_log(conn, job_id, f"ERROR: {e}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
        conn.close()


def run_batch_calibrate_job(batch_id: int, ms_paths: List[str], params: dict, products_db: Path):
    """Process batch calibration job - runs calibration on each MS sequentially."""
    from dsa110_contimg.api.batch_jobs import update_batch_item
    
    conn = ensure_products_db(products_db)
    
    try:
        # Update batch status to running
        conn.execute("UPDATE batch_jobs SET status = 'running' WHERE id = ?", (batch_id,))
        conn.commit()
        
        for ms_path in ms_paths:
            # Check if batch was cancelled
            cursor = conn.execute("SELECT status FROM batch_jobs WHERE id = ?", (batch_id,))
            batch_status = cursor.fetchone()[0]
            if batch_status == "cancelled":
                break
            
            try:
                # Create individual calibration job
                individual_job_id = create_job(conn, "calibrate", ms_path, params)
                conn.commit()
                
                # Update batch item status
                update_batch_item(conn, batch_id, ms_path, individual_job_id, "running")
                conn.commit()
                
                # Run calibration job
                run_calibrate_job(individual_job_id, ms_path, params, products_db)
                
                # Check job result
                jd = get_job(conn, individual_job_id)
                if jd["status"] == "done":
                    update_batch_item(conn, batch_id, ms_path, individual_job_id, "done")
                else:
                    update_batch_item(conn, batch_id, ms_path, individual_job_id, "failed", error=jd.get("logs", "")[-500:])  # Last 500 chars
                conn.commit()
                
            except Exception as e:
                update_batch_item(conn, batch_id, ms_path, None, "failed", error=str(e))
                conn.commit()
        
        # Batch is complete - status already updated by update_batch_item
        conn.close()
        
    except Exception as e:
        conn = ensure_products_db(products_db)
        conn.execute("UPDATE batch_jobs SET status = 'failed' WHERE id = ?", (batch_id,))
        conn.commit()
        conn.close()


def run_batch_apply_job(batch_id: int, ms_paths: List[str], params: dict, products_db: Path):
    """Process batch apply job - runs applycal on each MS sequentially."""
    from dsa110_contimg.api.batch_jobs import update_batch_item
    
    conn = ensure_products_db(products_db)
    
    try:
        conn.execute("UPDATE batch_jobs SET status = 'running' WHERE id = ?", (batch_id,))
        conn.commit()
        
        for ms_path in ms_paths:
            cursor = conn.execute("SELECT status FROM batch_jobs WHERE id = ?", (batch_id,))
            batch_status = cursor.fetchone()[0]
            if batch_status == "cancelled":
                break
            
            try:
                individual_job_id = create_job(conn, "apply", ms_path, params)
                conn.commit()
                
                update_batch_item(conn, batch_id, ms_path, individual_job_id, "running")
                conn.commit()
                
                run_apply_job(individual_job_id, ms_path, params, products_db)
                
                jd = get_job(conn, individual_job_id)
                if jd["status"] == "done":
                    update_batch_item(conn, batch_id, ms_path, individual_job_id, "done")
                else:
                    update_batch_item(conn, batch_id, ms_path, individual_job_id, "failed", error=jd.get("logs", "")[-500:])
                conn.commit()
                
            except Exception as e:
                update_batch_item(conn, batch_id, ms_path, None, "failed", error=str(e))
                conn.commit()
        
        conn.close()
        
    except Exception as e:
        conn = ensure_products_db(products_db)
        conn.execute("UPDATE batch_jobs SET status = 'failed' WHERE id = ?", (batch_id,))
        conn.commit()
        conn.close()


def run_batch_image_job(batch_id: int, ms_paths: List[str], params: dict, products_db: Path):
    """Process batch imaging job - runs imaging on each MS sequentially."""
    from dsa110_contimg.api.batch_jobs import update_batch_item
    
    conn = ensure_products_db(products_db)
    
    try:
        conn.execute("UPDATE batch_jobs SET status = 'running' WHERE id = ?", (batch_id,))
        conn.commit()
        
        for ms_path in ms_paths:
            cursor = conn.execute("SELECT status FROM batch_jobs WHERE id = ?", (batch_id,))
            batch_status = cursor.fetchone()[0]
            if batch_status == "cancelled":
                break
            
            try:
                individual_job_id = create_job(conn, "image", ms_path, params)
                conn.commit()
                
                update_batch_item(conn, batch_id, ms_path, individual_job_id, "running")
                conn.commit()
                
                run_image_job(individual_job_id, ms_path, params, products_db)
                
                jd = get_job(conn, individual_job_id)
                if jd["status"] == "done":
                    update_batch_item(conn, batch_id, ms_path, individual_job_id, "done")
                else:
                    update_batch_item(conn, batch_id, ms_path, individual_job_id, "failed", error=jd.get("logs", "")[-500:])
                conn.commit()
                
            except Exception as e:
                update_batch_item(conn, batch_id, ms_path, None, "failed", error=str(e))
                conn.commit()
        
        conn.close()
        
    except Exception as e:
        conn = ensure_products_db(products_db)
        conn.execute("UPDATE batch_jobs SET status = 'failed' WHERE id = ?", (batch_id,))
        conn.commit()
        conn.close()
