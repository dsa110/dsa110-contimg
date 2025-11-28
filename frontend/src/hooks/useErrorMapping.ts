import { useMemo } from "react";
import { errorMappings } from "../constants/errorMappings";
import { ErrorResponse } from "../types/errors";

const useErrorMapping = (errorResponse: ErrorResponse) => {
  return useMemo(() => {
    const mapping = errorMappings[errorResponse.code] || {
      user_message: "An unexpected error occurred.",
      action: "Please try again later.",
    };

    return {
      user_message: mapping.user_message,
      action: mapping.action,
      details: errorResponse.details || {},
      trace_id: errorResponse.trace_id || "",
      doc_anchor: errorResponse.doc_anchor || "",
    };
  }, [errorResponse]);
};

export default useErrorMapping;
