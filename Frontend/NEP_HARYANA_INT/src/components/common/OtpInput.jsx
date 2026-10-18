import React, { useRef, useEffect } from "react";

/**
 * Reusable 6-digit segmented OTP Input.
 *
 * Props:
 * - value: string (6 digits or less)
 * - onChange: (val: string) => void
 * - onComplete?: (val: string) => void
 * - disabled?: boolean
 * - hasError?: boolean
 * - autoFocus?: boolean
 */
export default function OtpInput({
  value = "",
  onChange,
  onComplete,
  disabled = false,
  hasError = false,
  autoFocus = true,
}) {
  const inputRefs = useRef([]);

  // Ensure digits array always has 6 items
  const digits = Array.from({ length: 6 }, (_, i) => value[i] || "");

  useEffect(() => {
    if (autoFocus && inputRefs.current[0] && !disabled) {
      inputRefs.current[0].focus();
    }
  }, [autoFocus, disabled]);

  const handleChange = (e, index) => {
    const rawVal = e.target.value;
    // Extract only digits
    const cleaned = rawVal.replace(/\D/g, "");

    if (!cleaned) {
      // Empty / cleared
      const newDigits = [...digits];
      newDigits[index] = "";
      const newValue = newDigits.join("");
      onChange(newValue);
      return;
    }

    if (cleaned.length > 1) {
      // Multiple digits entered (or paste through normal input)
      handlePastedText(cleaned, index);
      return;
    }

    // Single digit entered
    const digit = cleaned[cleaned.length - 1];
    const newDigits = [...digits];
    newDigits[index] = digit;
    const newValue = newDigits.join("");
    onChange(newValue);

    // Auto advance to next input
    if (index < 5 && inputRefs.current[index + 1]) {
      inputRefs.current[index + 1].focus();
    }

    if (newValue.length === 6 && onComplete) {
      onComplete(newValue);
    }
  };

  const handleKeyDown = (e, index) => {
    if (disabled) return;

    if (e.key === "Backspace") {
      if (!digits[index] && index > 0 && inputRefs.current[index - 1]) {
        // Move to previous input and clear it
        e.preventDefault();
        const newDigits = [...digits];
        newDigits[index - 1] = "";
        onChange(newDigits.join(""));
        inputRefs.current[index - 1].focus();
      } else if (digits[index]) {
        // Clear current
        e.preventDefault();
        const newDigits = [...digits];
        newDigits[index] = "";
        onChange(newDigits.join(""));
      }
    } else if (e.key === "ArrowLeft" && index > 0) {
      e.preventDefault();
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < 5) {
      e.preventDefault();
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pasteData = e.clipboardData.getData("text");
    handlePastedText(pasteData, 0);
  };

  const handlePastedText = (text, startIndex = 0) => {
    const numericOnly = text.replace(/\D/g, "");
    if (!numericOnly) return;

    const newDigits = [...digits];
    let writeIdx = startIndex;
    for (let i = 0; i < numericOnly.length && writeIdx < 6; i++) {
      newDigits[writeIdx] = numericOnly[i];
      writeIdx++;
    }

    const newValue = newDigits.join("").slice(0, 6);
    onChange(newValue);

    // Focus next empty or the last filled
    const nextFocus = Math.min(writeIdx, 5);
    inputRefs.current[nextFocus]?.focus();

    if (newValue.length === 6 && onComplete) {
      onComplete(newValue);
    }
  };

  return (
    <div
      className="flex items-center justify-center gap-2 sm:gap-3"
      onPaste={handlePaste}
      role="group"
      aria-label="6-digit verification code"
    >
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(el) => (inputRefs.current[index] = el)}
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          maxLength={1}
          value={digit}
          disabled={disabled}
          autoComplete={index === 0 ? "one-time-code" : "off"}
          onChange={(e) => handleChange(e, index)}
          onKeyDown={(e) => handleKeyDown(e, index)}
          onFocus={(e) => e.target.select()}
          aria-label={`Digit ${index + 1} of 6`}
          className={`w-11 h-14 sm:w-13 sm:h-16 text-center text-2xl font-bold rounded-xl border transition-all duration-200 outline-none select-all ${
            disabled
              ? "bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed"
              : hasError
              ? "border-red-400 bg-red-50/50 text-red-900 focus:border-red-600 focus:ring-2 focus:ring-red-200"
              : digit
              ? "border-[#600b0b] bg-white text-[#600b0b] shadow-sm focus:border-[#600b0b] focus:ring-2 focus:ring-[#600b0b]/20"
              : "border-slate-300 bg-slate-50/60 text-slate-900 focus:bg-white focus:border-[#600b0b] focus:ring-2 focus:ring-[#600b0b]/20"
          }`}
        />
      ))}
    </div>
  );
}
