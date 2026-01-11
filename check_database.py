import sqlite3
from sqlite3 import Error

class GPDataAnalyzer:
    """Analyzer for General Practitioner (GP) data classification"""
    
    def __init__(self, db_path='theclamed.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Connect to database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            return True
        except Error as e:
            print(f"❌ Database connection error: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def classify_gp_data(self):
        """Classify GP data into meaningful categories"""
        print("🎯 GENERAL PRACTITIONER (GP) DATA CLASSIFICATION")
        print("=" * 60)
        
        # Get all GP exams
        self.cursor.execute("""
            SELECT 
                e.id,
                e.title,
                e.source,
                e.release_date,
                COUNT(q.id) as total_questions,
                SUM(CASE WHEN q.topic IS NOT NULL AND q.topic != '' THEN 1 ELSE 0 END) as questions_with_topics
            FROM exams e
            LEFT JOIN questions q ON e.id = q.exam_id
            WHERE e.discipline_id = 'gp'
            GROUP BY e.id, e.title, e.source
            ORDER BY 
                CASE e.source 
                    WHEN 'singular' THEN 1
                    WHEN 'plural' THEN 2
                    WHEN 'quiz' THEN 3
                    WHEN 'intelligent' THEN 4
                    ELSE 5
                END,
                e.release_date DESC
        """)
        
        gp_exams = self.cursor.fetchall()
        
        # Classify by source with proper naming
        classifications = {
            'singular': [],
            'plural': [],
            'quiz': [],
            'intelligent': []
        }
        
        for exam in gp_exams:
            exam_id, title, source, release_date, total_q, topics_q = exam
            classifications[source].append({
                'id': exam_id,
                'title': title,
                'release_date': release_date,
                'total_questions': total_q,
                'questions_with_topics': topics_q,
                'completion_rate': (topics_q / total_q * 100) if total_q > 0 else 0
            })
        
        # Display with proper classification names
        self._display_gp_classification('📚 GP STUDY NOTES', 'singular', classifications['singular'])
        self._display_gp_classification('📝 GP EXAMS', 'plural', classifications['plural'])
        self._display_gp_classification('📄 GP REGULAR QUIZZES', 'quiz', classifications['quiz'])
        self._display_gp_classification('🤖 GP SMART QUIZZES', 'intelligent', classifications['intelligent'])
        
        # Topic analysis for GP
        self._analyze_gp_topics()
        
        # Summary statistics
        self._show_gp_summary(classifications)
    
    def _display_gp_classification(self, category_name, source_type, items):
        """Display GP classification with proper formatting"""
        print(f"\n{category_name}:")
        print("-" * 60)
        
        if not items:
            print("  (None found)")
            return
        
        for item in items:
            # Determine status based on topic completion
            if item['total_questions'] == 0:
                status = "🔘"
            elif item['questions_with_topics'] == item['total_questions']:
                status = "✅"
            elif item['questions_with_topics'] > 0:
                status = "⚠️"
            else:
                status = "❌"
            
            # Clean up the title
            title = item['title']
            if title:
                # Remove redundant prefixes
                if title.startswith("Gp ") or title.startswith("GP "):
                    title = title[3:]
                
                # Capitalize properly
                title = title.strip()
            
            print(f"  {status} {title[:60]}{'...' if len(title) > 60 else ''}")
            print(f"     Questions: {item['total_questions']} total, {item['questions_with_topics']} with topics")
            
            if item['completion_rate'] > 0:
                print(f"     Topic completion: {item['completion_rate']:.1f}%")
            
            if item['release_date']:
                date_str = str(item['release_date'])[:19]
                print(f"     Created: {date_str}")
            
            print(f"     ID: {item['id'][:8]}...")
            print()
    
    def _analyze_gp_topics(self):
        """Analyze topic distribution for GP questions"""
        print("\n📊 GP TOPIC ANALYSIS:")
        print("-" * 60)
        
        # Get topic distribution for GP questions
        self.cursor.execute("""
            SELECT 
                q.topic,
                COUNT(*) as question_count,
                COUNT(DISTINCT q.exam_id) as exam_count
            FROM questions q
            JOIN exams e ON q.exam_id = e.id
            WHERE e.discipline_id = 'gp'
              AND q.topic IS NOT NULL 
              AND q.topic != ''
            GROUP BY q.topic
            ORDER BY question_count DESC
        """)
        
        topics = self.cursor.fetchall()
        
        if not topics:
            print("  No topics found in GP questions")
            return
        
        total_questions_with_topics = sum(t[1] for t in topics)
        
        for topic, count, exam_count in topics:
            if topic and topic != '':
                percentage = (count / total_questions_with_topics * 100) if total_questions_with_topics > 0 else 0
                print(f"  • {topic}: {count} questions ({percentage:.1f}%) in {exam_count} exams")
        
        # Questions without topics
        self.cursor.execute("""
            SELECT COUNT(*) 
            FROM questions q
            JOIN exams e ON q.exam_id = e.id
            WHERE e.discipline_id = 'gp'
              AND (q.topic IS NULL OR q.topic = '')
        """)
        
        no_topic_count = self.cursor.fetchone()[0]
        
        self.cursor.execute("""
            SELECT COUNT(*) 
            FROM questions q
            JOIN exams e ON q.exam_id = e.id
            WHERE e.discipline_id = 'gp'
        """)
        
        total_gp_questions = self.cursor.fetchone()[0]
        
        print(f"\n  📈 Summary:")
        print(f"     Total GP questions: {total_gp_questions}")
        print(f"     Questions WITH topics: {total_questions_with_topics}")
        print(f"     Questions WITHOUT topics: {no_topic_count}")
        
        if total_gp_questions > 0:
            completion_rate = (total_questions_with_topics / total_gp_questions * 100)
            print(f"     Topic completion rate: {completion_rate:.1f}%")
    
    def _show_gp_summary(self, classifications):
        """Show GP summary statistics"""
        print("\n📈 GP DATA SUMMARY:")
        print("-" * 60)
        
        # Count totals
        total_exams = sum(len(items) for items in classifications.values())
        total_questions = 0
        total_questions_with_topics = 0
        
        for source_type, items in classifications.items():
            for item in items:
                total_questions += item['total_questions']
                total_questions_with_topics += item['questions_with_topics']
        
        print(f"  Total GP Exams/Notes: {total_exams}")
        print(f"  Total GP Questions: {total_questions}")
        print(f"  Questions with Topics: {total_questions_with_topics}")
        print(f"  Questions without Topics: {total_questions - total_questions_with_topics}")
        
        if total_questions > 0:
            completion_rate = (total_questions_with_topics / total_questions * 100)
            print(f"  Overall Topic Completion: {completion_rate:.1f}%")
            
            if completion_rate == 100:
                print(f"  ✅ EXCELLENT: All questions have topics")
            elif completion_rate >= 80:
                print(f"  ✅ GOOD: {completion_rate:.1f}% topic coverage")
            elif completion_rate >= 50:
                print(f"  ⚠️  MODERATE: {completion_rate:.1f}% topic coverage")
            else:
                print(f"  ❌ LOW: Only {completion_rate:.1f}% of questions have topics")
        
        # Source distribution
        print(f"\n  Distribution by type:")
        
        type_names = {
            'singular': 'GP Study Notes',
            'plural': 'GP Exams',
            'quiz': 'GP Regular Quizzes',
            'intelligent': 'GP Smart Quizzes'
        }
        
        for source_type, items in classifications.items():
            if items:
                question_count = sum(item['total_questions'] for item in items)
                type_name = type_names.get(source_type, source_type)
                print(f"    • {type_name}: {len(items)} items, {question_count} questions")
    
    def list_gp_study_notes(self):
        """List all GP Study Notes (singular source)"""
        print("\n📋 GP STUDY NOTES DETAILS:")
        print("-" * 60)
        
        self.cursor.execute("""
            SELECT 
                e.id,
                e.title,
                e.release_date,
                COUNT(q.id) as total_questions,
                SUM(CASE WHEN q.topic IS NOT NULL AND q.topic != '' THEN 1 ELSE 0 END) as questions_with_topics
            FROM exams e
            LEFT JOIN questions q ON e.id = q.exam_id
            WHERE e.discipline_id = 'gp'
              AND e.source = 'singular'
            GROUP BY e.id, e.title
            ORDER BY e.title
        """)
        
        study_notes = self.cursor.fetchall()
        
        if not study_notes:
            print("  No GP Study Notes found")
            return
        
        print(f"Found {len(study_notes)} GP Study Notes:\n")
        
        for note in study_notes:
            exam_id, title, release_date, total_q, topics_q = note
            
            # Clean title
            clean_title = title
            if clean_title:
                clean_title = clean_title.strip()
            
            print(f"📘 {clean_title}")
            print(f"   ID: {exam_id[:8]}...")
            print(f"   Questions: {total_q} total, {topics_q} with topics")
            
            if total_q > 0:
                completion = (topics_q / total_q * 100)
                print(f"   Topic completion: {completion:.1f}%")
            
            if release_date:
                print(f"   Created: {release_date[:19]}")
            
            print()
    
    def run_gp_analysis(self):
        """Run complete GP analysis"""
        if not self.connect():
            return
        
        try:
            self.classify_gp_data()
            self.list_gp_study_notes()
            
            print("\n" + "=" * 60)
            print("✅ GP ANALYSIS COMPLETE")
            print("=" * 60)
            
        finally:
            self.close()


def main():
    """Main function"""
    print("🔍 GENERAL PRACTITIONER (GP) DATA ANALYZER")
    print("=" * 60)
    
    analyzer = GPDataAnalyzer('theclamed.db')
    analyzer.run_gp_analysis()


if __name__ == "__main__":
    main()