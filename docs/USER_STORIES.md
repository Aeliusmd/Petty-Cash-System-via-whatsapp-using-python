# User Stories

## Petty Cash Management System (WhatsApp-Based)

---

## 1. User Onboarding

### 1.1 Onboard Staff

**As an** admin,  
**I want to** onboard staff into the petty-cash system,  
**So that** they can start submitting claims via WhatsApp.

### 1.2 Assign Grade & Unit

**As an** admin,  
**I want to** assign each staff member a grade, location, manager, and unit,  
**So that** the system can automatically apply batta rates and approval routing.

### 1.3 Register Manager Approval Chain

**As an** admin,  
**I want to** map each employee to a manager,  
**So that** submitted claims automatically route to the correct approver.

### 1.4 WhatsApp Activation

**As a** staff member,  
**I want to** activate my account on WhatsApp via OTP,  
**So that** I can securely use the system.

---

## 2. Staff Claim Submission (WhatsApp)

### 2.1 Submit a Claim

**As a** staff member,  
**I want to** submit petty cash requests via WhatsApp,  
**So that** I don't need to log into a separate system.

### 2.2 Select Claim Category

**As a** staff member,  
**I want to** categorize my request (batta, fuel, accommodation, sundry),  
**So that** the system knows which rules to apply.

### 2.3 Enter Claim Details

**As a** staff member,  
**I want to** specify amount, days, and location,  
**So that** the correct reimbursement can be calculated.

### 2.4 Upload Bills

**As a** staff member,  
**I want to** upload receipts (photos/PDFs) via WhatsApp,  
**So that** bill-based claims can be validated.

### 2.5 Submit Outright Claims

**As a** staff member,  
**I want to** make outright claims without uploading bills,  
**So that** fixed-rate categories (batta, sundry) are handled automatically.

### 2.6 View System-Calculated Amount

**As a** staff member,  
**I want** the system to show me the calculated batta amount based on grade and location,  
**So** I can confirm before submission.

### 2.7 Confirm Submission

**As a** staff member,  
**I want to** confirm request is sent to the manager,  
**So that** no mistaken submissions occur.

---

## 3. Dynamic Rule Application

### 3.1 Auto-Apply Batta Rate

**As a** system,  
**I want to** detect location and grade and apply the correct batta rate,  
**So that** staff don't manually calculate it.

### 3.2 Apply Category-Based Caps

**As a** system,  
**I want to** apply category-wise caps (fuel, accommodation, sundry),  
**So that** claims stay within policy.

### 3.3 Validate Bills Against Category

**As a** system,  
**I want to** match uploaded receipts to the correct expense type,  
**So that** wrong claims are filtered.

### 3.4 Generate Total Amount

**As a** system,  
**I want to** auto-calculate totals for bill-based or outright claims,  
**So** staff and managers see final numbers clearly.

---

## 4. Approval Workflow

### 4.1 Manager Receives Requests

**As a** manager,  
**I want to** receive claim notifications in WhatsApp,  
**So** I can review requests quickly.

### 4.2 View Claim Details

**As a** manager,  
**I want to** see category, amount, date, location, grade, and system-applied rates,  
**So** I can ensure policy compliance.

### 4.3 View Uploaded Bills

**As a** manager,  
**I want to** open receipts directly in WhatsApp,  
**So** I can verify legitimacy quickly.

### 4.4 Approve or Reject

**As a** manager,  
**I want to** approve or reject claims in one message,  
**So** I don't need to log into another system.

### 4.5 Add Comments

**As a** manager,  
**I want to** add optional comments on rejection,  
**So** staff understand why.

### 4.6 Staff Notification

**As a** staff member,  
**I want to** receive approval or rejection notifications,  
**So** I know the status immediately.

---

## 5. Reports & Analytics

### 5.1 Reports by Person

**As** finance staff,  
**I want to** view petty cash totals per employee,  
**So** I can track spending patterns.

### 5.2 Reports by Unit

**As** finance staff,  
**I want to** view expenses by department/unit,  
**So** I can monitor operational budgets.

### 5.3 Reports by Manager

**As** finance staff,  
**I want to** view claims approved by each manager,  
**So** I can spot approval trends.

### 5.4 Category Totals

**As** finance staff,  
**I want to** see totals by category (fuel, batta, accommodation),  
**So** I can understand cost distribution.

### 5.5 Event Exceptions

**As** finance staff,  
**I want to** view flagged anomalies (duplicate receipts, bypassed caps),  
**So** I can investigate.

### 5.6 Historical Comparisons

**As** finance staff,  
**I want to** compare current vs previous months' spending,  
**So** I can identify increases or decreases.

### 5.7 Future Extrapolation

**As a** finance manager,  
**I want** the system to project future petty cash spend,  
**So** budgeting becomes easier.

---

## 6. System Admin & Configuration

### 6.1 Configure Claim Categories

**As an** admin,  
**I want to** configure categories (batta, fuel, accommodation, sundry),  
**So that** policies can evolve.

### 6.2 Manage Batta Rates

**As an** admin,  
**I want to** set batta rates by location and employee grade,  
**So** the system applies correct calculations.

### 6.3 Set Category Caps

**As an** admin,  
**I want to** update maximum claim limits per category,  
**So** policy changes reflect instantly.

### 6.4 Audit Log

**As an** admin,  
**I want** a full log of all actions,  
**So** every approval or change is traceable.

---

## Story Priority Matrix

| Priority          | User Story ID      | Description                    |
| ----------------- | ------------------ | ------------------------------ |
| **P1 - Critical** | 1.1, 1.2, 1.3      | User Onboarding                |
| **P1 - Critical** | 2.1, 2.2, 2.3, 2.7 | Basic Claim Submission         |
| **P1 - Critical** | 3.1, 3.2           | Core Rules Engine              |
| **P1 - Critical** | 4.1, 4.4, 4.6      | Basic Approval Flow            |
| **P2 - High**     | 1.4                | OTP Verification               |
| **P2 - High**     | 2.4, 2.5, 2.6      | Advanced Claim Features        |
| **P2 - High**     | 3.3, 3.4           | Bill Validation & Calculations |
| **P2 - High**     | 4.2, 4.3, 4.5      | Advanced Approval Features     |
| **P3 - Medium**   | 5.1, 5.2, 5.3, 5.4 | Core Reports                   |
| **P3 - Medium**   | 6.1, 6.2, 6.3      | Admin Configuration            |
| **P4 - Low**      | 5.5, 5.6, 5.7      | Advanced Analytics             |
| **P4 - Low**      | 6.4                | Audit Logging                  |
