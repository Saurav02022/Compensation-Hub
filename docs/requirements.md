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

The HR Manager can ask compensation and workforce questions in natural language.

If Compensation Hub holds the data a question needs, Ask Compensation derives the answer from that data. If the data is not stored, it says which data is missing instead of guessing.

Answerability depends on the stored data and read-only relational queries over it, not on a list of anticipated questions. That includes filtering with any combination of conditions, looking up and ranking employees, counting, totals, averages, medians, minimums and maximums, grouping, comparisons with a group's own figures, rankings within groups, shares and percentages, differences and ratios, and expressing amounts in any currency with a seeded exchange rate. Answers stay within the product's safety and resource limits.

The HR Manager can ask follow-up questions that refine the previous one, such as converting a result to another currency or narrowing it to a department, without restating the whole question.

Answers must be based on application data and deterministic calculations. Ask Compensation never changes data, never makes salary recommendations, and never infers attributes that are not stored, such as gender from a name.

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
- running AI-generated SQL without validation (Ask Compensation runs only validated, read-only SQL over the approved employee and compensation data),
- document search or RAG.

These capabilities can be considered later if product requirements justify them.

## Success Criteria

The MVP is successful when the HR Manager can:

1. find an employee efficiently within 10,000 records,
2. view and update current compensation,
3. understand key compensation patterns across the organization,
4. compare compensation across countries using consistent currency values,
5. ask compensation questions, including follow-ups, and receive answers derived from application data,
6. get a clear response naming the missing data when a question cannot be answered from what is stored.