import { Skeleton, TableSkeleton } from "@/components/ui/States";

export default function Loading() {
  return (
    <div className="space-y-4" aria-busy="true">
      <div className="space-y-2">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-4 w-72" />
      </div>
      <Skeleton className="h-24 w-full rounded-surface" />
      <TableSkeleton rows={10} columns={6} />
    </div>
  );
}
