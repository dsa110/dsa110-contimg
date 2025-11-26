import ast
import glob
import json
import os
import sqlite3
from pathlib import Path


def analyze_databases(base_dir):
    print("\n=== Database Schema Analysis ===")
    db_files = glob.glob(os.path.join(base_dir, "state", "*.sqlite3"))
    for db_path in sorted(db_files):
        print(f"\nDatabase: {os.path.basename(db_path)}")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            for table in tables:
                table_name = table[0]
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                col_names = [col[1] for col in columns]
                print(f"  - {table_name}: {', '.join(col_names)}")
            conn.close()
        except Exception as e:
            print(f"  Error analyzing {db_path}: {e}")


def find_fastapi_routes(base_dir):
    print("\n=== FastAPI Route Analysis ===")
    api_dir = os.path.join(base_dir, "src", "dsa110_contimg", "api")
    for root, _, files in os.walk(api_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r") as f:
                    try:
                        tree = ast.parse(f.read())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                for decorator in node.decorator_list:
                                    if isinstance(decorator, ast.Call):
                                        if hasattr(
                                            decorator.func, "attr"
                                        ) and decorator.func.attr in [
                                            "get",
                                            "post",
                                            "put",
                                            "delete",
                                            "patch",
                                        ]:
                                            # Try to get the path from args
                                            if decorator.args:
                                                route_path = (
                                                    decorator.args[0].value
                                                    if hasattr(
                                                        decorator.args[0], "value"
                                                    )
                                                    else "unknown"
                                                )
                                                print(
                                                    f"  {decorator.func.attr.upper()} {route_path} ({file})"
                                                )
                    except:
                        pass


def main():
    base_dir = "/data/dsa110-contimg"
    analyze_databases(base_dir)
    find_fastapi_routes(base_dir)


if __name__ == "__main__":
    main()
