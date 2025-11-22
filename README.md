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

Here is how we process uploaded files:

```python
def process_uploaded_files(elements: list) -> tuple[list[dict], dict]:
    # Map MIME types to Bedrock formats
    mime_map = {
        "application/pdf": "pdf",
        "text/csv": "csv",
        "application/msword": "doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.ms-excel": "xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "text/html": "html",
        "text/plain": "txt",
        "text/markdown": "md"
    }
    
    docs = [f for f in elements if f.type == "file" and f.mime in mime_map]
    
    for doc in docs:
        # ... read bytes and sanitize filename ...
        content_blocks.append({
            "document": {
                "name": sanitize_filename(doc.name),
                "format": mime_map[doc.mime],
                "source": {"bytes": bytes}
            }
        })
        
    return content_blocks, files
```

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
@cl.on_message
async def handle_message(message: cl.Message):
    # ... setup ...

    if message.elements:
        content_blocks = get_content_blocks_from_message(message)
        # ... add files to context ...
    
    # ... construct final question ...

    try:
        async for event in agent.stream_async(final_question):
            # ... stream response ...
    except ContextWindowOverflowException:
        await msg.stream_token("\n\n⚠️ **Error:** The file is too large...")
```

This pattern allows for **ad-hoc analysis**. You don't need to pre-ingest data. You can:
1.  **Analyze Financials:** Upload an Excel sheet and ask for trends.
2.  **Review Contracts:** Upload a PDF and ask for clause summaries.
3.  **Debug Code:** Upload a source file and ask for a bug fix.

By leveraging the large context window of modern models like Claude 4.5 Sonnet, we can feed entire documents directly into the prompt, providing the model with full visibility without the information loss often associated with RAG chunking.

And that's all. With tools like Chainlit and powerful APIs like AWS Bedrock, we can create robust, multi-modal assistants that integrate seamlessly into our daily workflows.
