"""
budget.py v3.2 — Fixes:
- CAT_ALIAS đầy đủ hơn (map DB name → JAR name)
- get_budget_with_spent(): logic hũ "Chi tiêu khác" chính xác
- check_budget_alert() giữ nguyên
- get_all_users_budget() giữ nguyên
"""
from db_connection import execute_query
from income import get_total_income
from expense import get_total_expense

# 8 hũ cố định — thứ tự hiển thị
JAR_NAMES = ["Ăn uống", "Lưu trú", "Di chuyển", "Giải trí",
             "Sức khỏe", "Giáo dục", "Mua sắm", "Tiết kiệm"]
OTHER_JAR  = "Chi tiêu khác"

# FIX 1: Alias map đầy đủ — tên DB → tên hũ chuẩn trong JAR_NAMES
# Bổ sung tất cả tên có thể xuất hiện trong ExpenseCategories
CAT_ALIAS = {
    "Tiền nhà":  "Lưu trú",
    "Nhà cửa":   "Lưu trú",   # tên trong DB seed → hũ "Lưu trú"
    "Nhà":       "Lưu trú",
    "Thuê nhà":  "Lưu trú",
    "Transport": "Di chuyển",
    "Food":      "Ăn uống",
    "Shopping":  "Mua sắm",
    "Health":    "Sức khỏe",
    "Education": "Giáo dục",
    "Saving":    "Tiết kiệm",
    "Savings":   "Tiết kiệm",
}

# FIX 2: Map ngược JAR name → CategoryName trong DB
# Dùng để tra CategoryID khi lưu BudgetLimits
JAR_TO_DB_NAME = {
    "Lưu trú": "Nhà cửa",  # hoặc tên thực trong DB của bạn
}


def get_budget_status(user_id, month, year):
    sql = "SELECT fn_budget_status(%s, %s, %s) AS status"
    row = execute_query(sql, (user_id, month, year), fetchall=False)
    return row["status"] if row else "WARNING"


def check_budget_alert(user_id, month, year):
    income  = get_total_income(user_id, month, year)
    expense = get_total_expense(user_id, month, year)
    status  = get_budget_status(user_id, month, year)
    net     = income - expense
    ratio = round((expense / income * 100), 1) if income > 0 else 0

    messages = {
        "OK":      "Chi tiêu hợp lý — dưới 70% thu nhập",
        "WARNING": "Chú ý — chi tiêu từ 70–100% thu nhập",
        "OVER":    "Vượt ngân sách — chi nhiều hơn thu!",
    }
    return {
        "income":  income,
        "expense": expense,
        "net":     net,
        "ratio":   ratio,
        "status":  status,
        "message": messages.get(status, ""),
    }


def get_budget_with_spent(user_id: int, month: int, year: int) -> list:
    """
    Trả về danh sách tối đa 8+1 hũ, mỗi hũ gồm:
      { name, limit, spent, pct, status }
    """
    # Lấy spent thực tế theo từng danh mục
    spent_rows = execute_query("""
        SELECT c.CategoryName, COALESCE(SUM(e.Amount), 0) AS spent
        FROM   Expenses e
        JOIN   ExpenseCategories c ON e.CategoryID = c.CategoryID
        WHERE  e.UserID    = %s
          AND  MONTH(e.ExpenseDate) = %s
          AND  YEAR(e.ExpenseDate)  = %s
          AND  e.IsDeleted = 0
        GROUP  BY c.CategoryName
    """, (user_id, month, year))

    # Áp dụng alias
    spent_map: dict[str, float] = {}
    for r in (spent_rows or []):
        jar_name = CAT_ALIAS.get(r["CategoryName"], r["CategoryName"])
        spent_map[jar_name] = spent_map.get(jar_name, 0) + float(r["spent"])

    # FIX 3: Dùng LEFT JOIN để không bị loại mất row có CategoryID IS NULL
    # Row NULL = hũ "Chi tiêu khác" / tổng tháng
    limit_rows = execute_query("""
        SELECT COALESCE(c.CategoryName, 'Chi tiêu khác') AS CategoryName,
               b.LimitAmount,
               b.CategoryID
        FROM   BudgetLimits b
        LEFT   JOIN ExpenseCategories c ON b.CategoryID = c.CategoryID
        WHERE  b.UserID = %s AND b.Month = %s AND b.Year = %s
    """, (user_id, month, year))
    limit_map: dict[str, float] = {}
    other_limit: float = 0.0
    for r in (limit_rows or []):
        if r["CategoryID"] is None:
            # Hũ "Chi tiêu khác" — không áp alias, lưu riêng
            other_limit += float(r["LimitAmount"])
        else:
            jar_name = CAT_ALIAS.get(r["CategoryName"], r["CategoryName"])
            limit_map[jar_name] = limit_map.get(jar_name, 0) + float(r["LimitAmount"])

    # Gom chi tiêu thuộc danh mục không nằm trong JAR_NAMES → hũ "Chi tiêu khác"
    known_names = set(JAR_NAMES)
    other_spent = sum(v for k, v in spent_map.items() if k not in known_names)

    # Xây dựng 8 hũ cố định
    jars = []
    for name in JAR_NAMES:
        lim   = limit_map.get(name, 0)
        spent = spent_map.get(name, 0)
        pct   = round((spent / lim * 100), 1) if lim > 0 else 0
        status = (
            "over" if lim > 0 and spent > lim
            else "warn" if lim > 0 and pct >= 70
            else "ok"
        )
        jars.append({
            "name":   name,
            "limit":  lim,
            "spent":  spent,
            "pct":    min(pct, 100),
            "status": status,
        })

    # Hũ "Chi tiêu khác" — thêm nếu có spent ngoài danh mục hoặc có limit
    if other_spent > 0 or other_limit > 0:
        pct = round((other_spent / other_limit * 100), 1) if other_limit > 0 else 0
        status = (
            "over" if other_limit > 0 and other_spent > other_limit
            else "warn" if other_limit > 0 and pct >= 70
            else "ok"
        )
        jars.append({
            "name":   OTHER_JAR,
            "limit":  other_limit,
            "spent":  other_spent,
            "pct":    min(pct, 100),
            "status": status,
        })

    return jars


def get_all_users_budget(month, year):
    sql = """
        SELECT u.UserID, u.UserName,
               fn_total_income(u.UserID, %s, %s)  AS Income,
               fn_total_expense(u.UserID, %s, %s) AS Expense,
               fn_budget_status(u.UserID, %s, %s) AS Status
        FROM   Users u
        ORDER  BY u.UserID
    """
    return execute_query(sql, (month, year, month, year, month, year))