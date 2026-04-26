# Required GitHub Secrets

To enable full CI with live API calls, add these secrets to the repo:
Settings → Secrets and variables → Actions → New repository secret

| Secret | Description |
|--------|-------------|
| GROQ_API_KEY | Groq API key (llama-3.3-70b) |
| GOOGLE_API_KEY | Google AI Studio key (gemini-2.5) |
| TAVILY_API_KEY | Tavily search API key |

Without these secrets, CI runs in mock mode (unit tests only).
Integration tests requiring real APIs are skipped automatically.
