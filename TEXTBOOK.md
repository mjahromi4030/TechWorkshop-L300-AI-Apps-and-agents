# AI Agents, Docker & Real-Time Chat — A Textbook Guide

A conceptual companion to the Zava Multi-Agent Chat Application. Read this to understand the **theory and principles** behind the code before (or alongside) the code-focused [TUTORIAL.md](TUTORIAL.md).

---

## Table of Contents

- [Chapter 1: Understanding Large Language Models](#chapter-1-understanding-large-language-models)
- [Chapter 2: From LLM to AI Agent](#chapter-2-from-llm-to-ai-agent)
- [Chapter 3: Function Calling — Giving Agents Hands](#chapter-3-function-calling--giving-agents-hands)
- [Chapter 4: Structured Outputs — Guaranteeing Response Formats](#chapter-4-structured-outputs--guaranteeing-response-formats)
- [Chapter 5: Multi-Agent Systems & Orchestration](#chapter-5-multi-agent-systems--orchestration)
- [Chapter 6: The Model Context Protocol (MCP)](#chapter-6-the-model-context-protocol-mcp)
- [Chapter 7: Azure AI Foundry — Deploying Agents to the Cloud](#chapter-7-azure-ai-foundry--deploying-agents-to-the-cloud)
- [Chapter 8: Prompt Engineering — The Art of Agent Instructions](#chapter-8-prompt-engineering--the-art-of-agent-instructions)
- [Chapter 9: Docker & Containerization](#chapter-9-docker--containerization)
- [Chapter 10: WebSockets, FastAPI & Real-Time Communication](#chapter-10-websockets-fastapi--real-time-communication)
- [Chapter 11: Multimodal AI — Processing Text and Images Together](#chapter-11-multimodal-ai--processing-text-and-images-together)
- [Chapter 12: Putting It All Together — The Zava Architecture](#chapter-12-putting-it-all-together--the-zava-architecture)
- [Glossary](#glossary)

---

## Chapter 1: Understanding Large Language Models

### What Is an LLM?

A **Large Language Model (LLM)** is a type of artificial intelligence trained on massive amounts of text data — books, websites, code, conversations, and scientific papers. Through this training, the model learns patterns of language: grammar, facts, reasoning strategies, coding conventions, and even a degree of "common sense."

When you send a message to an LLM like GPT-4o, it doesn't "think" the way humans do. Instead, it predicts what text should come next, token by token, based on the patterns it learned during training. Despite this seemingly simple mechanism, the results are remarkably sophisticated — the model can write essays, solve math problems, generate code, and carry on nuanced conversations.

### Key Properties of LLMs

**Statelessness.** An LLM has no memory between requests. Each time you send a message, the model starts fresh. It doesn't remember what you asked five minutes ago. If you want continuity in a conversation, you must send the entire conversation history with each request. This is a fundamental constraint that agent architectures must work around.

**Context Window.** Every LLM has a maximum number of tokens (roughly words) it can process in a single request. For GPT-4o, this is typically 128,000 tokens. The context window includes both the input (your prompt + conversation history) and the output (the model's response). If your conversation exceeds the context window, you must truncate or summarize older messages.

**Non-Determinism.** Given the same input, an LLM may produce different outputs each time. This is controlled by a parameter called `temperature`:
- **Temperature 0:** Nearly deterministic — the model picks the most likely next token every time
- **Temperature 1:** More creative and varied — the model samples from a broader distribution
- For classification tasks (like the Handoff Service), you want low temperature; for creative tasks (like writing product descriptions), higher temperature is appropriate.

**Training Data Cutoff.** An LLM's knowledge is frozen at its training date. It doesn't know about events, products, or prices that changed after training. To provide current information, you must supply it through tools (like searching a product database) or by including the data in the prompt.

### How Tokens Work

LLMs don't process text character by character. Instead, they break text into **tokens** — chunks that typically correspond to common words, word parts, or characters. For example:

```
"I want blue paint" → ["I", " want", " blue", " paint"]  (4 tokens)
"ChatGPT"           → ["Chat", "G", "PT"]                 (3 tokens)
```

Understanding tokens matters because:
- You're billed per token (input + output)
- The context window is measured in tokens
- Very long conversations consume more tokens, increasing cost and latency

### The Completion API

At the lowest level, interacting with an LLM is a single API call:

```
Input:  System prompt + User message + Conversation history
Output: Model's response (text, or a function call request)
```

The system prompt sets the stage (who the model is, what it should do), the conversation history provides context (what was discussed before), and the user message is the current request. The model processes all of this together and generates a response.

This is the foundation that everything else builds on. Agents, tools, structured outputs, and multi-agent systems are all patterns built *on top of* this basic completion API.

### In the Zava Project: The Simplest Possible LLM Call

The file `src/app/tools/singleAgentExample.py` demonstrates this basic pattern — a raw LLM call with no agent framework:

```python
# src/app/tools/singleAgentExample.py
from openai import AzureOpenAI

# Initialize Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint=os.getenv("gpt_endpoint"),
    api_key=os.getenv("gpt_api_key"),
    api_version=os.getenv("gpt_api_version"),
)

def generate_response(text_input):
    # System prompt + User message → Completion
    chat_prompt = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are a helpful assistant working for Zava..."}]
        },
        {"role": "user", "content": text_input}
    ]

    completion = client.chat.completions.create(
        model=deployment,
        messages=chat_prompt,
        max_completion_tokens=10000,
    )
    return completion.choices[0].message.content
```

Notice:
- `messages` contains the system prompt and user message (the input)
- `completion.choices[0].message.content` is the model's response (the output)
- There's no memory, no tools, no structured output — just input → output

---

## Chapter 2: From LLM to AI Agent

### The Limitations of Raw LLMs

A raw LLM can answer questions based on its training data, but it can't:
- Look up current product prices in a database
- Check if an item is in stock
- Generate images
- Remember your previous conversation
- Guarantee its response format

An **AI Agent** is the layer we add around an LLM to overcome these limitations. Think of the LLM as a brain, and the agent as the body — it gives the brain eyes (image understanding), hands (tool use), memory (conversation threads), and a consistent personality (system prompt).

### The Four Pillars of an Agent

#### 1. System Prompt (Identity)

The system prompt is the agent's job description. It defines:
- **Who** the agent is: "You are Cora, a shopping assistant for Zava."
- **What** it does: "Help customers find products, answer questions about home improvement."
- **How** it responds: "Return responses in JSON format with answer, products, and cart fields."
- **What it refuses:** "If asked about unrelated topics, politely redirect to DIY."

Without a system prompt, an LLM is a general-purpose text generator. With one, it becomes a focused specialist. The quality of the system prompt is often the single biggest factor in an agent's usefulness.

#### 2. Tools (Capabilities)

Tools give an agent the ability to interact with the outside world. A tool is typically defined by:
- **Name:** What the tool is called (`mcp_product_recommendations`)
- **Description:** What it does (in plain English, so the LLM can decide when to use it)
- **Parameters:** What inputs it needs (as a JSON schema)
- **Implementation:** The actual code that runs when the tool is called

The LLM doesn't execute tools directly. It generates a structured request ("please call `mcp_product_recommendations` with question 'blue paint'"), and your application code intercepts this request, runs the actual function, and feeds the result back to the LLM.

#### 3. Memory (Conversation Threads)

A conversation thread is a sequence of messages that gives the agent context. Each message has a role:
- **System:** The system prompt (set once at the start)
- **User:** Messages from the human
- **Assistant:** Previous responses from the agent
- **Tool:** Results from function calls

By sending the full thread with each request, the agent appears to "remember" the conversation. In reality, it's re-reading the entire history every time — like an actor who re-reads the entire script before delivering each line.

Conversation threads can be managed locally (in your application code) or remotely (in a service like Azure AI Foundry). This project uses Foundry-managed conversations.

#### 4. Structured Output (Reliability)

When an agent needs to return data that your code will parse (not just text for humans to read), you need **structured outputs**. This constrains the model's generation to produce valid JSON matching a specific schema — every field is present, every type is correct, every time.

### Agent vs. Chatbot vs. Assistant

These terms are often used interchangeably, but they have nuanced differences:

| Term | Meaning |
|------|---------|
| **Chatbot** | Any program that converses with humans (may be rule-based, no LLM) |
| **Assistant** | An LLM-powered chatbot with a system prompt and conversation history |
| **Agent** | An assistant that can also use tools, make decisions, and take actions |

In this project, the "single agent example" (`singleAgentExample.py`) is really an **assistant** — it has a system prompt and can converse, but it can't use tools. The Foundry-deployed agents (Cora, Cart Manager, etc.) are true **agents** — they can reason about when to call tools and chain multiple actions together.

### In the Zava Project: Comparing an Assistant vs. an Agent

**The Assistant** (no tools, no Foundry) — `src/app/tools/singleAgentExample.py`:
```python
# Direct call to Azure OpenAI — no Foundry, no tools
client = AzureOpenAI(azure_endpoint=endpoint, api_key=api_key, api_version=api_version)
completion = client.chat.completions.create(model=deployment, messages=chat_prompt)
return completion.choices[0].message.content
```

**The Agent** (tools + Foundry) — `src/app/agents/shopperAgent_initializer.py`:
```python
# Agent deployed to Foundry with tools and a specialized prompt
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

project_client = AIProjectClient(
    endpoint=os.environ["FOUNDRY_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

# Cora gets the product recommendations tool
functions = create_function_tool_for_agent("cora")

initialize_agent(
    project_client=project_client,
    model=os.environ["gpt_deployment"],
    name="cora",
    description="Cora - Zava Shopping Assistant",
    instructions=CORA_PROMPT,   # Loaded from prompts/ShopperAgentPrompt.txt
    tools=functions              # [mcp_product_recommendations]
)
```

The assistant can only generate text from its training data. The agent can search real product catalogs, check inventory, and generate images.

---

## Chapter 3: Function Calling — Giving Agents Hands

### The Problem

Imagine you ask an AI assistant: "Is Whispering Blue paint in stock?" The LLM doesn't have access to your inventory database. It could guess, but guessing is worse than not knowing. What you need is a way for the LLM to say: "I don't have this information, but I know where to get it — please check the inventory system for me."

### How Function Calling Works

Function calling is a structured protocol between your application and the LLM:

**Step 1: Define Available Functions**

You tell the model what functions exist, what they do, and what parameters they accept:

```python
FunctionTool(
    name="mcp_inventory_check",
    description="Check inventory for products",
    parameters={
        "type": "object",
        "properties": {
            "product_list": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of product IDs to check"
            }
        },
        "required": ["product_list"]
    }
)
```

**Step 2: The Model Decides to Call a Function**

When the user asks about inventory, the model doesn't generate a text response. Instead, it generates a **function call**:

```json
{
    "type": "function_call",
    "name": "mcp_inventory_check",
    "arguments": "{\"product_list\": [\"PROD0003\"]}"
}
```

The model has decided that `mcp_inventory_check` is the right tool and has constructed appropriate arguments based on the user's question.

**Step 3: Your Code Executes the Function**

Your application intercepts the function call, runs the actual code, and captures the result:

```python
result = mcp_inventory_check(product_list=["PROD0003"])
# Returns: {"ProductName": "Whispering Blue", "QuantityInStock": 487, "Price": 47.99}
```

**Step 4: Feed the Result Back**

You send the function result back to the model, which now has real data to reference:

```python
FunctionCallOutput(
    type="function_call_output",
    call_id=item.call_id,
    output=json.dumps({"result": result})
)
```

**Step 5: The Model Generates the Final Response**

With the real data in hand, the model produces a human-friendly answer:

> "Great news! Whispering Blue paint is in stock — we have 487 units available at $47.99 each. Would you like me to add it to your cart?"

### The Strict Flag

When you set `strict=True` on a function definition, the model is guaranteed to produce arguments that conform exactly to your schema. Without strict mode, the model might add extra fields, use the wrong types, or omit required fields. Strict mode eliminates these issues at the cost of slightly longer generation times.

### When to Use Function Calling

Use function calling when:
- The agent needs real-time data (inventory, prices, customer data)
- The agent needs to take actions (generate images, send emails, update databases)
- The data changes frequently and can't be baked into the prompt

Don't use function calling when:
- The information is already in the agent's context (like the cart state in Cart Manager)
- The task is purely conversational (general chit-chat)
- Adding a tool call would increase latency without adding value

### In the Zava Project: The Full Tool Use Loop

Here's the actual code from `src/app/agents/agent_processor.py` that implements the tool use loop:

```python
# Step 1: Send message to the agent in Foundry
message = openai_client.responses.create(
    conversation=thread_id,
    extra_body={"agent": {"name": self.agent_id, "type": "agent_reference"}},
    input="",
    stream=False
)

# Step 2: Check if the agent wants to call a function
if len(message.output_text) == 0:
    input_list = []
    for item in message.output:
        if item.type == "function_call":
            # Step 3: Execute the function locally
            if item.name == "mcp_product_recommendations":
                func_result = mcp_product_recommendations(**json.loads(item.arguments))
            elif item.name == "mcp_calculate_discount":
                func_result = mcp_calculate_discount(**json.loads(item.arguments))
            elif item.name == "mcp_inventory_check":
                func_result = mcp_inventory_check(**json.loads(item.arguments))

            # Step 4: Package the result for the model
            input_list.append(FunctionCallOutput(
                type="function_call_output",
                call_id=item.call_id,
                output=json.dumps({"result": func_result})
            ))

    # Step 5: Send results back — model generates final text answer
    message = openai_client.responses.create(
        input=input_list,
        previous_response_id=message.id,
        extra_body={"agent": {"name": self.agent_id, "type": "agent_reference"}},
    )
```

And here's how a function tool is defined with `strict=True`:

```python
# From agent_processor.py — create_function_tool_for_agent()
from azure.ai.projects.models import FunctionTool

define_mcp_product_recommendations = FunctionTool(
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
    strict=True  # Guarantees the model's arguments match this schema exactly
)
```

---

## Chapter 4: Structured Outputs — Guaranteeing Response Formats

### The Reliability Problem

Consider this scenario: your Handoff Service needs to parse the agent's response to determine which agent to route to. If the agent returns:

```
"Based on the user's message about adding items to their cart, I believe this should be routed to the cart_manager domain with high confidence."
```

...your code would need complex parsing logic to extract "cart_manager" from that sentence. And what if the model phrases it differently next time? Or wraps it in markdown? Or adds extra fields?

### How Structured Outputs Work

Structured outputs use a technique called **constrained decoding**. At each step of text generation, the model is only allowed to produce tokens that would result in valid JSON conforming to your schema. It's not just a prompt instruction ("please return JSON") — it's an algorithmic constraint on the generation process.

You provide the schema using JSON Schema format (or via Pydantic in Python):

```python
class IntentClassification(BaseModel):
    domain: str = Field(description="Target domain")
    is_domain_change: bool = Field(description="Whether domain changed")
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(description="Brief explanation")
```

And the model will always return exactly this structure:

```json
{
    "domain": "cart_manager",
    "is_domain_change": true,
    "confidence": 0.95,
    "reasoning": "User explicitly asked to add to cart"
}
```

### Pydantic and JSON Schema

**Pydantic** is a Python library for data validation. You define a class with type annotations, and Pydantic ensures that any data you create or parse conforms to those types. In this project, Pydantic serves double duty:

1. **Schema definition:** `IntentClassification.model_json_schema()` auto-generates the JSON Schema that Azure AI Foundry uses to constrain the model's output
2. **Response validation:** When parsing the response, Pydantic ensures the data matches expectations

The `model_config = {"extra": "forbid"}` setting rejects any extra fields the model might try to include. Combined with structured outputs, this creates an airtight contract between your code and the model.

### When to Use Structured Outputs

Use structured outputs when:
- The response must be machine-parseable (routing decisions, API responses)
- You need guaranteed field presence and types
- Downstream code depends on a specific format

Don't use them when:
- The response is for human consumption (chat answers, explanations)
- You need flexible, variable-length output (product descriptions)
- The schema would be overly complex or restrictive

In this project, the Handoff Service uses structured outputs because routing decisions *must* be reliable. The other agents don't because their responses include freeform text ("answer" field) that shouldn't be constrained.

### In the Zava Project: Structured Output for Intent Classification

**Step 1: Define the schema with Pydantic** (`src/services/handoff_service.py`):

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

**Step 2: Deploy the agent with the schema** (`src/app/agents/handoffAgent_initializer.py`):

```python
from azure.ai.projects.models import (
    PromptAgentDefinition,
    PromptAgentDefinitionText,
    ResponseTextFormatConfigurationJsonSchema
)

agent = project_client.agents.create_version(
    agent_name="handoff-service",
    description="Zava Handoff Service Agent",
    definition=PromptAgentDefinition(
        model=os.environ["gpt_deployment"],
        text=PromptAgentDefinitionText(
            format=ResponseTextFormatConfigurationJsonSchema(
                name="IntentClassification",
                schema=IntentClassification.model_json_schema()  # ← Auto-generates JSON Schema from Pydantic
            )
        ),
        instructions=HANDOFF_AGENT_PROMPT
    )
)
```

**Step 3: Parse the guaranteed-valid response** (`src/services/handoff_service.py`):

```python
response = self.client.responses.create(
    conversation=conversation.id,
    extra_body={"agent": {"name": "handoff-service", "type": "agent_reference"}},
    input=""
)

# This is ALWAYS valid JSON matching the schema — no try/except needed for parsing
intent = json.loads(response.output_text)
# intent = {"domain": "cart_manager", "confidence": 0.95, "is_domain_change": true, "reasoning": "..."}
```

Contrast this with the other agents (like Cora), which return freeform text that the application then parses with `parse_agent_response()` — a more fragile approach that requires error handling.

---

## Chapter 5: Multi-Agent Systems & Orchestration

### Why Multiple Agents?

The simplest AI application has one agent that handles everything. This works for small projects, but breaks down at scale. Here's why:

**Prompt bloat.** A single system prompt that covers shopping, cart management, interior design, inventory checks, customer loyalty, and image generation would be enormous. LLMs perform worse with very long, complex prompts — they lose focus and make more mistakes.

**Tool confusion.** If one agent has access to image generation, product search, discount calculation, AND inventory checking, it might generate an image when you asked for a discount, or check inventory when you asked for a product recommendation. More tools = more room for the wrong choice.

**Maintenance nightmare.** When you need to update the cart management logic, you risk accidentally breaking the interior design behavior if they share the same prompt and tool set.

### The Specialization Principle

Multi-agent systems follow the **Single Responsibility Principle** from software engineering: each agent should do one thing well. In the Zava project:

| Agent | Specialty | Tools |
|-------|-----------|-------|
| Cora | General shopping questions | Product search |
| Interior Designer | Room design and visualization | Image generation + Product search |
| Cart Manager | Cart operations | None (context-only) |
| Customer Loyalty | Discount calculation | Discount calculator |
| Inventory Agent | Stock checking | Inventory check |

Each agent has a focused prompt, only the tools it needs, and no knowledge of the other agents' existence.

### The Orchestration Problem

If you have five specialists, who decides which one handles each message? This is the **orchestration problem**, and there are three common approaches:

#### Approach 1: Keyword Matching (Simple, Brittle)
```python
if "cart" in message:
    route_to("cart_manager")
elif "stock" in message or "available" in message:
    route_to("inventory_agent")
```
**Problem:** "What color options are available for the shopping cart page?" would match both "cart" and "available," and "available" doesn't mean inventory here.

#### Approach 2: Rule-Based Classification (Better, Still Limited)
Regex patterns, priority rules, and decision trees. More robust than keywords, but every new edge case requires a new rule. Doesn't handle ambiguity or novel phrasing.

#### Approach 3: LLM-Based Classification (Flexible, Smart)
Use another LLM to classify the intent. This is what the Zava project does — the Handoff Service agent reads the user's message and outputs a structured classification with domain, confidence, and reasoning.

**Advantages:**
- Handles novel phrasing ("I'd like to see how this would look on my wall" → interior_designer)
- Provides confidence scores for uncertain cases
- Can reason about context ("we were discussing paint colors, and the user says 'add it'" → cart_manager, not cora)

**Tradeoff:** Every message requires an extra LLM call for classification, adding latency and cost. The project mitigates this with **lazy classification** — the first message always goes to Cora without classification.

### Session-Aware Routing

The Handoff Service doesn't just classify individual messages — it considers the session context. If you're currently in a conversation with the Interior Designer about paint colors and you say "how much is that?", the service knows you're still in the interior design domain, not asking a general shopping question.

This is implemented by tracking the current domain per session:
```python
# If we're in "interior_designer" and user says "how much?",
# the classifier sees: "Current domain: interior_designer"
# and can decide to stay in the same domain.
```

### In the Zava Project: The Five Specialist Agents

Each agent is created by a separate initializer script. Here's a side-by-side showing how tools are assigned per agent type:

```python
# From src/app/agents/agent_processor.py — create_function_tool_for_agent()
def create_function_tool_for_agent(agent_type: str) -> List[Any]:
    # ... tool definitions ...

    if agent_type == "interior_designer":
        return [define_mcp_create_image, define_mcp_product_recommendations]
    elif agent_type == "customer_loyalty":
        return [define_mcp_calculate_discount]
    elif agent_type == "inventory_agent":
        return [define_mcp_inventory_check]
    elif agent_type == "cart_manager":
        return []   # ← No tools! Pure LLM reasoning from context
    elif agent_type == "cora":
        return [define_mcp_product_recommendations]
```

And here's the orchestrator routing in `src/chat_app.py`:

```python
# Handoff Service classifies intent → picks the right agent
intent_result = handoff_service.classify_intent(
    user_message=user_message,
    session_id=session_id,
    chat_history=formatted_history
)
agent_name = intent_result["agent_id"]       # e.g., "cora", "cart_manager"
agent_selected = validated_env_vars.get(agent_name)  # Get agent ID from environment

print(f"Intent classification: domain={intent_result['domain']}, "
      f"confidence={intent_result['confidence']:.2f}, "
      f"reasoning={intent_result['reasoning']}")
```

The Handoff Service's lazy classification skips the LLM call on the first message:

```python
# From src/services/handoff_service.py
def classify_intent(self, user_message, session_id, chat_history=None):
    current_domain = self._session_domains.get(session_id, None)

    # First message → skip classification, go straight to default agent
    if not current_domain:
        self._session_domains[session_id] = self.default_domain
        return {
            "domain": self.default_domain,    # "cora"
            "confidence": 1.0,
            "reasoning": f"First message, routing to {self.default_domain}",
            ...
        }
```

---

## Chapter 6: The Model Context Protocol (MCP)

### What Is MCP?

**MCP (Model Context Protocol)** is an open standard that defines how AI applications communicate with external tools and data sources. It was created by Anthropic and has been adopted broadly across the AI industry.

Think of MCP as **USB for AI tools**. Before USB, every device needed its own special connector. USB standardized the interface so any device works with any computer. Similarly, MCP standardizes the interface so any AI application can use any MCP-compatible tool.

### The Architecture: Server and Client

MCP uses a **client-server architecture**:

```
┌──────────────┐    SSE/stdio    ┌──────────────┐
│  MCP Client  │ ◄────────────► │  MCP Server   │
│ (Your App)   │                 │ (Tool Host)   │
└──────────────┘                 └──────────────┘
                                       │
                                       ▼
                                 ┌───────────┐
                                 │ Business   │
                                 │ Logic      │
                                 │ (DB, API,  │
                                 │  etc.)     │
                                 └───────────┘
```

**MCP Server:** Exposes tools with standardized interfaces. In this project, the server offers:
- `get_product_recommendations` — searches Cosmos DB
- `check_product_inventory` — looks up stock levels
- `get_customer_discount` — calculates loyalty discounts
- `generate_product_image` — creates images via DALL-E

**MCP Client:** Discovers and calls tools on the server. The client doesn't need to know implementation details — it just knows the tool's name and parameters.

### Transport Layers

MCP supports multiple transport mechanisms:
- **stdio:** Communication via standard input/output (for local processes)
- **SSE (Server-Sent Events):** Communication over HTTP (for networked services)

The Zava project uses **SSE** because the MCP server runs as a sub-application inside the FastAPI web server, accessible at `/mcp-inventory/sse`.

### Why Use MCP Instead of Direct Function Calls?

You could skip MCP entirely and call your tools directly:

```python
# Direct call (no MCP)
result = product_recommendations("blue paint")
```

So why add the MCP layer? Several reasons:

1. **Discoverability.** MCP clients can query the server to list all available tools at runtime. Useful for debugging and dynamic tool selection.

2. **Separation of concerns.** The tool implementation lives in the MCP server. The agent code only knows about the tool's interface. You can change the database behind `get_product_recommendations` without touching agent code.

3. **Reusability.** Multiple agents (and even external applications) can use the same MCP server. One tool implementation serves all consumers.

4. **Ecosystem compatibility.** MCP is an open standard. Third-party tools, IDEs, and AI platforms can interact with your MCP server without custom integration.

5. **Prompts as a Service.** MCP servers can also expose **prompts** — reusable prompt templates that clients can retrieve. The Zava MCP server exposes agent prompts via `@mcp.prompt()`, allowing tools to serve both implementations and instructions.

### MCP in the Zava Project

The MCP server is mounted directly inside the FastAPI application:

```python
app.mount("/mcp-inventory/", inventory_mcp.sse_app())
```

This means the MCP tools are co-located with the chat application — no separate deployment needed. The MCP client connects to this internal endpoint to execute tools during agent processing.

### In the Zava Project: Server, Client & Tool Implementation

**The MCP Server** (`src/app/servers/mcp_inventory_server.py`) — exposes tools via the `@mcp.tool()` decorator:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MCP Shop Inventory Server")

@mcp.tool()
def get_product_recommendations(question: str) -> str:
    """Search for product recommendations based on user query."""
    results = product_recommendations(question)   # Calls Cosmos DB vector search
    return json.dumps(results)

@mcp.tool()
def check_product_inventory(product_id: str) -> str:
    """Check inventory availability for a specific product."""
    product_dict = {"id": product_id}
    result = inventory_check(product_dict)         # Checks simulated inventory data
    return json.dumps(result)

@mcp.tool()
def get_customer_discount(customer_id: str) -> str:
    """Calculate available discounts for a customer."""
    result = calculate_discount(customer_id)       # Simulates Fabric + OpenAI discount logic
    return json.dumps(result)

@mcp.tool()
def generate_product_image(prompt: str, size: str = "1024x1024") -> str:
    """Generate an AI image based on a text description using DALL-E."""
    result = create_image(prompt, size)            # Calls gpt-image-1 + uploads to Blob
    return json.dumps(result)
```

The server also exposes **prompts** as reusable templates:

```python
@mcp.prompt(title="Agent Prompt")
def agentPrompt(agent_name: str) -> str:
    """Returns the appropriate agent prompt based on the agent name."""
    prompt_files = {
        "cora": "ShopperAgentPrompt.txt",
        "customer_loyalty": "CustomerLoyaltyAgentPrompt.txt",
        "interior_designer": "InteriorDesignAgentPrompt.txt",
        ...
    }
    return read_prompt_file(prompt_files[agent_name.lower()])
```

**The MCP Client** (`src/app/servers/mcp_inventory_client.py`) — connects to the server and calls tools:

```python
from mcp import ClientSession
from mcp.client.sse import sse_client

class MCPShopperToolsClient:
    def __init__(self, server_url="http://localhost:8000/sse"):
        self.server_url = server_url

    async def call_tool(self, tool_name: str, arguments: dict):
        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result_data = await session.call_tool(tool_name, arguments=arguments)
                return json.loads(result_data.content[0].text)

    async def list_tools(self):
        """Discover all tools available on the server."""
        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.list_tools()
```

**Mounting the server inside FastAPI** (`src/chat_app.py`):

```python
from app.servers.mcp_inventory_server import mcp as inventory_mcp

app = FastAPI()
inventory_mcp_app = inventory_mcp.sse_app()
app.mount("/mcp-inventory/", inventory_mcp_app)    # Tools at /mcp-inventory/sse
```

---

## Chapter 7: Azure AI Foundry — Deploying Agents to the Cloud

### What Is Azure AI Foundry?

**Azure AI Foundry** (formerly Azure AI Studio) is Microsoft's platform for building and deploying AI applications. For this project, Foundry serves as the **agent hosting and execution platform**. You define agents (with models, prompts, and tools) and deploy them to Foundry. Your application then calls these agents by name to process messages.

### Why Deploy Agents to Foundry?

You could run agents entirely in your own code — just call the OpenAI API directly with a system prompt and tools. So why use Foundry?

1. **Centralized management.** All agents are defined in one place. You can update an agent's prompt or tools without redeploying your application.
2. **Versioning.** `create_version()` creates a new version of an agent. You can roll back to previous versions if something goes wrong.
3. **Conversation management.** Foundry manages conversation threads, so your application doesn't need to store and send full conversation histories.
4. **Monitoring.** Foundry provides built-in telemetry, logging, and performance monitoring for agent invocations.
5. **Access control.** Foundry integrates with Azure's identity and access management for security.

### The Agent Lifecycle

```
1. DEFINE    → Write system prompt (.txt file) + choose tools
2. DEPLOY    → Run initializer script → Agent registered in Foundry
3. INVOKE    → Application calls agent by name via conversations API
4. ITERATE   → Update prompt/tools → Re-run initializer → New version deployed
```

### Authentication: DefaultAzureCredential

All communication with Foundry uses **DefaultAzureCredential**, which automatically tries multiple authentication methods in order:

1. Environment variables (for CI/CD pipelines)
2. Managed Identity (for Azure-hosted applications like App Service)
3. Azure CLI (`az login` — for local development)
4. Visual Studio / VS Code credentials

This means the same code works in development (using your CLI login) and production (using the App Service's managed identity) without any changes.

### In the Zava Project: Creating and Invoking Agents

**The universal agent factory** (`src/app/agents/agent_initializer.py`):

```python
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

def initialize_agent(project_client, model, name, description, instructions, tools):
    with project_client:
        agent = project_client.agents.create_version(
            agent_name=name,              # Name used to reference at runtime
            description=description,
            definition=PromptAgentDefinition(
                model=model,              # GPT deployment name
                instructions=instructions, # System prompt from .txt file
                tools=tools               # List of FunctionTool objects
            )
        )
        print(f"Created {name} agent, ID: {agent.id}")
```

**Invoking an agent at runtime** (`src/app/agents/agent_processor.py`):

```python
# 1. Get an OpenAI client from the project client
openai_client = self.project_client.get_openai_client()

# 2. Create a conversation thread
conversation = openai_client.conversations.create(
    items=[{"role": "user", "content": input_message}]
)
thread_id = conversation.id

# 3. Send to the Foundry agent by name
message = openai_client.responses.create(
    conversation=thread_id,
    extra_body={"agent": {"name": self.agent_id, "type": "agent_reference"}},
    input="",
    stream=False
)

# 4. Read the response
content = message.output_text
```

The key detail is `extra_body={"agent": {"name": self.agent_id, "type": "agent_reference"}}` — this tells the API "use the agent named X that's registered in Foundry" rather than sending a raw system prompt.

**Caching processors for performance** (`src/services/agent_service.py`):

```python
_agent_processor_cache: Dict[str, AgentProcessor] = {}

def get_or_create_agent_processor(agent_id, agent_type, thread_id, project_client):
    cache_key = f"{agent_type}_{agent_id}"
    if cache_key in _agent_processor_cache:
        processor = _agent_processor_cache[cache_key]
        processor.thread_id = thread_id   # Update thread for new conversation
        return processor
    processor = AgentProcessor(
        project_client=project_client,
        assistant_id=agent_id,
        agent_type=agent_type,
        thread_id=thread_id
    )
    _agent_processor_cache[cache_key] = processor
    return processor
```

---

## Chapter 8: Prompt Engineering — The Art of Agent Instructions

### What Is Prompt Engineering?

**Prompt engineering** is the practice of designing and refining the text instructions given to an LLM to elicit the desired behavior. It's part art, part science. A well-crafted prompt can be the difference between a helpful agent and a frustrating one.

### Anatomy of a Good System Prompt

The prompts in the `prompts/` directory follow a consistent structure:

#### 1. Role Definition
```
You are a Cart Manager Assistant for Zava, a home improvement and furniture retailer.
```
Tells the model who it is and what domain it operates in.

#### 2. Responsibility List
```
1. CART MANAGEMENT - Add products, remove products, update quantities
2. CART OPERATIONS - Parse requests, update state, confirm actions
3. RESPONSE FORMAT - Always respond in valid JSON format
```
A numbered list of specific duties helps the model understand its scope.

#### 3. Output Format Specification
```json
{
    "answer": "Friendly confirmation message",
    "cart": [{"product_id": "...", "name": "...", "quantity": 2, "price": 29.99}],
    "products": "Optional related product suggestions",
    "discount_percentage": ""
}
```
Showing the exact expected JSON structure is far more effective than describing it in prose.

#### 4. Behavioral Guidelines
```
- Be friendly and helpful
- Confirm actions clearly
- If unclear, ask for clarification
- Never generate content outside your domain
```

#### 5. Guardrails
```
- If asked about something not related to DIY, politely decline
- Do not generate content summaries or remove any data
```

### Prompt Storage Strategy

This project stores prompts as **external `.txt` files** rather than embedding them in Python code. This is a deliberate design choice:

- **Non-developers can edit prompts.** A product manager can tweak agent behavior without touching code.
- **Version control is cleaner.** Prompt changes show up as text diffs, easy to review.
- **No recompilation needed.** In some deployment models, you can update prompts without rebuilding the Docker image.
- **Separation of concerns.** Python files contain logic; prompt files contain behavior.

### The Handoff Prompt: A Special Case

The Handoff Service prompt is different from other agents' prompts. It's an **intent classification prompt** that tells the model:
- The available domains (with descriptions)
- How to analyze a message
- Rules for routing (e.g., "if user mentions cart → cart_manager")
- The current domain context

This prompt is designed for **precision over personality** — the model should classify accurately, not engagingly.

### In the Zava Project: All System Prompts

**Cora (Shopper Agent)** — `src/prompts/ShopperAgentPrompt.txt`:
```
Shopper Agent Guidelines
========================================
- You are the public facing assistant of Zava
- Greet people and help them as needed
- Return response in following json format (image_output and products empty)

answer: your answer,
image_output: []
products: []
```
Short, focused. Defines role, output format, and nothing else.

**Cart Manager** — `src/prompts/CartManagerPrompt.txt` (excerpt):
```
You are a Cart Manager Assistant for Zava, a home improvement and furniture retailer.

1. CART MANAGEMENT — Add/remove/update products
2. CART OPERATIONS — Parse requests, update state, confirm actions
3. RESPONSE FORMAT — Always respond in valid JSON:
   {
       "answer": "Friendly confirmation message",
       "cart": [{"product_id": "PROD-123", "name": "Product Name", "quantity": 2, "price": 29.99}],
       "products": "Optional related product suggestions",
       "discount_percentage": ""
   }
```
Long and detailed — because the Cart Manager has no tools and must figure out everything from context.

**Handoff Agent** — `src/prompts/HandoffAgentPrompt.txt` (excerpt):
```
You are an intent classifier for Zava shopping assistant.

Available domains:
1. cora: General shopping, product browsing
2. interior_designer: Room design, decorating, image creation
3. inventory_agent: Product availability, stock checks
4. customer_loyalty: Discounts, promotions, loyalty programs
5. cart_manager: Shopping cart operations

Rules:
- If user mentions "cart", "add to cart", "checkout" → cart_manager
- If uncertain, default to current domain with low confidence
- Default to 'cora' for general/ambiguous queries
```
Pure classification — no personality, just rules and domains.

**Loading prompts from files** (every initializer follows this pattern):

```python
# From src/app/agents/cartManagerAgent_initializer.py
CART_PROMPT_PATH = os.path.join(..., 'prompts', 'CartManagerPrompt.txt')
with open(CART_PROMPT_PATH, 'r', encoding='utf-8') as file:
    CART_MANAGER_PROMPT = file.read()

initialize_agent(
    ...
    instructions=CART_MANAGER_PROMPT,  # Loaded from file, not hardcoded
    ...
)
```

---

## Chapter 9: Docker & Containerization

### What Is Docker?

**Docker** is a platform for building, shipping, and running applications in isolated environments called **containers**. A container packages your application with everything it needs — OS libraries, runtime, dependencies, and code — into a single portable unit.

### The Problem Docker Solves

Without Docker, deploying an application involves:
1. Setting up a server with the right OS version
2. Installing the correct Python version
3. Installing system libraries (gcc, libgl1, etc.)
4. Installing Python packages (with the exact right versions)
5. Copying your code
6. Configuring environment variables
7. Hoping nothing conflicts with other software on the server

Each step can fail, and each failure is unique to the server's state. **"It works on my machine"** is the rallying cry of developers who haven't containerized.

Docker eliminates this by encoding all setup steps into a **Dockerfile** — a reproducible recipe that produces identical results everywhere.

### Key Concepts

#### Images and Containers

An **image** is a read-only template. A **container** is a running instance of an image.

| Concept | OOP Analogy | Action |
|---------|------------|--------|
| Image | Class | `docker build` creates it |
| Container | Object instance | `docker run` creates it from an image |

You can run multiple containers from the same image, each with its own state.

#### Layers and Caching

Each instruction in a Dockerfile creates a **layer**. Docker caches layers and reuses them when nothing has changed. This is why the order of instructions matters:

```dockerfile
# Good: Dependencies first (rarely change), code last (changes often)
COPY requirements.txt ./          # ← Layer 1: cached unless requirements change
RUN pip install -r requirements.txt  # ← Layer 2: cached unless Layer 1 changed
COPY . .                          # ← Layer 3: rebuilt every code change

# Bad: Everything together (no caching benefit)
COPY . .                          # ← Layer 1: rebuilt every code change
RUN pip install -r requirements.txt  # ← Layer 2: ALSO rebuilt (cache invalidated)
```

The good order means pip install only runs when `requirements.txt` changes. The bad order runs pip install on every single build.

#### The Build Context

When you run `docker build .`, Docker sends the entire directory (the **build context**) to the Docker daemon. If your directory contains large files you don't need in the image (like `.git/`, `node_modules/`, or data files), add them to a `.dockerignore` file to speed up builds.

#### EXPOSE vs. Port Mapping

`EXPOSE 8000` in a Dockerfile is **documentation** — it tells other developers (and tools) that the application listens on port 8000. It doesn't actually publish the port.

`docker run -p 8000:8000` is what actually **maps** host port 8000 to container port 8000. Without this flag, the container's port is accessible only from within Docker's network.

#### CMD vs. ENTRYPOINT

- **CMD** specifies the default command to run. Can be overridden at `docker run`.
- **ENTRYPOINT** specifies a command that always runs. CMD provides default arguments to it.

This project uses CMD, which makes it easy to override the startup command for debugging:
```bash
docker run -it chat-app /bin/bash  # Override CMD to get a shell instead
```

### Base Images: Slim vs. Full

| Base Image | Size | Includes | Use When |
|-----------|------|----------|----------|
| `python:3.12` | ~900MB | Full Debian, compilers, docs | You need to compile many C extensions |
| `python:3.12-slim` | ~150MB | Minimal Debian, Python only | You can install only what you need |
| `python:3.12-alpine` | ~50MB | Alpine Linux, musl libc | Maximum minimalism (may break some packages) |

The Zava project uses `slim` and explicitly installs the few system packages it needs (gcc, graphics libraries).

### Azure Container Registry (ACR)

**ACR** is a private Docker registry hosted in Azure. The workflow:

```
docker build -t chat-app .                              # Build locally
docker tag chat-app myacr.azurecr.io/chat-app:latest    # Tag for ACR
az acr login --name myacr                                # Authenticate
docker push myacr.azurecr.io/chat-app:latest             # Push to cloud
```

Azure App Service can then pull this image and run it as a container. The `Continuous Deployment: On` setting means App Service automatically pulls new images when you push updates.

### In the Zava Project: The Complete Dockerfile

```dockerfile
# src/Dockerfile

# Layer 1: Base image (slim = ~150MB vs ~900MB for full)
FROM python:3.12-slim

# Layer 2: Security updates
RUN apt-get update && apt-get upgrade -y && pip install --upgrade pip && rm -rf /var/lib/apt/lists/*

# Set working directory for all subsequent commands
WORKDIR /app

# Layer 3: System dependencies (C compiler for numpy/pandas, graphics libs for Pillow)
RUN apt-get update && apt-get install -y \
    build-essential unixodbc-dev gcc g++ \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Layer 4: Python dependencies (cached unless requirements.txt changes)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Layer 5: Application code (rebuilt every code change)
COPY . .
COPY .env .env

# Documentation + runtime config
EXPOSE 8000
ENV PORT=8000

# Start the FastAPI app with Uvicorn
CMD ["uvicorn", "chat_app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key packages from `requirements.txt`:**
```
fastapi==0.128.0          # Web framework
uvicorn[standard]==0.40.0 # ASGI server
azure-ai-projects==2.0.0b3 # Foundry agent SDK
openai==2.14.0            # Azure OpenAI client
azure-cosmos==4.14.3      # Cosmos DB for vector search
mcp==1.25.0               # Model Context Protocol
fastmcp==2.14.1           # FastMCP server framework
orjson==3.11.5            # Fast JSON serialization
azure-identity==1.25.2    # DefaultAzureCredential
```

---

## Chapter 10: WebSockets, FastAPI & Real-Time Communication

### HTTP: The Request-Response Model

Standard web communication uses **HTTP**. The browser sends a request, the server sends a response, and the connection closes. Every interaction is a separate round trip:

```
Browser  ──request──►  Server
Browser  ◄──response──  Server
(connection closed)
```

HTTP is perfect for loading web pages, submitting forms, and calling APIs. But for **real-time chat**, it has problems:
- **Overhead:** Each message requires a new TCP connection (handshake, headers, etc.)
- **No server push:** The server can only respond to requests — it can't proactively send data
- **Polling wasteful:** To simulate real-time updates, the browser must repeatedly ask "anything new?" (polling)

### WebSockets: Persistent Bidirectional Communication

**WebSockets** solve these problems by establishing a persistent, full-duplex connection:

```
Browser  ──handshake──►  Server    (one-time HTTP upgrade)
Browser  ◄═══════════►  Server    (persistent WebSocket connection)
         ◄── message ──           (either side can send at any time)
         ── message ──►
         ◄── message ──
         ◄── message ──           (server can send multiple without being asked)
```

Key characteristics:
- **Persistent:** One connection for the entire session (no repeated handshakes)
- **Bidirectional:** Both client and server can send messages independently
- **Low latency:** Messages are sent immediately, no connection setup overhead
- **Stateful:** The server can maintain state (shopping cart, chat history) tied to the connection

### Why WebSockets for This Chat App?

The Zava chat application needs real-time, stateful communication because:

1. **Agent responses take time.** The server needs to classify intent, call an agent, possibly execute tools, and return results. WebSockets allow streaming intermediate messages ("Analyzing your image...") while processing continues.

2. **Server-initiated messages.** The customer loyalty agent runs in the background. When it completes, the server pushes the loyalty discount to the client without the client asking.

3. **Session state.** The shopping cart, discount tier, and conversation history persist for the entire WebSocket connection. No need for database-backed sessions or cookies.

4. **Multiple messages per interaction.** A single user message might trigger multiple server responses (an "analyzing..." message, the main response, and a loyalty notification).

### FastAPI: The Web Framework

**FastAPI** is a modern Python web framework that natively supports both HTTP and WebSocket endpoints. Key features used in this project:

- **`@app.get("/")`** — HTTP endpoint that serves the chat HTML page
- **`@app.get("/health")`** — HTTP health check for Azure App Service monitoring
- **`@app.websocket("/ws")`** — WebSocket endpoint for real-time chat
- **`app.mount("/mcp-inventory/", ...)`** — Mount the MCP server as a sub-application

FastAPI is built on **Starlette** (for web handling) and uses **Pydantic** (for data validation). It's one of the fastest Python web frameworks available, capable of handling thousands of concurrent connections.

### ASGI and Uvicorn

**ASGI (Asynchronous Server Gateway Interface)** is the protocol that connects the web server to the Python application. **Uvicorn** is the ASGI server — it handles TCP connections, TLS encryption, and HTTP/WebSocket protocols, while FastAPI handles routing and business logic.

```
Internet → Uvicorn (network layer) → FastAPI (application layer) → Your code
```

The `async` keyword in the WebSocket handler is crucial — it allows the server to handle many concurrent WebSocket connections without blocking. While one connection waits for an agent response, others can be processing messages simultaneously.

### Session State Management

Each WebSocket connection in the Zava app maintains independent session state:

```python
# These variables exist for ONE user's connection
chat_history = deque(maxlen=5)        # Window of recent conversation
persistent_cart = []                   # Shopping cart contents
session_discount_percentage = ""       # Loyalty discount
image_cache = {}                       # Cached image descriptions
raw_io_history = deque(maxlen=100)     # Full request/response log
```

When the connection closes (user navigates away, network drops), all state is lost. For a more persistent experience, you'd store state in a database — but for this workshop application, in-memory state is sufficient.

### In the Zava Project: The WebSocket Handler

**Three endpoints** (`src/chat_app.py`):

```python
app = FastAPI()

# Mount MCP server as a sub-application
inventory_mcp_app = inventory_mcp.sse_app()
app.mount("/mcp-inventory/", inventory_mcp_app)

# HTTP: Serve the chat page
@app.get("/")
async def get():
    with open('chat.html', "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# HTTP: Health check for Azure App Service monitoring
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

# WebSocket: Real-time chat
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # ... session state and message loop ...
```

**Session state** (created fresh per connection):

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Per-session state — lives for the duration of this WebSocket connection
    chat_history: Deque[Tuple[str, str]] = deque(maxlen=5)  # Last 5 turns
    customer_loyalty_executed = False    # Only run loyalty check once
    session_discount_percentage = ""     # Persists across all messages
    persistent_image_url = ""            # Last uploaded image
    persistent_cart = []                 # Shopping cart state
    image_cache = {}                     # Avoid re-analyzing images
    bad_prompts = set()                  # Track rejected prompts
    raw_io_history = deque(maxlen=100)   # Full I/O log for cart manager
```

**Message loop** (receive → process → respond):

```python
    while True:
        # 1. Receive JSON from browser
        data = await websocket.receive_text()
        parsed = orjson.loads(data)       # Fast JSON parsing
        user_message = parsed.get("message", "")
        image_url = parsed.get("image_url", "")
        conversation_history = parsed.get("conversation_history", "")

        # 2. Classify intent → pick agent
        intent_result = handoff_service.classify_intent(user_message, session_id, formatted_history)
        agent_name = intent_result["agent_id"]

        # 3. Execute agent (context enrichment + agent call + response parsing)
        # ... (see TUTORIAL.md for full details)

        # 4. Send response back to browser
        response_json = fast_json_dumps({**parsed_response, "cart": persistent_cart})
        await websocket.send_text(response_json)
```

**Background loyalty task** (runs once, sends result later):

```python
    # Fire-and-forget at session start
    if not customer_loyalty_executed:
        asyncio.create_task(run_customer_loyalty_task(customer_id))
        customer_loyalty_executed = True
```

**The frontend WebSocket client** (`src/chat.html`):

```javascript
// Auto-detect protocol (ws for http, wss for https)
var ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
var ws = new WebSocket(ws_scheme + "://" + window.location.host + "/ws");

// Receive messages from server
ws.onmessage = function(event) {
    var data = JSON.parse(event.data);
    var answer = data.answer || event.data;
    var agent = data.agent || 'Bot';
    addMessage(agent, answer);             // Display in chat UI
    addDebugEntry('incoming', 'Server Response', data);  // Show raw JSON
};

// Send messages to server
function sendMessage() {
    var payload = {
        conversation_history: formatConversationHistory(),
        has_image: hasImage,
        customer_id: "CUST001",
        message: message
    };
    if (hasImage) payload.image_url = imageUrlInput.value;
    ws.send(JSON.stringify(payload));
}
```

---

## Chapter 11: Multimodal AI — Processing Text and Images Together

### What Is Multimodal AI?

**Multimodal AI** refers to models that can process multiple types of input — typically text and images, but potentially also audio, video, and structured data. GPT-4o is a multimodal model: you can send it both text and images in a single request, and it will reason about them together.

### How Image Understanding Works in This Project

The Zava app uses a **two-stage pipeline** for image processing:

**Stage 1: Image Analysis (Vision Model)**

When a user provides an image URL, the app sends it to a GPT model with vision capabilities:

```python
chat_prompt = [
    {"role": "system", "content": "You are a helpful assistant that summarizes image content."},
    {"role": "user", "content": image_url}
]
description = client.chat.completions.create(model=deployment, messages=chat_prompt)
```

The model returns a textual description: "A modern living room with blue walls, a white sofa, and hardwood floors."

**Stage 2: Context Enrichment**

This text description is then appended to the user's message before sending it to the agent:

```
User message: "What paint would match this room?"
+ Image description: "A modern living room with blue walls, white sofa, hardwood floors"
= Enriched context for the agent
```

The agent (Cora or Interior Designer) now knows what the image looks like and can make relevant recommendations.

### Caching Image Descriptions

Analyzing an image takes time and costs tokens. If the user sends multiple messages about the same image, re-analyzing it would be wasteful. The app caches descriptions:

```python
image_cache = {}  # Key: image URL, Value: text description
```

The first time an image URL appears, it's analyzed and cached. Subsequent references use the cached description instantly.

### Pre-Fetching

The app also **pre-fetches** image descriptions asynchronously. When a user uploads an image URL, the analysis starts immediately in the background — even before the user sends their actual question. By the time the question arrives, the description is often already cached.

### In the Zava Project: Vision Analysis & Context Enrichment

**Image analysis** (`src/app/tools/understandImage.py`):

```python
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint=os.getenv("gpt_endpoint"),
    api_key=os.getenv("gpt_api_key"),
    api_version=os.getenv("gpt_api_version"),
)

def get_image_description(image_url):
    """Send an image URL to GPT vision model, get a text description back."""
    chat_prompt = [
        {
            "role": "system",
            "content": [{"type": "text",
                         "text": "You are a helpful assistant that summarizes image content. Respond in Markdown."}]
        },
        {"role": "user", "content": image_url}
    ]
    completion = client.chat.completions.create(
        model=deployment,
        messages=chat_prompt,
        max_completion_tokens=10000
    )
    return completion.choices[0].message.content
```

**Caching with pre-fetch** (`src/chat_app.py`):

```python
async def get_cached_image_description(image_url: str, image_cache: dict) -> str:
    """Get image description with caching."""
    if image_url in image_cache:
        return image_cache[image_url]   # Cache hit — instant return

    loop = asyncio.get_event_loop()
    description = await loop.run_in_executor(thread_pool, get_image_description, image_url)
    image_cache[image_url] = description  # Store for future requests
    return description

async def pre_fetch_image_description(image_url: str, image_cache: dict):
    """Start analysis immediately when image URL is received."""
    if image_url and image_url not in image_cache:
        loop = asyncio.get_event_loop()
        description = await loop.run_in_executor(thread_pool, get_image_description, image_url)
        image_cache[image_url] = description
```

**Product search with Cosmos DB vector search** (`src/app/tools/aiSearchTools.py`):

```python
from azure.cosmos import CosmosClient

def product_recommendations(question: str, top_k: int = 8):
    # 1. Generate embedding for the user's query
    query_vector = get_request_embedding(question)

    # 2. Run Cosmos DB vector search (finds products semantically similar to the query)
    query = (
        "SELECT c.id, c.ProductID, c.ProductName, c.ProductCategory, "
        "c.ProductDescription, c.ImageURL, c.Price "
        "FROM c "
        "ORDER BY VECTORDISTANCE(c.request_vector, @vector) "
    )
    results = list(_container.query_items(
        query=query,
        parameters=[{"name": "@vector", "value": query_vector}],
        max_item_count=top_k
    ))
    return results
```

**Context enrichment pipeline** (`src/chat_app.py`):

```python
# Build enriched message with all available context
enriched_message = user_message
if image_data:
    enriched_message += f"\n\nImage description: {image_data}"
if products:
    enriched_message += f"\nAvailable products: {products}"
```

---

## Chapter 12: Putting It All Together — The Zava Architecture

### The Complete Request Flow

Here's what happens when a user types "Show me blue paint options" with an image of their kitchen attached:

```
1. BROWSER → WebSocket sends JSON:
   {message: "Show me blue paint options", image_url: "https://...kitchen.jpg"}

2. CHAT_APP.PY → Parses the message
   → Pre-fetches image description (async)

3. HANDOFF SERVICE → Classifies intent
   → Sends to handoff-service agent in Foundry
   → Returns: {domain: "cora", confidence: 0.85}

4. CONTEXT ENRICHMENT
   → Gets cached image description: "A modern kitchen with white cabinets and beige walls"
   → Searches Cosmos DB for blue paint products (vector search)
   → Builds enriched message with user text + image description + product data

5. AGENT PROCESSOR → Sends enriched message to Cora agent in Foundry
   → Cora decides to call mcp_product_recommendations
   → AgentProcessor intercepts, calls MCP Client
   → MCP Client calls MCP Server's get_product_recommendations
   → MCP Server queries Cosmos DB with vector search
   → Results flow back through the chain
   → Cora generates final response with product recommendations

6. RESPONSE PROCESSING
   → Parses Cora's JSON response
   → Adds session discount percentage
   → Updates conversation history

7. BROWSER ← WebSocket receives:
   {answer: "Here are some blue paint options...", products: [...], agent: "cora"}
```

### What Each File Does

| File | Role | When It Runs |
|------|------|-------------|
| `agent_initializer.py` | Factory function to create agents in Foundry | Once (deployment) |
| `*Agent_initializer.py` | Configures a specific agent and pushes to Foundry | Once (deployment) |
| `agent_processor.py` | Manages agent conversations and tool execution | Every message |
| `agent_service.py` | Caches AgentProcessor instances | Every message |
| `handoff_service.py` | Classifies intent and routes to agents | Every message |
| `chat_app.py` | Main FastAPI app, WebSocket handler, orchestration | Always running |
| `chat.html` | Frontend UI with WebSocket client | In browser |
| `mcp_inventory_server.py` | MCP server exposing tools | Always running |
| `mcp_inventory_client.py` | MCP client connecting to server | When tools are called |
| `aiSearchTools.py` | Cosmos DB vector search for products | When products searched |
| `imageCreationTool.py` | DALL-E image generation + Blob upload | When images created |
| `understandImage.py` | GPT vision model for image analysis | When images uploaded |
| `discountLogic.py` | Customer discount calculation | When loyalty checked |
| `inventoryCheck.py` | Simulated inventory data | When stock checked |
| `Dockerfile` | Container image definition | At build time |

### Design Principles Observed

Looking at the project as a whole, several software engineering principles emerge:

1. **Separation of Concerns.** Each file has one job. Prompts are in `.txt` files, tools are in the `tools/` directory, agents are in `agents/`, services are in `services/`.

2. **Factory Pattern.** `initialize_agent()` creates any agent. `create_function_tool_for_agent()` creates any tool set. `get_or_create_agent_processor()` creates any processor.

3. **Caching Everywhere.** Image descriptions, tool configurations, AgentProcessor instances, and MCP client connections are all cached to reduce latency and cost.

4. **Graceful Degradation.** If the Handoff Service fails, it falls back to the current domain. If image analysis fails, the conversation continues without image context. If a tool call fails, the error is caught and a user-friendly message is shown.

5. **Async by Default.** The WebSocket handler, image processing, loyalty checks, and agent execution are all async, allowing concurrent handling of multiple users.

---

## Glossary

| Term | Definition |
|------|-----------|
| **Agent** | An LLM wrapped with instructions, tools, and memory that can take actions and maintain state |
| **AI Foundry** | Microsoft's cloud platform (formerly Azure AI Studio) for deploying and managing AI agents |
| **ASGI** | Asynchronous Server Gateway Interface — the protocol that Uvicorn/FastAPI use for async web serving |
| **Azure Container Registry (ACR)** | A private Docker registry in Azure for storing container images |
| **Completion** | A single API call to an LLM: input (prompt) → output (generated text) |
| **Constrained Decoding** | A technique that restricts an LLM's token generation to produce valid structured output |
| **Context Enrichment** | The process of adding image descriptions, product data, and history to a user's message before sending it to an agent |
| **Context Window** | The maximum number of tokens an LLM can process in a single request |
| **Conversation Thread** | A persistent sequence of messages between a user and an agent, maintaining context across turns |
| **DefaultAzureCredential** | An Azure Identity class that automatically tries multiple authentication methods (managed identity, CLI, environment variables) |
| **Docker Container** | A running instance of a Docker image |
| **Docker Image** | A read-only blueprint containing an application and all of its dependencies |
| **Dockerfile** | A text file containing instructions for building a Docker image |
| **FastAPI** | A modern Python web framework for building APIs with automatic documentation and async support |
| **Function Calling** | An LLM capability where the model generates structured requests to call external functions |
| **FunctionTool** | An Azure AI SDK class that defines a callable function's name, description, and parameter schema |
| **Handoff** | The process of routing a user's message from one agent to another based on intent classification |
| **In-Context Learning** | An LLM's ability to learn patterns from examples provided in the prompt (without retraining) |
| **Intent Classification** | Analyzing a user's message to determine which domain/agent should handle it |
| **JSON Schema** | A standard for describing the structure of JSON data (field names, types, constraints) |
| **Layer (Docker)** | Each instruction in a Dockerfile creates a cached layer; unchanged layers are reused across builds |
| **LLM (Large Language Model)** | A neural network trained on text data that can understand and generate language (e.g., GPT-4o) |
| **MCP (Model Context Protocol)** | An open standard for connecting AI applications with external tools and data sources |
| **Managed Identity** | An Azure feature that gives services (like App Service) an identity for authenticating to other Azure services without passwords |
| **Multi-Agent System** | An architecture using multiple specialized agents, each handling a specific domain |
| **Multimodal** | Able to process multiple types of input (text, images, audio) |
| **Orchestration** | The process of coordinating multiple agents, deciding which one handles each request |
| **Prompt (System)** | Instructions given to an LLM that define its role, behavior, and output format |
| **Pydantic** | A Python library for data validation using type annotations; used to define structured output schemas |
| **SSE (Server-Sent Events)** | A protocol for servers to push data to clients over HTTP; used by MCP for tool communication |
| **Structured Output** | An LLM feature that guarantees the response conforms to a specific JSON schema |
| **Temperature** | A parameter controlling randomness in LLM output (0 = deterministic, 1 = creative) |
| **Token** | The basic unit of text that an LLM processes; roughly corresponds to a word or word-part |
| **Tool Use Loop** | The cycle of: model requests function call → code executes → result fed back → model generates final answer |
| **Uvicorn** | An ASGI web server that runs FastAPI applications |
| **Vector Search** | A database query technique that finds items similar to a query by comparing mathematical representations (embeddings) |
| **WebSocket** | A protocol for persistent, bi-directional communication between client and server |
