import re
import torch
import soundfile as sf

from transformers import AutoTokenizer, AutoModelForCausalLM, VitsModel, pipeline

# Optional RAG imports
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
print("LOADED AI_ENGINE VERSION: GUARDED_V1")

class LocalGovernanceAI:
    """
    Local governance assistant:
    - LLM: Telugu-LLM-Labs/Indic-gemma-2b-finetuned-sft-Navarasa-2.0
    - TTS: facebook/mms-tts-tel
    - Optional: RAG over a PDF using Chroma
    """

    def __init__(self):
        print("[INIT] Loading Navarasa 2.0 (Brain)...")
        self.model_name = "Telugu-LLM-Labs/Indic-gemma-2b-finetuned-sft-Navarasa-2.0"

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            device_map="auto",
            torch_dtype=torch.float16,
            load_in_4bit=True
        )

        print("[INIT] Loading MMS-TTS (Mouth)...")
        self.tts_tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-tel")
        self.tts_model = VitsModel.from_pretrained("facebook/mms-tts-tel")

        # Keep generation short + stable to reduce hallucinations and latency
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=80,         
            temperature=0.2,            
            top_p=0.9,
            do_sample=True,
            repetition_penalty=-1.15,
            return_full_text=True
        )

        self.retriever = None

    def setup_rag(self, pdf_path: str):
        print(f"[RAG] Ingesting {pdf_path}...")
        loader = PyPDFLoader(pdf_path)
        docs = loader.load_and_split()

        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        db = Chroma.from_documents(docs, embeddings, persist_directory="./chroma_db")
        self.retriever = db.as_retriever(search_kwargs={"k": 2})

        print("[RAG] Ready.")

    # ---------- Guardrails helpers ----------

    def _detect_script_hint(self, text: str) -> str:
        """
        Roughly detect if input contains Telugu/Kannada/English.
        We always respond in Telugu, but this can drive clarification questions.
        """
        if not text:
            return "unknown"

        # Telugu block: 0C00–0C7F, Kannada block: 0C80–0CFF
        if re.search(r"[\u0C00-\u0C7F]", text):
            return "telugu"
        if re.search(r"[\u0C80-\u0CFF]", text):
            return "kannada"
        if re.search(r"[A-Za-z]", text):
            return "english"
        return "unknown"

    def _clean(self, text: str) -> str:
        """
        Remove junk, code/math artifacts, long random IDs.
        Keep answer short and speakable.
        """
        if not text:
            return ""

        t = text.strip()

        # Remove HTML/template remnants
        for b in ["<script", "</script>", "<body", "</body>", "<html", "</html>", "end_of_turn", "start_of_turn"]:
            t = t.replace(b, "")

        # Remove ${...} and similar template/math blobs
        t = re.sub(r"\$\{.*?\}", "", t)

        # Remove LaTeX-ish / excessive symbols
        t = re.sub(r"[\{\}\[\]\(\)]{3,}", " ", t)

        # Remove weird long IDs like RZ/Z243679, GOI-PT-..., etc (keep if user asked? usually not needed in assistant reply)
        t = re.sub(r"\b[A-Z]{2,}[-/][A-Z0-9-]{5,}\b", "", t)

        # Remove repeated dots-only outputs
        if re.fullmatch(r"[.\s]+", t):
            return ""

        # Normalize whitespace
        t = re.sub(r"\s{2,}", " ", t).strip()

        # Keep it short (TTS-friendly)
        return t[:700]

    def _build_prompt(self, query: str, context: str) -> str:
        """
        Strict instruction prompt to prevent hallucination-y free generation.
        """
        return f"""
మీరు "తెలంగాణ గ్రామ డిజిటల్ సేవల" సహాయకుడు.

లక్ష్యం: పౌరులకు ప్రభుత్వ సేవలు/ఫిర్యాదులు/అర్జీలు గురించి **చర్యలకు ఉపయోగపడే** మార్గదర్శనం ఇవ్వడం.

కఠిన నియమాలు:
- సమాధానం పూర్తిగా తెలుగులోనే ఇవ్వాలి.
- 3 నుంచి 6 బుల్లెట్ పాయింట్లలో మాత్రమే ఇవ్వాలి.
- యాదృచ్ఛిక కోడ్, గణితం, హ్యాష్‌లు, ఐడీలు, అసంబద్ధ పదాలు ఇవ్వకూడదు.
- "సందర్భం" లో లేని విషయం ఊహించకూడదు.
- అవసరమైన సమాచారం లేకపోతే చివరలో 1 లేదా 2 ప్రశ్నలు మాత్రమే అడగాలి (ఉదా: గ్రామం/మండలం/వార్డు, సమస్య ఎప్పటి నుంచి, సంప్రదింపు నంబర్).

సందర్భం (ఉంటే మాత్రమే, లేకపోతే ఖాళీగా ఉంటుంది):
{context}

ప్రశ్న:
{query}

సమాధానం (బుల్లెట్ పాయింట్లలో):
-""".strip()

    # ---------- Main API ----------

    def ask(self, query: str) -> str:
        query = (query or "").strip()
        if not query:
            return "దయచేసి మీ సమస్యను వివరంగా టైప్ చేయండి."

        # Quick rule-based greetings (prevents weird “Hello -> హ్యూమిన్” type drift)
        low = query.lower()
        if low in {"hi", "hello", "hey"}:
            return "హాయ్! మీకు ఏ ప్రభుత్వ సేవ లేదా ఫిర్యాదులో సహాయం కావాలి?"

        # If user typed Kannada/English, still answer in Telugu but ask a gentle clarification
        script_hint = self._detect_script_hint(query)
        extra_hint = ""
        if script_hint == "kannada":
            extra_hint = "గమనిక: మీరు కన్నడలో టైప్ చేశారు—మీ సమస్యను వీలైతే తెలుగులో లేదా ఇంగ్లీషులో కూడా పంపండి.\n"

        # RAG context (keep it short)
        context = ""
        if self.retriever:
            try:
                docs = self.retriever.invoke(query)
                context = " ".join((d.page_content or "") for d in docs)[:1200]
            except Exception:
                context = ""

        prompt = self._build_prompt(query, context)

        try:
            out = self.pipe(prompt)[0]["generated_text"]
            answer = out.replace(prompt, "").strip()
            answer = self._clean(answer)

            # Hard fallback if model output is empty/garbage
            if not answer or len(answer) < 5:
                answer = "దయచేసి సమస్యను మరింత వివరంగా చెప్పండి (స్థలం/గ్రామం/మండలం, సమస్య ఎప్పటి నుంచి)."

            return self._clean(extra_hint + answer)

        except Exception:
            return "క్షమించండి—ప్రస్తుతం సమాధానం ఇవ్వడంలో సమస్య ఎదురైంది. దయచేసి మరోసారి ప్రయత్నించండి."

    def speak(self, text: str, output_path: str) -> str:
        """
        TTS guard:
        - Avoid empty strings
        - Ensure .wav
        """
        text = (text or "").strip()
        if len(text) < 2:
            text = "దయచేసి మీ సమస్యను మరింత వివరంగా చెప్పండి."

        if not output_path.endswith(".wav"):
            output_path += ".wav"

        inputs = self.tts_tokenizer(text, return_tensors="pt")

        with torch.no_grad():
            wav = self.tts_model(**inputs).waveform

        sf.write(output_path, wav.cpu().numpy().T, self.tts_model.config.sampling_rate)
        return output_path
