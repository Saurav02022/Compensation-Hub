import Link from "next/link";

import { buttonClassName } from "@/components/ui/Button";
import { Frame } from "@/components/ui/Page";
import { EmptyState } from "@/components/ui/States";

export default function EmployeeNotFound() {
  return (
    <Frame className="mt-2">
      <EmptyState
        icon="employees"
        title="Employee not found"
        description="No employee exists with that identifier. The link may be mistyped or out of date."
        action={
          <Link href="/employees" className={buttonClassName("secondary")}>
            Go to employees
          </Link>
        }
      />
    </Frame>
  );
}
