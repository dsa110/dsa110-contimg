import React from "react";
import DirectoryBrowser from "../QA/DirectoryBrowser";

export const FileBrowser: React.FC = () => {
  return (
    <DirectoryBrowser
      initialPath="/data/dsa110-contimg"
      onSelectFile={(path, type) => {
        // Handler for file selection
        // In the future, we can add navigation to a viewer or details page
      }}
    />
  );
};
