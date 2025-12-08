import uuid
from typing import Dict

class ProcedureAIService:
    def __init__(self):
        pass
    
    async def generate_procedure_guide(self, request_data: Dict) -> Dict:
        """Generate a procedure guide (simplified)"""
        procedure = request_data.get("procedure", "Medical Procedure")
        specialty = request_data.get("specialty", "general")
        
        return {
            "id": str(uuid.uuid4()),
            "title": f"Standard {procedure}",
            "description": f"Step-by-step guide for {procedure}",
            "specialty": specialty,
            "difficulty": "intermediate",
            "indications": ["Clinical need", "Diagnostic requirement", "Therapeutic intervention"],
            "contraindications": ["Patient refusal", "Unsafe conditions", "Lack of equipment"],
            "equipment": [
                {"name": "Sterile gloves", "specs": "Appropriate size", "quantity": 1},
                {"name": "Antiseptic solution", "specs": "Chlorhexidine or povidone-iodine", "quantity": 1},
            ],
            "steps": [
                {
                    "stepNumber": 1,
                    "title": "Prepare equipment and environment",
                    "instructions": "Gather all necessary equipment. Ensure adequate lighting and space. Perform hand hygiene.",
                    "durationSeconds": 120,
                    "commonErrors": ["Missing equipment", "Poor lighting", "Skipping hand hygiene"],
                    "criticalCheckpoints": ["All equipment present", "Hand hygiene performed"],
                    "tips": ["Use a checklist", "Organize equipment before starting"]
                },
                {
                    "stepNumber": 2,
                    "title": "Patient preparation and consent",
                    "instructions": "Explain procedure to patient. Obtain informed consent. Position patient appropriately.",
                    "durationSeconds": 180,
                    "commonErrors": ["Inadequate explanation", "Missing consent", "Poor positioning"],
                    "criticalCheckpoints": ["Informed consent obtained", "Patient positioned correctly"],
                    "tips": ["Use simple language", "Check understanding", "Ensure comfort"]
                }
            ],
            "complications": [
                {
                    "name": "Infection",
                    "recognition": "Redness, swelling, pus, fever",
                    "management": "Antibiotics, wound care, medical review",
                    "prevention": "Sterile technique, proper antisepsis",
                    "severity": "moderate"
                }
            ],
            "checklist": [
                {"item": "Patient consent obtained", "isCritical": True, "weight": 10},
                {"item": "Equipment checked", "isCritical": True, "weight": 10},
                {"item": "Hand hygiene performed", "isCritical": True, "weight": 10},
            ],
            "averageDuration": 600,
            "version": 1
        }
    
    async def evaluate_step(self, request_data: Dict) -> Dict:
        """Evaluate a procedure step (simplified)"""
        return {
            "score": 85,
            "feedback": "Procedure step performed adequately. Focus on technique refinement.",
            "errors": [],
            "suggestions": ["Practice timing", "Refine technique"],
            "passed": True,
            "nextStep": request_data.get("stepNumber", 0) + 1
        }

# Create instance
procedure_service = ProcedureAIService()