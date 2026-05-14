from db_connection import execute_query


def get_balance(user_id):
    sql = """
        SELECT AccountID, BankName, Balance
        FROM   BankAccounts
        WHERE  UserID = %s
        ORDER  BY AccountID
    """
    return execute_query(sql, (user_id,))


def get_total_balance(user_id):
    sql = "SELECT COALESCE(SUM(Balance), 0) AS total FROM BankAccounts WHERE UserID = %s"
    row = execute_query(sql, (user_id,), fetchall=False)
    return float(row["total"]) if row else 0.0


def show_balance_history(user_id, limit=10):
    sql = """
        SELECT 'Thu nhập' AS Type, Amount, IncomeDate AS TxDate, Description
        FROM   Income
        WHERE  UserID = %s AND IsDeleted = 0

        UNION ALL

        SELECT 'Chi tiêu' AS Type, Amount, ExpenseDate AS TxDate, Description
        FROM   Expenses
        WHERE  UserID = %s AND IsDeleted = 0

        ORDER  BY TxDate DESC
        LIMIT  %s
    """
    return execute_query(sql, (user_id, user_id, limit))
