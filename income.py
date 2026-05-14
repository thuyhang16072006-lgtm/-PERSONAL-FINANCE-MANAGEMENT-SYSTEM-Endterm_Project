from db_connection import execute_query, execute_update


def add_income(user_id: int, amount: float, income_date: str,
               description: str = "", account_id: int = None):
    """
    FIX: accepts optional account_id so user can choose which bank account
    receives the income. Trigger will update that specific account.
    """
    sql = """
        INSERT INTO Income (UserID, AccountID, Amount, IncomeDate, Description)
        VALUES (%s, %s, %s, %s, %s)
    """
    income_id = execute_update(sql, (user_id, account_id, amount, income_date, description))
    print(f"  ✓ Đã thêm thu nhập #{income_id}: {amount:,.0f} ₫ — {description}")
    return income_id


def get_income_by_month(user_id: int, month: int, year: int):
    sql = """
        SELECT i.IncomeID, i.Amount, i.IncomeDate, i.Description,
               b.BankName, i.AccountID
        FROM   Income i
        LEFT JOIN BankAccounts b ON i.AccountID = b.AccountID
        WHERE  i.UserID = %s
          AND  MONTH(i.IncomeDate) = %s
          AND  YEAR(i.IncomeDate)  = %s
          AND  i.IsDeleted = 0
        ORDER  BY i.IncomeDate DESC, i.IncomeID DESC
    """
    return execute_query(sql, (user_id, month, year))


def get_total_income(user_id: int, month: int, year: int) -> float:
    sql = "SELECT fn_total_income(%s, %s, %s) AS total"
    row = execute_query(sql, (user_id, month, year), fetchall=False)
    return float(row["total"]) if row else 0.0


def soft_delete_income(income_id: int):
    execute_update("UPDATE Income SET IsDeleted = 1 WHERE IncomeID = %s", (income_id,))
    print(f"  ✓ Đã xóa thu nhập #{income_id}")