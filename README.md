# 🖧 Python Proxy, Server, and Client System

This project demonstrates a system with a proxy server, a computation server, and a client. The system supports request caching, complex mathematical expression evaluation, and step-by-step explanations.

---

## ⭐ Features

### 🖥️ Proxy Server
- Manages requests between the client and server.
- Implements caching to improve efficiency.
- Handles stale and fresh data intelligently.
- Multithreaded to support multiple clients concurrently.

### 🧮 Computation Server
- Evaluates complex mathematical expressions.
- Provides step-by-step explanations for the computations.
- Supports caching for repeated requests.

### 👨‍💻 Client
- Sends mathematical expressions to the server via the proxy.
- Displays results and computation steps.
- Predefined set of example expressions for testing.

---

## 🛠️ Requirements
- Python 3.9+
- Required Modules:
  - `argparse`
  - `socket`
  - `threading`
  - Custom `api` module (included in the project).

---

## 🚀 How to Run

### Start the Server:
1. Navigate to the project directory.
2. Run the server:
   ```bash
   python server.py -H <host> -p <port>
Default: localhost:8080

Start the Proxy:
Navigate to the project directory.
Run the proxy:
bash
Copy code
python proxy.py -ph <proxy_host> -pp <proxy_port> -sh <server_host> -sp <server_port>
Example: Connect proxy to the server on localhost:
bash
Copy code
python proxy.py -ph localhost -pp 9090 -sh localhost -sp 8080
Start the Client:
Navigate to the project directory.
Run the client:
bash
Copy code
python client.py -H <proxy_host> -p <proxy_port>
Example:
bash
Copy code
python client.py -H localhost -p 9090
📜 Usage
The client displays a list of predefined mathematical expressions.
Choose an expression by its name or type exit to close the connection.
Results are fetched via the proxy, leveraging server computation and caching.
🗂️ File Overview
proxy.py: Implements the proxy server with caching and multithreading.
server.py: Evaluates mathematical expressions and provides computation steps.
client.py: Sends requests, receives responses, and displays results to the user.
