import pdfplumber
import docx
import magic
from typing import Optional, Dict
import os

class CVParser:
    def __init__(self):
        self.mime = magic.Magic(mime=True)
    
    def parse_resume(self, file_path: str) -> Optional[Dict]:
        """Parse resume file and extract structured data"""
        try:
            if not os.path.exists(file_path):
                return None
                
            file_type = self.mime.from_file(file_path)
            
            if file_type == 'application/pdf':
                return self._parse_pdf(file_path)
            elif file_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
                              'application/msword']:
                return self._parse_docx(file_path)
            elif file_type == 'text/plain':
                return self._parse_text(file_path)
            else:
                print(f"Unsupported file type: {file_type}")
                return None
                
        except Exception as e:
            print(f"Error parsing resume {file_path}: {e}")
            return None
    
    def _parse_pdf(self, file_path: str) -> Dict:
        """Extract text from PDF file"""
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"Error parsing PDF {file_path}: {e}")
        
        return self._extract_info_from_text(text)
    
    def _parse_docx(self, file_path: str) -> Dict:
        """Extract text from DOCX file"""
        text = ""
        try:
            doc = docx.Document(file_path)
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"
        except Exception as e:
            print(f"Error parsing DOCX {file_path}: {e}")
        
        return self._extract_info_from_text(text)
    
    def _parse_text(self, file_path: str) -> Dict:
        """Extract text from plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                text = file.read()
        except Exception as e:
            print(f"Error reading text file {file_path}: {e}")
            text = ""
        
        return self._extract_info_from_text(text)
    
    def _extract_info_from_text(self, text: str) -> Dict:
        """Basic information extraction from text"""
        lines = text.split('\n')
        
        # Extract email
        email = None
        for line in lines:
            if '@' in line and '.' in line:
                words = line.split()
                for word in words:
                    if '@' in word and '.' in word and ' ' not in word:
                        email_candidate = word.strip().lower()
                        if email_candidate.count('@') == 1:
                            email = email_candidate
                            break
                if email:
                    break
        
        # Extract skills (basic keyword matching)
        skills_keywords = [
            'python', 'javascript', 'java', 'react', 'angular', 'vue', 'node', 'express',
            'django', 'flask', 'fastapi', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'ci/cd', 'git', 'jenkins',
            'rest', 'graphql', 'typescript', 'html', 'css', 'sass', 'tailwind', 'bootstrap',
            'machine learning', 'ai', 'data science', 'pandas', 'numpy', 'tensorflow', 'pytorch'
        ]
        
        found_skills = []
        text_lower = text.lower()
        for skill in skills_keywords:
            if skill in text_lower:
                found_skills.append(skill.title())
        
        # Remove duplicates
        found_skills = list(set(found_skills))
        
        return {
            'email': email,
            'skills': found_skills,
            'text_length': len(text),
            'raw_text_preview': text[:500] + "..." if len(text) > 500 else text
        }