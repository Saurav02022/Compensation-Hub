import { Skeleton } from "@/components/ui/States";

export default function Loading() {
  return (
    <div className="space-y-5" aria-busy="true" aria-label="Loading analytics">
      <div className="space-y-2 pt-1">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-3.5 w-96 max-w-full" />
      </div>
      <div className="flex flex-wrap gap-2">
        <Skeleton className="h-8 w-28" />
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-8 w-28" />
      </div>
      <Skeleton className="h-[106px] rounded-surface" />
      <Skeleton className="h-[480px] rounded-surface" />
    </div>
  );
}
