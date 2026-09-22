"use client";

import { useEffect } from "react";

export default function EmployeesError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div role="alert" className="rounded border border-red-200 bg-red-50 p-4">
      <h1 className="font-semibold text-red-800">Employee data is unavailable</h1>
      <p className="mt-1 text-sm text-red-700">
        The employee directory could not be loaded. Check that the API is running and try again.
      </p>
      <button
        type="button"
        onClick={reset}
        className="mt-3 rounded bg-red-700 px-3 py-1.5 text-sm text-white hover:bg-red-800"
      >
        Try again
      </button>
    </div>
  );
}
