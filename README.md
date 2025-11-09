Afrivate Backend

This is the backend service for Afrivate, a platform that connects users, manages authentication, and supports all app features via RESTful APIs.
Built with Django and Django REST Framework (DRF).

🚀 Tech Stack

    Python 3.x
    
    Django
    
    Django REST Framework
    
    SQLite / PostgreSQL
    
    JWT Authentication
    
    CORS Headers
    
    React (frontend)

⚙️ Setup Instructions

Clone the Repository
   
    git clone https://github.com/your-username/afrivate-backend.git
    cd afrivate-backend

Create a Virtual Environment
   
    python -m venv venv
    venv\Scripts\activate  # (Windows)
    # or
    source venv/bin/activate  # (Mac/Linux)

Install Dependencies

    pip install -r requirements.txt

Setup Environment Variables
Create a .env file in the project root and add:

    SECRET_KEY=your_django_secret_key
    DEBUG=True
    DATABASE_URL=your_database_url
    ALLOWED_HOSTS=*

Apply Migrations

    python manage.py migrate

Run the Server

    python manage.py runserver

🔑 Authentication Logic

    Register – create new user with email & password
    
    Login – JWT-based authentication
    
    Forgot Password – request password reset via email link
    
    Reset Password – update password using valid token
    
    Change Password – authenticated users can change password

🧩 API Endpoints (Basic)

      Endpoint	Method	Description
      /api/register/	POST	Register user
      /api/login/	POST	Login and get token
      /api/user/	GET	Fetch user details
      /api/password/forgot/	POST	Request reset email
      /api/password/reset/	POST	Reset password
      /api/password/change/	PUT	Change password

🧰 Developer Notes

    Use Postman or Insomnia to test endpoints

Add new apps with:

    python manage.py startapp app_name


Run tests with:

    python manage.py test

🧑‍💻 Contributors
Backend: 

Frontend: Afrivate Frontend Team

Project: Afrivate Team
