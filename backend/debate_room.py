import os
import autogen
from typing import Dict, Any, List
from .prompts import BULL_RESEARCHER_PROMPT, BEAR_RESEARCHER_PROMPT

class DebateRoom:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("WARNING: GEMINI_API_KEY not found. Debate will fail.")
            
        self.config_list = [
            {
                "model": "gemini-2.5-flash", # User requested 2.5
                "api_key": self.api_key,
                "api_type": "google"
            }
        ]
        
        self.llm_config = {
            "config_list": self.config_list,
            "temperature": 0.7,
        }

    async def conduct_debate(self, context: str) -> str:
        """
        Conducts a debate between a Bull and a Bear based on the provided context.
        Returns the debate transcript.
        """
        print("--- Starting Bull/Bear Debate ---")
        
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
        # Note: AutoGen's initiate_chat is synchronous. We might need to run it in a thread 
        # if we want to be fully async, but for now blocking is acceptable for the debate phase.
        try:
            # Since initiate_chat with 2 agents is tricky without a GroupChatManager,
            # Let's use a GroupChat for robustness.
            
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
            print(f"Error during debate: {e}")
            return f"Debate failed: {e}"
