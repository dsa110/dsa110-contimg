import { useState, useCallback } from "react";
import { ErrorResponse } from "../types/errors";

const useErrorHandler = () => {
  const [error, setError] = useState<ErrorResponse | null>(null);

  const handleError = useCallback((errorResponse: ErrorResponse) => {
    setError(errorResponse);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    error,
    handleError,
    clearError,
  };
};

export default useErrorHandler;
