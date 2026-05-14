"""
MoneyMate — Personal Finance Management System
Project 13 · NEU-College of Technology
"""
from datetime import date

from income  import add_income, get_income_by_month, soft_delete_income
from expense import (add_expense, get_expense_by_month,
                     get_expense_by_category, soft_delete_expense, get_categories)
from account import get_balance, get_total_balance, show_balance_history
from budget  import check_budget_alert, get_all_users_budget
from reports import monthly_summary, yearly_summary, category_report, comparison_report

TODAY = date.today()
FMT   = "%Y-%m-%d"


# ── Utils ─────────────────────────────────────────────────────
def sep(char="═", n=52): print(char * n)
def header(title):
    print(); sep()
    print(f"  {title}")
    sep()

def ask_int(prompt, default=None):
    val = input(f"  {prompt} [{default}]: ").strip() if default else input(f"  {prompt}: ").strip()
    return int(val) if val else default

def ask_float(prompt):
    return float(input(f"  {prompt}: ").strip())

def ask_str(prompt, default=""):
    val = input(f"  {prompt} [{default}]: ").strip() if default else input(f"  {prompt}: ").strip()
    return val if val else default

def ask_date(prompt):
    val = input(f"  {prompt} [{TODAY}]: ").strip()
    return val if val else str(TODAY)

def current_user_id():
    uid = input("  User ID (mặc định 1): ").strip()
    return int(uid) if uid else 1


# ── Menu handlers ─────────────────────────────────────────────
def menu_add_income():
    header("THÊM THU NHẬP")
    uid   = current_user_id()
    # FIX: show user's accounts so they can pick which account receives money
    from account import get_balance
    accounts = get_balance(uid)
    if accounts:
        print()
        for a in accounts:
            print(f"    [{a['AccountID']}] {a['BankName']}  —  {float(a['Balance']):,.0f} ₫")
        print()
    acc_id = ask_int("AccountID nhận tiền (Enter để bỏ qua)")
    amt   = ask_float("Số tiền (₫)")
    dt    = ask_date("Ngày (YYYY-MM-DD)")
    desc  = ask_str("Mô tả")
    add_income(uid, amt, dt, desc, account_id=acc_id)

def menu_add_expense():
    header("THÊM CHI TIÊU")
    cats = get_categories()
    print()
    for c in cats:
        print(f"    [{c['CategoryID']}] {c['CategoryName']}")
    print()
    uid  = current_user_id()
    # FIX: show user's accounts so they can pick which account is debited
    from account import get_balance
    accounts = get_balance(uid)
    if accounts:
        print()
        for a in accounts:
            print(f"    [{a['AccountID']}] {a['BankName']}  —  {float(a['Balance']):,.0f} ₫")
        print()
    acc_id = ask_int("AccountID thanh toán từ (Enter để bỏ qua)")
    cid  = ask_int("Category ID")
    amt  = ask_float("Số tiền (₫)")
    dt   = ask_date("Ngày (YYYY-MM-DD)")
    desc = ask_str("Mô tả")
    add_expense(uid, cid, amt, dt, desc, account_id=acc_id)

def menu_view_income():
    header("XEM THU NHẬP THEO THÁNG")
    uid   = current_user_id()
    month = ask_int("Tháng", TODAY.month)
    year  = ask_int("Năm",  TODAY.year)
    rows  = get_income_by_month(uid, month, year)
    if not rows:
        print("  Không có dữ liệu."); return
    print(f"\n  {'ID':<6} {'Ngày':<12} {'Số tiền':>14}  Mô tả")
    print("  " + "·" * 54)
    for r in rows:
        print(f"  #{r['IncomeID']:<5} {str(r['IncomeDate']):<12} {float(r['Amount']):>13,.0f} ₫  {r['Description']}")

def menu_view_expense():
    header("XEM CHI TIÊU THEO THÁNG")
    uid   = current_user_id()
    month = ask_int("Tháng", TODAY.month)
    year  = ask_int("Năm",  TODAY.year)
    rows  = get_expense_by_month(uid, month, year)
    if not rows:
        print("  Không có dữ liệu."); return
    print(f"\n  {'ID':<6} {'Ngày':<12} {'Danh mục':<14} {'Số tiền':>14}  Mô tả")
    print("  " + "·" * 66)
    for r in rows:
        print(f"  #{r['ExpenseID']:<5} {str(r['ExpenseDate']):<12} {r['CategoryName']:<14} {float(r['Amount']):>13,.0f} ₫  {r['Description']}")

def menu_balance():
    header("SỐ DƯ TÀI KHOẢN")
    uid  = current_user_id()
    rows = get_balance(uid)
    for r in rows:
        print(f"  🏦 {r['BankName']:<16} {float(r['Balance']):>14,.0f} ₫")
    total = get_total_balance(uid)
    print(f"\n  {'TỔNG':<18} {total:>14,.0f} ₫")

def menu_balance_history():
    header("LỊCH SỬ GIAO DỊCH")
    uid   = current_user_id()
    limit = ask_int("Số giao dịch gần nhất", 10)
    rows  = show_balance_history(uid, limit)
    print(f"\n  {'Loại':<12} {'Ngày':<12} {'Số tiền':>14}  Mô tả")
    print("  " + "·" * 56)
    for r in rows:
        icon = "  ↑" if r["Type"] == "Thu nhập" else "  ↓"
        print(f"  {icon} {r['Type']:<10} {str(r['TxDate']):<12} {float(r['Amount']):>13,.0f} ₫  {r['Description']}")

def menu_budget_alert():
    header("KIỂM TRA NGÂN SÁCH")
    uid   = current_user_id()
    month = ask_int("Tháng", TODAY.month)
    year  = ask_int("Năm",  TODAY.year)
    info  = check_budget_alert(uid, month, year)
    print(f"\n  {info['message']}")
    print(f"  Thu nhập   : {info['income']:>14,.0f} ₫")
    print(f"  Chi tiêu   : {info['expense']:>14,.0f} ₫  ({info['ratio']:.1f}% thu nhập)")
    print(f"  Còn lại    : {info['net']:>14,.0f} ₫")

def menu_all_users_budget():
    header("NGÂN SÁCH TẤT CẢ USERS")
    month = ask_int("Tháng", TODAY.month)
    year  = ask_int("Năm",  TODAY.year)
    rows  = get_all_users_budget(month, year)
    print(f"\n  {'User':<18} {'Thu nhập':>14} {'Chi tiêu':>14}  Status")
    print("  " + "·" * 60)
    icons = {"OK": "✅", "WARNING": "⚠️ ", "OVER": "🚨"}
    for r in rows:
        icon = icons.get(r["Status"], "")
        print(f"  {r['UserName']:<18} {float(r['Income']):>13,.0f} ₫ {float(r['Expense']):>13,.0f} ₫  {icon} {r['Status']}")

def menu_monthly_report():
    header("BÁO CÁO THÁNG")
    uid   = current_user_id()
    month = ask_int("Tháng", TODAY.month)
    year  = ask_int("Năm",  TODAY.year)
    monthly_summary(uid, month, year)

def menu_yearly_report():
    header("BÁO CÁO NĂM")
    uid  = current_user_id()
    year = ask_int("Năm", TODAY.year)
    yearly_summary(uid, year)

def menu_category_report():
    header("BÁO CÁO THEO DANH MỤC")
    uid   = current_user_id()
    month = ask_int("Tháng", TODAY.month)
    year  = ask_int("Năm",  TODAY.year)
    category_report(uid, month, year)

def menu_comparison_report():
    header("SO SÁNH VỚI TRUNG BÌNH 3 THÁNG")
    uid = current_user_id()
    comparison_report(uid)

def menu_soft_delete():
    header("XÓA GIAO DỊCH (Soft Delete)")
    kind = input("  Xóa [1] Thu nhập  [2] Chi tiêu: ").strip()
    rid  = ask_int("ID cần xóa")
    if kind == "1":
        soft_delete_income(rid)
    elif kind == "2":
        soft_delete_expense(rid)


# ── Main Menu ─────────────────────────────────────────────────
MENUS = [
    ("── Giao dịch ──────────────────────", None),
    ("Thêm thu nhập",          menu_add_income),
    ("Thêm chi tiêu",          menu_add_expense),
    ("Xóa giao dịch",          menu_soft_delete),
    ("── Xem dữ liệu ───────────────────", None),
    ("Xem thu nhập theo tháng",menu_view_income),
    ("Xem chi tiêu theo tháng",menu_view_expense),
    ("Số dư tài khoản",        menu_balance),
    ("Lịch sử giao dịch",      menu_balance_history),
    ("── Ngân sách ──────────────────────", None),
    ("Kiểm tra ngân sách",     menu_budget_alert),
    ("Ngân sách tất cả users", menu_all_users_budget),
    ("── Báo cáo ────────────────────────", None),
    ("Tổng kết tháng",         menu_monthly_report),
    ("Tổng kết năm",           menu_yearly_report),
    ("Chi tiêu theo danh mục", menu_category_report),
    ("So sánh vs Avg 3 tháng", menu_comparison_report),
]

def show_menu():
    sep()
    print("  💰 MONEYMATE — Personal Finance System")
    sep()
    idx = 1
    for label, fn in MENUS:
        if fn is None:
            print(f"\n  {label}")
        else:
            print(f"  [{idx:>2}] {label}")
            idx += 1
    print("\n  [ 0] Thoát")
    sep()


def run():
    actions = [(label, fn) for label, fn in MENUS if fn is not None]
    while True:
        show_menu()
        choice = input("  Chọn: ").strip()
        if choice == "0":
            print("\n  Tạm biệt! 👋\n")
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(actions):
                actions[idx][1]()
            else:
                print("  ❌ Lựa chọn không hợp lệ.")
        except ValueError:
            print("  ❌ Vui lòng nhập số.")
        except Exception as e:
            print(f"  ❌ Lỗi: {e}")
        input("\n  [Enter để tiếp tục...]")


if __name__ == "__main__":
    run()