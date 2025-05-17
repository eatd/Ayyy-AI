from typing import List, Dict, Any
from dataclasses import dataclass
from utils import get_logger
from openai import OpenAI

from tools.base import ToolRegistry
import json


logger = get_logger(__name__)

class ToolExecutor:
    """Bridge between LLM and tool implementations."""
    
    def __init__(self):
        self.registry = ToolRegistry()
        self._initialize_tools()
        
    def _initialize_tools(self) -> None:
        """Initialize tools from all modules."""
        from tools import create_registry
        self.registry = create_registry()
        
    @property
    def tool_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all tools in LM Studio format."""
        return self.registry.get_lm_studio_schemas()
        
    @property
    def tool_names(self) -> List[str]:
        """Get a list of all tool names."""
        return list(self.registry._tools.keys())
        
    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool function with the provided arguments."""
        try:
            result = await self.registry.execute(tool_name, **args)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {str(e)}")
            return {"status": "error", "message": str(e)}
    
@dataclass
class ChatConfig:
    """Configuration for chat client."""
    base_url: str = "http://localhost:1234/v1"
    api_key: str = "lm-studio"
    model: str = "qwen2.5-vl-7b-instruct"
    
    
    def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool function with the provided arguments."""
        tool_executor = ToolExecutor()
        return tool_executor.execute(tool_name, args)
    
    


class ChatAssistant:
    def __init__(self, config: ChatConfig):
        self.config = config
        self.client = OpenAI(base_url=self.config.base_url, api_key=self.config.api_key)
        self.model = self.config.model
        self.messages = []
        self.tool_executor = ToolExecutor()
        
    def _get_completion(self):
        return self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.tool_executor.tool_schemas,
            tool_choice="auto"
        )
        
    def _handle_response(self, response):
        if not response.choices:
            return

        choice = response.choices[0]
        message = choice.message
        
        # Add assistant message to history
        self.messages.append({
            "role": "assistant",
            "content": message.content or "",
            **({"tool_calls": message.tool_calls} if message.tool_calls else {})
        })
        
        # Print text response if available
        if message.content:
            print(f"Assistant: {message.content}")
            
        # Process tool calls if present
        if message.tool_calls:
            self._process_tool_calls(message.tool_calls)
            return self._get_completion()
            
        return None

    def _process_tool_calls(self, tool_calls):
        for tool_call in tool_calls:
            try:
                args = json.loads(tool_call.function.arguments)
                result = self.tool_executor.execute(tool_call.function.name, args)
                
                # Add tool response to message history
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
                
                print(f"[Tool {tool_call.function.name}]: executed")
            except json.JSONDecodeError:
                print("[Tool Error]: Invalid JSON arguments")
                
    def chat_loop(self):
        print("Assistant: Hi! I can help you read and edit text files.")
        
        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() == "quit":
                break

            self.messages.append({"role": "user", "content": user_input})
            
            try:
                response = self._get_completion()
                follow_up = self._handle_response(response)
                
                # Handle follow-up responses after tool execution
                while follow_up:
                    follow_up = self._handle_response(follow_up)
                    
            except Exception as e:
                print(f"Error: {str(e)}")
                
def main():
    config = ChatConfig()
    assistant = ChatAssistant(config)
    
    print("Welcome to the File Assistant!")
    print("You can ask me to read or write files. Type 'quit' to exit.")
    
    assistant.chat_loop()
    
if __name__ == "__main__":
    main()
    
    