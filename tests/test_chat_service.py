


from app.services.chat_service import ChatService

chat = ChatService()

response = chat.ask(
    "Compute là gì?"
)

print("=" * 80)
print("QUESTION")
print(response["question"])

print("=" * 80)
print("ANSWER")
print(response["answer"])

print("=" * 80)
print("SOURCES")

for source in response["sources"]:
    print(f'Distance: {source["distance"]:.4f}')
    print(source["document"][:200])
    print("-" * 80)