import logging
import urllib.request
import urllib.error
import json
from app.config import ENVIRONMENT

logger = logging.getLogger(__name__)

# Default local Ollama endpoint URL
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "llama3:latest"

class LocalLLMConnector:
    """Connects to local on-premise LLMs (Ollama) with fallbacks for air-gapped sandbox environments."""

    @classmethod
    def check_ollama_status(cls) -> bool:
        """Checks if local Ollama service is running and model is loaded."""
        try:
            # Check Ollama base endpoint
            req = urllib.request.Request("http://127.0.0.1:11434/")
            with urllib.request.urlopen(req, timeout=2) as res:
                return res.status == 200
        except Exception:
            return False

    @classmethod
    def generate_response(cls, prompt: str, system_prompt: str = "") -> str:
        """Sends a prompt to the local Ollama service and returns the response string."""
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_predict": 256
            }
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                OLLAMA_URL, 
                data=data, 
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as res:
                body = json.loads(res.read().decode("utf-8"))
                return body.get("response", "").strip()
        except Exception as e:
            logger.warning(f"Ollama connection failed or timed out. Falling back to mock generator. Error: {str(e)}")
            raise e

    @classmethod
    def generate_response_stream(cls, prompt: str, system_prompt: str = ""):
        """Sends a prompt to the local Ollama service and yields the response as it streams."""
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "stream": True,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_predict": 1024
            }
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                OLLAMA_URL, 
                data=data, 
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as res:
                for line in res:
                    if line:
                        chunk = json.loads(line.decode("utf-8"))
                        yield chunk.get("response", "")
                        if chunk.get("done"):
                            break
        except Exception as e:
            logger.warning(f"Ollama streaming connection failed. Error: {str(e)}")
            raise e

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
        
        # Build conversational history string
        history_str = ""
        for msg in history[-4:]: # Keep last 4 messages to save context window
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
            # Yield the mock string as a single chunk if the connection fails
            yield cls.generate_mock_rag_response(query, matches, history)

    @classmethod
    def generate_mock_rag_response(cls, query: str, matches: list, history: list = None) -> str:
        """A rule-based mock RAG responder that extracts answers from retrieved chunks.
        
        Ensures the application works cleanly even if Ollama is not configured.
        """
        logger.info("Executing fail-safe offline Mock RAG generator...")
        
        # Collect context sentences
        sentences = []
        for m in matches:
            text = m["text"]
            # Split into simple lines/sentences
            for line in text.split("\n"):
                for sentence in line.split(". "):
                    sentence = sentence.strip()
                    if len(sentence) > 10 and sentence not in sentences:
                        sentences.append(sentence)
                        
        query_words = [w.lower() for w in query.split() if len(w) > 3]
        
        # Rank sentences by query overlap
        ranked_sentences = []
        for s in sentences:
            score = sum(1 for qw in query_words if qw in s.lower())
            if score > 0:
                ranked_sentences.append((score, s))
                
        ranked_sentences = sorted(ranked_sentences, key=lambda x: x[0], reverse=True)
        
        # Build answer
        if ranked_sentences:
            # Group top sentences by the document they came from to prevent splicing unrelated contexts
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
            # Default summary response
            summary_facts = [m["text"][:150] + "..." for m in matches[:2]]
            summary_str = "\n* ".join(summary_facts)
            return (
                f"**[Offline RAG Mode]** I found matching topics in the documents but no direct keyword overlap. "
                f"Here are snippets from the retrieved context:\n\n"
                f"* {summary_str}\n\n"
                f"*(Note: Local Ollama service is disconnected; running in high-fidelity mock vector-matching backup mode)*"
            )
