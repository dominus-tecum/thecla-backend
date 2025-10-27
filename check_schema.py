from sqlalchemy import create_engine, text

SQLALCHEMY_DATABASE_URL = "sqlite:///./theclamed.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

def check_exams_schema():
    """Check the actual schema of the exams table"""
    print("🔍 Checking exams table schema...")
    
    try:
        with engine.connect() as conn:
            # Get all columns from exams table
            result = conn.execute(text("PRAGMA table_info(exams)"))
            columns = []
            for row in result:
                columns.append({
                    'name': row[1],
                    'type': row[2],
                    'notnull': row[3],
                    'default': row[4],
                    'pk': row[5]
                })
            
            print("📋 Exams table columns:")
            for col in columns:
                print(f"   - {col['name']} ({col['type']})")
            
            # Check for required columns
            required_columns = ['source', 'is_released', 'release_date', 'is_active']
            missing_columns = []
            
            for req_col in required_columns:
                if not any(col['name'] == req_col for col in columns):
                    missing_columns.append(req_col)
            
            if missing_columns:
                print(f"❌ Missing columns: {missing_columns}")
            else:
                print("✅ All required columns present!")
                
            return columns
                
    except Exception as e:
        print(f"❌ Error checking schema: {e}")
        return []

if __name__ == "__main__":
    check_exams_schema()