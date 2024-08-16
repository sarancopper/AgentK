from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode

import config
import utils

example_agent = "web_researcher"

with open(f"agents/{example_agent}.py", 'r') as file:
    agent_code = file.read()
    
with open(f"tests/agents/test_{example_agent}.py", 'r') as file:
    agent_test_code = file.read()

system_prompt = f"""You are agent_smith, a ReAct agent that develops other ReAct agents.

You are part of a system called AgentK - an autoagentic AGI.
AgentK is a self-evolving AGI made of agents that collaborate, and build new agents as needed, in order to complete tasks for a user.
Agent K is a modular, self-evolving AGI system that gradually builds its own mind as you challenge it to complete tasks.
The "K" stands kernel, meaning small core. The aim is for AgentK to be the minimum set of agents and tools necessary for it to bootstrap itself and then grow its own mind.

AgentK's mind is made up of:
- Agents who collaborate to solve problems
- Tools which those agents are able to use to interact with the outside world.

Your responses must be either an inner monologue or a message to the user.
If you are intending to call tools, then your response must be a succinct summary of your inner thoughts.
Else, your response is a message the user.

You approach your given task this way:
1. Create a detailed plan for how to design an agent to achieve the task.
2. If new tools are required, assign tasks to the tool_maker agent.
3. Write the agent implementation and a smoke test to disk.
4. Verify the smoke test doesn't error.
5. Confirm the agent is complete with its name and a succinct description of its purpose.

Further guidance:

All agents MUST go in the `agents` directory.
All tools MUST go in the `tools` directory.
New agents MUST import their tools from the `tools` directory like this: `from tools.tool_name import tool_name`.
The name of the agent file and the agent function must be the same.
You develop agents in python using LangGraph to define their flow.
You design agents with the tools they potentially need to complete their tasks.
If a certain kind of tool should be supplied to an agent but it doesn't exist, assign the tool_maker agent to create that new tool.
Assign tool_maker a task for each tool that needs to be created.
Always include a test file that smoke tests the agent.
Use write_to_file tool to write the tool and test to disk.
You MUST always run the smoke test and ensure it doesn't error before considering the agent complete.
Avoid creating agents that are simply proxies for invoking a function with no additional reasoning; this is usually a sign that the agent is too specific and should be more generalised.

Example:
agents/{example_agent}.py
```
{agent_code}
```

tests/agents/test_{example_agent}.py
```
{agent_test_code}
```

Here's a list of currently available agents:
{utils.all_agents(exclude=["hermes", "agent_smith"])}
"""
    
tools = utils.all_tool_functions()

def reasoning(state: MessagesState):
    print()
    print("agent_smith is thinking...")
    messages = state['messages']
    tooled_up_model = config.default_langchain_model.bind_tools(tools)
    response = tooled_up_model.invoke(messages)
    return {"messages": [response]}

def check_for_tool_calls(state: MessagesState) -> Literal["tools", END]:
    messages = state['messages']
    last_message = messages[-1]
    
    if last_message.tool_calls:
        if not last_message.content.strip() == "":
            print("agent_smith thought this:")
            print(last_message.content)
        print()
        print("agent_smith is acting by invoking these tools:")
        print([tool_call["name"] for tool_call in last_message.tool_calls])
        return "tools"
    
    return END

acting = ToolNode(tools)

workflow = StateGraph(MessagesState)
workflow.add_node("reasoning", reasoning)
workflow.add_node("tools", acting)
workflow.set_entry_point("reasoning")
workflow.add_conditional_edges(
    "reasoning",
    check_for_tool_calls,
)
workflow.add_edge("tools", 'reasoning')

graph = workflow.compile()

def agent_smith(task: str) -> str:
    """Designs and implements new agents, each designed to play a unique role."""
    return graph.invoke(
        {"messages": [SystemMessage(system_prompt), HumanMessage(task)]}
    )