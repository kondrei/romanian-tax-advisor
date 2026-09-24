import os
import re
import pickle
import unicodedata
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def normalize_text(text: str) -> str:
    """Normalize Romanian text by removing diacritics and converting to lowercase."""
    if not text:
        return ""
    text = text.lower()
    # Replace Romanian specific characters
    replacements = {
        'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ş': 's', 'ț': 't', 'ţ': 't',
        'Ă': 'a', 'Â': 'a', 'Î': 'i', 'Ș': 's', 'Ş': 's', 'Ț': 't', 'Ţ': 't'
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text

class RomanianFiscalCodeRAG:
    def __init__(self, htm_path: str = "data/cod_fiscal_2023.htm", index_path: str = "data/rag_index.pkl"):
        self.htm_path = htm_path
        self.index_path = index_path
        self.chunks = []
        self.normalized_corpus = []
        self.vectorizer = None
        self.tfidf_matrix = None
        
        self.load_or_build()

    def load_or_build(self):
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "rb") as f:
                    data = pickle.load(f)
                    self.chunks = data["chunks"]
                    self.normalized_corpus = data["normalized_corpus"]
                    self.vectorizer = data["vectorizer"]
                    self.tfidf_matrix = data["tfidf_matrix"]
                return
            except Exception as e:
                print(f"Error loading index from {self.index_path}: {e}, rebuilding...")

        self.build_index()

    def build_index(self):
        if not os.path.exists(self.htm_path):
            raise FileNotFoundError(f"HTML file not found at {self.htm_path}")

        print("Building RAG index from Romanian Fiscal Code HTML...")
        with open(self.htm_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f, "lxml")

        text = soup.get_text("\n")
        lines = [l.strip() for l in text.splitlines() if l.strip()]

        chunks = []
        current_header = "Dispoziții Generale"
        current_lines = []

        for line in lines:
            # Check for Article / Chapter / Title headers
            if re.match(r'^(ART\.|Art\.|TITLUL|CAPITOLUL)\s*\d+|^ART\.\s*[0-9]+', line):
                if current_lines:
                    content = "\n".join(current_lines)
                    if len(content) > 30:
                        chunks.append({
                            "header": current_header,
                            "content": content,
                            "full_text": f"{current_header}\n{content}"
                        })
                    current_lines = []
                current_header = line
            else:
                current_lines.append(line)

        if current_lines:
            chunks.append({
                "header": current_header,
                "content": "\n".join(current_lines),
                "full_text": f"{current_header}\n{'\n'.join(current_lines)}"
            })

        self.chunks = chunks
        self.normalized_corpus = [normalize_text(c["full_text"]) for c in self.chunks]

        self.vectorizer = TfidfVectorizer(max_features=50000, ngram_range=(1, 2))
        self.tfidf_matrix = self.vectorizer.fit_transform(self.normalized_corpus)

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        with open(self.index_path, "wb") as f:
            pickle.dump({
                "chunks": self.chunks,
                "normalized_corpus": self.normalized_corpus,
                "vectorizer": self.vectorizer,
                "tfidf_matrix": self.tfidf_matrix
            }, f)
        print(f"Index built successfully with {len(self.chunks)} chunks.")

    def search(self, query: str, top_k: int = 4) -> list[dict]:
        """Search the Romanian Fiscal Code RAG index for relevant articles."""
        norm_query = normalize_text(query)
        q_vec = self.vectorizer.transform([norm_query])
        sims = cosine_similarity(q_vec, self.tfidf_matrix)[0]

        top_indices = sims.argsort()[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(sims[idx])
            if score > 0.05:
                chunk = self.chunks[idx]
                results.append({
                    "score": round(score, 4),
                    "header": chunk["header"],
                    "content": chunk["content"][:2000] # Limit chunk length for prompt context
                })
        return results

    def get_article(self, article_number: str) -> list[dict]:
        """Lookup specific Article by number (e.g. '17', '42', '220')."""
        pattern = re.compile(rf'ART\.\s*{re.escape(str(article_number))}\b', re.IGNORECASE)
        results = []
        for chunk in self.chunks:
            if pattern.search(chunk["header"]) or pattern.search(chunk["content"][:200]):
                results.append({
                    "header": chunk["header"],
                    "content": chunk["content"][:2500]
                })
        return results[:3]
