import { Skeleton } from "@/components/ui/States";

export default function Loading() {
  return (
    <div className="space-y-4" aria-busy="true">
      <div className="space-y-2">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <Skeleton className="h-24 rounded-surface" />
        <Skeleton className="h-24 rounded-surface" />
        <Skeleton className="h-24 rounded-surface" />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-64 rounded-surface" />
        <Skeleton className="h-64 rounded-surface" />
      </div>
    </div>
  );
}
