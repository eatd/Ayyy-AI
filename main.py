import asyncio
import json
import re
from typing import List, Dict, Any, cast, Optional

# Community-endorsed libraries
from pydantic import BaseSettings, Field
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# OpenAI library (v1.0.0+)
from openai import AsyncOpenAI, APIError
from openai.types.chat import (
    ChatCompletionToolParam,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
)

# Local project imports (assuming this script is in Ayyy-AI directory or Ayyy-AI is in PYTHONPATH)
from tools import initialize_tool_registry
from conversation_store import load_history, save_history

# Initialize Rich Console
console = Console()

class AppConfig(BaseSettings):
    base_url: str = Field(
        default="http://localhost:1234/v1",
        description="LLM API base URL",
        env="AYYY_BASE_URL",
    )
    api_key: str = Field(
        default="lm-studio-key",
        description="LLM API key (often optional for local LLMs)",
        env="AYYY_API_KEY",
    )
    model: str = Field(
        default="qwen2.5-vl-7b-instruct",
        description="LLM model identifier",
        env="AYYY_MODEL",
    )
    request_timeout: float = Field(
        default=120.0,
        description="API request timeout in seconds",
        env="AYYY_TIMEOUT",
    )
    history_file: str = Field(
        default="chat_history.json",
        description="Path to save conversation history",
        env="AYYY_HISTORY_FILE",
    )

class AgileToolExecutor:
    def __init__(self) -> None:
        self.registry = initialize_tool_registry()
        console.log(
            f"Tools loaded: [cyan]{', '.join(self.registry._tools.keys()) or 'none'}[/cyan]"
        )

    @property
    def tool_schemas(self) -> List[ChatCompletionToolParam]:
        """Get OpenAI-compatible tool schemas."""
        # The schema from ToolRegistry.get_lm_studio_schemas() should be compatible.
        return cast(List[ChatCompletionToolParam], self.registry.get_lm_studio_schemas())

    async def run_tool(self, tool_name: str, tool_args_json_str: str) -> Dict[str, Any]:
        """Execute a tool with JSON string arguments, returning a JSON-serializable dict."""
        console.log(f"Attempting tool: [bold magenta]{tool_name}[/bold magenta], Args: [yellow]{tool_args_json_str}[/yellow]")
        try:
            args = json.loads(tool_args_json_str)
            if not isinstance(args, dict): # Ensure args is a dict for **args unpacking
                raise ValueError("Tool arguments must be a JSON object (dictionary).")
            result = await self.registry.execute(tool_name, **args)
            # Tools should ideally return JSON-serializable results.
            # If a tool returns complex objects, they need a to_dict() or similar method,
            # or this part needs to handle serialization more robustly.
            return {"status": "success", "result": result}
        except json.JSONDecodeError as e:
            console.log(f"[Tool Error] Invalid JSON for {tool_name}: {e}", style="bold red")
            return {"status": "error", "message": f"Invalid JSON arguments: {str(e)}"}
        except Exception as e:
            console.log(f"[Tool Error] Execution failed for {tool_name}: {e}", style="bold red")
            return {"status": "error", "message": str(e)}

class ModernChatAssistant:
    def __init__(self, config: AppConfig):
        self.config = config
        self.client = AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.request_timeout,
        )
        self.tool_executor = AgileToolExecutor()
        self.messages: List[Dict[str, Any]] = load_history(config.history_file)
        if not self.messages:
            self.messages.append({
                "role": "system",
                "content": (
                    "You are a highly capable assistant. For complex requests, first create a step-by-step plan. "
                    "Output the plan as a JSON object in your response content if you decide a plan is needed, like this: "
                    '```json\n{"plan": [{"step_id": 1, "goal": "Describe the goal for this step", "tool_suggestion": "relevant_tool_name_or_null_if_none"}, ...]}\n```\n'
                    "Then, I will help you execute it. For simpler tasks, you can respond directly or use tools immediately. "
                    "You can use available tools to answer questions and solve problems."
                )
            })
            save_history(self.config.history_file, self.messages)
        
        # New state variables for planning
        self.global_objective: str | None = None
        self.current_plan: List[Dict[str, Any]] | None = None
        self.current_step_index: int = 0
        self.pending_error_info: Optional[Dict[str, Any]] = None # For handling tool errors

    def _save_history(self) -> None:
        save_history(self.config.history_file, self.messages)
        
        
    async def _get_llm_response(self, messages_override: List[Dict[str, Any]] | None = None) -> ChatCompletionMessage | None:
        tool_schemas = self.tool_executor.tool_schemas
        
        messages_to_send = messages_override if messages_override is not None else self.messages
        
        api_params: Dict[str, Any] = {
            "model": self.config.model,
            "messages": cast(List[ChatCompletionMessageParam], messages_to_send),
        }
        if tool_schemas:
            api_params["tools"] = tool_schemas
            api_params["tool_choice"] = "auto" # Let the LLM decide

        try:
            # console.print(f"DEBUG: Sending messages to LLM: {json.dumps(messages_to_send, indent=2)}", style="dim") # DEBUG
            response = await self.client.chat.completions.create(**api_params)
            return response.choices[0].message
        except APIError as e:
            console.print(f"[LLM API Error] Request failed: {e}", style="bold red")
            return None
        except Exception as e:
            console.print(f"[LLM Error] Unexpected issue: {e}", style="bold red")
            return None

    async def process_turn(self, user_input: str):
        self.messages.append({"role": "user", "content": user_input})
        self._save_history()
        self.global_objective = user_input
        
        # For a new user turn, always reset the plan.
        # pending_error_info is managed within the loop or cleared at the end of the turn.
        self.current_plan = None
        self.current_step_index = 0

        # Main loop for planning and execution
        while True:
            current_llm_messages_for_api_call = list(self.messages)
            was_handling_pending_error = False # Flag to know if this iteration was for error handling

            if self.pending_error_info:
                was_handling_pending_error = True
                err_info = self.pending_error_info
                tool_name_for_prompt = err_info['tool_name']
                error_handling_prompt = (
                    f"A previous tool call failed. Tool: '{err_info['tool_name']}', "
                    f"intended for step: '{err_info['step_goal']}' (part of overall objective: '{self.global_objective}'), "
                    f"failed with arguments: '{err_info['arguments']}' and error: '{err_info['error_message']}'.\n"
                    "How do you want to proceed with this specific step? You can:\n"
                    f"1. Try calling the tool '{tool_name_for_prompt}' again with different arguments.\n"
                    "2. Suggest a different tool for this step.\n"
                    "3. State that this step cannot be completed and explain why.\n"
                    "4. Propose a revised plan to achieve the overall objective, outputting the new plan in the required JSON format if you do so."
                )
                current_llm_messages_for_api_call.append({
                    "role": "system", "content": error_handling_prompt
                })
                console.print(Panel(error_handling_prompt, title="[bold red]Requesting LLM Guidance on Tool Error[/bold red]", expand=False))
                # We will clear pending_error_info if the LLM successfully handles it (new plan, successful tool call, or textual ack)

            elif self.current_plan and self.current_step_index < len(self.current_plan):
                current_step = self.current_plan[self.current_step_index]
                step_goal = current_step.get("goal", "No goal specified for this step.")
                console.print(Panel(
                    f"Executing Plan Step {self.current_step_index + 1}/{len(self.current_plan)}: [bold cyan]{step_goal}[/bold cyan]",
                    title="[blue]Plan Progress[/blue]", expand=False))
                current_llm_messages_for_api_call.append({
                    "role": "system",
                    "content": f"You are currently executing step {self.current_step_index + 1} of your plan: '{step_goal}'. "
                               f"The overall objective is: '{self.global_objective}'. "
                               "Decide if a tool is needed for this specific step or if you can answer directly. "
                               "If using a tool, provide the precise tool call. If not, provide the answer for this step."})
            elif self.current_plan and self.current_step_index >= len(self.current_plan):
                console.print("[bold green]Plan execution fully complete.[/bold green]")
                self.pending_error_info = None # Plan complete, clear any error resolved to get here.
                break
            else: # No plan yet
                console.print("[bold blue]No active plan. LLM will decide on action (generate plan, use tool, or respond).[/bold blue]")

            llm_response_message = await self._get_llm_response(messages_override=current_llm_messages_for_api_call)

            if llm_response_message is None:
                if self.messages and self.messages[-1]["role"] == "user":
                    self.messages.pop()
                console.print("[bold red]LLM response failed. Ending turn.[/bold red]")
                break
            
            assistant_message_for_history: Dict[str, Any] = {
                "role": "assistant", "content": llm_response_message.content or ""}
            
            new_plan_adopted_this_iteration = False
            if llm_response_message.content:
                try:
                    content_str = llm_response_message.content
                    match = re.search(r"```json\s*(\{.*?\})\s*```", content_str, re.DOTALL)
                    plan_json_str = None
                    if match: plan_json_str = match.group(1)
                    elif content_str.strip().startswith("{") and content_str.strip().endswith("}"): plan_json_str = content_str.strip()

                    if plan_json_str:
                        parsed_content = json.loads(plan_json_str)
                        if isinstance(parsed_content, dict) and "plan" in parsed_content and isinstance(parsed_content["plan"], list):
                            # Clean and deduplicate plan steps
                            seen = set()
                            cleaned_plan = []
                            for step in parsed_content["plan"]:
                                if not isinstance(step, dict) or "goal" not in step:
                                    continue
                                key = (step.get("step_id"), step["goal"])
                                if key in seen:
                                    continue
                                seen.add(key)
                                cleaned_plan.append(step)
                            is_valid_plan = bool(cleaned_plan)
                            if is_valid_plan:
                                # Show the adopted plan in full, as JSON, for user transparency
                                console.print(Panel(
                                    json.dumps({"plan": cleaned_plan}, indent=2),
                                    title="[bold blue]New/Revised Plan Received and Adopted[/bold blue]",
                                    expand=False
                                ))
                                self.current_plan = cleaned_plan
                                self.current_step_index = 0
                                self.pending_error_info = None
                                new_plan_adopted_this_iteration = True
                                assistant_message_for_history["content"] = "Okay, I have a new plan. I will now proceed with its execution."
                                assistant_message_for_history.pop("tool_calls", None)
                                llm_response_message.tool_calls = None
                            elif not parsed_content["plan"]:
                                console.print("[Plan Parsing] LLM proposed an empty plan.", style="yellow")
                            else:
                                console.print("[Plan Parsing] LLM proposed a plan, but it has an invalid structure.", style="yellow")
                except json.JSONDecodeError: pass
                except Exception as e: console.print(f"[Plan Parsing Error during adoption] {e}", style="bold red")

            if llm_response_message.tool_calls:
                assistant_message_for_history["tool_calls"] = [
                    {"id": tc.id, "function": {"name": tc.function.name, "arguments": tc.function.arguments}, "type": "function"}
                    for tc in llm_response_message.tool_calls]
            
            self.messages.append(assistant_message_for_history)
            self._save_history()
            if assistant_message_for_history["content"]:
                 console.print(f"[Assistant Response] {assistant_message_for_history['content']}", style="bold green")

            if llm_response_message.tool_calls:
                console.print("[bold yellow]Tool Calls Detected:[/bold yellow]")
                tool_message_batch_for_history: List[Dict[str, Any]] = []
                all_tool_calls_successful_this_round = True
                
                for tool_call in llm_response_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args_json_str = tool_call.function.arguments
                    tool_call_id = tool_call.id
                    console.print(f"Processing tool call: [bold magenta]{tool_name}[/bold magenta] (ID: {tool_call_id}) Args: {tool_args_json_str}", style="cyan")
                    tool_output_dict = await self.tool_executor.run_tool(tool_name, tool_args_json_str)
                    
                    tool_content_for_history: str
                    if tool_output_dict.get("status") == "error":
                        error_msg = tool_output_dict['message']
                        console.print(f"[Tool Error] {tool_name} failed: {error_msg}", style="bold red")
                        tool_content_for_history = f"Error: {error_msg}"
                        all_tool_calls_successful_this_round = False
                        
                        current_step_goal = "N/A"
                        if self.current_plan and self.current_step_index < len(self.current_plan): # If error in a plan step
                            current_step_goal = self.current_plan[self.current_step_index].get("goal", "Goal not specified")
                        elif was_handling_pending_error and self.pending_error_info : # If error happened during error recovery
                             current_step_goal = self.pending_error_info.get("step_goal", "N/A during error recovery")
                        
                        self.pending_error_info = { # Set/overwrite pending error
                            "tool_name": tool_name, "step_goal": current_step_goal,
                            "error_message": error_msg, "arguments": tool_args_json_str}
                        tool_message_batch_for_history.append({ # Add failed tool's result
                            "role": "tool", "tool_call_id": tool_call_id, "content": tool_content_for_history})
                        break # Break from processing further tools in this batch
                    else: # Tool success
                        if was_handling_pending_error: # Tool called to recover from error succeeded
                            self.pending_error_info = None # Clear the error that was being handled.
                        console.print(f"[Tool Output] {tool_name} (ID: {tool_call_id}): {json.dumps(tool_output_dict)}", style="bold green")
                        tool_content_for_history = json.dumps(tool_output_dict)
                
                    tool_message_batch_for_history.append({
                        "role": "tool", "tool_call_id": tool_call_id, "content": tool_content_for_history})
                
                self.messages.extend(tool_message_batch_for_history)
                self._save_history()

                if not all_tool_calls_successful_this_round and self.pending_error_info:
                    console.print("[bold red]Tool call failed. Will ask LLM for guidance in the next iteration.[/bold red]")
                    continue

                if all_tool_calls_successful_this_round:
                    self.pending_error_info = None # All tools in this round were successful.
                    if self.current_plan:
                        self.current_step_index += 1
                        if self.current_step_index >= len(self.current_plan):
                            console.print("[bold green]Plan execution complete after successful tool calls.[/bold green]")
                            break
                        else:
                            console.print(f"[bold blue]Moving to plan step {self.current_step_index + 1}...[/bold blue]")
                            continue
                    else: # Successful tools, but not part of a plan. Loop for LLM to process results.
                        continue
            else: # No tool calls made by the assistant in this round (i.e., textual response)
                if was_handling_pending_error and not new_plan_adopted_this_iteration:
                    # LLM responded textually to an error prompt, and didn't make a new plan.
                    # Assume the textual response is the resolution or statement it can't be resolved.
                    self.pending_error_info = None
                    console.print("[bold yellow]LLM provided a textual response to the error. Assuming error handled or cannot be resolved.[/bold yellow]")
                    if self.current_plan: # If the error was related to a plan step, advance it.
                         console.print(f"[bold blue]Advancing plan step {self.current_step_index + 1} after textual error resolution.[/bold blue]")
                         self.current_step_index +=1

                if self.current_plan:
                    if not new_plan_adopted_this_iteration and not (was_handling_pending_error and self.current_step_index < len(self.current_plan)):
                        # If not a new plan, and not an error being textually resolved for a plan step (that's handled above by advancing)
                        # then it's a normal textual response for a plan step.
                        console.print(f"[bold blue]Plan step {self.current_step_index + 1} considered handled by LLM's textual response or no tool needed.[/bold blue]")
                        self.current_step_index += 1
                    
                    if self.current_step_index >= len(self.current_plan):
                        console.print("[bold green]Plan execution complete (textual response).[/bold green]")
                        self.pending_error_info = None # Plan complete
                        break
                    else:
                        # If a new plan was just adopted, current_step_index is 0.
                        # Or if an error was handled textually and step advanced.
                        # Or if a normal step was handled textually and step advanced.
                        console.print(f"[bold blue]Proceeding with plan (next step: {self.current_step_index + 1})...[/bold blue]")
                        continue
                else: # No plan, no tools, simple turn is complete.
                    self.pending_error_info = None # Turn complete
                    break
        
        self.global_objective = None
        self.pending_error_info = None # Final cleanup at the end of the entire turn processing.
        self._save_history()

    async def run_interactive_session(self):
        console.print(Panel(
            Text(f"🚀 Ayyy-AI Assistant 🚀\nModel: {self.config.model}\nTools: {', '.join(self.tool_executor.registry._tools.keys()) or 'None'}", justify="center"),
            title="[bold blue]Chat Session Started[/bold blue]",
            expand=False
        ))
        console.print("Type your query or 'quit' to exit.")

        while True:
            try:
                # Using asyncio.to_thread for synchronous input in async context
                user_text = await asyncio.to_thread(console.input, "[bold cyan]You: [/bold cyan]")
                user_text_cleaned = user_text.strip()

                if not user_text_cleaned:
                    continue
                if user_text_cleaned.lower() == "quit":
                    console.print("Assistant: Goodbye! Session ended.", style="bold blue")
                    break
                
                await self.process_turn(user_text_cleaned)

            except KeyboardInterrupt:
                console.print("\nAssistant: Exiting due to user interrupt (Ctrl+C)...", style="bold yellow")
                break
            except Exception as e:
                console.print(f"[Critical Loop Error] An unexpected error occurred: {e}", style="bold red")
                console.print("You might need to restart the assistant.", style="yellow")
                # Depending on severity, might break or try to recover
                break

async def main_async():
    try:
        app_config = AppConfig() # Pydantic will load from ENV or use defaults
        # console.print(Panel(app_config.model_dump_json(indent=2), title="[bold green]Configuration[/bold green]"))
    except Exception as e: # Catch Pydantic validation errors if any
        console.print(f"[Config Error] Could not load configuration: {e}", style="bold red")
        return

    assistant = ModernChatAssistant(config=app_config)
    await assistant.run_interactive_session()

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        console.print("\nApplication terminated by user.", style="bold yellow")
    except Exception as e:
        console.print(f"\n[Unhandled Main Error] Application crashed: {e}", style="bold red")
