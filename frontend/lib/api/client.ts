const DEFAULT_API_BASE_URL = "http://localhost:8000";

interface ValidationIssue {
  loc: (string | number)[];
  msg: string;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function apiBaseUrl(): string {
  return process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

function fieldLabel(loc: (string | number)[]): string {
  const field = loc.filter((part) => part !== "body" && part !== "query").join(".");
  if (!field) {
    return "";
  }
  const words = field.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function describeDetail(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const issues = detail as ValidationIssue[];
    return issues
      .map((issue) => {
        const label = fieldLabel(issue.loc);
        return label ? `${label}: ${issue.msg}` : issue.msg;
      })
      .join("; ");
  }
  return "Request failed";
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let detail: unknown;
  try {
    detail = (await response.json())?.detail;
  } catch {
    detail = undefined;
  }
  return new ApiError(response.status, describeDetail(detail));
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    cache: "no-store",
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return (await response.json()) as T;
}
