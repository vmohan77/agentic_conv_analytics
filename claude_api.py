from anthropic import Anthropic
from dotenv import load_dotenv
import os


def claude_init():
    
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model = os.getenv("CLAUDE_MODEL")
    max_tokens = int(os.getenv("MAX_TOKENS"))
    client = Anthropic(api_key=api_key)

    return client, model, max_tokens

def claude_init_lg():
    
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model = os.getenv("CLAUDE_MODEL")
    max_tokens = int(os.getenv("MAX_TOKENS"))

    return model, max_tokens


def claude_call_with_tools_system(model, max_tokens, client, message, system, tools):
    
    #print(f"i am inside claude_call and message is {message}")
    
    claude_response  = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=message,
        system=system,
        tools=tools
    )
    return claude_response

def claude_call_wo_system_tools(model, max_tokens, client, message):
    
    #print(f"i am inside claude_call and message is {message}")
    
    claude_response  = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=message
    )
    return claude_response

def claude_check_tool_use(content: list) -> list:
    tool_uses = []
    #print(f"Entered Check Tool Usage requested by Claude \n")
    tool_uses = [b for b in content if b.type == "tool_use"]
    return tool_uses