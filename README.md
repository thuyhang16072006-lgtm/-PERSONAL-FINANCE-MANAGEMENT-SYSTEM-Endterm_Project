
# MoneyMate — Personal Finance Management System
> Project 13 · NEU-College of Technology · Personal finance management solution

---

## Overview

MoneyMate is a personal finance management application built with Python and MySQL. The project includes:
- Income, expense, and bank account management.
- Monthly budget tracking.
- Financial reporting and dashboard features.
- Command-line interface (CLI) and REST API powered by FastAPI.

---

## Project structure

```
moneymate/
├── Database.sql      # Database schema, tables, triggers, and seed data
├── account.py        # Bank account management module
├── app.py            # FastAPI REST API implementation
├── budget.py         # Budget checks and spending limits
├── db_config.py      # MySQL connection configuration
├── db_connection.py  # Shared database helpers
├── expense.py        # Expense management module
├── income.py         # Income management module
├── main.py           # Main CLI menu
├── reports.py        # Reporting, statistics, and charts
├── requirements.txt  # Python dependencies
└── README.md         # Project documentation
```

---

## Requirements

- Python 3.10+ (recommended 3.11+)
- MySQL or MariaDB server
- pip package manager

---

## Installation

1. Create and activate a virtual environment (recommended):

```bash
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create the database and tables using the provided SQL script:

```bash
mysql -u root -p < Database.sql
```

4. Update connection settings in `db_config.py`:

```python
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "your_password"
DB_NAME = "moneymate"
```

> If you use a `.env` file, adjust `db_config.py` to read environment variables accordingly.

---

## Run the application

### 1) Run CLI

```bash
python main.py
```

The CLI supports:
- Adding income and expenses.
- Viewing monthly income and expense records.
- Showing account balances and transaction history.
- Checking budget status and generating summary reports.

### 2) Run REST API

```bash
uvicorn app:app --reload
```

Then visit `http://127.0.0.1:8000/docs` to access the Swagger UI.

### 3) Run local static app viewer

If you want to view the `index.html` frontend in your browser, serve the project folder and open the local page:

```bash
cd "C:\Users\Admin\Downloads\moneymate"
python -m http.server 3000
```

Then visit `http://localhost:3000/`.

---

## Key features

- User, bank account, and expense category management.
- Create, list, and soft-delete income/expense transactions.
- Automatic account balance updates via MySQL triggers.
- Monthly and category-level budgeting.
- Monthly/yearly reports, category charts, and comparison views.
- Full REST API coverage for main application functions.

---

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check application and database status |
| POST | `/register` | Register a new user |
| POST | `/login` | Log in with email and password |
| GET | `/categories` | Get expense categories |
| POST | `/categories` | Create a new expense category |
| GET | `/accounts/{user_id}` | Get user accounts and total balance |
| POST | `/accounts` | Create a new bank account |
| PUT | `/accounts/{account_id}` | Update account name |
| POST | `/income` | Add income |
| GET | `/income` | List income by month |
| DELETE | `/income/{income_id}` | Soft-delete income transaction |
| POST | `/expenses` | Add expense |
| GET | `/expenses` | List expenses by month |
| DELETE | `/expenses/{expense_id}` | Soft-delete expense transaction |
| GET | `/budget/jars/{user_id}` | Get budget jars with spent amounts |
| GET | `/budget/{user_id}` | Get user budget limits |
| POST | `/budget` | Create or update a budget limit |
| DELETE | `/budget/{budget_id}` | Delete a budget limit |
| GET | `/dashboard/{user_id}` | Get dashboard summary and budget status |
| GET | `/reports/yearly/{user_id}` | Get yearly report |

---

## Database details

`Database.sql` includes:
- Database creation for `moneymate`
- Tables: `Users`, `ExpenseCategories`, `BankAccounts`, `Income`, `Expenses`, `BudgetLimits`
- MySQL triggers to keep account balances synchronized
- Integrity constraints and indexes for reporting

---

## Notes

- Income and expense records use `IsDeleted` for soft deletion and automatic balance reconciliation.
- `reports.py` contains aggregated reports and chart generation.
- `db_connection.py` handles shared MySQL database operations.
- `db_config.py` stores database connection settings.
- `app.py` exposes the REST API while `main.py` provides the CLI.

---

## Dependencies

- `mysql-connector-python`
- `matplotlib`
- `fastapi`
- `uvicorn[standard]`
- `python-dotenv`
- `pydantic`
- `bcrypt`

---

## Important

- Ensure MySQL is running and the connection information in `db_config.py` is correct.
- For production, avoid using `allow_origins=["*"]` in CORS policy.
- Use `Database.sql` to restore or recreate the project schema when needed.

---

## Presentation & App Demo
YouTube link: https://youtu.be/3TfSTQen59w
