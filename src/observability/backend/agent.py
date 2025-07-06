from agno.storage.agent.postgres import PostgresAgentStorage
from langchain.agents import AgentType, initialize_agent
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool
from langchain_community.llms import Ollama

from .connection import get_db_string
from .metrics_operations import (
    check_degraded_pgs,
    check_recent_osd_crashes,
    get_ceph_daemon_counts,
    get_cluster_health,
    get_diskoccupation,
    get_high_latency_osds,
)

# Define Tools
tools = [
    Tool(
        name="Get disk occupation",
        func=get_diskoccupation,
        description="Fetches the disk occupation per node.",
    ),
    Tool(
        name="Check degraded PGs",
        func=check_degraded_pgs,
        description="Checks degraded PGs.",
    ),
    Tool(
        name="Check recent OSD crashes",
        func=check_recent_osd_crashes,
        description="Checks recent OSD crashes.",
    ),
    Tool(
        name="Check cluster health",
        func=get_cluster_health,
        description="Check cluster health",
    ),
    Tool(
        name="Check high latency OSDs",
        func=get_high_latency_osds,
        description="Check high latency OSDs",
    ),
    Tool(
        name="Check count of daemons",
        func=get_ceph_daemon_counts,
        description="Check count of daemons",
    ),
]

# Memory for Conversation
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

chat_history = memory.load_memory_variables({}).get("chat_history", [])
if not isinstance(chat_history, list):
    chat_history = []

# Language Model
"""llm = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.1",
    token=HUGGINGFACEHUB_API_TOKEN
)"""
llm = Ollama(model="llama3")

agent_prompt = """You are a Ceph observability assistant. Only answer questions related to Ceph cluster status, health, storage, and performance. 
If a query is unrelated to Ceph, respond with: 'I can only assist with Ceph-related queries.'

- If the user asks for **disk occupation** (e.g., "Get disk occupation"), always use `Get disk occupation`.
- If the user asks for **cluster status** (e.g., "What is the status of Cluster 1?"), always use `Check cluster health`.
- If the user asks to **list OSDs**, use `Check count of daemons`.

Do not make assumptions. Only respond with the correct tool.
Do NOT guess. Only respond using the correct tool.
"""


def query_llm(prompt: str):
    return llm.text_generation(prompt, max_new_tokens=100)


# DB connection
storage = PostgresAgentStorage(
    table_name="agent_sessions",
    db_url=get_db_string(),
)

# Initialize AI Agent
agent = initialize_agent(
    storage=storage,
    tools=tools,
    prompt=agent_prompt,
    llm=llm,
    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
    memory=memory,
    verbose=True,
    handle_parsing_errors=True,
)


# Process query
def process_query(query: str):
    return agent.run(query)


def main_agentic():
    while True:
        query = input("\n💬 Enter command: ").strip()
        if query.lower() == "exit":
            print("👋 Exiting agent...")
            break

        response = process_query(query)
        print(response)


if __name__ == "__main__":
    # main_agentic_streamlit()
    main_agentic()
