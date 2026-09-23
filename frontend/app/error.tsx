"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/Button";
import { Frame, PageHeader } from "@/components/ui/Page";
import { EmptyState } from "@/components/ui/States";

export default function OverviewError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="space-y-5">
      <PageHeader title="Overview" />
      <Frame>
        <EmptyState
          icon="alert"
          role="alert"
          title="The overview couldn't be loaded"
          description="Compensation data is temporarily unavailable. Check that the API is running, then try again."
          action={<Button onClick={reset}>Try again</Button>}
        />
      </Frame>
    </div>
  );
}
