import { Frame } from "@/components/ui/Page";
import { Skeleton, TableSkeleton } from "@/components/ui/States";

export default function Loading() {
  return (
    <div className="space-y-5" aria-busy="true" aria-label="Loading employees">
      <div className="space-y-2 pt-1">
        <Skeleton className="h-6 w-36" />
        <Skeleton className="h-3.5 w-72 max-w-full" />
      </div>
      <div className="flex flex-wrap gap-2">
        <Skeleton className="h-8 w-full sm:w-72" />
        <Skeleton className="h-8 w-28" />
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-8 w-28" />
      </div>
      <Frame>
        <TableSkeleton rows={12} columns={6} />
      </Frame>
    </div>
  );
}
