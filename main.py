import asyncio
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any, cast, Optional

# Community-endorsed libraries
from pydantic import BaseSettings, Field
import yaml
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

# Local project imports
from tools import initialize_tool_registry
from conversation_store import load_history, save_history
from utils import get_logger

# Initialize Rich Console
console = Console()
logger = get_logger(__name__)

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
    config_file: Optional[str] = Field(
        default=None,
        description="Path to optional YAML config file",
        env="AYYY_CONFIG_FILE",
    )

    @classmethod
    def load(cls) -> "AppConfig":
        cfg_path = os.getenv("AYYY_CONFIG_FILE")
        if cfg_path and Path(cfg_path).exists():
            with open(cfg_path, "r") as fh:
                data = yaml.safe_load(fh) or {}
            return cls(**data)
        return cls()

class AgileToolExecutor:
    def __init__(self) -> None:
        self.registry = initialize_tool_registry()
        console.log(
            f"Tools loaded: [cyan]{', '.join(self.registry._tools.keys()) or 'none'}[/cyan]"
        )

    @property
    def tool_schemas(self) -> List[ChatCompletionToolParam]:
        return cast(List[ChatCompletionToolParam], self.registry.get_lm_studio_schemas())

    async def run_tool(self, tool_name: str, tool_args_json_str: str) -> Dict[str, Any]:
        console.log(f"Attempting tool: [bold magenta]{tool_name}[/bold magenta], Args: [yellow]{tool_args_json_str}[/yellow]")
        try:
            args = json.loads(tool_args_json_str)
            if not isinstance(args, dict):
                raise ValueError("Tool arguments must be a JSON object (dictionary).")
            result = await self.registry.execute(tool_name, **args)
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
        
        self.global_objective: str | None = None
        self.current_plan: List[Dict[str, Any]] | None = None
        self.current_step_index: int = 0
        self.pending_error_info: Optional[Dict[str, Any]] = None

    def _save_history(self) -> None:
        save_history(self.config.history_file, self.messages)

    async def _get_llm_response(self, messages_override: List[Dict[str, Any]] | None = None, *, stream: bool = False) -> ChatCompletionMessage | None:
        tool_schemas = self.tool_executor.tool_schemas
        messages_to_send = messages_override if messages_override is not None else self.messages

        api_params: Dict[str, Any] = {
            "model": self.config.model,
            "messages": cast(List[ChatCompletionMessageParam], messages_to_send),
        }
        if tool_schemas:
            api_params["tools"] = tool_schemas
            api_params["tool_choice"] = "auto"

        try:
            if stream:
                response_stream = await self.client.chat.completions.create(stream=True, **api_params)
                final_message = {"role": "assistant", "content": "", "tool_calls": []}
                async for chunk in response_stream:
                    choice = chunk.choices[0]
                    delta = choice.delta
                    if delta.content:
                        console.print(delta.content, end="", style="bold green")
                        final_message["content"] += delta.content
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = int(tc.index)
                            while len(final_message["tool_calls"]) <= idx:
                                final_message["tool_calls"].append({"id": tc.id, "function": {"name": "", "arguments": ""}})
                            entry = final_message["tool_calls"][idx]
                            if tc.function.name:
                                entry["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                entry["function"]["arguments"] += tc.function.arguments
                console.print()
                return ChatCompletionMessage(**final_message)
            else:
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
        self.current_plan = None
        self.current_step_index = 0

        while True:
            current_llm_messages_for_api_call = list(self.messages)
            was_handling_pending_error = False

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
                self.pending_error_info = None
                break
            else:
                console.print("[bold blue]No active plan. LLM will decide on action (generate plan, use tool, or respond).[/bold blue]")

            stream_mode = True
            is_multimodal = any(isinstance(m.get("content"), list) for m in current_llm_messages_for_api_call)
            if is_multimodal:
                stream_mode = False

            llm_response_message = await self._get_llm_response(messages_override=current_llm_messages_for_api_call, stream=stream_mode)

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
                            if cleaned_plan:
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
                except (json.JSONDecodeError, Exception) as e:
                    console.print(f"[Plan Parsing Error] {e}", style="yellow")

            if llm_response_message.tool_calls:
                assistant_message_for_history["tool_calls"] = [
                    {"id": tc.id, "function": {"name": tc.function.name, "arguments": tc.function.arguments}, "type": "function"}
                    for tc in llm_response_message.tool_calls]
            
            self.messages.append(assistant_message_for_history)
            self._save_history()

            if assistant_message_for_history["content"] and not stream_mode:
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

                    result = tool_output_dict.get("result", {})
                    if isinstance(result, dict) and result.get("type") == "image_analysis":
                        image_base64 = result.get("image_base64")
                        last_user_message = next((m for m in reversed(self.messages) if m["role"] == "user"), None)
                        if last_user_message and image_base64:
                            # Attach image to the most recent user message
                            last_user_message["content"] = [
                                {"type": "text", "text": last_user_message["content"]},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                                },
                            ]
                            tool_content_for_history = "Image attached to user message. The assistant will now analyze it."
                            console.print("[bold yellow]Image data attached to the last user message.[/bold yellow]")
                        else:
                            tool_content_for_history = "Image analysis failed: Could not find user message to attach to."
                            all_tool_calls_successful_this_round = False
                    elif tool_output_dict.get("status") == "error":
                        error_msg = tool_output_dict['message']
                        tool_content_for_history = f"Error: {error_msg}"
                        all_tool_calls_successful_this_round = False
                        self.pending_error_info = {"tool_name": tool_name, "step_goal": "N/A", "error_message": error_msg, "arguments": tool_args_json_str}
                        tool_message_batch_for_history.append({"role": "tool", "tool_call_id": tool_call_id, "content": tool_content_for_history})
                        break
                    else:
                        tool_content_for_history = json.dumps(tool_output_dict)

                    tool_message_batch_for_history.append({
                        "role": "tool", "tool_call_id": tool_call_id, "content": tool_content_for_history})
                
                self.messages.extend(tool_message_batch_for_history)
                self._save_history()

                if not all_tool_calls_successful_this_round:
                    continue

                if all_tool_calls_successful_this_round:
                    self.pending_error_info = None
                    if self.current_plan:
                        self.current_step_index += 1
                        if self.current_step_index >= len(self.current_plan):
                            break
                        else:
                            continue
                    else:
                        # Continue the loop to let the LLM process the tool results (including the image)
                        continue
            else:
                if was_handling_pending_error and not new_plan_adopted_this_iteration:
                    self.pending_error_info = None
                    if self.current_plan:
                         self.current_step_index +=1

                if self.current_plan:
                    if not new_plan_adopted_this_iteration:
                        self.current_step_index += 1
                    
                    if self.current_step_index >= len(self.current_plan):
                        break
                    else:
                        continue
                else:
                    break
        
        self.global_objective = None
        self.pending_error_info = None
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
                break

async def main_async():
    try:
        app_config = AppConfig.load()
    except Exception as e:
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