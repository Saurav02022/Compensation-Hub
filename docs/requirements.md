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

The HR Manager can ask supported compensation questions in natural language, such as:

- What is the average salary in Engineering?
- What is the total payroll for Germany?
- Show average compensation by department.
- How many Engineering employees are based in India?

Answers must be based on application data and deterministic calculations. If the available data cannot answer a question reliably, the product should say so rather than guess.

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
5. ask supported compensation questions and receive answers grounded in application data,
6. get a clear response when a question cannot be answered reliably.