import logging
from app.core.llm_provider import LLMProviderFactory, LocalLLMProvider

logger = logging.getLogger(__name__)

class LocalLLMConnector:
    """Connects to local on-premise LLMs via provider abstraction with fallbacks for air-gapped sandbox environments."""

    @classmethod
    def check_ollama_status(cls) -> bool:
        """Checks if local LLM service is active."""
        provider = LLMProviderFactory.get_provider()
        return provider.check_status()

    @classmethod
    def generate_response(cls, prompt: str, system_prompt: str = "") -> str:
        """Sends a prompt to the local LLM provider and returns the response string."""
        provider = LLMProviderFactory.get_provider()
        return provider.generate(prompt, system_prompt)

    @classmethod
    def generate_response_stream(cls, prompt: str, system_prompt: str = ""):
        """Sends a prompt to the local LLM provider and yields response tokens."""
        provider = LLMProviderFactory.get_provider()
        yield from provider.generate_stream(prompt, system_prompt)

    @classmethod
    def generate_rag_answer_stream(cls, query: str, matches: list, history: list = None):
        """Builds context, executes local LLM generation, and yields tokens as they arrive."""
        if history is None:
            history = []
            
        if not matches:
            yield "I could not find any relevant context in the uploaded documents to answer your question."
            return

        context_blocks = []
        for match in matches:
            context_blocks.append(f"[Filename: {match['metadata']['source_file']}]\n{match['text']}")
            
        context_str = "\n\n".join(context_blocks)
        
        system_prompt = (
            "You are a secure, local document intelligence AI. "
            "Answer the user's question based ONLY on the provided context. "
            "If the user asks you to explain or summarize a document, describe what the document is about using the provided text. "
            "IMPORTANT: Always refer to the documents by their actual filenames (e.g., 'In file 9281.png...'), NEVER refer to them as 'Document 1' or 'Document 2'. "
            "Provide a comprehensive answer using bullet points if necessary. "
            "If the context is completely unrelated to the question, state that you do not have enough information."
        )
        
        history_str = ""
        for msg in history[-4:]:
            role = "User" if msg["sender"] == "user" else "Assistant"
            if msg["text"]:
                history_str += f"{role}: {msg['text']}\n\n"
        
        prompt = (
            f"Document Context:\n"
            f"--------------------------------------------------\n"
            f"{context_str}\n"
            f"--------------------------------------------------\n\n"
        )
        
        if history_str:
            prompt += f"Conversation History:\n{history_str}"
            
        prompt += f"User: {query}\n\nAssistant:"

        try:
            for token in cls.generate_response_stream(prompt, system_prompt):
                yield token
        except Exception:
            yield cls.generate_mock_rag_response(query, matches, history)

    @classmethod
    def generate_mock_rag_response(cls, query: str, matches: list, history: list = None) -> str:
        """Rule-based mock RAG responder when no external local daemon is available."""
        logger.info("Executing fail-safe offline Mock RAG generator...")
        
        sentences = []
        for m in matches:
            text = m["text"]
            for line in text.split("\n"):
                for sentence in line.split(". "):
                    sentence = sentence.strip()
                    if len(sentence) > 10 and sentence not in sentences:
                        sentences.append(sentence)
                        
        query_words = [w.lower() for w in query.split() if len(w) > 3]
        
        ranked_sentences = []
        for s in sentences:
            score = sum(1 for qw in query_words if qw in s.lower())
            if score > 0:
                ranked_sentences.append((score, s))
                
        ranked_sentences = sorted(ranked_sentences, key=lambda x: x[0], reverse=True)
        
        if ranked_sentences:
            best_score = ranked_sentences[0][0]
            best_facts = [s for score, s in ranked_sentences if score >= best_score - 1][:3]
            facts_str = " ".join(best_facts)
            if not facts_str.endswith("."):
                facts_str += "."
            return (
                f"**[Offline RAG Mode]** Based on the retrieved context, here is what was found:\n\n"
                f"{facts_str}\n\n"
                f"*(Note: Local Ollama service is disconnected; running in high-fidelity mock vector-matching backup mode)*"
            )
        else:
            summary_facts = [m["text"][:150] + "..." for m in matches[:2]]
            summary_str = "\n* ".join(summary_facts)
            return (
                f"**[Offline RAG Mode]** I found matching topics in the documents but no direct keyword overlap. "
                f"Here are snippets from the retrieved context:\n\n"
                f"* {summary_str}\n\n"
                f"*(Note: Local Ollama service is disconnected; running in high-fidelity mock vector-matching backup mode)*"
            )

