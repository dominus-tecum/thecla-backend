import os
import json
import uuid
from datetime import datetime
from typing import Dict

class SimulationAIService:
    def __init__(self):
        # Simple service without OpenAI for now
        pass
    
    async def generate_patient_case(self, request_data: Dict) -> Dict:
        """Generate a patient case (simplified version)"""
        specialty = request_data.get("specialty", "emergency")
        difficulty = request_data.get("difficulty", "intermediate")
        
        return {
            "id": str(uuid.uuid4()),
            "title": f"{specialty.title()} Clinical Scenario - {difficulty.title()}",
            "presentation": f"Patient presents with symptoms typical for {specialty}. Requires clinical assessment and management.",
            "demographics": {"age": 45, "gender": "female", "relevantHistory": "Hypertension, non-smoker"},
            "initialVitals": {"hr": 110, "bp": "140/90", "rr": 22, "temp": 38.2, "spo2": 94, "pain": 6},
            "initialAssessment": "Patient appears anxious but alert. Requires immediate assessment and intervention.",
            "decisionPoints": [
                {
                    "id": "dp1",
                    "situation": "Initial patient assessment and management priorities",
                    "options": [
                        {
                            "text": "Perform ABCDE assessment and establish IV access",
                            "isOptimal": True,
                            "rationale": "Standard initial approach for emergency patients",
                            "consequences": ["Systematic assessment", "Early intervention"]
                        },
                        {
                            "text": "Order extensive lab tests before assessment",
                            "isOptimal": False,
                            "rationale": "Delays critical assessment and intervention",
                            "consequences": ["Wasted time", "Missed critical findings"]
                        }
                    ],
                    "correctActions": ["ABCDE assessment", "IV access", "Monitor vitals"],
                    "commonErrors": ["Jumping to diagnosis", "Missing vital signs"]
                },
                {
                    "id": "dp2",
                    "situation": "Patient's condition begins to deteriorate",
                    "options": [
                        {
                            "text": "Administer oxygen and call for senior help",
                            "isOptimal": True,
                            "rationale": "Appropriate escalation and basic intervention",
                            "consequences": ["Improved oxygenation", "Team support"]
                        },
                        {
                            "text": "Continue current management and monitor",
                            "isOptimal": False,
                            "rationale": "Insufficient response to deterioration",
                            "consequences": ["Further deterioration", "Missed intervention window"]
                        }
                    ],
                    "correctActions": ["Administer oxygen", "Escalate care", "Reassess"],
                    "commonErrors": ["Delaying escalation", "Underestimating severity"]
                }
            ],
            "learningPoints": [
                "Systematic assessment saves lives",
                "Early recognition of deterioration",
                "Appropriate escalation of care"
            ],
            "estimatedDuration": 20,
            "specialty": specialty,
            "difficulty": difficulty
        }
    
    async def process_decision(self, request_data: Dict) -> Dict:
        """Process a clinical decision (simplified)"""
        return {
            "patientResponse": "Patient shows improvement with appropriate intervention.",
            "newVitals": {"hr": 95, "bp": "130/85", "rr": 18, "temp": 37.8, "spo2": 96},
            "complications": [],
            "feedback": "Good clinical decision. Appropriate assessment and intervention.",
            "scoreImpact": 10,
            "patientStatus": "improving",
            "trends": {"hr": "down", "bp": "down", "spo2": "up"}
        }

# Create instance
simulation_service = SimulationAIService()