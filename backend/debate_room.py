import os
import autogen
import asyncio
from typing import Dict, Any, List
from .prompts import BULL_RESEARCHER_PROMPT, BEAR_RESEARCHER_PROMPT
from .config import Config

class DebateRoom:
    def __init__(self, ai_provider: str = "auto"):
        self.ai_provider = ai_provider
        self.api_key = Config.GEMINI_API_KEY
        if not self.api_key and ai_provider != "qwen":
            print("WARNING: GEMINI_API_KEY not found. Debate will fail.")
            
        self.config_list = [
            {
                "model": Config.MODEL_NAME,
                "api_key": self.api_key,
                "api_type": "google"
            }
        ]
        
        self.llm_config = {
            "config_list": self.config_list,
            "temperature": 0.7,
        }
        
        # Core agent for Qwen calls
        if ai_provider == "qwen":
            from trader_agent_core import TraderAgent
            self.core_agent = TraderAgent()

    async def conduct_debate(self, context: str) -> str:
        """
        Conducts a debate between a Bull and a Bear based on the provided context.
        Returns the debate transcript.
        """
        print("--- Starting Bull/Bear Debate ---")
        
        if self.ai_provider == "qwen":
            return await self._conduct_qwen_debate(context)
        
        # Run the blocking Autogen chat in a separate thread
        try:
            transcript = await asyncio.to_thread(self._run_autogen_chat, context)
            return transcript
        except Exception as e:
            print(f"Error during debate: {e}")
            return f"Debate failed: {e}"

    async def _conduct_qwen_debate(self, context: str) -> str:
        """Simulate a debate using Qwen CLI (single prompt)."""
        print("\n" + "="*40)
        print("       MARKET CONTEXT")
        print("="*40)
        print(context)
        print("="*40 + "\n")
        
        print("[DebateRoom] Using Qwen for debate simulation...")
        prompt = f"""
        You are simulating a debate between a Bull and a Bear regarding the following crypto asset.
        
        MARKET CONTEXT:
        {context}
        
        Please generate a transcript of their debate.
        
        BULL: [Arguments for buying]
        BEAR: [Arguments for selling/risks]
        MODERATOR: [Summary]
        
        Format the output as a dialogue.
        """
        try:
            # We use _call_qwen_cli but expect text, not JSON.
            # Since _call_qwen_cli tries to parse JSON, we might need a raw method.
            # Or we can just use subprocess directly here.
            import subprocess
            process = await asyncio.create_subprocess_exec(
                "qwen",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate(input=prompt.encode())
            if process.returncode != 0:
                return f"Debate failed: {stderr.decode()}"
            
            transcript = stdout.decode()
            print("\n" + "="*40)
            print("       QWEN DEBATE TRANSCRIPT")
            print("="*40)
            print(transcript)
            print("="*40 + "\n")
            
            return transcript
        except Exception as e:
            return f"Debate failed: {e}"

    def _run_autogen_chat(self, context: str) -> str:
        """
        Synchronous function to run Autogen chat.
        """
        # Initialize Agents
        bull_agent = autogen.AssistantAgent(
            name="Bull_Researcher",
            system_message=BULL_RESEARCHER_PROMPT,
            llm_config=self.llm_config,
        )

        bear_agent = autogen.AssistantAgent(
            name="Bear_Researcher",
            system_message=BEAR_RESEARCHER_PROMPT,
            llm_config=self.llm_config,
        )

        # User Proxy to facilitate the chat (acts as the moderator/environment)
        user_proxy = autogen.UserProxyAgent(
            name="Moderator",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=2,
            is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
            code_execution_config=False,
        )

        # Construct the initial prompt
        initial_message = f"""
        Here is the current market data and analysis for the asset:
        
        {context}
        
        Debate the future price direction. 
        Bull, you go first. Tell us why we should buy.
        Bear, respond to the Bull's points and explain the risks.
        """

        # Start the chat
        try:
            groupchat = autogen.GroupChat(
                agents=[user_proxy, bull_agent, bear_agent], 
                messages=[], 
                max_round=4
            )
            manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=self.llm_config)
            
            user_proxy.initiate_chat(
                manager,
                message=initial_message
            )
            
            # Extract transcript
            transcript = ""
            for msg in groupchat.messages:
                transcript += f"{msg['name']}: {msg['content']}\n\n"
                
            return transcript
            
        except Exception as e:
            raise e
