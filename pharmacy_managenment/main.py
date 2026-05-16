from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from app.core.config import settings
from app.database import engine, Base
from app.routers import (
  auth, admin, products, inventory,
  customers, orders, payments, reports,
  notifications, ai_integration
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
  """Lifespan context manager for startup/shutdown events"""
  # Startup
  logger.info("Starting Pharmacy Management System...")

  # Create database tables
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)

  # Start background tasks
  from app.tasks.scheduled_tasks import start_scheduled_tasks
  start_scheduled_tasks()

  yield

  # Shutdown
  logger.info("Shutting down Pharmacy Management System...")


# Create FastAPI app
app = FastAPI(
  title="Pharmacy Management System",
  description="Comprehensive pharmacy management with AI integration",
  version="1.0.0",
  lifespan=lifespan
)

# Configure CORS
app.add_middleware(
  CORSMiddleware,
  allow_origins=settings.CORS_ORIGINS,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventory"])
app.include_router(customers.router, prefix="/api/customers", tags=["Customers"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(ai_integration.router, prefix="/api/ai", tags=["AI Integration"])


@app.get("/")
async def root():
  return {
    "message": "Pharmacy Management System API",
    "version": "1.0.0",
    "docs": "/docs",
    "redoc": "/redoc"
  }


@app.get("/health")
async def health_check():
  return {"status": "healthy", "timestamp": "2024-01-15T10:30:00Z"}