#create claude formatted user message

def create_user_msg(user_message):
    user_msg = {
                "role": "user",
                "content": user_message
            }
    return user_msg

#create claude formatted assistant message

def create_claude_msg(message):
    claude_msg = {
            "role": "assistant",
            "content": message
        }
    return claude_msg