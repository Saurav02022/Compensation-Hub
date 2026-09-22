import Link from "next/link";

export default function EmployeeNotFound() {
  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-semibold">Employee not found</h1>
      <p className="text-sm text-slate-600">No employee exists with that identifier.</p>
      <Link href="/employees" className="text-sm text-slate-700 hover:underline">
        ← Back to employees
      </Link>
    </div>
  );
}
