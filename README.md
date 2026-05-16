# Pharmacy Management System

A comprehensive pharmacy management system built with FastAPI, featuring AI integration, real-time inventory tracking, customer management, and automated notifications.

## Features

### Core Features
- **User Management**: Role-based access control (Admin, Pharmacist, Technician, Cashier, etc.)
- **Inventory Management**: Real-time stock tracking, batch management, expiry alerts
- **Customer Management**: Customer profiles, prescription tracking, medical history
- **Order Processing**: Complete order lifecycle from prescription to dispensing
- **Payment Processing**: Multiple payment methods, invoice generation, payment tracking
- **Reporting**: Sales reports, inventory analysis, financial statements, customer analytics

### Advanced Features
- **AI Integration**: Market trend analysis, demand forecasting, pricing optimization
- **Automated Notifications**: Email & SMS alerts for expiry, low stock, order status
- **Scheduled Tasks**: Automated daily reports, data cleanup, backup
- **Dashboard**: Real-time analytics and key performance indicators
- **Multi-branch Support**: Manage multiple pharmacy locations
- **Audit Logging**: Complete audit trail for all actions

## Technology Stack

- **Backend**: FastAPI, Python 3.11+
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis
- **AI/ML**: OpenAI GPT, Google Gemini
- **Email**: SMTP with Jinja2 templates
- **SMS**: Twilio integration
- **Background Tasks**: Celery with Redis broker
- **API Documentation**: Auto-generated OpenAPI/Swagger UI

## Installation

### Prerequisites
- Python 3.11 or higher
- PostgreSQL 15 or higher
- Redis 7 or higher
- Virtual environment (recommended)

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/pharmacy-management-system.git
cd pharmacy-management-system
