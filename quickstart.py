import os
from dotenv import load_dotenv
from agentmail import AgentMail

# Load the API key from the .env file
load_dotenv()
api_key = os.getenv("AGENTMAIL_API_KEY")

# Initialize the client
client = AgentMail(api_key=api_key)

# Create an inbox
print("Creating inbox...")
inbox = client.inboxes.create() # domain is optional
print("Inbox created successfully!")
print(inbox)

