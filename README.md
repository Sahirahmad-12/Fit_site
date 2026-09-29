# 🏋️ EnterGYM — Gym Management Platform

**EnterGYM** is a full-featured gym management platform designed to digitize and simplify everyday gym operations. It provides gym owners, trainers, receptionists, and members with a centralized system for managing memberships, payments, attendance, invoices, notifications, reports, and other fitness-related operations.

🌐 **Live Website:** https://entergym.in/

---

## 📌 Overview

Managing a gym using paper registers, spreadsheets, and separate payment records can become difficult as the number of members increases.

EnterGYM provides a centralized digital solution where gym owners can manage their complete gym ecosystem from a single platform.

The platform supports:

* Member management
* Membership management
* Payment tracking
* Invoice generation
* Attendance management
* Trainer management
* Expense tracking
* Notifications
* Reports and analytics
* Member portal
* AI-powered face attendance
* QR-based attendance
* GPS-based attendance
* Online supplement store
* Multi-gym / multi-tenant architecture
* Role-based access control

---

## 🚀 Live Demo

### 🌐 EnterGYM

**https://entergym.in/**

The production application is deployed and accessible online.

---

## ✨ Key Features

### 👨‍💼 Admin Dashboard

Gym owners and administrators can manage their gym from a centralized dashboard.

**Features include:**

* Member management
* Membership management
* Payment tracking
* Attendance monitoring
* Revenue overview
* Expense management
* Reports
* Notifications
* Staff management

---

### 👤 Member Management

Manage complete member information from a centralized system.

* Add new members
* Update member information
* Membership plans
* Membership expiry tracking
* Payment status
* Pending payments
* Attendance history
* Member profile management

---

### 💳 Payment & Invoice Management

EnterGYM provides digital payment and billing management.

* Track member payments
* Pending payment tracking
* Payment history
* Invoice generation
* Receipt generation
* Tax invoice support
* Payment timestamps
* Financial records

---

### 📊 Reports & Analytics

Gym owners can monitor their business performance through reports and analytics.

The system provides information related to:

* Revenue
* Collections
* Attendance
* Expenses
* Membership trends
* Payment status
* Monthly performance

Reports can also be exported for further analysis.

---

### 📅 Attendance Management

EnterGYM supports multiple attendance mechanisms:

* QR Code Attendance
* GPS-Based Attendance
* Manual Staff Check-in
* AI Face Recognition Attendance

Attendance records are connected with member profiles and include timestamps.

---

### 🤖 AI Face Attendance

Members can use face recognition to record attendance without requiring:

* Cards
* Fingerprints
* QR codes
* Manual entry

The face attendance system automatically identifies the member and records the attendance.

---

### 🔔 Notifications

The platform provides automated notifications for important gym activities.

Examples:

* Membership expiry reminders
* Payment reminders
* Gym announcements
* Membership updates

This helps reduce manual communication with members.

---

### 🏪 Online Supplement Store

EnterGYM includes an integrated supplement and fitness-product store.

Gym owners can manage:

* Products
* Inventory
* Product information
* Supplement sales

Products can include items such as protein, creatine, and gym accessories.

---

### 📱 Member Portal

Members get their own digital portal where they can access their gym information.

Members can view:

* Membership details
* Membership validity
* Payment history
* Receipts
* Attendance history
* Pending payments
* Notifications

The platform is designed to provide a mobile-friendly member experience.

---

### 🏢 Multi-Tenant Gym Architecture

EnterGYM is designed as a multi-tenant platform.

Each gym operates within its own isolated environment.

Gym-specific data includes:

* Members
* Staff
* Payments
* Attendance
* Memberships
* Settings
* Reports
* Operational data

This allows multiple gyms to use the same platform while keeping their operational data separated.

---

### 🔐 Role-Based Access Control

Different users can have different permissions depending on their role.

Supported roles include:

* Super Admin
* Gym Owner
* Trainer
* Receptionist
* Member

This helps control access to sensitive gym operations and data.

---

## 🛠️ Technology Stack

### Backend

* Python
* Django
* Django REST Framework
* ASGI
* REST APIs

### Frontend

* HTML5
* CSS3
* JavaScript
* Django Templates

### Database

* MongoDB / Database Layer
* Database-backed member and operational records

### Authentication & Security

* User Authentication
* Role-Based Access Control
* Session Management
* Protected Routes
* Tenant-Based Data Isolation

### Other Technologies

* AI / Face Recognition
* QR Code
* GPS / Geolocation
* Push Notifications
* Cloud Storage
* Excel Report Export
* Invoice Generation

### Deployment

* GitHub
* Production Web Server
* ASGI
* Custom Domain

---

## 📂 Project Structure

```text
Fit_site/
│
├── AuthFit/
│   └── Authentication & user management
│
├── Fitness/
│   └── Core gym management functionality
│
├── Shop/
│   └── Supplement store functionality
│
├── notifications/
│   └── Notification system
│
├── templates/
│   └── HTML templates
│
├── static/
│   └── CSS, JavaScript, images and static assets
│
├── .vscode/
│   └── VS Code configuration
│
├── manage.py
│   └── Django management script
│
├── asgi.py
│   └── ASGI application configuration
│
├── Procfile
│   └── Production deployment configuration
│
└── .gitignore
```

---

## 🔄 Gym Management Workflow

```text
                ┌──────────────────┐
                │     Gym Owner    │
                └────────┬─────────┘
                         │
                         ▼
                ┌──────────────────┐
                │ Admin Dashboard  │
                └────────┬─────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   Members          Payments         Attendance
        │                │                │
        ▼                ▼                ▼
 Memberships         Invoices       QR / GPS / AI
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
                ┌──────────────────┐
                │ Reports & Alerts │
                └──────────────────┘
```

---

## 👥 User Roles

| Role         | Responsibilities                         |
| ------------ | ---------------------------------------- |
| Super Admin  | Manage the overall platform              |
| Gym Owner    | Manage gym operations                    |
| Trainer      | Manage assigned fitness activities       |
| Receptionist | Manage members, payments and attendance  |
| Member       | View membership, payments and attendance |

---

## 💡 Problems Solved

EnterGYM focuses on solving common problems faced by gyms using traditional management systems.

### Before EnterGYM

* Paper-based member records
* Difficult payment tracking
* Manual attendance
* No centralized database
* Difficult membership expiry tracking
* Manual invoice management
* Limited reporting
* Difficult remote management

### With EnterGYM

* Digital member enrollment
* Centralized member records
* Automated payment tracking
* Multiple attendance methods
* Digital invoices
* Membership expiry notifications
* Reports and analytics
* Mobile-friendly member portal
* Cloud-based operational management

---

## 📈 Platform Capabilities

EnterGYM is designed around multiple interconnected systems:

```text
                EnterGYM
                   │
       ┌───────────┼───────────┐
       │           │           │
    Members     Payments    Attendance
       │           │           │
       ├───────────┼───────────┤
       │           │           │
   Membership   Invoices   Notifications
       │           │           │
       └───────────┼───────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
     Reports              Shop
        │                     │
        └──────────┬──────────┘
                   │
              Member Portal
```

---

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/Sahirahmad-12/Fit_site.git
```

### 2. Navigate to the project

```bash
cd Fit_site
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

### 4. Activate the virtual environment

#### Windows

```bash
venv\Scripts\activate
```

#### macOS / Linux

```bash
source venv/bin/activate
```

### 5. Install dependencies

If the project contains a `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### 6. Configure environment variables

Create a `.env` file and configure the required environment variables.

Example:

```env
SECRET_KEY=your_secret_key
DEBUG=False

DATABASE_URL=your_database_url

CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
```

> Never commit `.env` files or API keys to GitHub.

### 7. Apply migrations

```bash
python manage.py migrate
```

### 8. Create an admin user

```bash
python manage.py createsuperuser
```

### 9. Start the development server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

---

## 🔐 Environment Variables

The exact variables depend on the services enabled in the deployment.

Typical configuration includes:

| Variable                 | Purpose                        |
| ------------------------ | ------------------------------ |
| `SECRET_KEY`             | Django security configuration  |
| `DEBUG`                  | Development/production mode    |
| `DATABASE_URL`           | Database connection            |
| `CLOUDINARY_CLOUD_NAME`  | Cloudinary cloud configuration |
| `CLOUDINARY_API_KEY`     | Cloudinary API authentication  |
| `CLOUDINARY_API_SECRET`  | Cloudinary API authentication  |
| Notification credentials | Push notification services     |
| AI configuration         | Face recognition services      |

---

## 🚀 Deployment

The project includes a `Procfile` and `asgi.py`, allowing it to be configured for production deployment using an ASGI-compatible server.

Production application:

**https://entergym.in/**

---

## 🔒 Security Considerations

The application should keep the following information private:

* Database credentials
* API keys
* Cloudinary credentials
* Django secret key
* Notification service credentials
* AI service credentials

Use environment variables instead of hardcoding secrets in source code.

---

## 🎯 Future Improvements

Potential improvements for future versions include:

* Advanced revenue analytics
* Automated WhatsApp notifications
* Online payment gateway integration
* Workout plan management
* Diet plan management
* Trainer scheduling
* Subscription auto-renewal
* Advanced AI fitness recommendations
* Mobile application expansion
* Advanced business intelligence dashboards
* Automated backup and recovery
* More third-party integrations

---

## 📸 Screenshots

Add screenshots of the following sections to make the repository more professional:

```text
screenshots/
├── dashboard.png
├── members.png
├── payments.png
├── attendance.png
├── reports.png
├── member-portal.png
└── shop.png
```

Example:

```markdown
## 📸 Screenshots

### Admin Dashboard

![Admin Dashboard](screenshots/dashboard.png)

### Member Management

![Member Management](screenshots/members.png)

### Attendance

![Attendance](screenshots/attendance.png)
```

---

## 🌐 Project Links

**Live Application:**
https://entergym.in/

**GitHub Repository:**
https://github.com/Sahirahmad-12/Fit_site

---

## 👨‍💻 Developer

**Sahir Ahmad**

GitHub:
https://github.com/Sahirahmad-12

---

## 📄 License

This project is intended for educational, portfolio, and commercial development purposes.

Add an appropriate open-source license such as MIT only if you intend to allow others to use, modify, and distribute the code.

---

## ⭐ Support

If you find this project useful, consider giving the repository a ⭐ on GitHub.

---

### EnterGYM

**Digitizing gym operations — from member registration to payments, attendance, reports, and member engagement.**
