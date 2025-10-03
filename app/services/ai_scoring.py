from typing import Dict, Optional
from app.config import settings

class AIScoringService:
    def __init__(self):
        self.openai_api_key = settings.openai_api_key
    
    def score_application(self, job_requirements: str, parsed_cv_data: Dict) -> Dict:
        """Score application based on job requirements"""
        
        if not self.openai_api_key:
            # Fallback to basic scoring if no OpenAI key
            return self._basic_scoring(job_requirements, parsed_cv_data)
        
        try:
            # Placeholder for advanced AI scoring
            # In production, integrate with OpenAI GPT-4 or similar
            return self._advanced_ai_scoring(job_requirements, parsed_cv_data)
        except Exception as e:
            print(f"AI scoring failed: {e}")
            return self._basic_scoring(job_requirements, parsed_cv_data)
    
    def _basic_scoring(self, job_requirements: str, parsed_cv_data: Dict) -> Dict:
        """Basic scoring based on keyword matching"""
        score = 50  # Base score
        
        # Score based on skills matching
        cv_skills = parsed_cv_data.get('skills', [])
        required_keywords = self._extract_keywords(job_requirements)
        
        matches = 0
        for keyword in required_keywords:
            if any(keyword.lower() in skill.lower() for skill in cv_skills):
                matches += 1
        
        if required_keywords:
            match_percentage = (matches / len(required_keywords)) * 100
            score += min(match_percentage * 0.4, 40)  # Up to 40 points for skills
        
        # Score based on content length (proxy for experience detail)
        text_length = parsed_cv_data.get('text_length', 0)
        if text_length > 2000:
            score += 10
        elif text_length > 1000:
            score += 5
        
        # Ensure score is between 0-100
        score = max(0, min(100, score))
        
        # Determine status
        if score >= 75:
            status = "shortlisted"
        elif score >= 50:
            status = "flagged"
        else:
            status = "rejected"
        
        return {
            'score': int(score),
            'status': status,
            'feedback': f"Matched {matches} out of {len(required_keywords)} key skills",
            'matched_skills': matches,
            'total_required_skills': len(required_keywords)
        }
    
    def _advanced_ai_scoring(self, job_requirements: str, parsed_cv_data: Dict) -> Dict:
        """Advanced AI scoring using OpenAI"""
        # This is a placeholder for actual OpenAI integration
        # You would make an API call to GPT-4 here
        basic_result = self._basic_scoring(job_requirements, parsed_cv_data)
        
        # Add some AI-specific enhancements
        if basic_result['score'] > 80:
            basic_result['feedback'] += " | Strong AI match"
        elif basic_result['score'] < 30:
            basic_result['feedback'] += " | Low AI confidence"
        
        return basic_result
    
    def _extract_keywords(self, text: str) -> list:
        """Extract relevant keywords from job requirements"""
        common_skills = [
            'python', 'javascript', 'java', 'react', 'angular', 'vue', 'node', 'express',
            'django', 'flask', 'fastapi', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'ci/cd', 'git', 'jenkins',
            'rest', 'graphql', 'typescript', 'html', 'css', 'sass', 'tailwind', 'bootstrap',
            'machine learning', 'ai', 'data science', 'pandas', 'numpy', 'tensorflow', 'pytorch',
            'agile', 'scrum', 'project management', 'leadership', 'communication', 'teamwork'
        ]
        
        found_skills = []
        text_lower = text.lower()
        for skill in common_skills:
            if skill in text_lower:
                found_skills.append(skill)
        
        return list(set(found_skills))