"""
Synth AI Audit Backend
FastAPI server with CORS enabled for frontend integration
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import uvicorn

app = FastAPI(title="Synth AI Audit Engine")

# Enable CORS for frontend (VERY IMPORTANT!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "Synth AI Audit Backend is running! 🚀"
    }

@app.post("/audit")
async def audit_files(files: List[UploadFile] = File(...)):
    """
    Main audit endpoint - receives files and returns analysis
    """
    try:
        uploaded_files = []
        
        # Process each uploaded file
        for file in files:
            # Read file content
            content = await file.read()
            
            uploaded_files.append({
                "filename": file.filename,
                "content_type": file.content_type,
                "size": len(content)
            })
            
            # TODO: Add your actual AI analysis logic here
            # For now, we'll return mock data
        
        # Mock audit report (replace with your actual AI analysis)
        report = {
            "status": "success",
            "files_analyzed": len(files),
            "files": uploaded_files,
            "audit_results": {
                "time_saved_annually": "2,400 hours",
                "cost_reduction": "$156,000",
                "automation_score": "82/100",
                "top_opportunities": [
                    {
                        "area": "Email Processing",
                        "potential_saving": "85%",
                        "impact": "High"
                    },
                    {
                        "area": "Data Entry",
                        "potential_saving": "72%",
                        "impact": "High"
                    },
                    {
                        "area": "Report Generation",
                        "potential_saving": "68%",
                        "impact": "Medium"
                    },
                    {
                        "area": "Customer Support",
                        "potential_saving": "61%",
                        "impact": "Medium"
                    }
                ],
                "recommendations": [
                    "Implement AI Email Assistant for automated email categorization",
                    "Deploy Data Extraction AI for processing invoices and forms",
                    "Set up automated report generation system"
                ]
            }
        }
        
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 Starting Synth AI Audit Backend")
    print("="*50)
    print("📍 Server running at: http://127.0.0.1:8000")
    print("📖 API docs at: http://127.0.0.1:8000/docs")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)