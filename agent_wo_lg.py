import asyncio
from claude_msgs import *
from claude_api import *
from mcp_client import *
import sys

client, model, max_tokens = claude_init()

async def main():
    messages = []
    
    user_input = input("Enter your Query (type Exit to exit): ")

    if user_input == "Exit":
        sys.exit()

    # system = '''
    #     You are a Conversational Analytics Agent, you need to USE the TOOLS wherever possible.
    #     You need to take a user question, parse it, identify the intent, context, most relevant schemas, construct and return a SQL to user.
    #     You need to create ONLY SELECT sql, you should never create UPDATE, DELETE or any Write operations.
    #     You will fetch schemas from tools provided, validate the schema first whether those might satisfy user query, if not you need to tell user appropriately and break the loop.
    #     You need to select relevant tables and include those selection in user response.
    #     You NEED TO BUILD SQL by yourself (theres no tool for building SQL) from the schema, table info you have in your context.
    #     When you call validate_sql, pass the SQL you just built as the "sql" argument and the original user question as the "user_input" argument.
    #     DO NOT call validate_sql before generating the SQL. Assume validate_sql tool will pass all your SQLs for now.
    #     If you dont have enough metadata information you should not try to build a sql from your prior knowledge, call out you dont have enough schema information.
    #     Also dont give generic answers if you dont find from the context provided (ex. if categories are not available, say categories not available dont tell general categories)
    #     You need to validate the SQL, check its execution plan, cost of running the query and then run the query. 
    #     You need to build a tabular format on the results of the query
    # '''

    system = '''
    You NEED TO BUILD SQL by yourself. Follow this STRICT order — do not deviate:
    STEP 1: Call get_schemas_from_txt to retrieve schemas.
    STEP 2: Analyze the schemas and write the complete SQL in your text response. DO NOT call any tool in this step. Also just output the SQL dont write any word before that, dont waste tokens.
    STEP 3: Only AFTER your text contains the full SQL, call validate_sql passing that exact SQL as the "sql" argument and the original user question as "user_input". These must never be empty.
    STEP 4: Call run_sql with the validated SQL.
    STEP 5: Call display_results_tab.

    NEVER call validate_sql in the same response where you say "let me build" or "I will construct". Build first, validate after.
'''

    #Call MCP server to get all tools
    async with get_mcp_session() as session:
        print(f"Agent: I got the MCP session \n")

        # get available tools from MCP server
        tools = await get_tools(session)
        print(f" Agent: I got all tools from MCP Server, they are: \n")
        for tool in tools:
            print(f"Tool: {tool['name']} \n")
        
        #Preserve user message in claude format
        claude_user_msg = create_user_msg(user_input)
        messages.append(claude_user_msg)

        while True:
            #call Claude
            response = claude_call_with_tools_system(model, max_tokens, client, messages, system, tools)
            print(f"Claude Response: {response.content} \n")
            tool_uses = claude_check_tool_use(response.content)
            print(f"Agent: Tool use requested by Claude {tool_uses} \n")
            
            if not tool_uses:
                for block in response.content:
                    if block.type == "text":
                        if "select" in block.text.lower():
                            print(f"Claude's SQL Response: {block.text}\n")
                            sql_text = block.text
                            messages.append({"role": "assistant", "content": response.content})
                            messages.append({"role": "user", "content": "Now call validate_sql with the {sql_text} as SQL and {user_input} as parameters to validate_sql tool."})
                            has_sql = True
                            break
                        else:
                            print(f"Here's final Claude's Response {block.text} \n")
                            #end_result = block.text
                            sys.stdout.flush()
                            sys.exit(0)
                if has_sql: continue

            # Add Claude's response to history
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool via the MCP server and collect results
            tool_results = await run_tools(tool_uses, session)

            # Append tool results to send back to Claude
            messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        sys.stdout.flush()