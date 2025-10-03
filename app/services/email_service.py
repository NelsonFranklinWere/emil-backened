import smtplib
from email.mime.text import MIMEText  # Fixed import
from email.mime.multipart import MIMEMultipart  # Fixed import
from email.mime.application import MIMEApplication
from jinja2 import Template
import os
from typing import List, Optional
from app.config import settings

class EmailService:
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
    
    def send_email(
        self, 
        to_emails: List[str], 
        subject: str, 
        html_content: str, 
        attachments: Optional[List[dict]] = None
    ) -> bool:
        try:
            msg = MIMEMultipart()  # Fixed class name
            msg['From'] = self.smtp_username
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            # Add HTML content
            msg.attach(MIMEText(html_content, 'html'))  # Fixed class name
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    if os.path.exists(attachment['path']):
                        with open(attachment['path'], 'rb') as file:
                            part = MIMEApplication(file.read(), Name=attachment['filename'])
                        part['Content-Disposition'] = f'attachment; filename="{attachment["filename"]}"'
                        msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            print(f"Email sent successfully to {to_emails}")
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def send_report_email(
        self, 
        to_emails: List[str], 
        job_title: str, 
        report_data: dict, 
        report_file_path: Optional[str] = None
    ) -> bool:
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .header { background: #f8f9fa; padding: 20px; text-align: center; border-radius: 8px; }
                .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 25px 0; }
                .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; border: 1px solid #e9ecef; }
                .shortlisted { border-top: 4px solid #10b981; }
                .flagged { border-top: 4px solid #f59e0b; }
                .rejected { border-top: 4px solid #ef4444; }
                .total { border-top: 4px solid #3b82f6; }
                .stat-number { font-size: 28px; font-weight: bold; margin: 10px 0; }
                .footer { margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; text-align: center; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0; color: #1f2937;">📊 Recruitment Report</h1>
                <p style="margin: 5px 0 0 0; color: #6b7280;">{{ job_title }}</p>
            </div>
            
            <div class="stats">
                <div class="stat-card total">
                    <h3 style="margin: 0; color: #6b7280;">Total Applicants</h3>
                    <div class="stat-number" style="color: #3b82f6;">{{ total_applicants }}</div>
                </div>
                <div class="stat-card shortlisted">
                    <h3 style="margin: 0; color: #6b7280;">Shortlisted</h3>
                    <div class="stat-number" style="color: #10b981;">{{ shortlisted }}</div>
                </div>
                <div class="stat-card flagged">
                    <h3 style="margin: 0; color: #6b7280;">Flagged</h3>
                    <div class="stat-number" style="color: #f59e0b;">{{ flagged }}</div>
                </div>
                <div class="stat-card rejected">
                    <h3 style="margin: 0; color: #6b7280;">Rejected</h3>
                    <div class="stat-number" style="color: #ef4444;">{{ rejected }}</div>
                </div>
            </div>
            
            {% if top_candidates %}
            <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #e9ecef;">
                <h2 style="color: #1f2937; margin-top: 0;">🏆 Top Candidates</h2>
                <ul style="padding-left: 20px;">
                {% for candidate in top_candidates %}
                    <li style="margin-bottom: 8px;">
                        <strong>{{ candidate.email }}</strong> 
                        <span style="color: #6b7280;">- Score: {{ candidate.score }}/100</span>
                    </li>
                {% endfor %}
                </ul>
            </div>
            {% endif %}
            
            <div class="footer">
                <p style="margin: 0; color: #6b7280;">
                    <em>This report was generated automatically by Emil AI Recruitment Platform</em>
                </p>
                <p style="margin: 10px 0 0 0; color: #9ca3af;">
                    Login to your dashboard for detailed analysis and candidate management.
                </p>
            </div>
        </body>
        </html>
        """
        
        template = Template(template_str)
        html_content = template.render(
            job_title=job_title,
            total_applicants=report_data.get('total_applicants', 0),
            shortlisted=report_data.get('shortlisted', 0),
            flagged=report_data.get('flagged', 0),
            rejected=report_data.get('rejected', 0),
            top_candidates=report_data.get('top_candidates', [])[:5]
        )
        
        attachments = []
        if report_file_path and os.path.exists(report_file_path):
            attachments.append({
                'path': report_file_path,
                'filename': f'report_{job_title.replace(" ", "_")}.pdf'
            })
        
        return self.send_email(
            to_emails=to_emails,
            subject=f"📊 Emil AI Report: {job_title}",
            html_content=html_content,
            attachments=attachments
        )