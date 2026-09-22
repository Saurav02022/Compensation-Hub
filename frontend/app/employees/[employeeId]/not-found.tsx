import Link from "next/link";

import { buttonClassName } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/States";

export default function EmployeeNotFound() {
  return (
    <EmptyState
      title="Employee not found"
      description="No employee exists with that identifier. It may have been mistyped or the link may be out of date."
      action={
        <Link href="/employees" className={buttonClassName("secondary")}>
          Back to employees
        </Link>
      }
    />
  );
}
