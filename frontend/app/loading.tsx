import { Skeleton } from "@/components/ui/States";

export default function Loading() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading overview">
      <div className="flex flex-wrap items-end justify-between gap-3 pt-1">
        <div className="space-y-2">
          <Skeleton className="h-6 w-28" />
          <Skeleton className="h-3.5 w-80 max-w-full" />
        </div>
        <Skeleton className="h-8 w-full sm:w-72" />
      </div>
      <Skeleton className="h-[106px] rounded-surface" />
      <div className="grid gap-5 lg:grid-cols-2">
        <Skeleton className="h-64 rounded-surface" />
        <Skeleton className="h-64 rounded-surface" />
      </div>
    </div>
  );
}
