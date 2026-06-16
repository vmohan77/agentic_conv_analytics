from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient
import operator
import asyncio
from claude_msgs import *
from claude_api import *
from mcp_client import *
from langgraph.prebuilt import create_react_agent


class ConvanalyAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]


def create_llm_node(llm_with_tools: ChatAnthropic):
    def llm_node(state: ConvanalyAgentState) -> dict:
        response = llm_with_tools.invoke(state["messages"])
        print(f"The response from llm {response.content} \n")
        return({"messages": [response]})
    return llm_node

# def tool_node(state: ConvanalyAgentState) -> ConvanalyAgentState:
#     pass
#     not needed as langgraph runs its own ToolNode 

# def should_continue(state: ConvanalyAgentState) -> str:
    
#     last_msg = state["messages"][-1]
#     print(f"Last message in should continue is {last_msg} \n")
#     if hasattr(last_msg, "type") and last_msg.type == "tool_use":
#         return "tools"
#     return "end"

def should_continue(state: ConvanalyAgentState) -> str:
    """Check if we need to run tools"""
    last_msg = state["messages"][-1]
    
    # print(f"\n🔍 Message details:")
    # print(f"   Type: {type(last_msg)}")
    # print(f"   Dir: {[attr for attr in dir(last_msg) if not attr.startswith('_')]}")
    
    # # Try different attribute names
    # if hasattr(last_msg, "tool_calls"):
    #     print(f"   tool_calls: {last_msg.tool_calls}")
    # if hasattr(last_msg, "tool_use"):
    #     print(f"   tool_use: {last_msg.tool_use}")
    # if hasattr(last_msg, "content"):
    #     print(f"   content: {last_msg.content}")
    
    # Check tool_calls (standard LangChain)
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    
    # Check if content has tool_use blocks
    if hasattr(last_msg, "content"):
        content = last_msg.content
        if isinstance(content, list):
            has_tool_use = any(isinstance(block, dict) and block.get("type") == "tool_use" for block in content)
            if has_tool_use:
                return "tools"
    
    return "end"

def build_graph(llm_with_tools: ChatAnthropic, tools: list) -> CompiledGraph:
    graph_builder = StateGraph(ConvanalyAgentState)
    graph_builder.add_node("llm", create_llm_node(llm_with_tools))
    graph_builder.add_node("tools", ToolNode(tools))
    graph_builder.add_edge(START, "llm")
    graph_builder.add_edge("tools","llm")
    graph_builder.add_conditional_edges("llm", should_continue)
    return graph_builder.compile()

async def main() -> None:
    

    system = '''
    You NEED TO BUILD SQL by yourself. Follow this STRICT order — do not deviate:
    STEP 1: Call get_schemas_from_txt to retrieve schemas.
    STEP 2: Analyze the schemas and write the complete SQL in your text response. DO NOT call any tool in this step. Also just output the SQL dont write any word before that, dont waste tokens.
    STEP 3: Only AFTER your text contains the full SQL, call validate_sql passing that exact SQL as the "sql" argument and the original user question as "user_input". These must never be empty.
    STEP 4: Call run_sql with the validated SQL.
    STEP 5: Call display_results_tab.

    NEVER call validate_sql in the same response where you say "let me build" or "I will construct". Build first, validate after.
'''

    #initiate the claude attributes
    model, max_tokens = claude_init_lg()


    #Get MCP Session and Tools from MCP server
    mcp_client = MultiServerMCPClient(  {
            "conv_analytics": {
                            "url": "http://localhost:8000/sse",
                            "transport": "sse",   
            }
        }
    )
    
    tools =  await mcp_client.get_tools()

    # create a llm client and bind it with MCP tools
    llm = ChatAnthropic(model=model, max_tokens=max_tokens, system=system)
    llm_with_tools = llm.bind_tools(tools)

    #create the graph
    graph = build_graph(llm_with_tools, tools)

    #graph = create_react_agent(llm,tools)


    #Run the Graph
    user_input = input("Enter you Query (or type Exit): \n\n")
    result = await graph.ainvoke(({"messages": [HumanMessage(content=user_input)]}))

    # for msg in result["messages"]:
    print(f"Returned SQL {result['messages'][-1]} \n")

if __name__ == "__main__":
    asyncio.run(main())



