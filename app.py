

import datetime
from decimal import Decimal
from typing import Optional, Any
from datetime import date
import bcrypt

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from db_connection import DatabaseError, execute_query, execute_update
from income  import add_income, get_income_by_month, soft_delete_income, get_total_income
from expense import (add_expense, get_expense_by_month, get_expense_by_category,
                     soft_delete_expense, get_categories, get_total_expense)
from account import get_balance, get_total_balance
from budget  import check_budget_alert, get_budget_with_spent
from reports import monthly_summary, yearly_summary

# ── App ───────────────────────────────────────────────────────

app = FastAPI(
    title="MoneyMate API",
    description="Hệ thống quản lý tài chính cá nhân — Project 13",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Đổi thành domain cụ thể khi deploy production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Helpers ───────────────────────────────────────────────────

def _serialize(obj: Any) -> Any:
    """Chuyển Decimal / Date / datetime → kiểu JSON-safe."""
    if obj is None:
        return None
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    return obj

# ── Pydantic Schemas ──────────────────────────────────────────

class IncomeCreate(BaseModel):
    user_id:     int
    amount:      float = Field(gt=0)
    income_date: date  = Field(default_factory=date.today)
    description: str   = ""
    account_id:  int

class ExpenseCreate(BaseModel):
    user_id:      int
    category_id:  int
    amount:       float = Field(gt=0)
    expense_date: date  = Field(default_factory=date.today)
    description:  str   = ""
    account_id:   int

class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class AccountCreate(BaseModel):
    user_id:         int
    bank_name:       str   = Field(min_length=1, max_length=100)
    initial_balance: float = Field(default=0, ge=0)

class AccountUpdate(BaseModel):
    bank_name: str = Field(min_length=1, max_length=100)

class BudgetLimitCreate(BaseModel):
    user_id:      int
    category_id:  Optional[int] = None   # None = hạn mức tổng tháng
    limit_amount: float = Field(gt=0)
    month:        int   = Field(ge=1, le=12)
    year:         int

class LoginRequest(BaseModel):
    email:    str
    password: str

class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    email:    str = Field(min_length=5, max_length=150)
    password: str = Field(min_length=6)
    phone:    str = ""

class RegisterRequest(BaseModel):
    username:     str = Field(min_length=2, max_length=100)
    email:        str = Field(min_length=5, max_length=150)
    phone:        str = Field(default="", max_length=15)
    password:     str = Field(min_length=6)

# ── 1. Health ─────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Ping thực sự vào DB để xác nhận kết nối."""
    try:
        execute_query("SELECT 1", fetchall=False)
        db_status = "connected"
    except Exception:
        db_status = "error"
    return {"status": "running", "database": db_status}

# ── 1b. Đăng ký & Đăng nhập ───────────────────────────────────

@app.post("/register", status_code=201)
def api_register(body: RegisterRequest):
    """
    Đăng ký tài khoản mới — hash mật khẩu bằng bcrypt trước khi lưu DB.
    Trả về thông tin user (không có hash) sau khi đăng ký thành công.
    """
    import bcrypt

    # Kiểm tra email đã tồn tại chưa
    existing = execute_query(
        "SELECT UserID FROM Users WHERE Email = %s",
        (body.email,), fetchall=False
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Email '{body.email}' đã được đăng ký.")

    # Hash mật khẩu với bcrypt (cost factor 12)
    pw_hash = bcrypt.hashpw(body.password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")

    user_id = execute_update(
        """INSERT INTO Users (UserName, Email, PhoneNumber, PasswordHash)
           VALUES (%s, %s, %s, %s)""",
        (body.username, body.email, body.phone or None, pw_hash)
    )
    return _serialize({
        "UserID":   user_id,
        "UserName": body.username,
        "Email":    body.email,
        "message":  "Đăng ký thành công!"
    })


@app.post("/login")
def api_login(body: LoginRequest):
    """Đăng nhập bằng Email + mật khẩu (bcrypt). Tài khoản seed cũ có hash NULL được bypass."""
    row = execute_query(
        "SELECT UserID, UserName, Email, PasswordHash FROM Users WHERE Email = %s",
        (body.email,), fetchall=False
    )
    if not row:
        raise HTTPException(status_code=401, detail="Email không tồn tại")

    stored_hash = row.get("PasswordHash") or ""
    # Chỉ verify bcrypt nếu có hash thật (dài > 30 ký tự và bắt đầu $2b$)
    if stored_hash and len(stored_hash) > 30 and stored_hash.startswith("$2b$"):
        try:
            if not bcrypt.checkpw(body.password.encode("utf-8"), stored_hash.encode("utf-8")):
                raise HTTPException(status_code=401, detail="Sai mật khẩu")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Sai mật khẩu")

    return _serialize({
        "UserID":   row["UserID"],
        "UserName": row["UserName"],
        "Email":    row["Email"],
    })

@app.post("/register", status_code=201)
def api_register(body: RegisterRequest):
    """Đăng ký tài khoản mới — hash mật khẩu bằng bcrypt cost 12."""
    existing = execute_query(
        "SELECT UserID FROM Users WHERE Email = %s",
        (body.email,), fetchall=False
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email này đã được đăng ký")

    hashed = bcrypt.hashpw(body.password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")
    user_id = execute_update(
        "INSERT INTO Users (UserName, Email, PhoneNumber, PasswordHash) VALUES (%s, %s, %s, %s)",
        (body.username, body.email, body.phone or None, hashed)
    )
    return _serialize({
        "UserID":   user_id,
        "UserName": body.username,
        "Email":    body.email,
        "message":  "Đăng ký thành công",
    })

# ── 2. Danh mục chi tiêu ─────────────────────────────────────

@app.get("/categories")
def api_get_categories():
    return _serialize(get_categories())

@app.post("/categories", status_code=201)
def api_create_category(body: CategoryCreate):
    """Thêm danh mục mới — kiểm tra trùng tên trước."""
    existing = execute_query(
        "SELECT CategoryID FROM ExpenseCategories WHERE CategoryName = %s",
        (body.name,), fetchall=False
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Danh mục '{body.name}' đã tồn tại.")
    cat_id = execute_update(
        "INSERT INTO ExpenseCategories (CategoryName) VALUES (%s)",
        (body.name,)
    )
    return {"id": cat_id, "name": body.name, "message": "Thêm danh mục thành công"}

# ── 3. Tài khoản ngân hàng ────────────────────────────────────

@app.get("/accounts/{user_id}")
def api_get_accounts(user_id: int):
    return {
        "items": _serialize(get_balance(user_id)),
        "total": get_total_balance(user_id),
    }

@app.post("/accounts", status_code=201)
def api_create_account(body: AccountCreate):
    """Thêm tài khoản ngân hàng mới — số dư ban đầu do user nhập (không qua trigger)."""
    acc_id = execute_update(
        "INSERT INTO BankAccounts (UserID, BankName, Balance) VALUES (%s, %s, %s)",
        (body.user_id, body.bank_name, body.initial_balance)
    )
    return {"id": acc_id, "bank_name": body.bank_name, "message": "Thêm tài khoản thành công"}

@app.put("/accounts/{account_id}")
def api_update_account(account_id: int, body: AccountUpdate):
    """Đổi tên tài khoản."""
    row = execute_query(
        "SELECT AccountID FROM BankAccounts WHERE AccountID = %s",
        (account_id,), fetchall=False
    )
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    execute_update(
        "UPDATE BankAccounts SET BankName = %s WHERE AccountID = %s",
        (body.bank_name, account_id)
    )
    return {"message": "Đã cập nhật tên tài khoản"}

# ── 4. Thu nhập ───────────────────────────────────────────────

@app.post("/income", status_code=201)
def api_create_income(body: IncomeCreate):
    income_id = add_income(
        body.user_id, body.amount,
        body.income_date.isoformat(),
        body.description, body.account_id
    )
    return {"id": income_id, "message": "Thêm thu nhập thành công"}

@app.get("/income")
def api_list_income(user_id: int, month: int, year: int):
    return _serialize(get_income_by_month(user_id, month, year))

@app.delete("/income/{income_id}")
def api_delete_income(income_id: int):
    """Soft-delete thu nhập — trigger DB tự hoàn lại số dư tài khoản."""
    row = execute_query(
        "SELECT IncomeID FROM Income WHERE IncomeID = %s AND IsDeleted = 0",
        (income_id,), fetchall=False
    )
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch thu nhập.")
    soft_delete_income(income_id)
    return {"ok": True, "message": f"Đã xóa thu nhập #{income_id}"}

# ── 5. Chi tiêu ───────────────────────────────────────────────

@app.post("/expenses", status_code=201)
def api_create_expense(body: ExpenseCreate):
    # FIX 2B: Kiểm tra số dư tài khoản trước khi ghi vào DB
    acc = execute_query(
        "SELECT Balance, BankName FROM BankAccounts WHERE AccountID = %s AND UserID = %s",
        (body.account_id, body.user_id), fetchall=False
    )
    if not acc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if float(acc["Balance"]) < body.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Số dư tài khoản {acc['BankName']} không đủ "
                   f"({float(acc['Balance']):,.0f} ₫ < {body.amount:,.0f} ₫)"
        )
    expense_id = add_expense(
        body.user_id, body.category_id, body.amount,
        body.expense_date.isoformat(), body.description, body.account_id
    )
    return {"id": expense_id, "message": "Thêm chi tiêu thành công"}

@app.get("/expenses")
def api_list_expenses(user_id: int, month: int, year: int, category_id: Optional[int] = None):
    return _serialize(get_expense_by_month(user_id, month, year, category_id))

@app.delete("/expenses/{expense_id}")
def api_delete_expense(expense_id: int):
    """Soft-delete chi tiêu — trigger DB tự hoàn lại số dư tài khoản."""
    row = execute_query(
        "SELECT ExpenseID FROM Expenses WHERE ExpenseID = %s AND IsDeleted = 0",
        (expense_id,), fetchall=False
    )
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch chi tiêu.")
    soft_delete_expense(expense_id)
    return {"ok": True, "message": f"Đã xóa chi tiêu #{expense_id}"}

# ── 6. Ngân sách / Budget Limits ─────────────────────────────

@app.get("/budget/jars/{user_id}")
def api_get_budget_jars(user_id: int, month: int, year: int):
    """
    Trả về tối đa 8 hũ ngân sách kèm spent + pct thực tế từ DB.
    Chi tiêu ngoài danh mục JAR chuẩn → gộp vào hũ 'Chi tiêu khác'.
    """
    return _serialize(get_budget_with_spent(user_id, month, year))

@app.get("/budget/{user_id}")
def api_get_budget(user_id: int, month: int, year: int):
    """Lấy toàn bộ hạn mức ngân sách của user trong tháng/năm."""
    rows = execute_query("""
        SELECT b.BudgetID,
               b.CategoryID,
               COALESCE(c.CategoryName, 'Tổng tháng') AS CategoryName,
               b.LimitAmount,
               b.Month,
               b.Year
        FROM   BudgetLimits b
        LEFT   JOIN ExpenseCategories c ON b.CategoryID = c.CategoryID
        WHERE  b.UserID = %s
          AND  b.Month  = %s
          AND  b.Year   = %s
        ORDER  BY b.CategoryID
    """, (user_id, month, year))
    return _serialize(rows)

@app.post("/budget", status_code=201)
def api_set_budget(body: BudgetLimitCreate):
    """Thêm hoặc cập nhật hạn mức (INSERT … ON DUPLICATE KEY UPDATE)."""
    execute_update("""
        INSERT INTO BudgetLimits (UserID, CategoryID, LimitAmount, Month, Year)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE LimitAmount = VALUES(LimitAmount)
    """, (body.user_id, body.category_id, body.limit_amount, body.month, body.year))
    return {"message": "Đã lưu hạn mức"}

@app.delete("/budget/{budget_id}")
def api_delete_budget(budget_id: int):
    """Xóa một hạn mức theo BudgetID."""
    row = execute_query(
        "SELECT BudgetID FROM BudgetLimits WHERE BudgetID = %s",
        (budget_id,), fetchall=False
    )
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy hạn mức.")
    execute_update("DELETE FROM BudgetLimits WHERE BudgetID = %s", (budget_id,))
    return {"ok": True, "message": f"Đã xóa hạn mức #{budget_id}"}

# ── 7. Dashboard & Báo cáo ────────────────────────────────────

@app.get("/dashboard/{user_id}")
def api_get_dashboard(
    user_id: int,
    month:   Optional[int] = None,
    year:    Optional[int] = None,
):
    m = month or date.today().month
    y = year  or date.today().year

    # Dùng trực tiếp get_total_income / get_total_expense thay vì monthly_summary
    # để tránh lỗi khi reports.py không trả về dict hoặc không có tham số silent
    total_inc = get_total_income(user_id, m, y)
    total_exp = get_total_expense(user_id, m, y)
    summary = {
        "TotalIncome":  total_inc,
        "TotalExpense": total_exp,
        "NetBalance":   total_inc - total_exp,
        "Status":       "SURPLUS" if (total_inc - total_exp) >= 0 else "DEFICIT",
    }

    top_categories = get_expense_by_category(user_id, m, y)
    budget_info    = check_budget_alert(user_id, m, y)

    return _serialize({
        "summary":              summary,
        "expenses_by_category": top_categories,
        "budget":               budget_info,
        "timestamp":            datetime.datetime.now(),
    })

@app.get("/reports/yearly/{user_id}")
def api_report_yearly(user_id: int, year: int):
    return _serialize(yearly_summary(user_id, year))

# ── 8. Error handlers ─────────────────────────────────────────

@app.exception_handler(DatabaseError)
async def db_exception_handler(request: Request, exc: DatabaseError):
    return JSONResponse(
        status_code=503,
        content={"detail": f"Lỗi Database: {str(exc)}"}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Lỗi server: {str(exc)}"}
    )