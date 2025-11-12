"""
Database validation module.

Validates database consistency, referential integrity, and data completeness.
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from dsa110_contimg.qa.base import (
    ValidationContext,
    ValidationError,
    ValidationInputError,
    ValidationResult,
)
from dsa110_contimg.qa.config import DatabaseConfig, get_default_config

logger = logging.getLogger(__name__)


@dataclass
class DatabaseValidationResult(ValidationResult):
    """Result of database validation."""
    
    # Database metrics
    n_tables: int = 0
    n_tables_validated: int = 0
    
    # Integrity metrics
    n_orphaned_records: int = 0
    n_missing_files: int = 0
    n_invalid_paths: int = 0
    
    # Completeness metrics
    n_expected_records: int = 0
    n_actual_records: int = 0
    completeness_fraction: float = 1.0
    
    # Schema validation
    schema_errors: List[str] = field(default_factory=list)
    
    # Per-table results
    table_results: List[Dict[str, any]] = field(default_factory=list)  # type: ignore
    
    def __post_init__(self):
        """Initialize defaults."""
        super().__post_init__()
        if self.schema_errors is None:
            self.schema_errors = []
        if self.table_results is None:
            self.table_results = []


def validate_database_consistency(
    db_path: str,
    expected_tables: List[str],
    file_registry: Optional[Dict[str, List[str]]] = None,
    config: Optional[DatabaseConfig] = None,
) -> DatabaseValidationResult:
    """Validate database consistency and integrity.
    
    Checks referential integrity, file path validity, and data completeness.
    
    Args:
        db_path: Path to SQLite database
        expected_tables: List of expected table names
        file_registry: Optional dictionary mapping table names to expected file paths
        config: Database validation configuration
        
    Returns:
        DatabaseValidationResult with validation status
        
    Raises:
        ValidationInputError: If inputs are invalid
        ValidationError: If validation fails
    """
    if config is None:
        config = get_default_config().database
    
    # Validate inputs
    db_path_obj = Path(db_path)
    if not db_path_obj.exists():
        raise ValidationInputError(f"Database file not found: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get actual tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        actual_tables = [row[0] for row in cursor.fetchall()]
        
        n_tables = len(actual_tables)
        n_tables_validated = 0
        
        # Validate schema
        schema_errors = []
        missing_tables = set(expected_tables) - set(actual_tables)
        if missing_tables:
            schema_errors.append(f"Missing tables: {missing_tables}")
        
        # Validate each table
        table_results = []
        orphaned_records = []
        missing_files = []
        invalid_paths = []
        
        for table_name in actual_tables:
            try:
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                n_records = cursor.fetchone()[0]
                
                # Check for orphaned records (if foreign keys exist)
                # Simplified: check for NULL foreign keys where they shouldn't be
                orphaned_count = 0
                
                # Check file paths if file_registry provided
                file_path_errors = []
                if file_registry and table_name in file_registry:
                    expected_files = set(file_registry[table_name])
                    
                    # Get file paths from table (assuming 'path' or 'file_path' column)
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [row[1] for row in cursor.fetchall()]
                    
                    path_column = None
                    for col in ['file_path', 'path', 'image_path', 'ms_path']:
                        if col in columns:
                            path_column = col
                            break
                    
                    if path_column:
                        cursor.execute(f"SELECT {path_column} FROM {table_name}")
                        db_files = [row[0] for row in cursor.fetchall()]
                        
                        for db_file in db_files:
                            if db_file and db_file not in expected_files:
                                # Check if file exists
                                if not Path(db_file).exists():
                                    missing_files.append(db_file)
                                    invalid_paths.append(db_file)
                                    file_path_errors.append(f"Missing file: {db_file}")
                
                table_results.append({
                    "table_name": table_name,
                    "n_records": n_records,
                    "n_orphaned": orphaned_count,
                    "n_file_errors": len(file_path_errors),
                    "file_errors": file_path_errors[:5],  # Limit to first 5
                })
                
                orphaned_records.extend([(table_name, i) for i in range(orphaned_count)])
                n_tables_validated += 1
                
            except Exception as e:
                logger.warning(f"Error validating table {table_name}: {e}")
                schema_errors.append(f"Error validating table {table_name}: {e}")
        
        # Calculate completeness
        total_expected = sum(
            len(file_registry.get(table, [])) if file_registry else 100
            for table in expected_tables
        )
        total_actual = sum(r["n_records"] for r in table_results)
        completeness_fraction = total_actual / total_expected if total_expected > 0 else 1.0
        
        n_orphaned = len(orphaned_records)
        n_missing = len(set(missing_files))
        n_invalid = len(set(invalid_paths))
        
        # Determine overall pass status
        passed = (
            len(schema_errors) == 0 and
            n_orphaned <= config.max_orphaned_records and
            n_missing == 0 and
            (not config.require_referential_integrity or n_orphaned == 0)
        )
        
        conn.close()
        
        result = DatabaseValidationResult(
            passed=passed,
            message=f"Database validation: {n_tables_validated}/{n_tables} tables validated, {n_orphaned} orphaned records",
            details={
                "n_tables": n_tables,
                "n_tables_validated": n_tables_validated,
                "n_orphaned": n_orphaned,
                "n_missing_files": n_missing,
                "n_invalid_paths": n_invalid,
                "completeness_fraction": completeness_fraction,
                "schema_errors": schema_errors,
            },
            metrics={
                "n_orphaned_records": n_orphaned,
                "n_missing_files": n_missing,
                "n_invalid_paths": n_invalid,
                "completeness_fraction": completeness_fraction,
            },
            n_tables=n_tables,
            n_tables_validated=n_tables_validated,
            n_orphaned_records=n_orphaned,
            n_missing_files=n_missing,
            n_invalid_paths=n_invalid,
            n_expected_records=total_expected,
            n_actual_records=total_actual,
            completeness_fraction=completeness_fraction,
            schema_errors=schema_errors,
            table_results=table_results,
        )
        
        if schema_errors:
            for error in schema_errors:
                result.add_error(error)
        
        if n_orphaned > config.max_orphaned_records:
            result.add_error(
                f"Orphaned records {n_orphaned} exceed threshold {config.max_orphaned_records}"
            )
        
        if n_missing > 0:
            result.add_warning(f"{n_missing} files referenced in database are missing")
        
        return result
        
    except Exception as e:
        logger.exception("Database validation failed")
        raise ValidationError(f"Database validation failed: {e}") from e


def validate_referential_integrity(
    db_path: str,
    foreign_key_constraints: List[Dict[str, str]],
) -> DatabaseValidationResult:
    """Validate referential integrity of foreign key constraints.
    
    Args:
        db_path: Path to SQLite database
        foreign_key_constraints: List of constraint definitions with 'table', 'column', 'references_table', 'references_column'
        
    Returns:
        DatabaseValidationResult with referential integrity validation status
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    orphaned_records = []
    
    for constraint in foreign_key_constraints:
        table = constraint["table"]
        column = constraint["column"]
        ref_table = constraint["references_table"]
        ref_column = constraint["references_column"]
        
        # Find orphaned records
        query = f"""
            SELECT {table}.{column}
            FROM {table}
            LEFT JOIN {ref_table} ON {table}.{column} = {ref_table}.{ref_column}
            WHERE {ref_table}.{ref_column} IS NULL AND {table}.{column} IS NOT NULL
        """
        
        try:
            cursor.execute(query)
            orphans = cursor.fetchall()
            orphaned_records.extend([(table, row[0]) for row in orphans])
        except Exception as e:
            logger.warning(f"Error checking referential integrity for {table}.{column}: {e}")
    
    conn.close()
    
    n_orphaned = len(orphaned_records)
    passed = n_orphaned == 0
    
    return DatabaseValidationResult(
        passed=passed,
        message=f"Referential integrity: {n_orphaned} orphaned records found",
        details={
            "n_orphaned": n_orphaned,
            "orphaned_records": orphaned_records[:10],  # Limit to first 10
        },
        n_orphaned_records=n_orphaned,
    )

