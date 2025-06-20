import streamlit as st
import os, sys
import paramiko
from agno.storage.agent.postgres import PostgresAgentStorage

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.metrics_operations import check_degraded_pgs, check_recent_osd_crashes, get_ceph_daemon_counts, get_cluster_health, get_diskoccupation, get_high_latency_osds
from backend.scrape_metricsdata import scrape_metrics
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory
from langchain.agents import initialize_agent, AgentType
from langchain_community.llms import Ollama

# Tool Functions
def get_disk_occupation(*args, **kwargs):
    jobs = get_diskoccupation(*args, **kwargs)
    if jobs:
        return " ## 📊 **Ceph Disk Occupation Per Node** \n" + "Here are some disk occupation status:\n" + "\n".join(
            [f"Node: {node}, Disk Occupation: {disk_usage} \n " for node, disk_usage in jobs]
        )


    return "Failed to fetch disk occupation status."

def checkdegraded_pgs(*args, **kwargs):
    pgs = check_degraded_pgs(*args, **kwargs)
    if pgs == 'True':
        return "we have few PGs degraded"

    return "No, we don't have any PGs degraded"

def checkrecent_osd_crashes(*args, **kwargs):
    response = check_recent_osd_crashes(*args, **kwargs)
    return response

def getcluster_health(*args, **kwargs):
    response = get_cluster_health(*args, **kwargs)
    health_status = response["health"]
    if response:
        return " ## 📊 **Ceph Health status** \n" + "\n ".join(
            [f"{health_status} \n "]
        )
    else:
        return "❌ Failed to get cluster health."

def checkhigh_latency_osds(*args, **kwargs):
    response =  get_high_latency_osds(*args, **kwargs)
    if response:
        return " ## 📊 **Ceph High Latency OSDs** \n" + "\n ".join(
            [f"OSD ID: {res['osd_id']}, Max Latency: {res['max_latency']}ms, Status: {res['status']} - {res['description']} \n " for res in response["high_latency_osds"]]
        )
    else:
        return "❌ No high latency OSDs found or there was an issue with the data."
    
def getcount_of_daemons(*args, **kwargs):
    response =  get_ceph_daemon_counts(*args, **kwargs)
    message = response["message"]
    if response:
        return " ## 📊 **Ceph Daemon Count** \n" + "\n ".join(
            [f"{message} \n "]
        )
    else:
        return "❌ Failed to get count of daemons from cluster."

# Define Tools
tools = [
    Tool(
        name="Get disk occupation status",
        func=get_disk_occupation,
        description="Lists the disk occupation status",
        return_direct=True,  # Ensures the response is directly sent to the user
    ),
    Tool(
        name="Get degraded PGs",
        func=checkdegraded_pgs,
        description="Get degraded PGs",
        return_direct=True,  # Ensures the response is directly sent to the user
    ),
    Tool(
        name="Check recent OSD crashes",
        func=checkrecent_osd_crashes,
        description="Check recent OSD crashes",
        return_direct=True,  # Ensures the response is directly sent to the user
    ),
    Tool(
        name="Check Cluster health",
        func=getcluster_health,
        description="Check cluster health",
        return_direct=True,  # Ensures the response is directly sent to the user
    ),
    Tool(
        name="Check high latency OSDs",
        func=checkhigh_latency_osds,
        description="Check high latency OSDs",
        return_direct=True,  # Ensures the response is directly sent to the user
    ),
    Tool(
        name="Get daemons count",
        func=getcount_of_daemons,
        description="Get daemons count",
        return_direct=True,  # Ensures the response is directly sent to the user
    ),
]

# Memory and LLM
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
llm = Ollama(model="llama3")

db_url = 'postgresql://postgres:postgres@localhost:5432/postgres'

storage = PostgresAgentStorage(
    # store sessions in the ai.sessions table
    table_name="agent_sessions",
    # db_url: Postgres database URL
    db_url=db_url,
)

# Initialize AI Agent
agent = initialize_agent(
    storage=storage,
    tools=tools,
    llm=llm,
    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
    memory=memory,
    verbose=True,
    handle_parsing_errors=True
)

def process_query(query: str):
    response = agent.run(query)
    # st.session_state.chat_history.append((query, response))
    return response

def test_ssh_connection(ip, username, password):
    """Attempts SSH connection to a given Ceph cluster IP."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(ip, username=username, password=password, timeout=5)
        ssh.close()
        return True
    except Exception as e:
        return str(e)  # Return the error message

# Streamlit page configuration
st.set_page_config(page_title="Observability AI Bot", page_icon="🤖", layout="wide")

# Custom CSS for a more attractive UI
st.markdown("""
    <style>
        body { font-family: 'Arial', sans-serif; }
        .sidebar .sidebar-content { background-color: #1E1E1E; color: white; }
        .sidebar h2 { color: #4CAF50; }
        .chat-bubble { padding: 10px; border-radius: 10px; margin: 5px; }
        .user-bubble { background-color: #E3F2FD; }
        .bot-bubble { background-color: #D9F7BE; }
    </style>
""", unsafe_allow_html=True)

# Custom chat message function
def chat_message(role, content):
    if role == "user":
        st.markdown(f"""
        <div class="chat-bubble user-bubble">
            <strong>👤 You:</strong><br> {content}
        </div>
        """, unsafe_allow_html=True)
    elif role == "assistant":
        st.markdown(f"""
        <div class="chat-bubble bot-bubble">
            <strong>🤖 Bot:</strong><br> {content}
        </div>
        """, unsafe_allow_html=True)

# Display the main title
st.markdown("""
    <h1 style='text-align: center; color: #4CAF50; font-size: 36px;'>🤖 Observability AI Bot</h1>
    <p style='text-align: center; font-size: 18px; color: gray;'>Monitor and manage your Ceph cluster effortlessly</p>
    <hr style='border: 1px solid #ccc;'>
""", unsafe_allow_html=True)


# Initialize session state for storing cluster data
if "cluster_data" not in st.session_state:
    st.session_state.cluster_data = {}  # Stores {"Cluster 1": "192.168.1.10", ...}

# Sidebar: Ceph SSH Authentication Panel
st.sidebar.markdown("<h2>🔐 Ceph SSH Authentication</h2>", unsafe_allow_html=True)

with st.sidebar.expander("⚙️ SSH Configuration", expanded=True):
    ssh_username = st.text_input("👤 SSH Username", placeholder="Enter SSH username")
    ssh_password = st.text_input("🔒 SSH Password", placeholder="Enter SSH password", type="password")

    # Add multiple cluster IPs dynamically
    cluster_ips = st.text_area("🌍 Ceph Cluster IPs", placeholder="Enter IPs, one per line", height=100)

    connect_button = st.button("🔗 Connect to Clusters")
    
# Handle SSH authentication
if connect_button:
    if ssh_username and ssh_password and cluster_ips.strip():
        ip_list = [ip.strip() for ip in cluster_ips.split("\n") if ip.strip()]  # Remove empty lines

        failed_ips = {}

        for ip in ip_list:
            scrape_metrics(ip)
            if ip in st.session_state.cluster_data.values():  # Skip already connected IPs
                continue

            result = test_ssh_connection(ip, ssh_username, ssh_password)
            if result is True:
                # Find the next available cluster name
                existing_numbers = [
                    int(name.split(" ")[1]) for name in st.session_state.cluster_data.keys()
                ]
                next_cluster_number = max(existing_numbers, default=0) + 1
                cluster_name = f"Cluster {next_cluster_number}"
                
                st.session_state.cluster_data[cluster_name] = ip  # Store correctly
            else:
                failed_ips[ip] = result  # Store error message per IP

        if failed_ips:
            for ip, error in failed_ips.items():
                st.sidebar.error(f"❌ Failed to connect to {ip}: {error}")
        elif ip_list:
            st.sidebar.success(f"✅ Successfully connected to {len(ip_list) - len(failed_ips)} new cluster(s)!")
    else:
        st.sidebar.error("❌ Please fill in all fields before connecting.")
        
# Show connected clusters at the left bottom
if st.session_state.cluster_data:
    with st.sidebar.expander("🔗 Connected Ceph Clusters", expanded=True):
        selected_clusters = st.multiselect(
            "Select clusters to disconnect:", 
            list(st.session_state.cluster_data.keys()), 
            key="selected_disconnect"
        )

        if st.button("❌ Disconnect Selected"):
            for cluster_name in selected_clusters:
                del st.session_state.cluster_data[cluster_name]  # Remove from session state

            st.sidebar.success(f"✅ Disconnected {len(selected_clusters)} cluster(s)!")
            st.rerun()  # Refresh UI after removal

        for cluster_name, ip in st.session_state.cluster_data.items():
            st.markdown(f"✅ **{cluster_name}: {ip}**")

# Class to handle individual chat sessions
class ChatSession:
    def __init__(self, session_name):
        self.session_name = session_name
        self.messages = self.get_default_messages()

    def get_default_messages(self):
        return []

    def reset_user_messages(self):
        self.messages = self.get_default_messages()

# Class to manage chat history
class ChatHistory:
    def __init__(self):
        if "chat_sessions" not in st.session_state:
            st.session_state["chat_sessions"] = {"default": ChatSession("default")}
        if "current_chat" not in st.session_state:
            st.session_state["current_chat"] = "default"

# Class to interact with Ollama model
class OllamaChat:
    def __init__(self, model="llama3.2"):
        self.model = model

    def fetch_response(self, prompt):
        try:
            ollama_llm = Ollama(model=self.model)
            response = ollama_llm.invoke(prompt)
            return response
        except Exception as e:
            return f"Error: {e}"

# Display the main title
st.markdown("<h1 style='text-align: center;'>🤖 Welcome to Observability bot!</h1>", unsafe_allow_html=True)

# Initialize chat history and session
chat_history = ChatHistory()

# Get current chat session
current_chat_name = st.session_state.current_chat
current_chat = st.session_state.chat_sessions[current_chat_name]

# Check if user has entered any message
user_has_entered_message = any(msg["role"] in ["user", "assistant"] for msg in current_chat.messages)

# Display chat history
for message in current_chat.messages:
    role = message.get("role", "system")
    if role == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])
    elif role == "assistant":
        with st.chat_message("assistant"):
            st.markdown(message["content"])
    else:
        st.markdown(message["content"], unsafe_allow_html=True)

# Initialize Ollama model
ollama_chat = OllamaChat()

# Chat input
if prompt := st.chat_input("Type your message here..."):
    current_chat.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🤔 Thinking..."):       
            response = process_query(prompt)
            st.markdown(response)
            current_chat.messages.append({"role": "assistant", "content": response})

    st.rerun()
    

# Show "Clear Chat" button if messages exist
if user_has_entered_message:
    if st.button(f"🗑️ Clear {current_chat_name} Chat", key=f"clear_chat_{current_chat_name}"):
        st.session_state.chat_sessions[current_chat_name].reset_user_messages()
        st.rerun()
