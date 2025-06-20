# MetricMinds
Agentic AI implementation of observability 

# Supported python version
`>=3.10` and `<3.13`

# Architecture
<img width="1056" alt="Screenshot 2025-02-17 at 6 26 01 PM" src="https://github.com/user-attachments/assets/59068685-8df9-4e90-959d-76f9502df1a2" />


# Pre-requisites

1. Have ceph cluster with prometheus and telemetry enabled.
2. PostgreSQL should be up and running.
3. python3.10 is supported version
4. ollama to be installed in your machine.
5. (if we want to run any LLM model) Run
```
ollama pull deepseek-r1
```


# To run the UI Bot (frontend) code
1. source venv/bin/activate
2. git clone git@github.com:HaruChebrolu/MetricMinds.git
3. cd MetricMinds/
4. update username,password and database values in backend/.env
5. pip install -r backend/requirements.txt
6. pip install -r frontend/requirements.txt
7. cd frontend
8. streamlit run frontend.py

# To run the UI Bot backend code
1. python3 -m venv venv
2. source venv/bin/activate
3. git clone git@github.com:HaruChebrolu/MetricMinds.git
4. cd MetricMinds/
5. update username,password and database values in backend/.env
6. pip install -r frontend/requirements.txt
7. cd backend
8. python3 agent.py
