/**
 * @name CASA Task Security Check
 * @description Detects calls to CASA tasks that may be security-sensitive
 * @kind problem
 * @problem.severity warning
 * @id casa-task-security
 * @tags security
 */

import python

/**
 * Finds calls to CASA tasks by name pattern
 */
from Call call, Name name
where
  call.getFunc() = name and
  (
    name.getId().matches("%clean%") or
    name.getId().matches("%tclean%") or
    name.getId().matches("%calibrate%") or
    name.getId().matches("%applycal%") or
    name.getId().matches("%split%") or
    name.getId().matches("%concat%")
  )
select call, "CASA task call detected. Review for security implications: $@", call, "CASA task call"
