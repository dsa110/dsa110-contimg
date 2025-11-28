/**
 * Pure function for selection state logic
 * Extracted from ControlPage for easier testing and debugging
 */
export function computeSelectedMS(
  paths: string[],
  prevList: string[],
  currentSelectedMS: string
): string {
  if (paths.length > 0) {
    // Find the newly added item if selection grew
    if (paths.length > prevList.length) {
      const newItem = paths.find((p) => !prevList.includes(p));
      if (newItem) {
        return newItem;
      }
      return paths[0];
    } else if (paths.length < prevList.length) {
      // Something was removed
      if (paths.includes(currentSelectedMS)) {
        return currentSelectedMS; // Keep current if still in list
      }
      return paths.length > 0 ? paths[0] : "";
    } else {
      // Same length - might have been a reorder
      return paths.includes(currentSelectedMS) ? currentSelectedMS : paths[0];
    }
  } else {
    return "";
  }
}
