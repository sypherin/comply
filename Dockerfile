FROM python:3.11-slim AS builder
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ unixodbc-dev curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip wheel --wheel-dir=/wheels -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 PORT=8501
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg apt-transport-https unixodbc libodbc1 odbcinst && rm -rf /var/lib/apt/lists/*
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - &&     curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list &&     apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
