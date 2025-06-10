<body>

  <h1>💬 Ollama Chat App</h1>
  <p>Real-time, multi-room chat application powered by a local LLM (LLaMA 3.2) via Ollama, with asynchronous messaging using Socket.IO and a Streamlit frontend. Fully containerized with Docker Compose for seamless deployment.</p>

  <h2>📋 Project Overview</h2>
  <ul>
    <li>Local LLM inference using Ollama (e.g., LLaMA 3)</li>
    <li>Asynchronous real-time messaging with Flask + Socket.IO</li>
    <li>Modern web UI built on Streamlit</li>
    <li>Multi-user, multi-room support</li>
    <li>Containerized deployment via Docker Compose</li>
  </ul>
  <p><strong>Deliverables:</strong> Public GitHub repo with source code, Dockerfiles, docker-compose.yml, and detailed README</p>

  <h2>🎥 Demo Video</h2>
  <div class="video-container">
    <p> Video LINK : https://www.youtube.com/watch?v=dcsJC71RYmk </p>
  </div>
  
  <h2>🚀 Quick Start</h2>
  <ol>
    <li>Clone repository:
      <pre><code>git clone https://github.com/Stu-ops/ollama-chat-application.git</code></pre>
    </li>
    <li>Navigate to folder:
      <pre><code>cd ollama-chat-application</code></pre>
    </li>
    <li>Build & launch containers:
      <pre><code>docker-compose up --build -d</code></pre>
    </li>
    <li>Verify logs:
      <pre><code>docker-compose logs -f</code></pre>
    </li>
    <li>Open UI:
      <ul>
        <li>Frontend: <a href="http://localhost:8501">http://localhost:8501</a></li>
        <li>Backend API: <a href="http://localhost:5000">http://localhost:5000</a></li>
        <li>Ollama API: <a href="http://localhost:11434">http://localhost:11434</a></li>
      </ul>
    </li>
  </ol>

  <h2>💬 Usage</h2>
  <ol>
    <li>In the sidebar, enter your username and pick a room (general, tech, random)</li>
    <li>Click <strong>Connect</strong></li>
    <li>Type messages in the input box and press <strong>Send</strong></li>
    <li>To trigger AI, prefix your message with <code>@ai</code> or include this into your text</li>
  </ol>

  <h2>🔧 Architecture</h2>
  <p><strong>Diagram:</strong></p>
  <p>[ Streamlit Frontend ] ←→ [ Flask + Socket.IO Backend ] ←→ [ Ollama LLM Container ]</p>
  <ul>
    <li><strong>Frontend:</strong> <code>streamlit_app.py</code> for chat UI</li>
    <li><strong>Backend:</strong> <code>app.py</code> (Flask + Socket.IO)</li>
    <li><strong>AI:</strong> Ollama container serving LLaMA 3.2</li>
    <li><strong>Deployment:</strong> Docker Compose with services: <code>ollama</code>, <code>backend</code>, <code>frontend</code></li>
  </ul>

  <h2>🛠 Technology Stack</h2>
  <ul>
    <li>Language: Python 3.9</li>
    <li>LLM Server: Ollama (LLaMA 3.2)</li>
    <li>Backend: Flask, Flask-SocketIO</li>
    <li>Frontend: Streamlit, python-socketio</li>
    <li>Deployment: Docker, Docker Compose</li>
  </ul>

  <h2>⚙️ Configuration & Customization</h2>
  <ul>
    <li><strong>Model:</strong> Set <code>MODEL_NAME</code> in <code>docker-compose.yml</code></li>
    <li><strong>Rooms:</strong> Modify default list in <code>streamlit_app.py</code></li>
    <li><strong>AI Trigger:</strong> Adjust logic in <code>app.py</code></li>
    <li><strong>Docker Volumes:</strong> Use mounts for dev, remove for production</li>
  </ul>

  <h2>📊 Monitoring & Health</h2>
  <ul>
    <li>Backend health: <code>GET /health</code> → returns <code>status: healthy</code></li>
    <li>Ollama status: <code>GET /ollama-status</code></li>
    <li>Logs:
      <pre><code>docker-compose logs backend</code></pre>
      <pre><code>docker-compose logs frontend</code></pre>
    </li>
  </ul>

  <h2>🔄 Scaling & Production</h2>
  <ul>
    <li>Add Redis for session store</li>
    <li>Use DB for chat history</li>
    <li>Load balancer (Nginx/HAProxy)</li>
    <li>Enable GPU (NVIDIA runtime)</li>
  </ul>

  <h2>🙋‍♂️ Contact</h2>
  <p>For any questions or feedback, reach out to <a href="mailto:priyankbansal124@gmail.com">priyankbansal124@gmail.com</a></p>
  <p>Made with ❤ by Priyank Bansal</p>

</body>
</html>
