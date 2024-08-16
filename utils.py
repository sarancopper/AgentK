import sqlite3
import importlib.util
import sys
import string
import secrets
import traceback

from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
checkpointer = SqliteSaver(conn)

def all_tool_functions():
    tools = list_tools()
    tool_funcs = []
    
    for tool in tools:
        try:
            module = load_module(f"tools/{tool}.py")
            tool_func = getattr(module, tool)
            tool_funcs.append(tool_func)
        except Exception as e:
            print(f"WARN: Could not load tool \"{tool}\". {e.__class__.__name__}: {e}")
    
    return tool_funcs

def list_broken_tools():
    tools = list_tools()
    broken_tools = {}
    
    for tool in tools:
        try:
            module = load_module(f"tools/{tool}.py")
            getattr(module, tool)
            del sys.modules[module.__name__]
        except Exception as e:
            exception_trace = traceback.format_exc()
            broken_tools[tool] = [e, exception_trace]
    
    return broken_tools

def list_tools():
    """
    list all tools available in the tools directory

    :return: list of tools
    """
    import os
    tools = []
    for file in os.listdir("tools"):
        if file.endswith(".py"):
            tools.append(file[:-3])

    return tools

def all_agents(exclude=["hermes"]):
    agents = list_agents()
    agents = [agent for agent in agents if agent not in exclude]
    agent_funcs = {}
    
    for agent in agents:
        try:
            module = load_module(f"agents/{agent}.py")
            agent_func = getattr(module, agent)
            agent_funcs[agent] = agent_func.__doc__
            del sys.modules[module.__name__]
        except Exception as e:
            print(f"WARN: Could not load agent \"{agent}\". {e.__class__.__name__}: {e}")
    
    return agent_funcs

def list_broken_agents():
    agents = list_agents()
    broken_agents = {}
    
    for agent in agents:
        try:
            module = load_module(f"agents/{agent}.py")
            getattr(module, agent)
            del sys.modules[module.__name__]
        except Exception as e:
            exception_trace = traceback.format_exc()
            broken_agents[agent] = [e, exception_trace]
    
    return broken_agents

def list_agents():
    """
    list all agents available in the agents directory

    :return: list of agents
    """
    import os
    agents = []
    for file in os.listdir("agents"):
        if file.endswith(".py") and file != "__init__.py":
            agents.append(file[:-3])

    return agents

def gensym(length=32, prefix="gensym_"):
    """
    generates a fairly unique symbol, used to make a module name,
    used as a helper function for load_module

    :return: generated symbol
    """
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits
    symbol = "".join([secrets.choice(alphabet) for i in range(length)])

    return prefix + symbol

def load_module(source, module_name=None):
    """
    reads file source and loads it as a module

    :param source: file to load
    :param module_name: name of module to register in sys.modules
    :return: loaded module
    """

    if module_name is None:
        module_name = gensym()

    spec = importlib.util.spec_from_file_location(module_name, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module