export interface Compensation {
  /** Exact decimal amount serialized by the API as a string, e.g. "123456.78". */
  annual_salary: string;
  currency_code: string;
}

export interface Employee {
  id: number;
  employee_code: string;
  full_name: string;
  country: string;
  department: string;
  job_title: string;
  compensation: Compensation | null;
}

export interface EmployeePage {
  items: Employee[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface EmployeeFilterOptions {
  countries: string[];
  departments: string[];
  job_titles: string[];
}

export interface EmployeeListQuery {
  page?: number;
  page_size?: number;
  search?: string;
  country?: string;
  department?: string;
  job_title?: string;
}

export interface CompensationUpdate {
  annual_salary: string;
  currency_code: string;
}
