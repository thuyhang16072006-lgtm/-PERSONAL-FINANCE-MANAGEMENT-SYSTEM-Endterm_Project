from db_connection import execute_query, execute_update


def add_expense(user_id: int, category_id: int, amount: float,
                expense_date: str, description: str = "", account_id: int = None):
    """
    FIX: accepts optional account_id so user can choose which bank account
    is debited. Trigger will update that specific account.
    """
    sql = """
        INSERT INTO Expenses (UserID, AccountID, CategoryID, Amount, ExpenseDate, Description)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    expense_id = execute_update(
        sql, (user_id, account_id, category_id, amount, expense_date, description)
    )
    print(f"  ✓ Đã thêm chi tiêu #{expense_id}: {amount:,.0f} ₫ — {description}")
    return expense_id


def get_expense_by_month(user_id: int, month: int, year: int, category_id: int = None):
    if category_id:
        sql = """
            SELECT e.ExpenseID, c.CategoryName, e.Amount, e.ExpenseDate,
                   e.Description, b.BankName, e.AccountID
            FROM   Expenses e
            JOIN   ExpenseCategories c ON e.CategoryID = c.CategoryID
            LEFT JOIN BankAccounts  b  ON e.AccountID  = b.AccountID
            WHERE  e.UserID = %s
              AND  MONTH(e.ExpenseDate) = %s
              AND  YEAR(e.ExpenseDate)  = %s
              AND  e.CategoryID = %s
              AND  e.IsDeleted = 0
            ORDER  BY e.ExpenseDate DESC, e.ExpenseID DESC
        """
        return execute_query(sql, (user_id, month, year, category_id))
    sql = """
        SELECT e.ExpenseID, c.CategoryName, e.Amount, e.ExpenseDate,
               e.Description, b.BankName, e.AccountID
        FROM   Expenses e
        JOIN   ExpenseCategories c ON e.CategoryID = c.CategoryID
        LEFT JOIN BankAccounts  b  ON e.AccountID  = b.AccountID
        WHERE  e.UserID = %s
          AND  MONTH(e.ExpenseDate) = %s
          AND  YEAR(e.ExpenseDate)  = %s
          AND  e.IsDeleted = 0
        ORDER  BY e.ExpenseDate DESC, e.ExpenseID DESC
    """
    return execute_query(sql, (user_id, month, year))


def get_expense_by_category(user_id: int, month: int, year: int):
    sql = """
        SELECT c.CategoryName,
               SUM(e.Amount)  AS TotalSpent,
               COUNT(*)       AS NumTransactions
        FROM   Expenses e
        JOIN   ExpenseCategories c ON e.CategoryID = c.CategoryID
        WHERE  e.UserID = %s
          AND  MONTH(e.ExpenseDate) = %s
          AND  YEAR(e.ExpenseDate)  = %s
          AND  e.IsDeleted = 0
        GROUP  BY c.CategoryName
        ORDER  BY TotalSpent DESC
    """
    return execute_query(sql, (user_id, month, year))


def get_top5_categories(user_id: int):
    sql = """
        SELECT c.CategoryName,
               SUM(e.Amount) AS TotalSpent,
               COUNT(*)      AS NumTransactions
        FROM   Expenses e
        JOIN   ExpenseCategories c ON e.CategoryID = c.CategoryID
        WHERE  e.UserID = %s AND e.IsDeleted = 0
        GROUP  BY c.CategoryName
        ORDER  BY TotalSpent DESC
        LIMIT  5
    """
    return execute_query(sql, (user_id,))


def get_total_expense(user_id: int, month: int, year: int) -> float:
    sql = "SELECT fn_total_expense(%s, %s, %s) AS total"
    row = execute_query(sql, (user_id, month, year), fetchall=False)
    return float(row["total"]) if row else 0.0


def soft_delete_expense(expense_id: int):
    execute_update("UPDATE Expenses SET IsDeleted = 1 WHERE ExpenseID = %s", (expense_id,))
    print(f"  ✓ Đã xóa chi tiêu #{expense_id}")


def get_categories():
    return execute_query(
        "SELECT CategoryID, CategoryName FROM ExpenseCategories ORDER BY CategoryID"
    )