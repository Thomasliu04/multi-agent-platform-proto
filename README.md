# multi-agent-platform-proto

For your final project, your team will design and implement a Multi-Agent Collaborative Platform. This system will bridge the gap between human instruction and autonomous AI execution. You are required to build a framework where multiple heterogeneous agents can communicate, dynamically divide complex tasks, interact with humans, execute code, and evolve their capabilities over time based on past experiences.

The team members will be finalized by the end of next week.

Core System Boundaries & Design Constraints
To ensure a level playing field and focus purely on backend AI engineering, your system must strictly adhere to the following architectural boundaries:

2.1. Communication & Collaboration Topologies

1-on-1 & Group Chats: The system must support direct Agent-to-Human private messaging as well as Multi-Agent + Human group chats.
Autonomous Delegation: When a human assigns a high-level task to the group, the agent collective must be able to autonomously decompose the task, negotiate roles, and delegate sub-tasks among themselves. Agents must also be capable of assigning tasks to other specialized agents.
Human-in-the-Loop (HITL): Agents must be programmed to proactively pause and query humans for clarification or permission when they encounter ambiguity or before executing critical actions.

2.2. Agent Evolution & Workspace Isolation

Memory & Evolution: Each individual agent must possess its own memory mechanism (e.g., using a vector database or local JSON logs). Agents must learn from past task executions (successes/failures) to improve their performance on future tasks.
Isolated Environments: Each agent must operate within its own private execution sandbox and maintain its own dedicated file system to prevent data leakage and ensure independent task execution.

2.3. Action Space (Tool Integration) Agents must be equipped with tools to interact with the external world. Required capabilities include:

Internet search and data retrieval.
File system operations (Read, Generate, Update, Delete).
Writing, testing, and executing code (e.g., Python scripts).
Version control operations (Committing and pushing code to GitHub).

2.4. File Format Constraints Do NOT spend time implementing parsing or generation for complex proprietary formats (e.g., PDF, Word/DOCX, PowerPoint/PPT). All document-related tasks and outputs must strictly use plain-text formats, specifically Markdown (.md) and Plain Text (.txt).

2.5. User Interface (UI) Keep the UI strictly minimal and functional. You may use a simple CLI (Command Line Interface), Telegram/Slack bot integrations, or a basic Gradio/Streamlit text interface. No extra credit will be given for elaborate frontend web design; your grade depends entirely on the AI engineering and orchestration backend.

2.6. Standardized LLM Backbone To ensure fair performance benchmarking across all teams, the use of OpenAI/Anthropic APIs is prohibited. All systems must be built uniformly using the DeepSeek or HKGAI API. Dedicated API keys will be distributed to each team later in the semester.

Evaluation & Metrics
Your system's effectiveness will be quantitatively evaluated. The harness you build must automatically track and report the following core metrics during evaluation:

Task Completion Rate: The percentage of sub-tasks and overarching goals successfully achieved without fatal crashes.
Execution Time: The total time taken from task assignment to final output generation.
The Final Evaluation Dataset: You will not know the final evaluation tasks in advance. A standardized, closed Test Set will be released to all groups exactly 3 weeks before the final submission deadline. Your system must be run against this dataset to generate your final performance metrics.

Deliverables and Submission Requirements
Your final submission must include the following strictly enforced components:

Complete Codebase & Commit Verification
You must submit the link to your GitHub repository.
Commit History Requirement: The repository must demonstrate a continuous, collaborative development process. You must include screenshots of the Git commit history in your final documentation, clearly proving that every team member made significant code contributions throughout the half-semester. Bulk-uploading code at the end of the project will be heavily penalized or flagged for academic integrity review.

System Architecture Document
A comprehensive design document detailing your multi-agent routing logic, memory/evolution mechanisms, and sandbox implementations.

Test Results & Performance Report
A formal report analyzing your system's performance on the mid/final Test Set (released in the last 3/1 weeks), detailing your Task Completion Rates, Execution Times, and a discussion on failure modes and how your agents' memory evolved during testing. 
