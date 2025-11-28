/**
 * Validated TextField Component
 * Provides inline validation with error messages
 */
import React, { useState, useEffect } from "react";
import { TextField } from "@mui/material";
import type { TextFieldProps } from "@mui/material";
import {
  useFieldValidation,
  type ValidationRule,
  type ValidationResult,
} from "../utils/formValidation";

interface ValidatedTextFieldProps extends Omit<TextFieldProps, "error"> {
  validationRules?: ValidationRule<string>[];
  validateOnChange?: boolean;
  validateOnBlur?: boolean;
}

export function ValidatedTextField({
  validationRules: rules = [],
  validateOnChange = true,
  validateOnBlur = true,
  value,
  onBlur,
  onChange,
  helperText,
  ...props
}: ValidatedTextFieldProps) {
  const [touched, setTouched] = useState(false);
  const [showValidation, setShowValidation] = useState(false);

  const validation = useFieldValidation(value as string, rules);
  const shouldShowError = showValidation && !validation.isValid;

  useEffect(() => {
    if (validateOnChange && touched) {
      setShowValidation(true);
    }
  }, [value, touched, validateOnChange]);

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    setTouched(true);
    if (validateOnBlur) {
      setShowValidation(true);
    }
    onBlur?.(e);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (validateOnChange && touched) {
      setShowValidation(true);
    }
    onChange?.(e);
  };

  return (
    <>
      <TextField
        {...props}
        value={value}
        onChange={handleChange}
        onBlur={handleBlur}
        error={shouldShowError}
        helperText={shouldShowError ? validation.error : helperText}
      />
    </>
  );
}

/**
 * Time Range Validator
 * Validates that end time is after start time
 */
export function validateTimeRange(startTime: string, endTime: string): ValidationResult {
  if (!startTime || !endTime) {
    return { isValid: true }; // Let required rule handle empty values
  }

  try {
    const start = new Date(startTime);
    const end = new Date(endTime);

    if (isNaN(start.getTime()) || isNaN(end.getTime())) {
      return {
        isValid: false,
        error: "Invalid date format. Use YYYY-MM-DD HH:MM:SS",
      };
    }

    if (end <= start) {
      return {
        isValid: false,
        error: "End time must be after start time",
      };
    }

    return { isValid: true };
  } catch {
    return {
      isValid: false,
      error: "Invalid date format",
    };
  }
}
