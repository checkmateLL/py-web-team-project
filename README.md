# py-web-team-project
Team project for GoIT PYTHON SOFTWARE ENGINEERING
# Start project
```
git clone https://github.com/checkmateLL/py-web-team-project.git
```
```
cd py-web-team-project
```
Create Image
```
docker build -t py-web-team-project-web:latest .
```
Create and start docker-compose
```
docker-compose up -d
```
Set PYTHONPATH
```
export PYTHONPATH=/path/to/your/py-web-team-project 
```
Set alembic
```
docker-compose exec web alembic revision --autogenerate -m "Initial migration"
```
```
docker-compose exec web alembic upgrade head
```
<img width="1057" alt="Снимок экрана 2025-02-18 в 14 32 03" src="https://github.com/user-attachments/assets/9520aeb5-4306-4ee6-b27e-a78f566c7380" />


Open URL 
```
http://localhost:8000/
```
