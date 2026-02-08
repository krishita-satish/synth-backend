"""
Minimal test server - if this works, the problem is in your main.py
"""
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Backend is working!"}

if __name__ == "__main__":
    print("\n🧪 Testing if FastAPI works...")
    print("If you see 'Uvicorn running', backend is OK!")
    print("Open: http://127.0.0.1:8000")
    print("-" * 50 + "\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8000)



