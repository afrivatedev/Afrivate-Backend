import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Afrivate.settings')
django.setup()

from support.models import KnowledgeBaseArticle

articles = [
    {
        "title": "How to reset your password",
        "category": "Account Management",
        "status": "approved",
        "description": "User has forgotten their password and cannot log into their Afrivate account.",
        "solution": "To reset your password, go to the login page and click on the 'Forgot Password?' link. Enter the email address associated with your Afrivate account. You will receive an email with a secure link to reset your password. Click the link and enter your new password. If you don't see the email, please check your spam folder."
    },
    {
        "title": "How to apply for a volunteer opportunity",
        "category": "Volunteering",
        "status": "approved",
        "description": "A volunteer wants to find and apply for new opportunities posted by organizations.",
        "solution": "To apply for a volunteer opportunity, log into your Pathfinder dashboard and click on 'Available Opportunities' in the left sidebar. Browse or search the list of open roles. Click on an opportunity to view its details, requirements, and duration. If you are a good fit, click the 'Apply' button and submit your application. You can track the status of your applications under the 'My Applications' tab."
    },
    {
        "title": "Viewing and Downloading Credentials",
        "category": "Credentials",
        "status": "approved",
        "description": "A user wants to access the certificates or credentials they earned after completing a volunteer engagement.",
        "solution": "Once an organization verifies that you have successfully completed a volunteer engagement, your credentials will automatically be issued to your profile. To view them, navigate to the 'My Experience' section in your dashboard. Here, you will see a list of your completed engagements and a button to view, download, or share your official Afrivate certificate."
    }
]

for data in articles:
    KnowledgeBaseArticle.objects.get_or_create(title=data["title"], defaults=data)

print(f"Successfully seeded {len(articles)} Knowledge Base articles into the database!")
