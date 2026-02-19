# ai_engine_ollama.py (Ollama version - OPTIMIZED)

import re
import torch
import soundfile as sf
import requests
import json
from transformers import VitsModel, AutoTokenizer


from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings

print("LOADED AI_ENGINE VERSION: OLLAMA_V2_FIXED")

class LocalGovernanceAI:
    """
    Local governance assistant:
    - LLM: Ollama (llama3.2:3b)
    - TTS: facebook/mms-tts-tel
    - RAG: Focused retrieval from governance_brochure.pdf
    """

    def __init__(self, ollama_model="llama3.2:3b", ollama_url="http://localhost:11434"):
        print("[INIT] Connecting to Ollama...")
        self.ollama_model = ollama_model
        self.ollama_url = ollama_url
        self.ollama_endpoint = f"{ollama_url}/api/generate"
        
        try:
            response = requests.post(
                self.ollama_endpoint,
                json={"model": self.ollama_model, "prompt": "Hi", "stream": False},
                timeout=10
            )
            if response.status_code == 200:
                print(f"[INIT] ✓ Ollama connected! Model: {self.ollama_model}")
            else:
                raise Exception(f"Ollama error: {response.status_code}")
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            raise

        print("[INIT] Loading MMS-TTS (Mouth)...")
        try:
            self.tts_tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-tel")
            self.tts_model = VitsModel.from_pretrained("facebook/mms-tts-tel")
            print("[INIT] ✓ TTS loaded")
        except Exception as e:
            print(f"[ERROR] Failed to load TTS: {e}")
            raise

        self.retriever = None

    def setup_rag(self, txt_path: str):
        print(f"[RAG] Ingesting {txt_path}...")
        loader = TextLoader(txt_path)
        docs = loader.load_and_split()
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        db = Chroma.from_documents(docs, embeddings, persist_directory="./chroma_db")
        # CHANGED: Increased k from 2 to 4 to ensure all relevant helplines are caught
        self.retriever = db.as_retriever(search_kwargs={"k": 4})
        print("[RAG] Ready.")

    def _clean(self, text: str) -> str:
        if not text:
            return ""
        
        t = text.strip()
        # Remove LLM artifacts
        for b in ["<s>", "</s>", "[BOS]", "[EOS]", "[PAD]", "Answer:", "సమాధానం:"]:
            t = t.replace(b, "")
        
        t = re.sub(r"https?://\S+", "", t)
        
        # CHANGED: Increased character limit. Telugu tokens are large; 
        # 250 was cutting off the actual help instructions.
        if len(t) > 800:
            t = t[:800] + "..."
        
        return t.strip()

    def ask(self, user_message: str) -> str:
        try:
            context = ""
            if self.retriever:
                try:
                    retrieved = self.retriever.invoke(user_message)
                    if retrieved:
                        # Combine retrieved chunks clearly
                        context = "\n".join([doc.page_content for doc in retrieved])
                except Exception as e:
                    print(f"[RAG ERROR] {e}")

            # CHANGED: Implemented a strict System Prompt to prevent hallucinations.
            # This forces the model to use the PDF data or admit it doesn't know.
            prompt = f"""మీరు "తెలంగాణ గ్రామ డిజిటల్ సేవల" సహాయకుడు.
ఈ క్రింద ఇవ్వబడిన 'సందర్భం' (Context) ఉపయోగించి మాత్రమే సమాధానం చెప్పండి. 
సమాధానం కేవలం తెలుగులో, 3-5 బుల్లెట్ పాయింట్లలో ఉండాలి.

సందర్భం:
{context}

ప్రశ్న: {user_message}
సమాధానం (తెలుగులో):"""
            
            print(f"[OLLAMA] Querying {self.ollama_model} with RAG context...")
            
            response = requests.post(
                self.ollama_endpoint,
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
		    "options":{
				"temperature":0.0,
			   "repeat_penalty:": 1.5,
			"num_ctx":4096,
                  	  "num_predict": 400   # Enough tokens for full Telugu sentences
			}
                },
                timeout=120
            )
            
            if response.status_code != 200:
                return "క్షమించండి, సాంకేతిక సమస్య ఎదురైంది."
            
            result = response.json()
            answer = result.get("response", "").strip()
            
            # Final cleaning
            answer = self._clean(answer)
            print(f"[OLLAMA RESULT] {answer}")
            return answer
        
        except Exception as e:
            print(f"[ERROR] ask() failed: {e}")
            return "క్షమించండి, ప్రస్తుతం సమాధానం ఇవ్వలేను."

    def speak(self, text: str, output_path: str = "response.wav") -> str:
        try:
            inputs = self.tts_tokenizer(text, return_tensors="pt")
            with torch.no_grad():
                output = self.tts_model(**inputs).waveform
            sf.write(output_path, output.cpu().numpy()[0], self.tts_model.config.sampling_rate)
            return output_path
        except Exception as e:
            print(f"[TTS ERROR] {e}")
            return ""
