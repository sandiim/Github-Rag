# App-specific Ollama context

Use `github-rag-llama3.1:8k`, built from `ollama/Modelfile`, for answer generation. It derives from the installed `llama3.1:latest` model and sets `num_ctx` to 8192. Keep the application pointed at Ollama's OpenAI-compatible local endpoint; no paid-provider fallback is configured.

This limits the memory required by the answer model without changing the base model or other local applications. The tradeoff is a smaller context window: long retrieved prompts may need future budgeting or trimming. The alias must be created once on every machine running Ollama before the application can use it.
