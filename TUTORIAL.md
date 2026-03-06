# Zava Multi-Agent Chat Application — Complete Tutorial

This tutorial walks through the entire Zava project: how agents are created and pushed to Azure AI Foundry, how the Dockerfile works, and how the chat interface ties everything together. Each section begins with **conceptual background** (the "textbook" material) followed by how those concepts are applied in the actual project code.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Part 1: Creating Agents & Pushing to Azure AI Foundry](#2-part-1-creating-agents--pushing-to-azure-ai-foundry)
   - [2.0 What Is an AI Agent? (Conceptual Background)](#20-what-is-an-ai-agent-conceptual-background)
   - [2.1 The Universal Agent Initializer](#21-the-universal-agent-initializer)
   - [2.2 Agent Type 1: Standard Agent with Function Tools (Cora)](#22-agent-type-1-standard-agent-with-function-tools-cora)
   - [2.3 Agent Type 2: Agent with Structured JSON Output (Handoff Service)](#23-agent-type-2-agent-with-structured-json-output-handoff-service)
   - [2.4 Agent Type 3: Tool-Specialized Agents](#24-agent-type-3-tool-specialized-agents)
   - [2.5 Agent Type 4: Stateless Context-Only Agent (Cart Manager)](#25-agent-type-4-stateless-context-only-agent-cart-manager)
   - [2.6 The Single Agent Pattern (Simple Example)](#26-the-single-agent-pattern-simple-example)
   - [2.7 How Function Tools Are Built (MCP Integration)](#27-how-function-tools-are-built-mcp-integration)
   - [2.8 The Agent Processor (Runtime Execution)](#28-the-agent-processor-runtime-execution)
   - [2.9 The Handoff Service (Intent-Based Routing)](#29-the-handoff-service-intent-based-routing)
   - [2.10 Summary of All Agent Techniques](#210-summary-of-all-agent-techniques)
3. [Part 2: Understanding the Dockerfile](#3-part-2-understanding-the-dockerfile)
   - [3.0 What Is Docker? (Conceptual Background)](#30-what-is-docker-conceptual-background)
4. [Part 3: The Chat Interface](#4-part-3-the-chat-interface)
   - [4.0 What Are WebSockets and FastAPI? (Conceptual Background)](#40-what-are-websockets-and-fastapi-conceptual-background)
   - [4.1 Backend — FastAPI WebSocket Server](#41-backend--fastapi-websocket-server)
   - [4.2 Frontend — HTML/JS Chat UI](#42-frontend--htmljs-chat-ui)
   - [4.3 Request/Response Flow (End-to-End)](#43-requestresponse-flow-end-to-end)
5. [Glossary](#5-glossary)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    User Browser                         │
│              chat.html (WebSocket client)                │
└──────────────────────┬──────────────────────────────────┘
                       │ WebSocket (ws:// or wss://)
                       ▼
┌─────────────────────────────────────────────────────────┐
│             FastAPI Server (chat_app.py)                 │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ Handoff      │  │ Agent        │  │ MCP Inventory  │ │
│  │ Service      │──│ Processor    │──│ Server/Client  │ │
│  │ (Routing)    │  │ (Execution)  │  │ (Tools)        │ │
│  └──────────────┘  └──────────────┘  └───────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │ Azure AI Projects SDK
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Azure AI Foundry                           │
│                                                         │
│  ┌─────────┐ ┌──────────────┐ ┌───────────────────────┐│
│  │  Cora   │ │ Cart Manager │ │ Interior Designer     ││
│  │ (GPT)   │ │ (GPT)        │ │ (GPT + Image Tools)   ││
│  └─────────┘ └──────────────┘ └───────────────────────┘│
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────┐ │
│  │  Customer    │ │  Inventory   │ │  Handoff        │ │
│  │  Loyalty     │ │  Agent       │ │  Service Agent  │ │
│  └──────────────┘ └──────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

The project uses **6 specialized agents** deployed to Azure AI Foundry, with an MCP (Model Context Protocol) server providing tools, and a FastAPI WebSocket server connecting users to the right agent.

---

## 2. Part 1: Creating Agents & Pushing to Azure AI Foundry

### 2.0 What Is an AI Agent? (Conceptual Background)

Before diving into code, it's important to understand the foundational concepts behind AI agents and multi-agent systems.

#### What Is an LLM?

A **Large Language Model (LLM)** is a neural network trained on massive amounts of text data. Models like GPT-4o can understand and generate human language, follow instructions, reason about problems, and produce structured outputs. However, an LLM by itself is stateless — it receives a prompt and returns a completion. It doesn't remember previous conversations, it can't take actions in the real world, and it doesn't know how to access external data. An LLM is like a brilliant consultant who can answer any question you ask, but who forgets you the moment you walk out of the room.

#### From LLM to Agent

An **AI Agent** wraps an LLM with additional capabilities that make it useful in real applications:

- **System Prompt (Instructions):** A set of instructions that define the agent's personality, role, and behavior. For example, "You are a shopping assistant for Zava, a home improvement retailer." This is like giving the consultant a job description.
- **Tools (Function Calling):** The ability to call external functions — search a database, check inventory, generate an image, calculate a discount. Tools give the agent hands to interact with the real world.
- **Memory (Conversation Threads):** A conversation thread that preserves context across multiple messages, so the agent remembers what you discussed earlier in the session.
- **Structured Output:** The ability to guarantee that the agent's response conforms to a specific JSON schema, eliminating parsing errors in downstream code.

Think of it this way:

| Component | Without Agent | With Agent |
|-----------|--------------|------------|
| Knowledge | Only training data | Training data + real-time tool results |
| Memory | None (stateless) | Conversation threads |
| Actions | Can only generate text | Can call functions, search databases, create images |
| Output | Free-form text | Can be constrained to exact JSON schemas |

#### What Is Azure AI Foundry?

**Azure AI Foundry** (formerly Azure AI Studio) is Microsoft's cloud platform for building, deploying, and managing AI applications. In the context of this project, Foundry serves as the **hosting layer for agents**. When you "push an agent to Foundry," you're registering the agent's definition (model, prompt, tools) so that it can be invoked at runtime via API calls. Think of Foundry as a registry — you define an agent once, and then any application can call it by name.

Key Foundry concepts used in this project:
- **Project:** A workspace in Foundry that contains your AI resources (models, agents, connections)
- **Agent:** A named entity with a model, instructions, and tools, deployed inside a project
- **Conversation:** A thread of messages between a user and an agent, maintaining context
- **Response:** The agent's reply to a message, which may include text output or function calls

#### What Is a Multi-Agent Architecture?

A **multi-agent system** uses multiple specialized agents instead of one general-purpose agent. Each agent is an expert in a narrow domain. A central **orchestrator** (in this project, the "Handoff Service") examines each user message and routes it to the appropriate specialist.

Why use multiple agents instead of one?

1. **Specialization:** Each agent has a focused system prompt and only the tools it needs. A cart management agent doesn't need image generation tools, and an interior design agent doesn't need discount calculation.
2. **Reliability:** Smaller, focused prompts produce more reliable outputs than one massive prompt trying to handle everything.
3. **Maintainability:** You can update one agent's behavior without affecting others.
4. **Security:** Each agent only has access to the tools and data it needs (principle of least privilege).

The tradeoff is complexity — you need a routing mechanism to direct messages to the right agent. This is where the **Handoff Service** comes in.

#### What Is the Model Context Protocol (MCP)?

**MCP (Model Context Protocol)** is an open standard (created by Anthropic) that defines how AI applications communicate with external tools and data sources. Think of it as a universal adapter between AI agents and the services they need.

In traditional function calling, you hard-code each tool's implementation directly in your agent code. With MCP, tools are exposed through a **server** that any MCP-compatible **client** can discover and call. This creates a clean separation:

```
Without MCP:  Agent Code → Direct function call → Database/API
With MCP:     Agent Code → MCP Client → MCP Server → Database/API
```

Benefits of MCP:
- **Discoverability:** Clients can list all available tools at runtime
- **Reusability:** One MCP server can serve multiple agents
- **Standardization:** Any MCP client can talk to any MCP server
- **Testing:** You can test tools independently of agents

In this project, the MCP server runs alongside the FastAPI app and exposes tools like product search, inventory check, discount calculation, and image generation via Server-Sent Events (SSE).

#### What Is Function Calling?

**Function calling** (also called "tool use") is a capability of modern LLMs where the model can decide to call an external function instead of (or in addition to) generating text. Here's how it works:

1. You tell the model about available functions (name, description, parameters as JSON schema)
2. The user asks a question like "What paint products do you have?"
3. The model decides it needs to call `mcp_product_recommendations` with `{"question": "paint products"}`
4. Your code executes the function and returns the result to the model
5. The model uses the function result to generate a final human-readable response

The model doesn't actually execute functions — it generates a structured request that your code intercepts and fulfills. The `strict: true` flag in this project ensures the model's function call arguments always conform exactly to the defined JSON schema.

#### What Are Structured Outputs?

**Structured outputs** are a feature that forces an LLM to return its response in a specific JSON format defined by a schema. Without structured outputs, you might ask "classify this intent" and get free-form text like "I think this is about cart management." With structured outputs, you guarantee you'll get:

```json
{"domain": "cart_manager", "confidence": 0.95, "is_domain_change": true, "reasoning": "User mentioned adding to cart"}
```

This is critical for the Handoff Service agent, which must return a machine-parseable classification, not prose. Structured outputs eliminate an entire class of bugs where the LLM returns unexpected formats.

#### Prompt Engineering: The Art of Agent Instructions

Every agent in this project has a **system prompt** stored as a `.txt` file in the `prompts/` directory. These prompts are carefully designed to:

1. **Define the agent's role:** "You are a Cart Manager Assistant for Zava, a home improvement retailer."
2. **Specify capabilities:** "Your primary responsibilities: add products, remove products, update quantities..."
3. **Define output format:** "Always respond in valid JSON format: {answer, cart, products, discount_percentage}"
4. **Set guardrails:** "If asked about something unrelated to DIY projects, politely decline."
5. **Provide examples:** Sample inputs and expected outputs help the model understand the pattern.

Storing prompts in external files (rather than hardcoding them in Python) makes them easy to iterate on — you can update an agent's behavior by editing a text file without touching any code.

---

### 2.1 The Universal Agent Initializer

In software engineering, a common pattern is the **Factory Pattern** — a single function that creates different types of objects based on input parameters. The agent initializer in this project follows exactly this pattern: one function that can create any type of agent and deploy it to Azure AI Foundry.

The key insight is that *all agents share the same creation structure*: a name, a model, instructions, and a list of tools. What differs between agents is the content of those fields. By centralizing creation into one function, the project avoids duplicating boilerplate code across six different agent scripts.

**File:** `src/app/agents/agent_initializer.py`

This is the **core function** that creates and pushes any agent to Azure AI Foundry:

```python
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

def initialize_agent(project_client, model, name, description, instructions, tools):
    with project_client:
        agent = project_client.agents.create_version(
            agent_name=name,            # Unique name in Foundry (e.g., "cora")
            description=description,     # Human-readable description
            definition=PromptAgentDefinition(
                model=model,             # GPT deployment name (e.g., "gpt-4o")
                instructions=instructions,  # System prompt (loaded from .txt files)
                tools=tools              # List of FunctionTool objects
            )
        )
        print(f"Created {name} agent, ID: {agent.id}")
```

**Key concepts:**
- **`project_client.agents.create_version()`** — Creates or updates an agent in Azure AI Foundry
- **`PromptAgentDefinition`** — Defines the agent with a model, system prompt, and tools
- **`agent_name`** — The name used to reference this agent at runtime (e.g., `"cora"`, `"cart-manager"`)
- **`tools`** — A list of `FunctionTool` objects that define what functions the agent can call

**Authentication is always via `DefaultAzureCredential`:**
```python
from azure.identity import DefaultAzureCredential

project_client = AIProjectClient(
    endpoint=os.environ["FOUNDRY_ENDPOINT"],
    credential=DefaultAzureCredential(),
)
```

---

### 2.2 Agent Type 1: Standard Agent with Function Tools (Cora)

This is the most common agent pattern you'll encounter. A **standard agent with function tools** combines natural language understanding with the ability to call external services. The agent reads the user's message, decides whether it needs additional data, calls a tool if needed, and then formulates a response using both its knowledge and the tool's results.

The key design principle here is **separation of concerns**: the agent handles natural language understanding and response generation, while the tool handles data retrieval. The agent doesn't know *how* to search a product database — it only knows *when* to search and *what* to ask for.

**File:** `src/app/agents/shopperAgent_initializer.py`

Cora is the **general shopping assistant** — the default agent that handles product browsing and general questions.

```python
# 1. Load the prompt from a text file
CORA_PROMPT_TARGET = os.path.join(..., 'prompts', 'ShopperAgentPrompt.txt')
with open(CORA_PROMPT_TARGET, 'r', encoding='utf-8') as file:
    CORA_PROMPT = file.read()

# 2. Create function tools specific to this agent type
functions = create_function_tool_for_agent("cora")
# For "cora", this returns: [mcp_product_recommendations]

# 3. Push to Foundry
initialize_agent(
    project_client=project_client,
    model=os.environ["gpt_deployment"],    # e.g., "gpt-4o"
    name="cora",                           # Agent name in Foundry
    description="Cora - Zava Shopping Assistant",
    instructions=CORA_PROMPT,              # System prompt
    tools=functions                        # [mcp_product_recommendations]
)
```

**What makes this pattern special:**
- Loads instructions from an external `.txt` file (easy to update without code changes)
- Gets its tool set from `create_function_tool_for_agent()` (centralized tool management)
- Tools are `FunctionTool` objects that define the JSON schema of callable functions

**Cora's tool — `mcp_product_recommendations`:**
```python
FunctionTool(
    name="mcp_product_recommendations",
    parameters={
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Natural language user query describing what products they're looking for"
            }
        },
        "required": ["question"],
        "additionalProperties": False
    },
    description="Search for product recommendations based on user query.",
    strict=True
)
```

When Cora decides to search for products, the LLM generates a function call with a `question` parameter. The `AgentProcessor` intercepts this, executes the tool via MCP, and feeds the result back.

---

### 2.3 Agent Type 2: Agent with Structured JSON Output (Handoff Service)

One of the biggest challenges in building LLM-powered systems is **output reliability**. When you ask an LLM to return JSON, it might return valid JSON, or it might wrap it in markdown code blocks, add a conversational preamble, or subtly change the field names. In production systems, this unpredictability causes parsing failures and crashes.

**Structured outputs** solve this definitively. By providing a JSON schema to the API, you instruct the model to *only* produce output that conforms to that schema. The model's token generation is constrained at the decoding level — it literally cannot produce invalid JSON. This is fundamentally different from just asking the model "please respond in JSON" in the prompt.

This technique is particularly valuable for **orchestration agents** (like the Handoff Service) where the output must be machine-parseable, not human-readable. A routing decision needs to be a clean data structure, not a paragraph of text.

**File:** `src/app/agents/handoffAgent_initializer.py`

The Handoff Service agent is **unique** — it doesn't use function tools. Instead, it uses **structured output** to guarantee a JSON schema response.

```python
from azure.ai.projects.models import (
    PromptAgentDefinition,
    PromptAgentDefinitionText,
    ResponseTextFormatConfigurationJsonSchema
)
from services.handoff_service import IntentClassification

# Note: Does NOT use initialize_agent() — uses a custom creation flow
with project_client:
    agent = project_client.agents.create_version(
        agent_name="handoff-service",
        description="Zava Handoff Service Agent",
        definition=PromptAgentDefinition(
            model=os.environ["gpt_deployment"],
            text=PromptAgentDefinitionText(
                format=ResponseTextFormatConfigurationJsonSchema(
                    name="IntentClassification",
                    schema=IntentClassification.model_json_schema()
                )
            ),
            instructions=HANDOFF_AGENT_PROMPT
        )
    )
```

**What makes this different from other agents:**
1. **No tools** — This agent only classifies intent, it doesn't call external functions
2. **`PromptAgentDefinitionText` with `ResponseTextFormatConfigurationJsonSchema`** — Forces the model to output a specific JSON structure
3. **Pydantic model defines the schema** — Uses `IntentClassification.model_json_schema()` to auto-generate the JSON schema

**The Pydantic model that defines the output:**
```python
from pydantic import BaseModel, Field

class IntentClassification(BaseModel):
    model_config = {"extra": "forbid", "additionalProperties": False}
    
    domain: str = Field(
        description="Target domain: cora, interior_designer, inventory_agent, customer_loyalty, or cart_manager"
    )
    is_domain_change: bool = Field(
        description="Whether this represents a change from the current domain"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score between 0.0 and 1.0"
    )
    reasoning: str = Field(
        description="Brief explanation of the classification decision"
    )
```

**Why this technique matters:** By using structured outputs, the handoff agent is *guaranteed* to return a valid JSON object with `domain`, `is_domain_change`, `confidence`, and `reasoning`. No parsing failures, no hallucinated formats.

---

### 2.4 Agent Type 3: Tool-Specialized Agents

A core principle in multi-agent design is the **Single Responsibility Principle** — each agent should do one thing well. Rather than giving one agent every tool in the system, you create specialists. This mirrors how real organizations work: you have a design team, an inventory team, and a customer service team, each with their own expertise and tools.

The benefit of specialization is twofold: (1) the agent's prompt can be highly focused, leading to better quality responses, and (2) you reduce the risk of the agent calling the wrong tool. An inventory agent with only `mcp_inventory_check` literally cannot generate images by accident.

These agents each have domain-specific tools:

#### Interior Designer Agent
**File:** `src/app/agents/interiorDesignAgent_initializer.py`

```python
functions = create_function_tool_for_agent("interior_designer")
# Returns: [mcp_create_image, mcp_product_recommendations]

initialize_agent(
    project_client=project_client,
    model=os.environ["gpt_deployment"],
    name="interior-designer",
    description="Zava Interior Design Agent",
    instructions=ID_PROMPT,       # Interior design-specific prompt
    tools=functions               # Can generate images AND recommend products
)
```

**Tools:** `mcp_create_image` (DALL-E image generation) + `mcp_product_recommendations`

#### Customer Loyalty Agent
**File:** `src/app/agents/customerLoyaltyAgent_initializer.py`

```python
functions = create_function_tool_for_agent("customer_loyalty")
# Returns: [mcp_calculate_discount]

initialize_agent(
    project_client=project_client,
    model=os.environ["gpt_deployment"],
    name="customer-loyalty",
    description="Zava Customer Loyalty Agent",
    instructions=CL_PROMPT,
    tools=functions               # Can calculate customer discounts
)
```

**Tool:** `mcp_calculate_discount` — Looks up customer data and calculates loyalty discount.

#### Inventory Agent
**File:** `src/app/agents/inventoryAgent_initializer.py`

```python
functions = create_function_tool_for_agent("inventory_agent")
# Returns: [mcp_inventory_check]

initialize_agent(
    project_client=project_client,
    model=os.environ["gpt_deployment"],
    name="inventory-agent",
    description="Zava Inventory Agent",
    instructions=IA_PROMPT,
    tools=functions               # Can check product inventory levels
)
```

**Tool:** `mcp_inventory_check` — Checks stock levels for product IDs.

---

### 2.5 Agent Type 4: Stateless Context-Only Agent (Cart Manager)

Not every agent needs tools. Sometimes, all the information an agent needs is in the conversation itself. The **context-only agent** pattern demonstrates that LLMs can perform complex state management (like maintaining a shopping cart) purely through prompting and reasoning, with no external function calls.

The trick is in the prompt design: you tell the agent exactly what format to return (a JSON cart array), and you feed it the complete history of everything that has happened in the session. The LLM then reasons about the current state and produces an updated cart. This is a form of **in-context learning** — the model learns the current state from the examples in its context window.

This pattern works well when:
- The state is small enough to fit in the context window
- The logic is deterministic and well-defined (add/remove/update items)
- You want to avoid the latency of extra tool calls

**File:** `src/app/agents/cartManagerAgent_initializer.py`

```python
functions = create_function_tool_for_agent("cart_manager")
# Returns: [] (EMPTY — no tools!)

initialize_agent(
    project_client=project_client,
    model=os.environ["gpt_deployment"],
    name="cart-manager",
    description="Zava Cart Manager Agent",
    instructions=CART_MANAGER_PROMPT,
    tools=functions               # Empty list — pure LLM reasoning
)
```

**What makes this unique:** The Cart Manager has **zero tools**. It relies entirely on:
- The full conversation history (`RAW_IO_HISTORY`) passed in via the message
- Its system prompt that tells it how to parse add/remove/update cart operations
- Pure LLM reasoning to understand what the user wants and return an updated cart JSON

This demonstrates that not every agent needs tools — some work best with just context and clever prompting.

---

### 2.6 The Single Agent Pattern (Simple Example)

Before understanding multi-agent systems, it's important to understand the simplest possible pattern: a **single agent** that directly calls the Azure OpenAI API. This is where most AI applications start, and it's still the right choice for simple use cases.

The single agent pattern has three components:
1. **A client** — an `AzureOpenAI` instance configured with your endpoint and credentials
2. **A system prompt** — instructions that define the agent's behavior
3. **A completion call** — sending the user's message to the model and getting a response

There's no Foundry, no deployment, no tools, no routing. It's the "Hello World" of AI applications. Understanding this pattern helps you appreciate what the multi-agent architecture adds on top.

**File:** `src/app/tools/singleAgentExample.py`

Before the multi-agent architecture, there's a simpler pattern — a **direct Azure OpenAI call** without Foundry agents:

```python
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint=os.getenv("gpt_endpoint"),
    api_key=os.getenv("gpt_api_key"),
    api_version=os.getenv("gpt_api_version"),
)

def generate_response(text_input):
    chat_prompt = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are a helpful assistant for Zava..."}]
        },
        {"role": "user", "content": text_input}
    ]

    completion = client.chat.completions.create(
        model=deployment,
        messages=chat_prompt,
        max_completion_tokens=10000
    )
    return completion.choices[0].message.content
```

**Key difference from the multi-agent pattern:**
- Uses `AzureOpenAI` client directly (not `AIProjectClient`)
- No agent deployment to Foundry
- No tools, no routing
- Just a system prompt + user message → response

This is useful for understanding the evolution: **Single Agent → Multi-Agent with Handoff**.

---

### 2.7 How Function Tools Are Built (MCP Integration)

In traditional software, connecting an AI model to external tools requires writing custom glue code for each tool. Function calling standardizes the *interface* between the model and your code, but you still need to write the implementation, manage connections, and handle errors for each tool.

**MCP (Model Context Protocol)** adds another layer of abstraction on top of function calling. With MCP:
- A **server** exposes tools with standardized interfaces (name, description, input schema)
- A **client** discovers and calls these tools without knowing implementation details
- The transport layer (SSE in this project) handles communication

The architecture in this project chains these layers:
```
Agent in Foundry → decides to call a function
    → AgentProcessor intercepts the function call
        → MCP Client sends request to MCP Server
            → MCP Server executes the actual business logic
                → Result flows back through the chain
```

**File:** `src/app/agents/agent_processor.py` — `create_function_tool_for_agent()`

The project uses **Model Context Protocol (MCP)** to provide tools. Here's how functions are defined and routed per agent:

```python
def create_function_tool_for_agent(agent_type: str) -> List[Any]:
    # Define all available tools
    define_mcp_create_image = FunctionTool(
        name="mcp_create_image",
        parameters={"type": "object", "properties": {"prompt": {"type": "string", ...}}, ...},
        description="Generate an AI image using GPT image model.",
        strict=True
    )
    define_mcp_product_recommendations = FunctionTool(...)
    define_mcp_calculate_discount = FunctionTool(...)
    define_mcp_inventory_check = FunctionTool(...)

    # Route tools based on agent type
    if agent_type == "interior_designer":
        return [define_mcp_create_image, define_mcp_product_recommendations]
    elif agent_type == "customer_loyalty":
        return [define_mcp_calculate_discount]
    elif agent_type == "inventory_agent":
        return [define_mcp_inventory_check]
    elif agent_type == "cart_manager":
        return []  # No tools!
    elif agent_type == "cora":
        return [define_mcp_product_recommendations]
```

**Tool-to-Agent mapping summary:**

| Agent | Tools |
|-------|-------|
| Cora | `mcp_product_recommendations` |
| Interior Designer | `mcp_create_image`, `mcp_product_recommendations` |
| Customer Loyalty | `mcp_calculate_discount` |
| Inventory Agent | `mcp_inventory_check` |
| Cart Manager | *(none)* |
| Handoff Service | *(none — uses structured output)* |

**The MCP Server** (`src/app/servers/mcp_inventory_server.py`) exposes these tools via SSE:
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MCP Shop Inventory Server")

@mcp.tool()
def get_product_recommendations(question: str) -> str:
    """Searches Cosmos DB with vector search for products."""
    results = product_recommendations(question)
    return json.dumps(results)

@mcp.tool()
def check_product_inventory(product_id: str) -> str:
    """Checks simulated inventory data."""
    ...

@mcp.tool()
def get_customer_discount(customer_id: str) -> str:
    """Calculates loyalty discount from simulated customer data."""
    ...

@mcp.tool()
def generate_product_image(prompt: str) -> str:
    """Generates images via gpt-image-1 and uploads to Azure Blob."""
    ...
```

**The MCP Client** (`src/app/servers/mcp_inventory_client.py`) connects to the server:
```python
class MCPShopperToolsClient:
    async def call_tool(self, tool_name, arguments):
        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result_data = await session.call_tool(tool_name, arguments=arguments)
                return result_data
```

---

### 2.8 The Agent Processor (Runtime Execution)

Creating an agent in Foundry is only half the story. You also need a **runtime execution layer** that handles the back-and-forth between your application and the agent. This is because agents with tools don't produce their final answer in a single call — they may need to:

1. Receive the user's message
2. Decide they need data from a tool
3. Return a "function call" request (not a final answer)
4. Wait for your code to execute the tool and provide results
5. Use those results to formulate the final answer

This is called the **tool use loop**, and the `AgentProcessor` class manages it. It also handles:
- **Conversation threading** — creating and reusing conversation threads for multi-turn dialogue
- **Tool dispatch** — mapping function call names to actual Python functions
- **Caching** — reusing tool configurations and processor instances for performance
- **Async execution** — running agent calls in a thread pool to avoid blocking the web server

**File:** `src/app/agents/agent_processor.py` — `AgentProcessor` class

Once agents are created in Foundry, the `AgentProcessor` handles runtime execution:

```python
class AgentProcessor:
    def __init__(self, project_client, assistant_id, agent_type, thread_id=None):
        self.project_client = project_client
        self.agent_id = assistant_id      # Agent name in Foundry (e.g., "cora")
        self.agent_type = agent_type
        self.thread_id = thread_id
        self.toolset = self._get_or_create_toolset(agent_type)  # Cached tools
```

**The conversation flow:**
1. **Create a conversation thread** (or reuse existing):
   ```python
   conversation = openai_client.conversations.create(
       items=[{"role": "user", "content": input_message}]
   )
   ```

2. **Send to the Foundry agent for processing:**
   ```python
   message = openai_client.responses.create(
       conversation=thread_id,
       extra_body={"agent": {"name": self.agent_id, "type": "agent_reference"}},
       input=""
   )
   ```

3. **Handle function calls** (if agent requested tool use):
   ```python
   for item in message.output:
       if item.type == "function_call":
           if item.name == "mcp_product_recommendations":
               func_result = mcp_product_recommendations(**json.loads(item.arguments))
           # ... dispatch to other functions
           
           input_list.append(FunctionCallOutput(
               type="function_call_output",
               call_id=item.call_id,
               output=json.dumps({"result": func_result})
           ))
   
   # Re-run to get the final text response
   message = openai_client.responses.create(
       input=input_list,
       previous_response_id=message.id,
       extra_body={"agent": {"name": self.agent_id, "type": "agent_reference"}},
   )
   ```

4. **Return the text response** to the caller

**Caching:** The `AgentProcessor` caches tool configurations per agent type to avoid re-initialization:
```python
_toolset_cache: Dict[str, List[FunctionTool]] = {}
```

The service layer (`src/services/agent_service.py`) also caches `AgentProcessor` instances:
```python
_agent_processor_cache: Dict[str, AgentProcessor] = {}

def get_or_create_agent_processor(agent_id, agent_type, thread_id, project_client):
    cache_key = f"{agent_type}_{agent_id}"
    if cache_key in _agent_processor_cache:
        processor = _agent_processor_cache[cache_key]
        processor.thread_id = thread_id
        return processor
    processor = AgentProcessor(...)
    _agent_processor_cache[cache_key] = processor
    return processor
```

---

### 2.9 The Handoff Service (Intent-Based Routing)

In a multi-agent system, something needs to decide which agent handles each message. This is the **orchestration problem**, and there are several approaches:

1. **Keyword matching:** Simple but brittle. "If message contains 'cart', use cart agent."
2. **Hardcoded rules:** More sophisticated but inflexible. Requires updating code for new patterns.
3. **LLM-based classification:** Use a model to understand intent and route dynamically.

This project uses approach #3 — an **LLM-powered intent classifier**. The Handoff Service is itself backed by an agent in Foundry (the "handoff-service" agent) that uses structured outputs to guarantee a parseable classification result.

The Handoff Service also implements several production-worthy patterns:
- **Session tracking:** Remembers the current domain per session to provide context for classification
- **Lazy classification:** On the first message, routes to the default agent without calling the LLM
- **Graceful fallback:** If classification fails, stays with the current domain rather than crashing
- **Confidence scoring:** Each classification includes a confidence score for potential future use (e.g., "ask user to clarify" if confidence is low)

**File:** `src/services/handoff_service.py`

The Handoff Service determines **which agent to route each message to**:

```python
class HandoffService:
    def classify_intent(self, user_message, session_id, chat_history=None):
        # 1. First message → route to default agent ("cora")
        if not current_domain:
            return {"domain": "cora", "confidence": 1.0, ...}
        
        # 2. Create a conversation with the handoff agent in Foundry
        conversation = self.client.conversations.create(
            items=[{"type": "message", "role": "user",
                    "content": f"Current domain: {current_domain}\nUser message: {user_message}"}]
        )
        
        # 3. Get structured JSON response (guaranteed by the agent's schema)
        response = self.client.responses.create(
            conversation=conversation.id,
            extra_body={"agent": {"name": "handoff-service", "type": "agent_reference"}},
            input=""
        )
        
        # 4. Parse the structured intent → {"domain": "cart_manager", "confidence": 0.95, ...}
        intent = json.loads(response.output_text)
        return intent
```

**Domain routing rules (from the prompt):**
- "cart", "add to cart", "checkout" → `cart_manager`
- Room design, color schemes → `interior_designer`
- Stock checks, availability → `inventory_agent`
- Discounts, loyalty → `customer_loyalty`
- General/ambiguous → `cora` (default)

---

### 2.10 Summary of All Agent Techniques

| # | Technique | Example | Key Feature |
|---|-----------|---------|-------------|
| 1 | **Standard Agent + Function Tools** | Cora, Interior Designer | Prompt + tools registered in Foundry |
| 2 | **Structured Output Agent** | Handoff Service | JSON schema guarantees output format |
| 3 | **Tool-Specialized Agent** | Customer Loyalty, Inventory | Single-purpose tools (discount calc, stock check) |
| 4 | **Context-Only Agent (No Tools)** | Cart Manager | Pure LLM reasoning from conversation history |
| 5 | **Single Agent (No Foundry)** | `singleAgentExample.py` | Direct `AzureOpenAI` call, no deployment |
| 6 | **MCP Tool Server/Client** | Inventory MCP Server | Tools exposed via Model Context Protocol |
| 7 | **Intent-Based Handoff** | Handoff Service | Routes messages to the right agent |

**To push all agents to Foundry, run each initializer script:**
```bash
cd src/app/agents
python shopperAgent_initializer.py
python cartManagerAgent_initializer.py
python customerLoyaltyAgent_initializer.py
python interiorDesignAgent_initializer.py
python inventoryAgent_initializer.py
python handoffAgent_initializer.py
```

---

## 3. Part 2: Understanding the Dockerfile

### 3.0 What Is Docker? (Conceptual Background)

Before reading the Dockerfile, let's understand the fundamental concepts of containerization.

#### The Problem Docker Solves

Imagine you build a Python application on your laptop. It works perfectly. Then you deploy it to a server and it fails — different Python version, missing system libraries, conflicting dependencies. "It works on my machine" is one of the most common problems in software development.

**Docker** solves this by packaging your application along with *everything it needs to run* — the operating system, system libraries, Python runtime, pip packages, your code, and your configuration — into a single portable unit called a **container**. If it runs in a Docker container on your laptop, it will run identically on any server, any cloud, anywhere.

#### Key Docker Concepts

| Concept | What It Is | Analogy |
|---------|-----------|---------|
| **Image** | A read-only blueprint that contains your app + all dependencies | A recipe |
| **Container** | A running instance of an image | A dish made from the recipe |
| **Dockerfile** | A text file with instructions to build an image | The recipe card |
| **Layer** | Each instruction in a Dockerfile creates a layer; layers are cached | Steps in the recipe |
| **Registry** | A repository for storing and sharing images (like Azure Container Registry) | A cookbook library |
| **Tag** | A label for a specific version of an image (e.g., `latest`, `v1.0`) | Edition number |

#### How Docker Builds Work

When you run `docker build`, Docker reads your Dockerfile and executes each instruction in order. Each instruction creates a new **layer** on top of the previous one. Docker caches these layers — if nothing has changed in a layer (and all layers before it), Docker reuses the cached version instead of rebuilding.

This has a critical implication for Dockerfile design: **put things that change infrequently (like system packages) at the top, and things that change often (like your code) at the bottom.** This way, most builds only rebuild the last few layers.

```
Layer 1: Base OS (python:3.12-slim)         ← Rarely changes
Layer 2: System packages (gcc, libgl1...)     ← Rarely changes
Layer 3: pip install requirements.txt         ← Changes when you add a new package
Layer 4: COPY your source code                ← Changes every time you edit code
```

If you only change your source code (Layer 4), Docker reuses Layers 1-3 from cache. This can save minutes on each build.

#### Images vs. Containers

An **image** is a static artifact — think of it like a class in object-oriented programming. A **container** is a running instance — like an object instantiated from the class. You can create many containers from one image, each running independently with its own state.

```
docker build -t chat-app .           # Creates an IMAGE
docker run -p 8000:8000 chat-app     # Creates a CONTAINER from that image
```

#### Azure Container Registry (ACR)

Once you build a Docker image, you need to store it somewhere that Azure services can pull from. **Azure Container Registry (ACR)** is a private Docker registry hosted in Azure. It's like Docker Hub, but private to your organization and integrated with Azure services like App Service.

The workflow is: **Build locally → Tag for ACR → Push to ACR → App Service pulls from ACR.**

#### Why Slim Base Images?

Docker images based on `python:3.12` include the full Debian OS with compilers, documentation, and tools. Most of this is unnecessary at runtime. `python:3.12-slim` strips it down to essentials, reducing image size from ~900MB to ~150MB. Smaller images mean:
- **Faster builds and pushes** (especially important when pushing over the network)
- **Faster container startup** (less to download when deploying)
- **Smaller attack surface** (fewer installed packages = fewer potential vulnerabilities)

The tradeoff is that you must explicitly install any system packages you need (like `gcc` for compiling Python C extensions).

---

Now let's read the actual Dockerfile line by line:

**File:** `src/Dockerfile`

```dockerfile
FROM python:3.12-slim
```
**Base image:** Uses Python 3.12 slim variant — a minimal Debian-based image (~150MB vs ~900MB for the full image). This reduces container size and attack surface.

```dockerfile
RUN apt-get update && apt-get upgrade -y && pip install --upgrade pip && rm -rf /var/lib/apt/lists/*
```
**Security hardening:** Updates system packages and pip to patch known vulnerabilities. `rm -rf /var/lib/apt/lists/*` cleans the apt cache to reduce image size.

```dockerfile
WORKDIR /app
```
**Working directory:** All subsequent commands run inside `/app`. This is where your application code lives inside the container.

```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential unixodbc-dev gcc g++ \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*
```
**System dependencies:**
- `build-essential`, `gcc`, `g++` — C/C++ compiler toolchain (needed to compile Python packages like `numpy`, `pandas`)
- `unixodbc-dev` — ODBC driver headers (for database connectivity)
- `libgl1`, `libglib2.0-0`, `libsm6`, `libxext6`, `libxrender1` — Graphics libraries needed by `PIL`/`Pillow` for image processing (used by the image creation tool)

```dockerfile
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
```
**Dependency installation:** Copies `requirements.txt` first and installs dependencies **before** copying the rest of the code. This is a **Docker layer caching optimization** — if only your code changes (not dependencies), Docker reuses the cached layer and skips pip install.

`--no-cache-dir` prevents pip from storing downloaded packages, reducing image size.

```dockerfile
COPY . .
COPY .env .env
```
**Application code:** Copies all source code into the container. The `.env` file is copied separately for `python-dotenv` to load at runtime.

> **Production note:** In production, you should NOT include `.env` in the image. Instead, use Azure App Service environment variables or Azure Key Vault.

```dockerfile
EXPOSE 8000
ENV PORT=8000
```
**Port configuration:** Documents that the app listens on port 8000. `ENV PORT=8000` sets a default that can be overridden at runtime.

```dockerfile
CMD ["uvicorn", "chat_app:app", "--host", "0.0.0.0", "--port", "8000"]
```
**Startup command:** Runs the FastAPI app using `uvicorn`:
- `chat_app:app` — Import the `app` object from `chat_app.py`
- `--host 0.0.0.0` — Listen on all network interfaces (required inside Docker)
- `--port 8000` — Match the exposed port

**Key dependencies from `requirements.txt`:**
| Package | Purpose |
|---------|---------|
| `fastapi` + `uvicorn` | Web framework + ASGI server |
| `azure-ai-projects` | Azure AI Foundry agent creation & management |
| `azure-ai-agents` | Agent runtime (telemetry, tracing) |
| `openai` | Azure OpenAI client for LLM calls |
| `azure-cosmos` | Cosmos DB for product catalog (vector search) |
| `mcp` + `fastmcp` | Model Context Protocol server/client |
| `orjson` | Fast JSON serialization |
| `Pillow` (via image tools) | Image processing for gpt-image-1 |
| `azure-identity` | `DefaultAzureCredential` for authentication |
| `opentelemetry-sdk` + `azure-monitor-opentelemetry` | Observability & tracing |

**Complete Docker build and push workflow:**
```bash
# 1. Build the image
docker build -t chat-app .

# 2. Login to ACR
az acr login --name YOUR_ACR_NAME

# 3. Tag for ACR
docker tag chat-app YOUR_ACR_NAME.azurecr.io/chat-app:latest

# 4. Push to ACR
docker push YOUR_ACR_NAME.azurecr.io/chat-app:latest
```

---

## 4. Part 3: The Chat Interface

### 4.0 What Are WebSockets and FastAPI? (Conceptual Background)

Before looking at the chat code, let's understand the technologies that power real-time web communication.

#### HTTP vs. WebSockets: Two Ways to Talk

The web traditionally uses **HTTP**, a request-response protocol. The client (browser) sends a request, the server sends a response, and the connection closes. This is like sending a letter — you send one, wait for a reply, send another.

**WebSockets** are a different protocol that creates a persistent, two-way connection between client and server. Once the connection is established, both sides can send messages at any time, without the overhead of opening and closing connections. This is like a phone call — once connected, both parties can talk freely.

```
HTTP (Request-Response):
  Browser: "What's my cart?" →
                               ← Server: "Here's your cart"
  Browser: "Add paint" →
                               ← Server: "Done, here's your updated cart"
  (Each arrow is a new connection — handshake, request, response, close)

WebSocket (Persistent Connection):
  Browser ←→ Server  (connection stays open)
  Browser: "What's my cart?"
  Server: "Here's your cart"
  Server: "Also, your loyalty discount is 32%"  ← Server can push without being asked!
  Browser: "Add paint"
  Server: "Done, updated cart"
  (All on the same connection — no overhead)
```

For a chat application, WebSockets are essential because:
1. **Low latency:** No connection setup overhead for each message
2. **Server push:** The server can send messages proactively (e.g., loyalty discount notification)
3. **Bi-directional:** Both client and server can send at any time
4. **Persistent state:** The server can maintain session variables for the duration of the connection

#### What Is FastAPI?

**FastAPI** is a modern Python web framework built on top of Starlette (for web handling) and Pydantic (for data validation). It's designed for building APIs quickly with automatic documentation, type checking, and high performance.

Key FastAPI features used in this project:
- **WebSocket support:** Native WebSocket handling with `@app.websocket("/ws")`
- **HTML serving:** Serve the chat page with `HTMLResponse`
- **Sub-application mounting:** Mount the MCP server as a sub-app at `/mcp-inventory/`
- **Async support:** All handlers are `async`, enabling concurrent request handling
- **Health checks:** Simple JSON endpoints for monitoring (`/health`)

#### What Is ASGI?

**ASGI (Asynchronous Server Gateway Interface)** is a specification for Python web servers that support asynchronous operations. **Uvicorn** is the ASGI server that runs FastAPI applications. It handles the low-level network operations (accepting connections, managing sockets) while FastAPI handles the application logic (routing, request processing).

```
Browser → Uvicorn (ASGI Server) → FastAPI (Application) → Your Code
```

The startup command `uvicorn chat_app:app --host 0.0.0.0 --port 8000` tells Uvicorn to:
- Import the `app` object from `chat_app.py`
- Listen on all network interfaces (`0.0.0.0`)
- Accept connections on port 8000

#### Session State in WebSockets

Unlike HTTP (where each request is independent), a WebSocket connection is **stateful**. The server can store data that persists for the entire duration of the connection. In this project, each WebSocket connection represents a user session with its own:

- **Shopping cart** — Items added persist across messages
- **Chat history** — Previous conversation turns provide context
- **Discount tier** — Calculated once and applied to all subsequent responses
- **Image cache** — Analyzed images are cached to avoid re-processing

When the user closes the browser tab, the WebSocket disconnects and all session state is lost. This is acceptable for a shopping assistant — sessions are typically short-lived.

#### Multimodal AI: Text + Images

This application is **multimodal** — it can process both text and images. When a user uploads an image URL:

1. The image is sent to a **vision model** (GPT with vision capabilities) to generate a textual description
2. That description is added to the agent's context, enriching its understanding
3. The agent can now make recommendations based on both what the user said AND what the image shows

For example, if a user uploads a photo of a blue living room and asks "what paint would match?", the vision model describes the room's colors and style, and the product recommendation agent uses that description to search for matching paint products.

#### Context Enrichment Pipeline

Before any agent processes a message, the application builds an **enriched context** that combines multiple data sources:

```
User's Text Message
    + Image Analysis (if image provided)
    + Product Recommendations (if relevant)
    + Conversation History (for continuity)
    + Cart State (for cart operations)
    = Enriched Context → Agent
```

This pipeline ensures every agent has the full picture, not just the raw user message. Different agents receive different context:
- **Cart Manager** gets the full I/O history (to track every cart change)
- **Cora** gets formatted chat history (for conversational continuity)
- **Interior Designer** gets image descriptions and product data (for visual recommendations)

---

Now let's see how all of this comes together in the actual code:

### 4.1 Backend — FastAPI WebSocket Server

**File:** `src/chat_app.py`

The backend is a **FastAPI** application with three endpoints:

```python
app = FastAPI()

# 1. Serve the HTML chat page
@app.get("/")
async def get():
    with open('chat.html', "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# 2. Health check for Azure App Service
@app.get("/health")
async def health_check():
    return {"status": "healthy", ...}

# 3. WebSocket endpoint for real-time chat
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    ...
```

**The MCP server is mounted as a sub-application:**
```python
from app.servers.mcp_inventory_server import mcp as inventory_mcp

inventory_mcp_app = inventory_mcp.sse_app()
app.mount("/mcp-inventory/", inventory_mcp_app)
```
This means the MCP tools are accessible at `http://localhost:8000/mcp-inventory/sse`.

**WebSocket session lifecycle:**

```
User connects → WebSocket accepted → Session initialized
      │
      ▼
  ┌─── Message Loop ────────────────────────────────────┐
  │ 1. Receive JSON from client                         │
  │ 2. Parse: message, image_url, conversation_history  │
  │ 3. Handoff Service classifies intent → agent_name   │
  │ 4. Enrich context (images, product search)          │
  │ 5. Execute agent via AgentProcessor                 │
  │ 6. Parse structured response                        │
  │ 7. Update session state (cart, discount, history)   │
  │ 8. Send JSON response to client                     │
  └─────────────────────────────────────────────────────┘
      │
      ▼
  User disconnects → Session cleanup
```

**Session state variables (per WebSocket connection):**
```python
chat_history: Deque[Tuple[str, str]] = deque(maxlen=5)   # Last 5 conversation turns
customer_loyalty_executed = False      # Run loyalty check only once
session_discount_percentage = ""       # Persisted discount across messages
persistent_image_url = ""             # Last uploaded image URL
persistent_cart = []                  # Shopping cart state
image_cache = {}                      # Cache image descriptions
bad_prompts = set()                   # Redacted bad prompts
raw_io_history = deque(maxlen=100)    # Full I/O log for cart manager
```

**Context enrichment before agent execution:**

```python
# 1. Image analysis (if user sent an image)
if image_url:
    image_data = await get_cached_image_description(image_url, image_cache)

# 2. Product recommendations (for relevant agents)
if agent_name in ["interior_designer", "interior_designer_create_image", "cora"]:
    products = product_recommendations(search_query)

# 3. Build enriched message
enriched_message = f"{user_message}\n\nImage description: {image_data}\nAvailable products: {products}"
```

**Agent-specific context preparation:**
```python
if agent_name == "cart_manager":
    # Cart manager gets FULL raw I/O history
    agent_context = f"{enriched_message}\n\nRAW_IO_HISTORY:\n{json.dumps(list(raw_io_history))}"

elif agent_name == "cora":
    # Cora gets formatted chat history
    agent_context = f"{formatted_history}\n\nUser: {enriched_message}"

else:
    # Other agents get the enriched message only
    agent_context = enriched_message
```

**Special case — Image creation:**
```python
if agent_name == "interior_designer_create_image":
    # Uses gpt-image-1 directly (not an agent)
    image = create_image(text=enriched_message, image_url=persistent_image_url)
    # Uploads to Azure Blob Storage, returns URL
```

**Background loyalty task (runs once per session):**
```python
if not customer_loyalty_executed:
    asyncio.create_task(run_customer_loyalty_task(customer_id))
    customer_loyalty_executed = True

# The loyalty response is delayed until the first cart operation:
if agent_name == "cart_manager" and session_loyalty_response and not loyalty_response_sent:
    await websocket.send_text(fast_json_dumps(loyalty_response_with_cart))
    loyalty_response_sent = True
```

---

### 4.2 Frontend — HTML/JS Chat UI

**File:** `src/chat.html`

The frontend is a **single HTML file** with embedded CSS and JavaScript. It has two panels:

1. **Chat panel** (left) — User interaction with the chatbot
2. **Debug panel** (right) — Raw JSON input/output for debugging

**WebSocket connection:**
```javascript
// Auto-detect ws:// or wss:// based on page protocol
var ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
var ws = new WebSocket(ws_scheme + "://" + window.location.host + "/ws");
```

**Sending a message:**
```javascript
function sendMessage() {
    var payload = {
        conversation_history: formatConversationHistory(),  // Full chat history as text
        has_image: hasImage,
        customer_id: "CUST001",
        message: message
    };
    
    if (hasImage) {
        payload.image_url = imageUrlInput.value;  // URL to an image
    }
    
    ws.send(JSON.stringify(payload));
}
```

**Receiving a response:**
```javascript
ws.onmessage = function(event) {
    var data = JSON.parse(event.data);
    var answer = data.answer || event.data;
    var agent = data.agent || 'Bot';    // Shows which agent responded
    
    addMessage(agent, answer);           // Add to chat UI
    addDebugEntry('incoming', 'Server Response', data);  // Show raw JSON
};
```

**Message rendering with Markdown:**
```javascript
// Bot messages are rendered as Markdown using the marked.js library
bubble.innerHTML = '<b>' + role + ':</b> ' + marked.parse(cleanText);
```

**Image support:**
- User checks the "Image" checkbox
- Enters an image URL
- The URL is sent to the backend in `payload.image_url`
- The backend analyzes the image using GPT vision, then uses the description as context

**Conversation history tracking:**
```javascript
var conversationHistory = [];

function formatConversationHistory() {
    return conversationHistory.map(item => {
        return (item.role === 'user' ? 'user: ' : 'bot: ') + item.msg;
    }).join('\n');
}
```

---

### 4.3 Request/Response Flow (End-to-End)

Here's what happens when a user types "Add blue paint to my cart":

```
1. [Browser] User types message, clicks Send
   →  WebSocket sends: {"message": "Add blue paint to my cart", "conversation_history": "...", ...}

2. [chat_app.py] Receives JSON via WebSocket
   →  Parses message, image_url, conversation_history
   →  Appends to raw_io_history

3. [HandoffService] Classifies intent
   →  Sends to handoff-service agent in Foundry
   →  Returns: {"domain": "cart_manager", "confidence": 0.95}

4. [chat_app.py] Context Enrichment
   →  agent_name = "cart_manager"
   →  No image processing needed
   →  No product recommendations for cart_manager
   →  Prepares context with RAW_IO_HISTORY

5. [AgentProcessor] Executes cart-manager agent
   →  Creates conversation thread in Foundry
   →  Sends enriched message to cart-manager agent
   →  Agent returns structured JSON with updated cart

6. [chat_app.py] Response Processing
   →  Parses agent response
   →  Updates persistent_cart with new items
   →  Adds session_discount_percentage
   →  Sends response to client

7. [Browser] Receives JSON response
   →  Displays agent's answer in chat bubble
   →  Shows "cart_manager" as the responding agent
   →  Logs raw JSON in debug panel
```

**Response JSON structure:**
```json
{
    "answer": "I've added Blue Paint to your cart!",
    "agent": "cart_manager",
    "cart": [
        {"product_id": "PROD0003", "name": "Whispering Blue", "quantity": 1, "price": 47.99}
    ],
    "products": "",
    "discount_percentage": "32.4%",
    "image_url": "",
    "additional_data": ""
}
```

---

## Quick Reference: Running the Project

```bash
# 1. Set up environment
cp env_sample.txt .env
# Fill in all Azure credentials in .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Push agents to Foundry (one-time setup)
cd src/app/agents
python shopperAgent_initializer.py
python cartManagerAgent_initializer.py
python customerLoyaltyAgent_initializer.py
python interiorDesignAgent_initializer.py
python inventoryAgent_initializer.py
python handoffAgent_initializer.py

# 4. Run the app locally
cd src
uvicorn chat_app:app --host 0.0.0.0 --port 8000

# 5. Or build and run with Docker
docker build -t chat-app .
docker run -p 8000:8000 --env-file .env chat-app

# 6. Open browser
# http://localhost:8000
```

---

## 5. Glossary

A quick reference for key terms used throughout this tutorial.

| Term | Definition |
|------|-----------|
| **Agent** | An LLM wrapped with instructions, tools, and memory that can take actions and maintain state |
| **AI Foundry** | Microsoft's cloud platform (formerly Azure AI Studio) for deploying and managing AI agents |
| **ASGI** | Asynchronous Server Gateway Interface — the protocol that Uvicorn/FastAPI use for async web serving |
| **Azure Container Registry (ACR)** | A private Docker registry in Azure for storing container images |
| **Conversation Thread** | A persistent sequence of messages between a user and an agent, maintaining context across turns |
| **Context Enrichment** | The process of adding image descriptions, product data, and history to a user's message before sending it to an agent |
| **DefaultAzureCredential** | An Azure Identity class that automatically tries multiple authentication methods (managed identity, CLI, environment variables) |
| **Docker Image** | A read-only blueprint containing an application and all of its dependencies |
| **Docker Container** | A running instance of a Docker image |
| **Dockerfile** | A text file containing instructions for building a Docker image |
| **FastAPI** | A modern Python web framework for building APIs with automatic documentation and async support |
| **Function Calling** | An LLM capability where the model generates structured requests to external functions instead of (or alongside) text |
| **FunctionTool** | An Azure AI SDK class that defines a callable function's name, description, and parameter schema |
| **Handoff** | The process of routing a user's message from one agent to another based on intent classification |
| **Intent Classification** | Analyzing a user's message to determine which domain/agent should handle it |
| **Layer (Docker)** | Each instruction in a Dockerfile creates a cached layer; unchanged layers are reused across builds |
| **LLM (Large Language Model)** | A neural network trained on text data that can understand and generate language (e.g., GPT-4o) |
| **MCP (Model Context Protocol)** | An open standard for connecting AI applications with external tools and data sources |
| **Multi-Agent System** | An architecture using multiple specialized agents, each handling a specific domain |
| **Multimodal** | Able to process multiple types of input (text, images, audio) |
| **Prompt (System)** | Instructions given to an LLM that define its role, behavior, and output format |
| **Pydantic** | A Python library for data validation using type annotations; used to define structured output schemas |
| **SSE (Server-Sent Events)** | A protocol for servers to push data to clients over HTTP; used by MCP for tool communication |
| **Structured Output** | An LLM feature that guarantees the response conforms to a specific JSON schema |
| **Uvicorn** | An ASGI web server that runs FastAPI applications |
| **Vector Search** | A database query technique that finds items similar to a query by comparing mathematical representations (embeddings) |
| **WebSocket** | A protocol for persistent, bi-directional communication between client and server |
