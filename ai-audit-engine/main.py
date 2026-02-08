from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from typing import List
import shutil
import os
import uvicorn
import pandas as pd
from collections import Counter

from services.audit_runner import run_audit_pipeline
from services.file_parser import parse_file
from services.ai_classifier import classify_bulk

app = FastAPI(title="Synth AI Audit Engine")

# CORS - Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Your Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


@app.get("/")
def root():
    return {
        "status": "running",
        "message": "Synth AI Audit Backend Running 🚀",
        "version": "1.0.0"
    }


@app.post("/audit")
async def audit_files(files: List[UploadFile] = File(...)):
    """
    Main audit endpoint - receives files and returns complete analysis
    This is what the frontend calls!
    """
    try:
        uploaded_files = []
        all_messages = []
        
        # Process each uploaded file
        for file in files:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            print(f"✅ Uploaded: {file.filename}")
            
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
                    "error": str(e)
                })
        
        # Run AI classification on messages
        print("🤖 Running AI classification...")
        category_counts = classify_bulk(all_messages[:100])  # Limit to 100 to save API costs
        
        # Calculate time and money savings
        total_messages = sum(category_counts.values())
        minutes_per_message = 8
        hours_saved_monthly = (total_messages * minutes_per_message) / 60
        hourly_rate = 300  # ₹ per hour
        money_saved_monthly = hours_saved_monthly * hourly_rate
        annual_hours_saved = hours_saved_monthly * 12
        annual_money_saved = money_saved_monthly * 12
        
        # Calculate automation score
        automatable_categories = ["Order Status", "Refund/Return", "Payment Issue"]
        automatable_count = sum(category_counts[cat] for cat in automatable_categories if cat in category_counts)
        automation_score = int((automatable_count / total_messages * 100)) if total_messages > 0 else 0
        
        # Build top opportunities
        top_opportunities = []
        for category, count in category_counts.most_common(5):
            percentage = int((count / total_messages * 100)) if total_messages > 0 else 0
            impact = "High" if percentage > 20 else "Medium" if percentage > 10 else "Low"
            
            top_opportunities.append({
                "area": category,
                "count": count,
                "potential_saving": f"{percentage}%",
                "impact": impact
            })
        
        # Generate recommendations
        recommendations = []
        if category_counts.get("Order Status", 0) > 10:
            recommendations.append("Deploy AI Order Tracking Bot - automate order status queries")
        if category_counts.get("Refund/Return", 0) > 10:
            recommendations.append("Implement Automated Refund Processing System")
        if category_counts.get("Payment Issue", 0) > 5:
            recommendations.append("Set up Payment Issue Auto-Resolution Agent")
        if len(all_messages) > 50:
            recommendations.append("Enable 24/7 AI Email Assistant for customer support")
        
        # Create comprehensive audit report
        audit_report = {
            "status": "success",
            "files_analyzed": len(files),
            "files": uploaded_files,
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
        
        # Also generate PDF report
        try:
            run_audit_pipeline(os.path.join(UPLOAD_FOLDER, files[0].filename))
            audit_report["pdf_available"] = True
        except Exception as e:
            print(f"⚠️ PDF generation failed: {e}")
            audit_report["pdf_available"] = False
        
        print("✅ Audit complete!")
        return audit_report
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download-report/")
def download_report():
    """Download the generated PDF report"""
    file_path = os.path.abspath(os.path.join(OUTPUT_FOLDER, "audit_report.pdf"))

    if not os.path.exists(file_path):
        return {"error": "Report not found. Run audit first."}

    print(f"📄 Serving report: {file_path}")
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename="Synth_AI_Audit_Report.pdf",
    )


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 Starting Synth AI Audit Backend")
    print("="*60)
    print("📍 Server: http://127.0.0.1:8000")
    print("📖 API Docs: http://127.0.0.1:8000/docs")
    print("📊 Upload test: http://127.0.0.1:8000")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")