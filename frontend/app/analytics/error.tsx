"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/States";
import { PageHeader } from "@/components/ui/Surface";

export default function AnalyticsError({
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
    <div className="space-y-4">
      <PageHeader title="Analytics" />
      <Alert tone="error" title="Analytics could not be loaded" action={<Button onClick={reset}>Try again</Button>}>
        Compensation analytics are temporarily unavailable. Check that the API is running, then try again.
      </Alert>
    </div>
  );
}
