/**
 * @name Hardcoded Data Paths
 * @description Detects hardcoded paths that may not be portable
 * @kind problem
 * @problem.severity warning
 * @id hardcoded-data-paths
 * @tags maintainability
 */

import python

/**
 * Finds hardcoded paths to data directories
 */
predicate isHardcodedDataPath(Expr expr) {
  exists(string path |
    expr.(StringLiteral).getValue() = path and
    (
      path.matches("%/data/%") or
      path.matches("%/stage/%") or
      path.matches("%/scratch/%") or
      path.matches("%/products/%") or
      path.matches("%/incoming/%")
    ) and
    not path.matches("%os.environ%") and
    not path.matches("%os.getenv%") and
    not path.matches("%config%")
  )
}

from Expr expr
where isHardcodedDataPath(expr)
select expr, "Hardcoded data path detected. Consider using environment variables or configuration: $@", expr, "Hardcoded path"

