-- ============================================================
--  MoneyMate — Personal Finance Management System
--  Project 13 · NEU-College of Technology
--  FULL PRODUCTION SCRIPT v3.0
-- ============================================================

CREATE DATABASE IF NOT EXISTS moneymate
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE moneymate;

-- ── 1. Cấu trúc bảng ──────────────────────────────────────────

CREATE TABLE Users (
    UserID       INT AUTO_INCREMENT PRIMARY KEY,
    UserName     VARCHAR(100) NOT NULL,
    Email        VARCHAR(150) NOT NULL UNIQUE,
    PhoneNumber  VARCHAR(15),
    PasswordHash VARCHAR(255) NULL,
    CreatedAt    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ExpenseCategories (
    CategoryID   INT AUTO_INCREMENT PRIMARY KEY,
    CategoryName VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE BankAccounts (
    AccountID INT AUTO_INCREMENT PRIMARY KEY,
    UserID    INT NOT NULL,
    BankName  VARCHAR(100) NOT NULL,
    Balance   DECIMAL(15,2) NOT NULL DEFAULT 0,
    CONSTRAINT fk_ba_user FOREIGN KEY (UserID) REFERENCES Users(UserID)
);

CREATE TABLE Income (
    IncomeID    INT AUTO_INCREMENT PRIMARY KEY,
    UserID      INT NOT NULL,
    AccountID   INT NOT NULL,
    Amount      DECIMAL(15,2) NOT NULL CHECK (Amount > 0),
    IncomeDate  DATE NOT NULL,
    Description VARCHAR(255),
    IsDeleted   TINYINT(1) NOT NULL DEFAULT 0,
    CONSTRAINT fk_inc_user    FOREIGN KEY (UserID)    REFERENCES Users(UserID),
    CONSTRAINT fk_inc_account FOREIGN KEY (AccountID) REFERENCES BankAccounts(AccountID)
);

CREATE TABLE Expenses (
    ExpenseID   INT AUTO_INCREMENT PRIMARY KEY,
    UserID      INT NOT NULL,
    AccountID   INT NOT NULL,
    CategoryID  INT NOT NULL,
    Amount      DECIMAL(15,2) NOT NULL CHECK (Amount > 0),
    ExpenseDate DATE NOT NULL,
    Description VARCHAR(255),
    IsDeleted   TINYINT(1) NOT NULL DEFAULT 0,
    CONSTRAINT fk_exp_user    FOREIGN KEY (UserID)     REFERENCES Users(UserID),
    CONSTRAINT fk_exp_cat     FOREIGN KEY (CategoryID) REFERENCES ExpenseCategories(CategoryID),
    CONSTRAINT fk_exp_account FOREIGN KEY (AccountID)  REFERENCES BankAccounts(AccountID)
);

CREATE TABLE BudgetLimits (
    BudgetID    INT AUTO_INCREMENT PRIMARY KEY,
    UserID      INT NOT NULL,
    CategoryID  INT NULL,                          -- NULL = hũ "Chi tiêu khác" / tổng tháng
    LimitAmount DECIMAL(15,2) NOT NULL CHECK (LimitAmount > 0),
    Month       TINYINT NOT NULL CHECK (Month BETWEEN 1 AND 12),
    Year        SMALLINT NOT NULL,
    CONSTRAINT fk_bl_user FOREIGN KEY (UserID)     REFERENCES Users(UserID),
    CONSTRAINT fk_bl_cat  FOREIGN KEY (CategoryID) REFERENCES ExpenseCategories(CategoryID),
    -- MySQL NULL != NULL nên UNIQUE(UserID,CategoryID,Month,Year) cho phép nhiều NULL row
    -- Dùng unique index + partial approach: tạo index riêng
    CONSTRAINT uq_budget  UNIQUE (UserID, CategoryID, Month, Year)
);

CREATE INDEX idx_expenses_user_date ON Expenses(UserID, ExpenseDate);
CREATE INDEX idx_income_user_date   ON Income(UserID, IncomeDate);

-- ── 2. Triggers ───────────────────────────────────────────────

DELIMITER $$

-- FIX 2A: Dùng BEFORE INSERT để chặn chi tiêu khi số dư không đủ
CREATE TRIGGER trg_before_insert_expense
BEFORE INSERT ON Expenses FOR EACH ROW
BEGIN
    DECLARE v_bal DECIMAL(15,2);
    IF NEW.IsDeleted = 0 THEN
        SELECT Balance INTO v_bal
        FROM BankAccounts
        WHERE AccountID = NEW.AccountID;
        IF v_bal < NEW.Amount THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Số dư tài khoản không đủ để thực hiện giao dịch này';
        END IF;
    END IF;
END$$

CREATE TRIGGER trg_after_insert_income
AFTER INSERT ON Income FOR EACH ROW
BEGIN
    IF NEW.IsDeleted = 0 THEN
        UPDATE BankAccounts SET Balance = Balance + NEW.Amount WHERE AccountID = NEW.AccountID;
    END IF;
END$$

CREATE TRIGGER trg_after_insert_expense
AFTER INSERT ON Expenses FOR EACH ROW
BEGIN
    IF NEW.IsDeleted = 0 THEN
        UPDATE BankAccounts SET Balance = Balance - NEW.Amount WHERE AccountID = NEW.AccountID;
    END IF;
END$$

CREATE TRIGGER trg_after_update_income
AFTER UPDATE ON Income FOR EACH ROW
BEGIN
    IF OLD.IsDeleted = 0 AND NEW.IsDeleted = 1 THEN
        UPDATE BankAccounts SET Balance = Balance - OLD.Amount WHERE AccountID = OLD.AccountID;
    ELSEIF OLD.IsDeleted = 1 AND NEW.IsDeleted = 0 THEN
        UPDATE BankAccounts SET Balance = Balance + NEW.Amount WHERE AccountID = NEW.AccountID;
    ELSEIF NEW.IsDeleted = 0 THEN
        UPDATE BankAccounts SET Balance = Balance - OLD.Amount WHERE AccountID = OLD.AccountID;
        UPDATE BankAccounts SET Balance = Balance + NEW.Amount WHERE AccountID = NEW.AccountID;
    END IF;
END$$

CREATE TRIGGER trg_after_update_expense
AFTER UPDATE ON Expenses FOR EACH ROW
BEGIN
    IF OLD.IsDeleted = 0 AND NEW.IsDeleted = 1 THEN
        UPDATE BankAccounts SET Balance = Balance + OLD.Amount WHERE AccountID = OLD.AccountID;
    ELSEIF OLD.IsDeleted = 1 AND NEW.IsDeleted = 0 THEN
        UPDATE BankAccounts SET Balance = Balance - NEW.Amount WHERE AccountID = NEW.AccountID;
    ELSEIF NEW.IsDeleted = 0 THEN
        UPDATE BankAccounts SET Balance = Balance + OLD.Amount WHERE AccountID = OLD.AccountID;
        UPDATE BankAccounts SET Balance = Balance - NEW.Amount WHERE AccountID = NEW.AccountID;
    END IF;
END$$

DELIMITER ;

-- ── 3. Views ──────────────────────────────────────────────────

-- FIX: Thêm lại 2 views bị thiếu — được dùng bởi reports.py
CREATE VIEW v_monthly_income AS
SELECT
    u.UserID,
    u.UserName,
    YEAR(i.IncomeDate)  AS Year,
    MONTH(i.IncomeDate) AS Month,
    SUM(i.Amount)       AS TotalIncome
FROM Income i
JOIN Users u ON i.UserID = u.UserID
WHERE i.IsDeleted = 0
GROUP BY u.UserID, u.UserName, YEAR(i.IncomeDate), MONTH(i.IncomeDate);

CREATE VIEW v_monthly_expense AS
SELECT
    u.UserID,
    u.UserName,
    YEAR(e.ExpenseDate)  AS Year,
    MONTH(e.ExpenseDate) AS Month,
    SUM(e.Amount)        AS TotalExpense
FROM Expenses e
JOIN Users u ON e.UserID = u.UserID
WHERE e.IsDeleted = 0
GROUP BY u.UserID, u.UserName, YEAR(e.ExpenseDate), MONTH(e.ExpenseDate);

CREATE VIEW v_category_spending AS
SELECT
    u.UserID, u.UserName, c.CategoryName,
    SUM(e.Amount) AS TotalSpent,
    COUNT(*)      AS NumTransactions
FROM Expenses e
JOIN Users u             ON e.UserID     = u.UserID
JOIN ExpenseCategories c ON e.CategoryID = c.CategoryID
WHERE e.IsDeleted = 0
GROUP BY u.UserID, u.UserName, c.CategoryName;

CREATE VIEW v_budget_performance AS
SELECT
    b.UserID, b.Month, b.Year,
    c.CategoryName,
    b.LimitAmount,
    COALESCE((
        SELECT SUM(e.Amount) FROM Expenses e
        WHERE e.UserID = b.UserID
          AND e.CategoryID = b.CategoryID
          AND MONTH(e.ExpenseDate) = b.Month
          AND YEAR(e.ExpenseDate)  = b.Year
          AND e.IsDeleted = 0
    ), 0) AS ActualSpent
FROM BudgetLimits b
JOIN ExpenseCategories c ON b.CategoryID = c.CategoryID;

-- ── 4. Stored Procedure ───────────────────────────────────────

DELIMITER $$
CREATE PROCEDURE sp_monthly_close(IN p_userID INT, IN p_month INT, IN p_year INT)
BEGIN
    DECLARE v_inc DECIMAL(15,2);
    DECLARE v_exp DECIMAL(15,2);

    SELECT COALESCE(SUM(Amount), 0) INTO v_inc
    FROM Income
    WHERE UserID = p_userID AND MONTH(IncomeDate) = p_month
      AND YEAR(IncomeDate) = p_year AND IsDeleted = 0;

    SELECT COALESCE(SUM(Amount), 0) INTO v_exp
    FROM Expenses
    WHERE UserID = p_userID AND MONTH(ExpenseDate) = p_month
      AND YEAR(ExpenseDate) = p_year AND IsDeleted = 0;

    SELECT
        p_month          AS Month,
        p_year           AS Year,
        v_inc            AS TotalIncome,
        v_exp            AS TotalExpense,
        (v_inc - v_exp)  AS NetBalance,
        CASE
            WHEN (v_inc - v_exp) >= 0 THEN 'SURPLUS'
            ELSE 'DEFICIT'
        END              AS Status;
END$$
DELIMITER ;

-- ── 5. User Defined Functions ─────────────────────────────────

SET GLOBAL log_bin_trust_function_creators = 1;

DELIMITER $$
CREATE FUNCTION fn_total_income(p_userID INT, p_month INT, p_year INT)
RETURNS DECIMAL(15,2)
DETERMINISTIC READS SQL DATA
BEGIN
    DECLARE v_total DECIMAL(15,2) DEFAULT 0;
    SELECT COALESCE(SUM(Amount), 0) INTO v_total
    FROM Income
    WHERE UserID = p_userID AND MONTH(IncomeDate) = p_month
      AND YEAR(IncomeDate) = p_year AND IsDeleted = 0;
    RETURN v_total;
END$$

CREATE FUNCTION fn_total_expense(p_userID INT, p_month INT, p_year INT)
RETURNS DECIMAL(15,2)
DETERMINISTIC READS SQL DATA
BEGIN
    DECLARE v_total DECIMAL(15,2) DEFAULT 0;
    SELECT COALESCE(SUM(Amount), 0) INTO v_total
    FROM Expenses
    WHERE UserID = p_userID AND MONTH(ExpenseDate) = p_month
      AND YEAR(ExpenseDate) = p_year AND IsDeleted = 0;
    RETURN v_total;
END$$

CREATE FUNCTION fn_budget_status(p_userID INT, p_month INT, p_year INT)
RETURNS VARCHAR(10)
DETERMINISTIC READS SQL DATA
BEGIN
    DECLARE v_inc  DECIMAL(15,2) DEFAULT 0;
    DECLARE v_exp  DECIMAL(15,2) DEFAULT 0;
    DECLARE v_ratio DECIMAL(5,2) DEFAULT 0;

    SELECT COALESCE(SUM(Amount), 0) INTO v_inc
    FROM Income
    WHERE UserID = p_userID AND MONTH(IncomeDate) = p_month
      AND YEAR(IncomeDate) = p_year AND IsDeleted = 0;

    SELECT COALESCE(SUM(Amount), 0) INTO v_exp
    FROM Expenses
    WHERE UserID = p_userID AND MONTH(ExpenseDate) = p_month
      AND YEAR(ExpenseDate) = p_year AND IsDeleted = 0;

    IF v_inc = 0 THEN RETURN 'WARNING'; END IF;
    SET v_ratio = v_exp / v_inc;
    IF    v_ratio <= 0.70 THEN RETURN 'OK';
    ELSEIF v_ratio <= 1.00 THEN RETURN 'WARNING';
    ELSE                        RETURN 'OVER';
    END IF;
END$$
DELIMITER ;

-- ── 6. Database Security ──────────────────────────────────────

CREATE ROLE IF NOT EXISTS 'app_user';
CREATE ROLE IF NOT EXISTS 'admin_user';

GRANT SELECT, INSERT, UPDATE ON moneymate.* TO 'app_user';
GRANT ALL PRIVILEGES         ON moneymate.* TO 'admin_user';

CREATE USER IF NOT EXISTS 'finance_app'@'localhost'   IDENTIFIED BY 'App@12345';
CREATE USER IF NOT EXISTS 'finance_admin'@'localhost' IDENTIFIED BY 'Admin@12345';

GRANT 'app_user'   TO 'finance_app'@'localhost';
GRANT 'admin_user' TO 'finance_admin'@'localhost';
FLUSH PRIVILEGES;

-- ── 7. Seed Data ──────────────────────────────────────────────

INSERT INTO Users (UserName, Email, PhoneNumber, PasswordHash) VALUES
('Nguyen Van An',  'an.nguyen@neu.edu.vn',   '0901234567', '$2b$12$hash1'),
('Tran Thi Bich',  'bich.tran@neu.edu.vn',   '0912345678', '$2b$12$hash2'),
('Le Minh Duc',    'duc.le@neu.edu.vn',       '0923456789', '$2b$12$hash3'),
('Pham Thi Lan',   'lan.pham@neu.edu.vn',     '0934567890', '$2b$12$hash4'),
('Hoang Van Em',   'em.hoang@neu.edu.vn',     '0945678901', '$2b$12$hash5');

INSERT INTO ExpenseCategories (CategoryName) VALUES
('Ăn uống'), ('Di chuyển'), ('Giải trí'), ('Sức khỏe'),
('Giáo dục'), ('Nhà cửa'), ('Mua sắm');

INSERT INTO BankAccounts (UserID, BankName, Balance) VALUES
(1, 'Vietcombank',  0),
(1, 'Momo Wallet',  0),
(2, 'Techcombank',  0),
(3, 'BIDV',         0),
(4, 'Agribank',     0),
(5, 'MB Bank',      0);

-- Income — triggers sẽ tự cập nhật Balance
INSERT INTO Income (UserID, AccountID, Amount, IncomeDate, Description) VALUES
(1, 1, 12000000, '2025-01-25', 'Lương tháng 1'),
(1, 1, 12000000, '2025-02-25', 'Lương tháng 2'),
(1, 1, 12000000, '2025-03-25', 'Lương tháng 3'),
(1, 1, 12000000, '2025-04-25', 'Lương tháng 4'),
(1, 1, 12000000, '2025-05-25', 'Lương tháng 5'),
(1, 2,  3000000, '2025-02-10', 'Freelance tháng 2'),
(1, 2,  2000000, '2025-04-05', 'Thu nhập phụ'),
(2, 3,  8000000, '2025-01-25', 'Lương tháng 1'),
(2, 3,  8000000, '2025-02-25', 'Lương tháng 2'),
(3, 4, 18000000, '2025-01-25', 'Lương tháng 1'),
(3, 4,  5000000, '2025-03-01', 'Thưởng quý 1'),
(4, 5,  7500000, '2025-02-25', 'Lương tháng 2'),
(5, 6, 10000000, '2025-01-25', 'Lương tháng 1'),
(5, 6, 10000000, '2025-03-25', 'Lương tháng 3');

-- Expenses — triggers sẽ tự trừ Balance
INSERT INTO Expenses (UserID, AccountID, CategoryID, Amount, ExpenseDate, Description) VALUES
(1, 1, 1, 1500000, '2025-01-05', 'Ăn uống tháng 1'),
(1, 1, 2,  300000, '2025-01-10', 'Xăng xe tháng 1'),
(1, 1, 6, 3000000, '2025-01-15', 'Tiền nhà tháng 1'),
(1, 1, 1, 1600000, '2025-02-05', 'Ăn uống tháng 2'),
(1, 1, 6, 3000000, '2025-02-15', 'Tiền nhà tháng 2'),
(1, 2, 3,  500000, '2025-02-14', 'Xem phim'),
(1, 1, 1, 1700000, '2025-03-05', 'Ăn uống tháng 3'),
(1, 1, 6, 3000000, '2025-03-15', 'Tiền nhà tháng 3'),
(1, 1, 2,  350000, '2025-03-20', 'Grab tháng 3'),
(1, 1, 1, 1800000, '2025-04-05', 'Ăn uống tháng 4'),
(1, 1, 6, 3000000, '2025-04-15', 'Tiền nhà tháng 4'),
(1, 2, 7, 1200000, '2025-04-20', 'Mua sắm tháng 4'),
(1, 1, 1, 1400000, '2025-05-05', 'Ăn uống tháng 5'),
(1, 1, 2,  280000, '2025-05-08', 'Xăng xe tháng 5'),
(2, 3, 1, 1200000, '2025-02-03', 'Ăn uống'),
(2, 3, 3,  500000, '2025-02-14', 'Giải trí'),
(3, 4, 5, 2000000, '2025-01-20', 'Học tiếng Anh'),
(3, 4, 7, 1800000, '2025-03-12', 'Mua sắm'),
(4, 5, 4,  600000, '2025-02-08', 'Khám sức khỏe'),
(5, 6, 1, 1300000, '2025-03-05', 'Ăn uống');

-- Budget limits cho user 1 tháng 5/2025
INSERT INTO BudgetLimits (UserID, CategoryID, LimitAmount, Month, Year) VALUES
(1, 1, 2000000, 5, 2025),
(1, 2,  500000, 5, 2025),
(1, 3,  800000, 5, 2025),
(1, 4,  500000, 5, 2025),
(1, 6, 3500000, 5, 2025),
(1, 7, 1500000, 5, 2025);

-- Verify
SELECT 'Users'            AS tbl, COUNT(*) AS cnt FROM Users      UNION ALL
SELECT 'Income',            COUNT(*) FROM Income                  UNION ALL
SELECT 'Expenses',          COUNT(*) FROM Expenses                UNION ALL
SELECT 'BankAccounts',      COUNT(*) FROM BankAccounts            UNION ALL
SELECT 'BudgetLimits',      COUNT(*) FROM BudgetLimits;

SELECT AccountID, BankName, Balance FROM BankAccounts WHERE UserID = 1;
-- ── 8. Migration patch (chạy nếu DB đã tồn tại) ─────────────
-- Cho phép CategoryID = NULL trong BudgetLimits (hũ "Chi tiêu khác")
ALTER TABLE BudgetLimits MODIFY CategoryID INT NULL;

-- Thêm danh mục "Tiết kiệm" nếu chưa có (hũ thứ 8 cố định)
INSERT IGNORE INTO ExpenseCategories (CategoryName) VALUES ('Tiết kiệm');