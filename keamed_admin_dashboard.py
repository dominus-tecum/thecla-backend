from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import os

app = FastAPI()

# Database dependency
def get_db():
    # Your existing database setup
    pass

@app.get("/admin/keamedexam", response_class=HTMLResponse)
async def admin_dashboard():
    """Main admin dashboard page"""
    # Serve your HTML template
    with open("templates/keamed_admin_dashboard.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/admin/keamedexam/results")
async def get_keamedexam_results(db: Session = Depends(get_db)):
    """API endpoint to get all KeamedExam results"""
    try:
        # Get all results with basic info
        results = db.execute(text('''
            SELECT user_name, user_profession, exam_type, exam_id, score, timestamp 
            FROM keamedexam_results 
            ORDER BY timestamp DESC
        ''')).fetchall()
        
        # Convert to list of dictionaries
        results_list = []
        for row in results:
            results_list.append(dict(row._mapping))
        
        return results_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.api_route("/admin/keamedexam/config", methods=["GET", "POST"])
async def manage_exam_config(db: Session = Depends(get_db)):
    """Manage exam configurations"""
    try:
        from fastapi import Request
        request: Request = Depends()
        
        if request.method == "POST":
            # Update configuration
            data = await request.json()
            exam_type = data.get('exam_type')
            time_per_question = data.get('time_per_question')
            total_questions = data.get('total_questions')
            
            db.execute(text('''
                INSERT OR REPLACE INTO keamedexam_config 
                (exam_type, time_per_question, total_questions)
                VALUES (:exam_type, :time_per_question, :total_questions)
            '''), {
                "exam_type": exam_type,
                "time_per_question": time_per_question,
                "total_questions": total_questions
            })
            db.commit()
            
            return {"status": "success"}
        
        else:
            # Get current configurations
            configs = db.execute(text('SELECT * FROM keamedexam_config')).fetchall()
            config_list = [dict(row._mapping) for row in configs]
            return config_list
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Create templates directory if it doesn't exist
    if not os.path.exists("templates"):
        os.makedirs("templates")
    
    uvicorn.run(app, host="0.0.0.0", port=5000)