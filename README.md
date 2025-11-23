# Chat with your Data: Building a File-Aware AI Agent with AWS Bedrock and Chainlit

We all know LLMs are powerful, but their true potential is unlocked when they can see your data. While RAG (Retrieval-Augmented Generation) is great for massive knowledge bases, sometimes you just want to drag and drop a file and ask questions about it.

Today we'll build a "File-Aware" AI agent that can natively understand a wide range of document formats—from PDFs and Excel sheets to Word docs and Markdown files. We'll use **AWS Bedrock** with **Claude 4.5 Sonnet** for the reasoning engine and **Chainlit** for the conversational UI.

The idea is straightforward: Upload a file, inject it into the model's context, and let the LLM do the rest. No vector databases, no complex indexing pipelines—just direct context injection for immediate analysis.

The architecture is simple yet effective. We intercept file uploads in the UI, process them into a format the LLM understands, and pass them along with the user's query.

```
┌──────────────┐      ┌──────────────┐      ┌────────────────────┐
│   Chainlit   │      │  Orchestrator│      │   AWS Bedrock      │
│      UI      │─────►│    Agent     │─────►│(Claude 4.5 Sonnet) │
└──────┬───────┘      └──────────────┘      └────────────────────┘
       │                      ▲
       │    ┌────────────┐    │
       └───►│ File Proc. │────┘
            │   Logic    │
            └────────────┘
```

The tech stack includes:
- **AWS Bedrock** with **Claude 4.5 Sonnet** for high-quality reasoning and large context windows.
- **Chainlit** for a chat-like interface with native file upload support.
- **Python** for the backend logic.

The core challenge is handling different file types and presenting them to the LLM. We support a variety of formats by mapping them to Bedrock's expected input types.

To enable file uploads in Chainlit, you need to configure the `[features.spontaneous_file_upload]` section in your `.chainlit/config.toml`. This is where you define which MIME types are accepted.

```toml
[features.spontaneous_file_upload]
    enabled = true
    accept = [
        "application/pdf",
        "text/csv",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/html",
        "text/plain",
        "text/markdown",
        "text/x-markdown"
    ]
    max_files = 20
    max_size_mb = 500
```

The main agent loop handles the conversation. It checks for uploaded files, processes them, and constructs the message payload for the LLM. We also include robust error handling to manage context window limits gracefully.

```python
def get_content_blocks_from_message(message: cl.Message):
    docs = [f for f in message.elements if f.type == "file" and f.mime in MIME_MAP]
    content_blocks = []

    for doc in docs:
        file = Path(doc.path)
        file_bytes = file.read_bytes()
        shutil.rmtree(file.parent)

        content_blocks.append({
            "document": {
                "name": sanitize_filename(doc.name),
                "format": MIME_MAP[doc.mime],
                "source": {"bytes": file_bytes}
            }
        })

    if content_blocks:
        content_blocks.append({"text": message.content})

    return content_blocks

@cl.on_message
async def handle_message(message: cl.Message):
    agent = cl.user_session.get("agent")
    message_history = cl.user_session.get("message_history")
    question = get_question_from_message(message)
    message_history.append({"role": "user", "content": question})

    task = asyncio.create_task(process_user_task(agent, question, DEBUG))
    cl.user_session.set("task", task)
    cl.user_session.set("conversation_history", message_history)
    try:
        await task
    except asyncio.CancelledError:
        logger.info("User task was cancelled.")
```

This pattern allows for **ad-hoc analysis**. You don't need to pre-ingest data. You can:
1.  **Analyze Financials:** Upload an Excel sheet and ask for trends.
2.  **Review Contracts:** Upload a PDF and ask for clause summaries.
3.  **Debug Code:** Upload a source file and ask for a bug fix.

By leveraging the large context window of modern models like Claude 4.5 Sonnet, we can feed entire documents directly into the prompt, providing the model with full visibility without the information loss often associated with RAG chunking.

And that's all. With tools like Chainlit and powerful APIs like AWS Bedrock, we can create robust, multi-modal assistants that integrate seamlessly into our daily workflows.
