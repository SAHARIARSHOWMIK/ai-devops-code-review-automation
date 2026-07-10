AI DEVOPS & CODE REVIEW AUTOMATION PLATFORM - WINDOWS

1. Install Python 3.12+, Node.js 20+, and Git.
2. Run setup_windows.bat once.
3. Run seed_demo.bat once to load controlled sample data.
4. Run start_backend.bat.
5. Run start_frontend.bat in a second window.
6. Open http://localhost:5173.
7. Log in with admin@demo.com / demo1234.
8. API documentation: http://localhost:8000/docs.

For the full PostgreSQL/Redis/worker stack, copy .env.example to .env,
replace secrets, install Docker Desktop, and run: docker compose up --build
