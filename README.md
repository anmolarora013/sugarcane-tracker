# 🌾 Sugarcane Purchy Tracker

![Architecture](https://img.shields.io/badge/Architecture-Serverless-green) 
![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-blue)
![Backend](https://img.shields.io/badge/Backend-AWS%20Lambda-orange)
![Database](https://img.shields.io/badge/Database-DynamoDB-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

A complete end‑to‑end **sugarcane supply tracking system** designed for farmers and small agricultural businesses.

This application helps track sugarcane *purchies*, maintain multiple accounts, analyze supply trends, and manage daily entries — all through a simple, mobile‑friendly interface.

---

# 📸 Logo  
```
   _________                     _                            
  /   _____/______ ____ ________/ |_    ____   ____  __ __    
  \_____  \\_  __ \\__  \\_  __ \\   __\_/ __ \/ ___\|  |  \
  /        \|  | \/ / __ \|  | \/|  |  \  ___/\  \___|  |  /
 /_______  /|__|   (____  /__|   |__|   \___  >\___  >____/ 
         \/             \/                  \/     \/        
```

---

# 🚀 Features

### 🎯 Core
- Add / Edit / Delete Purchies  
- Add / Edit Accounts  
- Auto-calc **Total Weight** and **Total Amount**  
- Advanced filtering  
- Instant search & summary view  

### 📱 Mobile-Optimized  
- Large input fields  
- Fast loading  
- Offline-friendly pattern  

### ☁️ Cloud-Native Backend  
- Zero maintenance  
- Fast, scalable, reliable  

---

# 🏗️ Full System Architecture

```mermaid
flowchart TD

A[React Frontend (Vite)] --> B[S3 Static Hosting]
B --> C[API Gateway]
C --> D[AWS Lambda Functions]
D --> E[(DynamoDB - Purchies Table)]
D --> F[(DynamoDB - Accounts Table)]
```

---

# 🧩 Repository Structure

```
/
├── frontend/                  # React Application (Vite)
│   ├── src/
│   │   ├── App.jsx
│   │   ├── Summary.jsx
│   │   ├── Api.js
│   │   └── components...
│   ├── package.json
│   └── vite.config.js
│
└── backend/                   # All Lambda Functions (Python)
    ├── add_account.py
    ├── get_accounts.py
    ├── add_purchy.py
    ├── get_purchies.py
    ├── delete_purchy.py
    └── edit_purchy.py
```

---

# 🗄️ Database Schema

## 📘 Accounts Table  
| Field        | Type   | Description |
|--------------|--------|-------------|
| account_id   | PK     | Unique ID |
| account_name | string | Display Name |
| description  | string | Optional |
| created_at   | string | ISO Timestamp |

---

## 📙 Purchies Table  
**Composite Key**  
- `account_id` (PK)  
- `purchy_ts` (SK, ISO timestamp)  

| Field        | Type      | Description |
|--------------|-----------|-------------|
| account_id   | string    | Linked account |
| purchy_ts    | string    | Unique timestamp |
| date         | string    | Purchy date |
| weight       | number    | Decimal |
| purchy_id    | string    | Purchy number |
| note         | string    | Optional |
| rate         | number    | Optional |
| amount       | number    | Calculated |

---

# 🌐 API Endpoints

| Method | Path        | Purpose |
|--------|-------------|---------|
| GET    | /accounts   | List accounts |
| POST   | /accounts   | Add account |
| GET    | /purchies   | Get purchies |
| POST   | /purchies   | Add purchy |
| PUT    | /purchies   | Edit purchy |
| DELETE | /purchies   | Delete purchy |

---

# 🧪 Sample Lambda Event
```json
{
  "httpMethod": "PUT",
  "isBase64Encoded": false,
  "body": "{"account_id":"ACC001","purchy_ts":"2025-01-10T08:30:10Z","weight":85.5}"
}
```

---

# 🛠️ Local Development

### Install dependencies
```bash
cd frontend
npm install
```

### Run dev server
```bash
npm run dev
```

### Build for production
```bash
npm run build
```

---

# ☁️ Deployment

### 🎨 Frontend (S3)
1. Build: `npm run build`  
2. Upload `/dist` to S3  
3. Enable static hosting  
4. Allow public read via bucket policy  

### 🔥 Backend (Lambda + API Gateway)
- Upload code directly or via zip  
- Attach functions to API routes  
- Enable CORS  
- Deploy API stage  

---

# 🚀 Future Enhancements
- CloudFront + HTTPS + Custom Domain  
- Authentication (Cognito)  
- Export reports (PDF/Excel)  
- Graphs & Charts  
- Multi-user roles  
- Automatic WhatsApp/SMS summaries  

---

# 📄 License
MIT License © 2025

---

# ❤️ Support  
If you want features added or need help hosting on AWS, feel free to open an issue.

