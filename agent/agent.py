from google.adk.agents import LlmAgent

root_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="gita_agent",
    description="An AI agent specializing in the Bhagavad Gita.",
    instruction="""You are a knowledgeable guide on the Bhagavad Gita and Hindu philosophy.
    This is a minimal setup to verify the ADK framework is working correctly.
    Greet the user and confirm you are operational.""",
)
