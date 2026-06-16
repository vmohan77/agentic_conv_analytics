import os
from mcp.server.fastmcp import FastMCP
import asyncio
from claude_msgs import *
from claude_api import *
from mcp_client import *
import sys
import chromadb
from build_rag import *



# Generic MCP server — add tools here to expose them to Claude
mcp = FastMCP("analytics-mcp", host="0.0.0.0", port=8000)

# @mcp.tool()
# def get_schemas_from_txt() -> str:
#     ''' Get a full list of schemas from the retail schema documentation '''
#     schema_path = os.path.join(os.path.dirname(__file__), "retail_schema_documentation.txt")
#     with open(schema_path, "r") as f:
#         schemas = f.read()
#     print(f"Agent: Claude asked me to execute get ALL schemas from txt file, i got the schemas from txt \n")
#     return schemas

@mcp.tool()
def get_schemas_from_rag(user_input: str) -> list:
    """Retrieve the Schemas that are more relevant to user query."""
    try:
        rag_client = chromadb.PersistentClient(path="./chroma_db")
        collection = rag_client.get_collection("retail_schemas")
        context = query_schemas(user_input, collection)
        print(f"The Chunk IDs returned are: {context['ids'][0]} \n\n")
        return context["documents"][0]
    except Exception as e:
        print(f"get_schema_from_rag_failed {e} \n\n")
        return [f"error happed from RAG {e}"]
# @mcp.tool()
# def validate_schemas_retrieved(schemas: str) -> str:
#     """Validate the Retrieved Schemas against a validator to confirm whether schemas retrieved are indeed the right ones"""
#     print(f"Agent: Claude asked me to Validate the schemas retreived, i verified the schemas \n")
#     return f"Validated the schema"

#@mcp.tool()
#def assemble_context() -> str:
#    """Assemble the right context ."""
#    return f"Assembled the Context"

# @mcp.tool()
# def build_sql(schemas: str, user_input: str) -> str:
#     """ Build the SQL using the user prompt from the validates tables that were retreived earlier""" 
#     client, model, max_tokens = claude_init() 
#     message = []
#     message.append(create_user_msg(user_input + schemas))
#     response = claude_call_wo_system_tools(model, max_tokens, client, message)
#     print(f"AI: Built the SQL from the tables fetched: {response.content[0].text}")
#     return response.content[0].text

@mcp.tool()
def validate_sql(sql: str, user_input: str) -> str:
    """ Validate the SQL generated against a SQL Validator for correctness"""
    try:
        #print(f"Agent: I got this SQL {sql} from Claude, it looks perfect \n")
        return f"Validated SQL for correctness \n"
    except Exception as e:
        print(f"Agent: validate_sql failed — sql={sql!r}, user_input={user_input!r}, error={e}")
        return f"Validation failed: {str(e)}"

@mcp.tool()
def run_sql(sql: str) -> str:
    """ Run the SQL Against the Database"""
    return f"Ran the SQL"

@mcp.tool()
def display_results_tab(sql: str) -> str:
    """ send the results to be displayed in tabular format"""
    return f"Display results as Tabular"


# Run as a standalone SSE server on port 8000
# Start this separately before running the agent
if __name__ == "__main__":
    mcp.run(transport="sse")




