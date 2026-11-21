import os
from typing import Dict, List
from src.wealth_platform.config import GEMINI_API_KEY, GEMINI_MODEL

# Document store of SEC 10-K & earnings filings insights
SEC_FINANCIAL_KNOWLEDGE_BASE = [
    {
        "ticker": "AAPL",
        "company": "Apple Inc.",
        "section": "Item 1A. Risk Factors & Business Overview",
        "content": "Apple operates in highly competitive tech markets with rapid technological changes. Key revenue drivers include iPhone, Services (App Store, Apple Pay, iCloud), and Wearables. Main supply chain dependencies revolve around semiconductor foundry single-source suppliers (TSMC) in Taiwan. Regulatory risks include EU Digital Markets Act antitrust scrutiny over App Store fees."
    },
    {
        "ticker": "MSFT",
        "company": "Microsoft Corp.",
        "section": "Item 1A. Risk Factors & Business Overview",
        "content": "Microsoft's core growth engines are Intelligent Cloud (Azure), Productivity Services (Office 365, Copilot), and Personal Computing. Capex has increased significantly to build out global AI data centers and GPU clusters. Operational risks include cybersecurity threats and enterprise adoption rates of generative AI tools."
    },
    {
        "ticker": "NVDA",
        "company": "NVIDIA Corp.",
        "section": "Item 1A. Risk Factors & Business Overview",
        "content": "NVIDIA dominates data center GPU acceleration (Hopper, Blackwell architectures) for AI LLM training. Growth is tied to hyperscaler AI capital expenditure. Key risks include export control restrictions on advanced AI chips to certain international regions, customer concentration among top hyperscalers, and semiconductor supply chain constraints at TSMC."
    },
    {
        "ticker": "GOOGL",
        "company": "Alphabet Inc.",
        "section": "Item 1A. Risk Factors & Business Overview",
        "content": "Alphabet generates revenue predominantly through Google Search, YouTube Ads, and Google Cloud (GCP). Heavy investments in Gemini generative AI models across consumer and enterprise products. Key risks include antitrust litigation regarding Search distribution contracts and competitive pressure in AI search capabilities."
    },
    {
        "ticker": "AMZN",
        "company": "Amazon.com Inc.",
        "section": "Item 1A. Risk Factors & Business Overview",
        "content": "Amazon relies on Amazon Web Services (AWS) for operating income margin, alongside North American and International e-commerce fulfillment. Risks include logistics inflation, consumer discretionary spending sensitivity, and competitive pressure in cloud infrastructure."
    }
]

class SECFinancialRAGAgent:
    def __init__(self, api_key: str = GEMINI_API_KEY):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.client = None
        self._init_gemini()

    def _init_gemini(self):
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                print("[AI Agent] Gemini Client initialized successfully.")
            except Exception as e:
                print(f"[AI Agent Warning] Could not initialize Gemini SDK ({e}). Utilizing built-in Financial AI Analyst Engine.")

    def search_knowledge_base(self, query: str) -> List[Dict]:
        """Simple semantic / keyword search over financial SEC store."""
        query_terms = query.lower().split()
        results = []
        for doc in SEC_FINANCIAL_KNOWLEDGE_BASE:
            score = sum(1 for term in query_terms if term in doc["content"].lower() or term in doc["ticker"].lower())
            if score > 0 or not query_terms:
                results.append((score, doc))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:3]]

    def answer_financial_query(self, query: str) -> str:
        """Answers financial question using relevant SEC contexts and Gemini / Analyst logic."""
        context_docs = self.search_knowledge_base(query)
        context_str = "\n\n".join([f"[{d['company']} ({d['ticker']}) - {d['section']}]: {d['content']}" for d in context_docs])

        prompt = f"""
You are a Senior Equity Research Analyst & Financial Risk Specialist.
Answer the user's question accurately based on the provided SEC filing context and sound financial principles.

Context from SEC Filings:
{context_str}

User Question: {query}

Provide a concise, professional answer highlighting key revenue drivers, risk factors, or strategic outlook.
"""
        if self.client:
            try:
                response = self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                print(f"[AI Agent Error] Gemini API call failed ({e}). Falling back to Financial AI Analyst.")

        # Fallback Analyst Engine Response
        return self._rule_based_financial_answer(query, context_docs)

    def _rule_based_financial_answer(self, query: str, context_docs: List[Dict]) -> str:
        """Heuristic financial analysis fallback response."""
        q_lower = query.lower()
        if "risk" in q_lower or "threat" in q_lower:
            ans = "### ⚠️ Key Portfolio Risk Factors Analysis\n\n"
            for d in context_docs:
                ans += f"**{d['company']} ({d['ticker']})**: {d['content']}\n\n"
            ans += "**Summary Risk Takeaway**: Supply chain single-sourcing (TSMC), cloud hyperscaler capex dependency, and antitrust scrutiny represent the top macroeconomic threats across tech assets."
            return ans
        elif "growth" in q_lower or "revenue" in q_lower or "driver" in q_lower:
            ans = "### 📈 Portfolio Revenue Drivers & Growth Analysis\n\n"
            for d in context_docs:
                ans += f"**{d['company']} ({d['ticker']})**: Focuses heavily on AI infrastructure expansion, cloud enterprise services, and high-margin recurring subscriptions.\n\n"
            return ans
        else:
            ans = f"### 📊 Financial Analysis for Query: '{query}'\n\n"
            for d in context_docs:
                ans += f"- **{d['company']} ({d['ticker']})**: {d['content']}\n"
            ans += "\n*Source: SEC 10-K & 10-Q Disclosures indexed by Wealth Intelligence RAG Engine.*"
            return ans
