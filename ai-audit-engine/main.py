from dotenv import load_dotenv
load_dotenv() 

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from typing import List
import shutil
import os
import re
import uuid
import time
import hashlib
import uvicorn
from collections import Counter, defaultdict

from services.audit_runner import run_audit_pipeline
from services.file_parser import parse_file
from services.ai_classifier import classify_bulk, generate_recommendations, get_available_industries

import sqlite3
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional


# ─── Security Configuration ──────────────────────────────────────────
MAX_FILE_SIZE_MB = 10           # Max size per file (MB)
MAX_TOTAL_SIZE_MB = 50          # Max total upload size (MB)
MAX_FILES_PER_REQUEST = 10      # Max number of files per audit
MAX_REQUESTS_PER_MINUTE = 10    # Rate limit per IP
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".pdf", ".txt", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".eml"}
BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".sh", ".ps1", ".dll", ".so", ".py", ".js", ".php", ".rb", ".jar", ".msi"}

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "prod_secret_key_synth_ai_2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── Database Setup ──────────────────────────────────────────────────
DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            full_name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            created_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ─── Auth Models ─────────────────────────────────────────────────────
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

# ─── Auth Helpers ────────────────────────────────────────────────────
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ─── App Setup ────────────────────────────────────────────────────────
app = FastAPI(
    title="Synth AI Audit Engine",
    docs_url="/docs" if os.getenv("ENVIRONMENT", "development") == "development" else None,  # Disable docs in production
    redoc_url=None,
)

# ─── CORS ─────────────────────────────────────────────────────────────
# In production, we allow all origins since we use JWT for auth (no cookies)
# and Vercel uses many dynamic subdomains.
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

vercel_url = os.getenv("FRONTEND_URL", "")
if vercel_url:
    allowed_origins.append(vercel_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for the engine
    allow_credentials=False, # Must be False for allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Trusted Hosts (prevent host header attacks) ─────────────────────
trusted_hosts = ["localhost", "127.0.0.1"]
if vercel_url:
    # Extract hostname
    from urllib.parse import urlparse
    parsed = urlparse(vercel_url)
    if parsed.hostname:
        trusted_hosts.append(parsed.hostname)

render_url = os.getenv("RENDER_EXTERNAL_HOSTNAME", "")
if render_url:
    trusted_hosts.append(render_url)

# In production, add your actual domain
trusted_hosts.append("*.onrender.com")
trusted_hosts.append("*.vercel.app")

app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)


# ─── Rate Limiting ───────────────────────────────────────────────────
request_counts: dict[str, list[float]] = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple in-memory rate limiter. For production, use Redis-backed."""
    # Only rate-limit the /audit endpoint
    if request.url.path == "/audit":
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60  # 1 minute window

        # Clean old entries
        request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < window]

        if len(request_counts[client_ip]) >= MAX_REQUESTS_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Please wait before trying again.", "retry_after_seconds": 60}
            )

        request_counts[client_ip].append(now)

    response = await call_next(request)
    return response


# ─── Security Headers Middleware ─────────────────────────────────────
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    # Remove server info
    if "server" in response.headers:
        del response.headers["server"]
    return response


# ─── File Security Utilities ─────────────────────────────────────────
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and injection attacks."""
    # Remove path separators and null bytes
    filename = filename.replace("/", "").replace("\\", "").replace("\x00", "")
    # Remove any directory components
    filename = os.path.basename(filename)
    # Only allow safe characters: alphanumeric, dots, hyphens, underscores
    filename = re.sub(r'[^\w\-.]', '_', filename)
    # Prevent hidden files
    filename = filename.lstrip('.')
    # Add UUID prefix to prevent collisions and make names unpredictable
    safe_name = f"{uuid.uuid4().hex[:8]}_{filename}" if filename else f"{uuid.uuid4().hex}.tmp"
    return safe_name


def validate_file(file: UploadFile) -> tuple[bool, str]:
    """Validate uploaded file for security."""
    if not file.filename:
        return False, "File has no name"

    # Check extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext in BLOCKED_EXTENSIONS:
        return False, f"File type '{ext}' is blocked for security reasons"
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' is not supported. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"

    # Check content type
    dangerous_types = {"application/x-executable", "application/x-msdownload", "application/javascript"}
    if file.content_type and file.content_type in dangerous_types:
        return False, f"Content type '{file.content_type}' is not allowed"

    return True, "OK"


def check_file_size(file_path: str) -> tuple[bool, str]:
    """Check file size after saving."""
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return False, f"File exceeds {MAX_FILE_SIZE_MB}MB limit ({size_mb:.1f}MB)"
    return True, "OK"


# ─── Endpoints ────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "running",
        "message": "Synth AI Audit Backend Running 🚀",
        "version": "1.0.0",
        "openai_key_set": bool(os.getenv("OPENAI_API_KEY"))
    }

# ─── Authentication Endpoints ────────────────────────────────────────
@app.post("/signup", response_model=Token)
async def signup(user: UserCreate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT email FROM users WHERE email = ?", (user.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_pwd = get_password_hash(user.password)
    cursor.execute(
        "INSERT INTO users (id, full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, user.full_name, user.email, hashed_pwd, datetime.utcnow())
    )
    conn.commit()
    conn.close()
    
    # Generate token
    user_data = {"id": user_id, "email": user.email, "full_name": user.full_name}
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer", "user": user_data}

@app.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, full_name, email, password_hash FROM users WHERE email = ?", (user_credentials.email,))
    db_user = cursor.fetchone()
    conn.close()
    
    if not db_user or not verify_password(user_credentials.password, db_user[3]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user_data = {"id": db_user[0], "full_name": db_user[1], "email": db_user[2]}
    access_token = create_access_token(data={"sub": db_user[2]})
    
    return {"access_token": access_token, "token_type": "bearer", "user": user_data}


@app.post("/audit")
async def audit_files(
    files: List[UploadFile] = File(...),
    industry: str = "general",
):
    """
    Main audit endpoint - receives files and returns complete analysis.
    """
    # ... (security checks)
    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_FILES_PER_REQUEST} files per request. You sent {len(files)}."
        )

    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided.")

    saved_paths = []  # Track for cleanup

    try:
        uploaded_files = []
        all_messages = []
        total_size = 0

        for file in files:
            # ... (validation and saving)
            is_valid, reason = validate_file(file)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"File '{file.filename}' rejected: {reason}")

            safe_name = sanitize_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, safe_name)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_paths.append(file_path)

            size_ok, size_msg = check_file_size(file_path)
            if not size_ok:
                raise HTTPException(status_code=400, detail=f"File '{file.filename}': {size_msg}")

            total_size += os.path.getsize(file_path)
            if total_size > MAX_TOTAL_SIZE_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"Total upload size exceeds {MAX_TOTAL_SIZE_MB}MB limit."
                )

            print(f"✅ Uploaded: {file.filename} → {safe_name}")

            # Parse file content
            try:
                messages = parse_file(file_path)
                all_messages.extend(messages)

                uploaded_files.append({
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "size": os.path.getsize(file_path),
                    "messages_extracted": len(messages)
                })
            except Exception as e:
                print(f"⚠️ Could not parse {file.filename}: {e}")
                uploaded_files.append({
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "size": os.path.getsize(file_path),
                    "error": "File could not be parsed"
                })

        if not all_messages:
            raise HTTPException(status_code=400, detail="No content could be extracted from uploaded files.")

        # Run AI classification
        print(f"🤖 Running AI classification ({industry}) on {len(all_messages)} messages...")
        category_counts = classify_bulk(all_messages, industry=industry)

        # Calculate savings
        total_messages = sum(category_counts.values())
        minutes_per_message = 8
        hours_saved_monthly = (total_messages * minutes_per_message) / 60
        hourly_rate = 300  # ₹ per hour
        money_saved_monthly = hours_saved_monthly * hourly_rate
        annual_hours_saved = hours_saved_monthly * 12
        annual_money_saved = money_saved_monthly * 12

        # Automation score
        # List of categories that are typically automatable
        automatable_categories = [
            # Ecommerce/General
            "Order Status", "Refund/Return", "Payment Issue", "Shipping/Delivery",
            "Billing Inquiry", "Technical Support", "Account Access",
            # HR
            "Leave Request", "Payroll Query", "Benefits Inquiry",
            # IT
            "Access/Permissions", "Password Reset", "Software Issue",
            # Sales
            "New Lead", "Demo Request", "Follow-up"
        ]
        
        automatable_count = sum(count for cat, count in category_counts.items() if cat in automatable_categories)
        automation_score = min(int((automatable_count / total_messages * 100)), 100) if total_messages > 0 else 0

        # Top opportunities
        top_opportunities = []
        for category, count in category_counts.most_common(5):
            if category == "Other" and len(category_counts) > 1:
                continue # Skip "Other" in top ops if we have better ones
            percentage = int((count / total_messages * 100)) if total_messages > 0 else 0
            impact = "High" if percentage > 20 else "Medium" if percentage > 10 else "Low"
            top_opportunities.append({
                "area": category,
                "count": count,
                "potential_saving": f"{percentage}%",
                "impact": impact
            })

        # AI-powered recommendations
        print(f"💡 Generating AI recommendations for {industry}...")
        recommendations = generate_recommendations(category_counts, total_messages, industry=industry)

        # Build response
        audit_report = {
            "status": "success",
            "industry": industry,
            "files_analyzed": len(files),
            "total_messages_analyzed": total_messages,
            "audit_results": {
                "time_saved_monthly": f"{hours_saved_monthly:.1f} hours",
                "time_saved_annually": f"{annual_hours_saved:.1f} hours",
                "cost_reduction_monthly": f"₹{money_saved_monthly:,.0f}",
                "cost_reduction_annually": f"₹{annual_money_saved:,.0f}",
                "automation_score": f"{automation_score}/100",
                "category_breakdown": dict(category_counts),
                "top_opportunities": top_opportunities,
                "recommendations": recommendations
            }
        }

        # Generate PDF
        try:
            audit_data = {
                "total_messages": total_messages,
                "category_breakdown": dict(category_counts),
                "top_opportunities": top_opportunities,
                "recommendations": recommendations,
                "time_saved_annually": f"{annual_hours_saved:.1f} hours",
                "cost_reduction_annually": f"₹{annual_money_saved:,.0f}",
                "automation_score": automation_score,
            }
            run_audit_pipeline(all_messages, audit_data)
            audit_report["pdf_available"] = True
        except Exception as e:
            print(f"⚠️ PDF generation failed: {e}")
            audit_report["pdf_available"] = False

        print("✅ Audit complete!")
        return audit_report

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is

    except Exception as e:
        print(f"❌ Error: {e}")
        # Don't expose internal error details in production
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")

    finally:
        # ALWAYS clean up uploaded files, even on errors
        for path in saved_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass


@app.get("/download-report/")
def download_report():
    """Download the generated PDF report."""
    file_path = os.path.abspath(os.path.join(OUTPUT_FOLDER, "audit_report.pdf"))

    # Security: ensure path is within output folder
    if not file_path.startswith(os.path.abspath(OUTPUT_FOLDER)):
        raise HTTPException(status_code=400, detail="Invalid report path.")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found. Run audit first.")

    print(f"📄 Serving report: {file_path}")
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename="Synth_AI_Audit_Report.pdf",
    )


# Health check endpoint for monitoring
@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print("\n" + "="*60)
    print("🚀 Starting Synth AI Audit Backend")
    print("="*60)
    print(f"📍 Server: http://0.0.0.0:{port}")
    print(f"📖 API Docs: http://localhost:{port}/docs")
    print(f"🔒 Security: Rate limiting, file validation, headers enabled")
    print("="*60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")