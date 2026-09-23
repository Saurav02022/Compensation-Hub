import { Skeleton } from "@/components/ui/States";

export default function Loading() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading employee">
      <Skeleton className="h-4 w-28" />
      <div className="space-y-2">
        <Skeleton className="h-6 w-56" />
        <Skeleton className="h-3.5 w-72 max-w-full" />
      </div>
      <Skeleton className="h-14 w-full" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_16rem]">
        <Skeleton className="h-44 rounded-surface" />
        <Skeleton className="h-32 rounded-surface" />
      </div>
    </div>
  );
}
