"""
reports.py v3.0
FIX:
- Sửa KeyError row['Status'] — dùng .get() fallback
- yearly_summary dùng v_monthly_income/v_monthly_expense đã có lại
- category_report giữ lại (main.py cần)
- comparison_report dùng đúng v_monthly_expense
"""
from db_connection import execute_query
from expense import get_expense_by_category

try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

COLORS = ["#ff6eb4","#c084fc","#fbbf24","#4ade80","#5b9cf6",
          "#fb7a55","#38bdf8","#e879f9","#f87171","#60e0c0"]


def _fmt(amount: float) -> str:
    return f"{amount:>14,.0f} ₫"

def _sep(char="─", n=52):
    print(char * n)


def monthly_summary(user_id: int, month: int, year: int, silent: bool = False) -> dict:
    rows = execute_query("CALL sp_monthly_close(%s, %s, %s)", (user_id, month, year))
    if not rows:
        if not silent: print("  Không có dữ liệu.")
        return {}
    row = rows[0]
    # FIX: dùng .get() — an toàn với cả DB cũ không có cột Status
    net    = float(row.get("NetBalance", 0))
    status = row.get("Status", "SURPLUS" if net >= 0 else "DEFICIT")
    row["Status"] = status
    if not silent:
        _sep()
        print(f"  TỔNG KẾT THÁNG {month:02d}/{year} — User #{user_id}")
        _sep()
        print(f"  Thu nhập   : {_fmt(float(row['TotalIncome']))}")
        print(f"  Chi tiêu   : {_fmt(float(row['TotalExpense']))}")
        print(f"  Còn lại    : {_fmt(net)}")
        print(f"  Trạng thái : {'✅ THẶNG DƯ' if status == 'SURPLUS' else '🔴 THÂM HỤT'}")
        _sep()
    return row


def yearly_summary(user_id: int, year: int) -> list:
    # FIX: dùng v_monthly_income + v_monthly_expense (đã thêm lại vào DB v3.0)
    sql = """
        SELECT m.Month,
               COALESCE(inc.TotalIncome,  0) AS Income,
               COALESCE(exp.TotalExpense, 0) AS Expense,
               COALESCE(inc.TotalIncome,0) - COALESCE(exp.TotalExpense,0) AS Net
        FROM (SELECT 1 AS Month UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
              UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8
              UNION SELECT 9 UNION SELECT 10 UNION SELECT 11 UNION SELECT 12) m
        LEFT JOIN v_monthly_income  inc ON inc.UserID=%s AND inc.Year=%s AND inc.Month=m.Month
        LEFT JOIN v_monthly_expense exp ON exp.UserID=%s AND exp.Year=%s AND exp.Month=m.Month
        ORDER BY m.Month
    """
    rows = execute_query(sql, (user_id, year, user_id, year))
    print(f"\n  TỔNG KẾT NĂM {year} — User #{user_id}")
    _sep()
    print(f"  {'Tháng':<8} {'Thu nhập':>14} {'Chi tiêu':>14} {'Còn lại':>14}")
    _sep("·")
    for r in rows:
        if float(r["Income"]) == 0 and float(r["Expense"]) == 0:
            continue
        icon = "✅" if float(r["Net"]) >= 0 else "🔴"
        print(f"  T{r['Month']:02d}      {_fmt(float(r['Income']))} {_fmt(float(r['Expense']))} {_fmt(float(r['Net']))} {icon}")
    _sep()
    return rows


def category_report(user_id: int, month: int, year: int) -> list:
    rows = get_expense_by_category(user_id, month, year)
    if not rows:
        print("  Không có chi tiêu nào.")
        return []
    total = sum(float(r["TotalSpent"]) for r in rows)
    _sep()
    print(f"  CHI TIÊU THEO DANH MỤC — T{month:02d}/{year}")
    _sep()
    for r in rows:
        amt = float(r["TotalSpent"])
        pct = amt / total * 100 if total > 0 else 0
        bar = "█" * int(pct / 5)
        print(f"  {r['CategoryName']:<16} {_fmt(amt)} {pct:5.1f}%  {bar}")
    _sep()
    if HAS_MPL: _plot_category_bar(rows, month, year)
    return rows


def comparison_report(user_id: int) -> list:

    sql = """
        SELECT Year, Month, TotalExpense,
               ROUND(AVG(TotalExpense) OVER (
                   PARTITION BY UserID ORDER BY Year, Month
                   ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
               ), 0) AS Avg3MonthsBefore
        FROM v_monthly_expense
        WHERE UserID=%s
        ORDER BY Year, Month
    """
    rows = execute_query(sql, (user_id,))
    if not rows:
        print("  Không đủ dữ liệu.")
        return []
    _sep()
    print(f"  SO SÁNH CHI TIÊU VS AVG 3 THÁNG TRƯỚC")
    _sep()
    for r in rows:
        curr = float(r["TotalExpense"])
        avg  = float(r["Avg3MonthsBefore"]) if r["Avg3MonthsBefore"] else 0
        diff = curr - avg
        icon = "🔺" if diff > 0 else "🔹"
        print(f"  {r['Month']:02d}/{r['Year']}   {_fmt(curr)} vs {_fmt(avg)}  {icon}{abs(diff):,.0f}")
    _sep()
    if HAS_MPL: _plot_comparison(rows)
    return rows


# ── Matplotlib ────────────────────────────────────────────────
def _setup_dark():
    plt.style.use("dark_background")
    plt.rcParams.update({
        "axes.facecolor": "#160f1a", "figure.facecolor": "#0d0a0f",
        "text.color": "#f5eef8", "xtick.color": "#9b7eab", "ytick.color": "#9b7eab",
    })

def _plot_category_bar(rows, month, year):
    _setup_dark()
    labels = [r["CategoryName"] for r in rows]
    values = [float(r["TotalSpent"]) for r in rows]
    fig, ax = plt.subplots(figsize=(8, max(3, len(rows) * 0.7)))
    bars = ax.barh(labels, values, color=[COLORS[i % len(COLORS)] for i in range(len(rows))],
                   height=0.55, edgecolor="none")
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values)*0.01, bar.get_y()+bar.get_height()/2,
                f"{val:,.0f} ₫", va="center", fontsize=9)
    ax.set_title(f"Chi tiêu theo danh mục — T{month:02d}/{year}", fontsize=12)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1e6:.1f}M"))
    ax.invert_yaxis(); ax.grid(axis="x", alpha=0.3); plt.tight_layout()
    fname = f"report_category_{year}{month:02d}.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight")
    print(f"  📊 {fname}"); plt.show()

def _plot_comparison(rows):
    _setup_dark()
    labels = [f"T{r['Month']:02d}/{r['Year']}" for r in rows]
    curr = [float(r["TotalExpense"]) for r in rows]
    avg3 = [float(r["Avg3MonthsBefore"]) if r["Avg3MonthsBefore"] else 0 for r in rows]
    fig, ax = plt.subplots(figsize=(9, 4))
    x = range(len(labels))
    ax.plot(x, curr, color="#ff6eb4", linewidth=2.2, marker="o", markersize=5, label="Tháng này")
    ax.plot(x, avg3, color="#9b7eab", linewidth=1.5, linestyle="--", marker="o",
            markersize=4, label="Avg 3 tháng trước")
    ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v/1e6:.1f}M"))
    ax.set_title("Chi tiêu vs Avg 3 tháng trước"); ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("report_comparison.png", dpi=150, bbox_inches="tight")
    print("  📊 report_comparison.png"); plt.show()