# Business Requirements Document (BRD)

## Petty Cash Management System (WhatsApp-Based)

---

## 1. Overview

The Petty Cash Management System allows staff to submit claims (batta, fuel, accommodation, sundry expenses) through WhatsApp. The system auto-applies rules, validates bills, and routes approvals to managers. It generates reports and supports both bill-based and outright claims.

---

## 2. Objectives

- Automate petty cash claims via WhatsApp
- Enforce dynamic rules (location, grade, category caps)
- Reduce manual admin work
- Provide real-time approvals
- Ensure auditability with simple reporting modules

---

## 3. Key Features

### 3.1 WhatsApp-Based Claim Submission

Staff initiate claims by sending messages in natural language via WhatsApp.

**Supported Claims:**

1. Batta
2. Fuel
3. Accommodation
4. Sundry Expenses

**Mandatory Inputs:**

- Location
- Amount (if bill-based)
- Category
- Duration (for batta)
- Upload bills (if applicable)

---

## 4. Dynamic Rules Engine

### 4.1 Location & Grade-Based Batta Rates

Rates differ by:

- Location (e.g., Colombo, Jaffna, Kandy, Galle)
- Employee Grade (A, B, C, etc.)

System automatically calculates correct rate.

**Examples:**
| Grade | Location | Rate (LKR/day) |
|-------|----------|----------------|
| A | Colombo | 2000 |
| B | Jaffna | 1500 |
| C | Kandy | 1800 |

**System Response Example:**

```
User: "Batta for 2 days in Kandy"
System: "Batta LKR 1800/day applied (Grade C, Kandy). Total: LKR 3600. Send to manager?"
```

### 4.2 Category-Based Caps

Each expense type has caps:

- Fuel
- Accommodation
- Sundry
- Special allowances

System blocks or warns if cap is exceeded.

### 4.3 Claim Types

#### 4.3.1 Bill-Supported Claims

- Staff upload image of receipt
- System extracts amount (OCR)
- Category auto-matched (fuel/accommodation)
- Reimbursement based on actual amount (within cap)

**Example:**

```
Staff: "Fuel LKR 2500 (upload receipt)"
System: "Receipt received. Send to manager for LKR 2500 reimbursement?"
```

#### 4.3.2 Outright Claims (No Bills)

- Fixed rates based on location, grade, and category

**Example:**

```
Staff: "Batta for 1 day in Galle"
System: "Batta LKR 1500 (Grade B, Galle). Send to manager?"
```

---

## 5. Approval Workflow

### 5.1 Manager Approval via WhatsApp

Managers receive:

- Claim description
- Auto-calculated totals
- Receipt (if uploaded)
- Staff details
- Policy warnings (if any)

**Actions:**

- Approve
- Reject
- Request clarification

**System Response Example:**

```
Manager: "Approved"
System: "Claim approved and recorded."
```

---

## 6. WhatsApp Interaction Flow

### 6.1 Staff Workflow

1. Staff initiates claim
2. System validates inputs
3. System applies rules
4. System computes final amount
5. Staff confirms sending to manager
6. Manager receives claim
7. Manager approves/rejects
8. Staff notified

### 6.2 Manager Workflow

1. Manager receives summary
2. Views receipts (if any)
3. Approves or rejects
4. System logs decision

---

## 7. Reporting Module

**Reports Required:**

1. By Person
2. By Unit / Department
3. By Manager
4. Event Exceptions (over-limit, rejected, duplicates)
5. Totals by Category
6. Historical Comparisons
7. Future Extrapolations
8. Monthly/Quarterly Summaries
9. Export Options: CSV, PDF, spreadsheet

---

## 8. Data Requirements

**Master Data Needed:**

- Employee List (Name, Grade, Unit, Manager)
- Batta Rates Table (Grade × Location)
- Expense Category Caps
- Manager Mapping
- Location List
- Roles & Permissions

---

## 9. Onboarding Process (Very Important)

How staff/managers get added to the system:

### 9.1 Onboarding Steps

1. HR/Admin uploads list of staff with phone numbers
2. System registers WhatsApp numbers
3. Staff receive a welcome message:
   - Allowed claim types
   - Their grade
   - Location rules
4. Manager mappings activated
5. System verifies identity using OTP
6. Ready to use

---

## 10. Exception Handling

**Situations the system must detect:**

- Missing receipts for bill-based claims
- OCR mismatch amount vs user-specified amount
- Rate not found for grade/location
- Exceeding category cap
- Duplicate submission
- Missing location
- Invalid date or unclear duration (for batta)

**System Response Example:**

```
"Cannot process this claim. Fuel claims in Colombo require a receipt. Please upload one."
```

---

## 11. Audit Trail

System must store:

- Timestamp
- Staff input
- System calculations
- Manager approval
- Receipt images
- Policy exceptions
- Rejection reasons

---

## 12. Simple System Architecture (High-Level)

1. **Frontend:** WhatsApp chatbot
2. **Backend:** Petty cash rules engine
3. **Database:**
   - Employees
   - Rates / caps
   - Claims
   - Approvals
   - Receipts
4. **Reporting Engine**
5. **Admin Panel (web-based)**

---

## 13. Security Requirements

- OTP verification
- Role-based permissions
- Secured storage for receipts
- Encrypted communication
- Admin audit logs

---

## 14. Future Enhancements (Optional)

- Integration with payroll
- Integration with accounting systems
- Geo-tagging validation
- Auto-detection of frequent travellers for higher limits
- Rise alerts for policy updates
