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

Ask Compensation is a read-only natural-language interface over the data Compensation Hub actually stores.

The product rule is:

> If Compensation Hub has the data required to answer the question, Ask Compensation derives the answer from that data. If the required data is not available, it identifies what is missing rather than inventing an answer.

The assistant is not limited to the metrics or views exposed by the Analytics page. It can combine safe read-only operations over employee, current-compensation, and exchange-rate data when those operations are required to answer the user's question.

Follow-up questions can use a bounded history of prior validated intent so the HR Manager can refine a question without restating its full context.

The language model interprets language and proposes a structured read-only program. Application code validates that program, constructs the allowed SQLAlchemy operations, and uses PostgreSQL plus deterministic application calculations for the authoritative result.

Ask Compensation cannot mutate data, make salary recommendations, infer fields that are not stored, or execute arbitrary model-generated SQL.

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