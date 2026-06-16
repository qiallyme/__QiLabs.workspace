# Environment Files Security Review

A listing and security classification of all environment configuration files in the workspace. No values are printed to preserve credential privacy.

---

## 1. Active Configuration Files (`.env`)

These files contain active local credentials, API keys, or connection strings. They are marked for secret risk and should **never** be committed to Git.

| File Path | Classification |
| :--- | :--- |
| `C:\QiLabs\1000_QiApps\qicare\apps\frontend\.env` | `review_secret_risk` |
| `C:\QiLabs\1000_QiApps\qiportals\USBLegalAidv2\frontend\.env` | `review_secret_risk` (obsolete) |
| `C:\QiLabs\1000_QiApps\qiportals\src\features\qicases\.env` | `review_secret_risk` |
| `C:\QiLabs\1000_QiApps\qiportals\src\features\qihome-test\.env` | `review_secret_risk` |
| `C:\QiLabs\1000_QiApps\qiportals\src\features\qinote\.env` | `review_secret_risk` |
| `C:\QiLabs\10_QiAccess\.env` | `review_secret_risk` |
| `C:\QiLabs\20_QiSystem\packages\database\.env` | `review_secret_risk` |
| `C:\QiLabs\20_QiSystem\packages\qiobject\energy\.env` | `review_secret_risk` |
| `C:\QiLabs\20_QiSystem\packages\qiobject\rides\.env` | `review_secret_risk` |
| `C:\QiLabs\40_QiCapture\python_local\qiarchive\api\.env` | `review_secret_risk` |

---

## 2. Environment Templates (`.env.example` / `.env.local`)

These are safe template blueprints or default local overrides which do not contain production secrets.

| File Path | Classification |
| :--- | :--- |
| `C:\QiLabs\1000_QiApps\qicare\apps\frontend\.env.example` | `safe_template_candidate` |
| `C:\QiLabs\1000_QiApps\qicare\apps\momcare-desktop-admin\.env.example` | `safe_template_candidate` |
| `C:\QiLabs\1000_QiApps\qilegacy\.env.example` | `safe_template_candidate` |
| `C:\QiLabs\1000_QiApps\qiportals\.env.example` | `safe_template_candidate` |
| `C:\QiLabs\1000_QiApps\qiportals\app\features\qicontacts\.env.example` | `safe_template_candidate` (obsolete) |
| `C:\QiLabs\1000_QiApps\qiportals\app\features\qicontacts\QiCase\.env.example` | `safe_template_candidate` (obsolete) |
| `C:\QiLabs\1000_QiApps\qiportals\app\features\qicontacts\QiLitigation\.env.example` | `safe_template_candidate` (obsolete) |
| `C:\QiLabs\1000_QiApps\qiportals\app\features\qidocs\.env.example` | `safe_template_candidate` (obsolete) |
| `C:\QiLabs\1000_QiApps\qiportals\src\features\qicase\.env.example` | `safe_template_candidate` |
| `C:\QiLabs\1000_QiApps\qiportals\src\features\qicontacts\.env.example` | `safe_template_candidate` |
| `C:\QiLabs\1000_QiApps\qiportals\src\features\qidocs\.env.example` | `safe_template_candidate` |
| `C:\QiLabs\1000_QiApps\qiportals\src\features\qinote\.env.example` | `safe_template_candidate` |
| `C:\QiLabs\1000_QiApps\qiportals\src\features\qinote\worker\.env.example` | `safe_template_candidate` |
| `C:\QiLabs\1000_QiApps\sites\qially-web\.env.example` | `safe_template_candidate` |
| `C:\QiLabs\10_QiAccess\.env.example` | `safe_template_candidate` |
| `C:\QiLabs\20_QiSystem\50_data\supabase\.env.example` | `safe_template_candidate` |
| `C:\QiLabs\40_QiCapture\10_ingestion\20_drive_imports\RAG\.env.example` | `safe_template_candidate` |
| `C:\QiLabs\40_QiCapture\python_local\services\local-agent\.env.example` | `safe_template_candidate` |
| `C:\QiLabs\1100_QiApp_QiLife\frontend\.env.local` | `safe_template_candidate` |
| `C:\QiLabs\1000_QiApps\qiportals\.env.local` | `safe_template_candidate` |
| `C:\QiLabs\1000_QiApps\qiportals\src\features\qidocs\.env.local` | `safe_template_candidate` |
| `C:\QiLabs\1000_QiApps\qiportals\src\features\qinote\.env.local` | `safe_template_candidate` |
