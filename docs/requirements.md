# Compensation Hub — MVP Requirements

## Problem

HR manages compensation for 10,000 employees across multiple countries. Spreadsheet-based management makes it harder to find employee information quickly, keep current salary data accurate, and understand compensation across the organization.

Compensation Hub provides a single place for an HR Manager to manage current employee compensation and explore how the organization pays its people.

## User

The MVP is designed for a single trusted HR Manager who needs to:

- find an employee quickly,
- view and update current compensation,
- understand compensation across teams and countries,
- ask common compensation questions without manually analysing spreadsheet data.

## MVP Scope

### Employee Directory

The HR Manager can:

- browse employees using server-side pagination,
- search by employee name or employee code,
- filter by country, department, and job title,
- open an employee to view their details and current compensation.

The application contains a deterministic seed dataset of 10,000 employees.

### Current Compensation

The HR Manager can:

- view an employee's current annual salary in local currency,
- update the current salary,
- receive clear validation errors for invalid values.

The MVP manages current compensation only.

### Multi-Country Compensation

Salaries are stored in local currency.

For organization-wide analytics, monetary values are normalized to USD using a fixed set of seeded exchange rates. This keeps comparisons meaningful and results reproducible without depending on a live exchange-rate service.

### Compensation Insights

The HR Manager can view:

- employee count,
- total annual payroll,
- average annual salary,
- breakdowns by country, department, and job title.

Cross-country monetary metrics use the normalized analytics currency.

### Ask Compensation

The HR Manager can ask read-only questions in natural language whenever the answer can be derived from the employee, current-compensation, and exchange-rate data stored by Compensation Hub.

Examples include:

- What is the average salary in Engineering?
- What is the total payroll for Germany?
- Who are the five highest-paid Engineering employees in India?
- What percentage of employees are in Engineering?
- What currencies are used in Germany?
- Convert that payroll result to INR.
- What is the median salary in Sales?

Ask Compensation supports contextual follow-up questions by carrying forward prior validated query intent. The language model interprets the question; application code validates the plan and PostgreSQL performs the authoritative query or calculation.

If a question requires data the product does not store, the response should identify the missing data rather than guess. For example, a question filtered by gender cannot be answered because gender is not part of the employee model.

Ask Compensation remains read-only. It cannot update employee or compensation data, make salary recommendations, or execute arbitrary model-generated SQL.

## Deliberate Non-Goals

The MVP does not include:

- authentication or role-based access,
- salary history,
- employee onboarding or offboarding,
- payroll processing,
- compensation approval workflows,
- bonuses, benefits, equity, or tax calculations,
- live exchange-rate synchronization,
- salary recommendations,
- arbitrary AI-generated database queries,
- document search or RAG.

These capabilities can be considered later if product requirements justify them.

## Success Criteria

The MVP is successful when the HR Manager can:

1. find an employee efficiently within 10,000 records,
2. view and update current compensation,
3. understand key compensation patterns across the organization,
4. compare compensation across countries using consistent currency values,
5. ask natural-language questions that can be derived from available product data, including contextual follow-ups,
6. receive deterministic, data-grounded answers rather than model-generated figures,
7. get a specific explanation when a question requires data the product does not have.