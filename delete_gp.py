import sqlite3

def delete_duplicate_gp_exams():
    """Delete duplicate GP exams from database"""
    
    db_path = 'theclamed.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🗑️  DELETING DUPLICATE GP EXAMS")
        print("=" * 60)
        
        # 1. First find all duplicate GP exams
        cursor.execute("""
            SELECT 
                title,
                source,
                COUNT(*) as duplicate_count,
                GROUP_CONCAT(id) as exam_ids,
                MIN(release_date) as first_created,
                MAX(release_date) as last_created
            FROM exams 
            WHERE discipline_id = 'gp'
            GROUP BY title, source 
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC, title
        """)
        
        duplicates = cursor.fetchall()
        
        if not duplicates:
            print("✅ No duplicate GP exams found")
            return
        
        print(f"Found {len(duplicates)} sets of duplicate exams:\n")
        
        total_to_delete = 0
        total_questions_to_delete = 0
        
        for title, source, count, exam_ids, first_created, last_created in duplicates:
            print(f"📝 '{title}' ({source}): {count} duplicates")
            print(f"   First created: {first_created}")
            print(f"   Last created: {last_created}")
            print(f"   Exam IDs: {exam_ids[:100]}...")
            
            # Count questions in these exams
            exam_id_list = exam_ids.split(',')
            placeholders = ','.join(['?'] * len(exam_id_list))
            
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM questions 
                WHERE exam_id IN ({placeholders})
            """, exam_id_list)
            
            question_count = cursor.fetchone()[0]
            print(f"   Total questions: {question_count}")
            
            # Determine which ones to keep (keep the newest)
            cursor.execute("""
                SELECT id 
                FROM exams 
                WHERE title = ? AND source = ? AND discipline_id = 'gp'
                ORDER BY release_date DESC 
                LIMIT 1
            """, (title, source))
            
            keep_id = cursor.fetchone()[0]
            print(f"   Keeping (newest): {keep_id[:8]}...")
            
            # Mark exams to delete (all except the newest)
            exams_to_delete = [eid for eid in exam_id_list if eid != keep_id]
            print(f"   Deleting: {len(exams_to_delete)} exams")
            
            total_to_delete += len(exams_to_delete)
            total_questions_to_delete += question_count - (question_count // count)  # Subtract one exam's worth
            
            print()
        
        # 2. Ask for confirmation
        print(f"\n⚠️  SUMMARY:")
        print(f"   Total duplicate exam sets: {len(duplicates)}")
        print(f"   Exams to delete: {total_to_delete}")
        print(f"   Approx. questions to delete: {total_questions_to_delete}")
        
        confirm = input("\nType 'DELETE' to confirm deletion: ").strip()
        if confirm != "DELETE":
            print("❌ Deletion cancelled")
            return
        
        print("\n🔧 Starting deletion...")
        
        # 3. Delete questions from duplicate exams first
        deleted_questions = 0
        deleted_exams = 0
        
        for title, source, count, exam_ids, first_created, last_created in duplicates:
            exam_id_list = exam_ids.split(',')
            
            # Get the ID to keep (newest)
            cursor.execute("""
                SELECT id 
                FROM exams 
                WHERE title = ? AND source = ? AND discipline_id = 'gp'
                ORDER BY release_date DESC 
                LIMIT 1
            """, (title, source))
            
            keep_id = cursor.fetchone()[0]
            
            # Delete questions from exams we're removing
            exams_to_delete = [eid for eid in exam_id_list if eid != keep_id]
            
            if exams_to_delete:
                placeholders = ','.join(['?'] * len(exams_to_delete))
                cursor.execute(f"""
                    DELETE FROM questions 
                    WHERE exam_id IN ({placeholders})
                """, exams_to_delete)
                
                questions_deleted = cursor.rowcount
                deleted_questions += questions_deleted
                print(f"   Deleted {questions_deleted} questions from '{title}' duplicates")
        
        # 4. Delete the duplicate exams
        for title, source, count, exam_ids, first_created, last_created in duplicates:
            exam_id_list = exam_ids.split(',')
            
            # Get the ID to keep
            cursor.execute("""
                SELECT id 
                FROM exams 
                WHERE title = ? AND source = ? AND discipline_id = 'gp'
                ORDER BY release_date DESC 
                LIMIT 1
            """, (title, source))
            
            keep_id = cursor.fetchone()[0]
            
            # Delete duplicate exams
            exams_to_delete = [eid for eid in exam_id_list if eid != keep_id]
            
            if exams_to_delete:
                placeholders = ','.join(['?'] * len(exams_to_delete))
                cursor.execute(f"""
                    DELETE FROM exams 
                    WHERE id IN ({placeholders})
                """, exams_to_delete)
                
                exams_deleted = cursor.rowcount
                deleted_exams += exams_deleted
                print(f"   Deleted {exams_deleted} duplicate exams of '{title}'")
        
        # 5. Commit changes
        conn.commit()
        
        # 6. Verify deletion
        print(f"\n✅ DELETION COMPLETE!")
        print(f"   Deleted exams: {deleted_exams}")
        print(f"   Deleted questions: {deleted_questions}")
        
        # Show remaining exams
        cursor.execute("""
            SELECT title, source, COUNT(*) as count
            FROM exams 
            WHERE discipline_id = 'gp'
            GROUP BY title, source
            HAVING COUNT(*) > 1
        """)
        
        remaining_duplicates = cursor.fetchall()
        
        if remaining_duplicates:
            print(f"\n⚠️  WARNING: Still have duplicates:")
            for title, source, count in remaining_duplicates:
                print(f"   • '{title}' ({source}): {count} copies")
        else:
            print(f"\n✅ All duplicates removed!")
        
        # Show summary of remaining GP exams
        cursor.execute("""
            SELECT 
                source,
                COUNT(*) as exam_count,
                SUM((SELECT COUNT(*) FROM questions q WHERE q.exam_id = e.id)) as question_count
            FROM exams e
            WHERE e.discipline_id = 'gp'
            GROUP BY source
        """)
        
        print(f"\n📊 REMAINING GP EXAMS:")
        for source, exam_count, question_count in cursor.fetchall():
            source_name = {
                'singular': 'Study Notes',
                'plural': 'Exams',
                'quiz': 'Regular Quizzes',
                'intelligent': 'Smart Quizzes'
            }.get(source, source)
            
            print(f"   • {source_name}: {exam_count} exams, {question_count} questions")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def check_current_duplicates():
    """Check current duplicate situation"""
    
    db_path = 'theclamed.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 CHECKING FOR DUPLICATES")
        print("=" * 60)
        
        # Check GP duplicates
        cursor.execute("""
            SELECT 
                title,
                source,
                COUNT(*) as duplicate_count,
                GROUP_CONCAT(id) as exam_ids
            FROM exams 
            WHERE discipline_id = 'gp'
            GROUP BY title, source 
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC, title
        """)
        
        gp_duplicates = cursor.fetchall()
        
        print(f"GP Duplicates: {len(gp_duplicates)} sets")
        for title, source, count, exam_ids in gp_duplicates:
            print(f"  • '{title}' ({source}): {count} copies")
        
        # Check Nurse duplicates
        cursor.execute("""
            SELECT 
                title,
                source,
                COUNT(*) as duplicate_count
            FROM exams 
            WHERE discipline_id = 'nurse'
            GROUP BY title, source 
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC, title
        """)
        
        nurse_duplicates = cursor.fetchall()
        
        print(f"\nNurse Duplicates: {len(nurse_duplicates)} sets")
        for title, source, count in nurse_duplicates:
            print(f"  • '{title}' ({source}): {count} copies")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Main function"""
    print("🧹 GP DUPLICATE CLEANUP TOOL")
    print("=" * 60)
    
    # First check what duplicates exist
    check_current_duplicates()
    
    print("\n" + "=" * 60)
    print("OPTIONS:")
    print("1. Delete duplicate GP exams")
    print("2. Just check for duplicates")
    print("3. Exit")
    print("=" * 60)
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == '1':
        delete_duplicate_gp_exams()
    elif choice == '2':
        check_current_duplicates()
    elif choice == '3':
        print("👋 Exiting...")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()