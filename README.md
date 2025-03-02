# | PhotoShare ~~~~~~

![alt text](app/templates/static/logo.png)
## 1. Introdusion to PhotoShare
*PhotoShare is a user-friendly and intuitive social media platform designed to revolutionize the way users share, discover, and interact with visual content. Our app offers a seamless experience for capturing, editing, and sharing photos, all while fostering a community of like-minded individuals who appreciate the beauty of visual storytelling.*
## 2. Precondition

Before starting the project, make sure that you have the following tools installed:

### 2.1. Python 3.11+

Make sure you have Python 3.11 or higher installed. You can check the current version of Python with the command:

```bash
python --version
```
```
python3 --version
```
### 2.2. Poetry
```
pip install poetry
```
After install you can verify the installed version with:
```
poetry --version
```
### 2.3. Docker

Make sure you have Docker installed
```
docker --version
```
### 2.4. Running PostgreSQL and Redis Containers

You can use Docker to run the necessary containers for PostgreSQL and Redis. Below are the commands to run them:
#### PostgreSQL Container
```
docker run --name postgres -e POSTGRES_PASSWORD=mysecretpassword -d postgres:latest
```
This command will start a PostgreSQL container with the default password set to mysecretpassword. You can change this password according to your requirements.
#### Redis Container
```
docker run --name redis -d redis:latest
```
This command will start a Redis container using the latest Redis image.
### 2.5. Install Project Dependencies
```
poetry install
```
After that, all dependencies will be installed, and the project will be ready to run.
```
This section describes the minimum requirements for working with your project. You can adapt it to your specific needs.
```
### 2.6. [.env] Configuration

You will need to create a .env file in the project root directory to configure the environment variables. Below is an example of what your .env file should look like:
```
# Path to your Python project
PYTHONPATH = <path_to_your_project>

# PostgreSQL configuration
PG_DRIVER=postgresql
PG_USER=your_pg_user
PG_PASSWORD=your_pg_password
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=your_pg_database

# Superuser credentials for PostgreSQL
POSTGRES_USER=your_pg_superuser
POSTGRES_PASSWORD=your_pg_superuser_password
POSTGRES_DB=your_pg_superuser_db

# SQLAlchemy Database URL
SQLALCHEMY_DATABASE_URL=${PG_DRIVER}://${PG_USER}:${PG_PASSWORD}@${PG_HOST}:${PG_PORT}/${PG_DATABASE}

# JWT Secret Key and Algorithm
SECRET_KEY_JWT=your_secret_key
ALGORITHM=HS256

# Cloudinary API credentials
CLD_NAME=your_cloudinary_name
CLD_API_KEY=your_cloudinary_api_key
CLD_API_SECRET=your_cloudinary_api_secret

# Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_DECODE_RESPONSES=True
REDIS_PASSWORD=your_redis_password
REDIS_URL_CORS=http://localhost:8000

# Email configuration
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your_email_username
MAIL_PASSWORD=your_email_password
MAIL_FROM=your_email@example.com
MAIL_FROM_NAME=PhotoShare
MAIL_SSL_TLS=True
MAIL_STARTTLS=True
```
Make sure to replace the placeholder values with your actual credentials !
----
This section describes the minimum requirements for working with your project. You can adapt it to your specific needs.
## 3. Installation instructions
- Step-by-step instructions on how to install a project on your local computer.

    - Step 1: Clone repository:
    ```
    git clone https://github.com/checkmateLL/py-web-team-project.git
    ```
    - Step 2: install requirements:
    ```
    poetry install
    ```
    - Step 3: Set virtual env, cinfigurations.
    - Step 4: Start project in terminal or docker conteiner.
    ```
    fastapi dev app/main.py
    ```
    ```
    docker build -t py-web-team-project-web:latest .
    docker-compose up -d
    ```
## 4.Testing
```
pytest
```
```
pytest --cov=.
```
## 5. Other information in Wiki project

https://github.com/checkmateLL/py-web-team-project/wiki

