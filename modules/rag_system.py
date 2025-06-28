import os, re, uuid
from pathlib import Path
from typing import List, Dict, Iterable

import pymupdf                                   # PyMuPDF
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import chromadb
from openai import OpenAI


class RAGSys:
    """
    1. Crawls *.pdf under `pdf_dir`.
    2. Splits pages into paragraph-level chunks (merging bullet lists).
    3. Embeds with SentenceTransformer and stores in ChromaDB.
    4. Retrieves raw chunks (search) or crafts a GPT-4o-mini answer (ask_gpt).
    """

    # ------------------------ init ------------------------ #
    def __init__(
        self,
        pdf_dir: str | Path,
        chroma_dir: str | Path = "./vectordb",
        collection_name: str = "cyberpunk_library",
        embed_model_name: str = "all-MiniLM-L6-v2",
        openai_api_key: str | None = None,          # optional
    ):
        self.pdf_dir = Path(pdf_dir)
        self.chroma_dir = Path(chroma_dir)
        self.collection_name = collection_name
        self.embedder = SentenceTransformer(embed_model_name)
        self.db = chromadb.PersistentClient(path=str(self.chroma_dir))
        self.collection = self.db.get_or_create_collection(self.collection_name)
        self.open_ai = OpenAI(api_key=openai_api_key) if openai_api_key else None

    # --------------------- public API --------------------- #
    def build_index(self) -> None:
        """Embed & upsert chunks for **all PDFs** if collection is empty."""
        if self.collection.count() > 0:
            print("✓ Chroma collection already populated — skipping rebuild")
            return

        print(f"⏳ Scanning {self.pdf_dir} for PDFs …")
        pdf_paths = [
            p for p in self.pdf_dir.rglob("*.pdf") if p.is_file()
        ]
        print(f"⏳ Found {len(pdf_paths)} PDF(s). Chunking & embedding …")

        batch, ids, docs, metas = [], [], [], []
        for pdf in pdf_paths:
            for ch in self._chunk_pdf(pdf):
                batch.append(ch["text"])
                ids.append(ch["id"])
                docs.append(ch["text"])
                metas.append(ch["meta"])
                if len(batch) == 128:
                    self._flush(batch, ids, docs, metas)
                    batch, ids, docs, metas = [], [], [], []

        if batch:
            self._flush(batch, ids, docs, metas)

        print("✓ Index ready")

    def search(self, query: str, k: int = 5) -> List[Dict]:
        """Return top-k raw chunks."""
        q = self.embedder.encode(query).tolist()
        res = self.collection.query(query_embeddings=[q], n_results=k)
        return [
            {
                "text": d,
                "page": m["page"],
                "chapter": m["chapter"],
                "source_pdf": m["source_pdf"],
            }
            for d, m in zip(res["documents"][0], res["metadatas"][0])
        ]

    def ask_gpt(self, user_query: str, k: int = 5, temperature: float = 0.4) -> str:
        if not self.open_ai:
            raise RuntimeError("OpenAI key not supplied; can't call ask_gpt().")

        rules = self.search(user_query, k=k)
        context = "\n\n".join(
            f"{r['source_pdf']} [p.{r['page']} – {r['chapter']}]\n{r['text']}"
            for r in rules
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a Cyberpunk RED game assistant. Answer the user's question "
                    "using only the official rules. Include relevant citations "
                    "(PDF name, page number, chapter). If the rules are unclear, say so."
                )
            },
            {"role": "user", "content": f"{user_query}\n\nRelevant Rules:\n{context}"},
        ]

        rsp = self.open_ai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=temperature,
        )
        return rsp.choices[0].message.content

    # ------------- debugging helpers ------------------ #
    def page_chunks(self, pdf_name: str, page: int) -> List[str]:
        """Return all chunks stored for a given PDF + page number."""
        return self.collection.query(
            query_texts=["*"],  # wildcard text
            n_results=1000,
            where={
                "$and": [  # 👈 single operator at the top
                    {"source_pdf": {"$eq": pdf_name}},
                    {"page": {"$eq": page}}
                ]
            }
        )["documents"][0]

    def debug_page(self, pdf_name: str, page: int, max_chars: int = 120):
        chunks = self.page_chunks(pdf_name, page)
        if not chunks:
            print(f"No chunks for {pdf_name} page {page}")
            return
        for i, txt in enumerate(chunks, 1):
            preview = txt#[:max_chars] + ("…" if len(txt) > max_chars else "")
            print(f"[{i}/{len(chunks)}] {preview}\n")

    # -------------------- internals ---------------------- #
    def _flush(self, batch, ids, docs, metas):
        embs = self.embedder.encode(batch).tolist()
        self.collection.add(ids=ids, embeddings=embs, documents=docs, metadatas=metas)

    def _chunk_pdf(self, pdf_path: Path) -> Iterable[Dict]:
        book = pymupdf.open(pdf_path)
        toc = book.get_toc(simple=True)
        page_map, t_i = {}, 0
        for p in range(len(book)):
            while t_i + 1 < len(toc) and toc[t_i + 1][2] <= p + 1:
                t_i += 1
            page_map[p] = toc[t_i][1] if toc else "Unknown"

        for p in range(len(book)):
            raw = [ln.strip() for ln in book.load_page(p).get_text("text").splitlines()]
            merged, buf = [], []
            for ln in raw + [""]:
                short_or_bullet = ln and (len(ln) < 30 or re.match(r"^[•\-\u2022\*]", ln))
                if short_or_bullet:
                    buf.append(re.sub(r"^[•\-\u2022\*]\s*", "", ln))
                else:
                    if buf:
                        merged.append(" • ".join(buf)); buf = []
                    if ln:
                        merged.append(ln)

            for para in re.split(r"\n{2,}", "\n".join(merged)):
                clean = para.strip()
                if len(clean) >= 30:
                    yield {
                        "id": str(uuid.uuid4()),
                        "text": clean,
                        "meta": {
                            "page": p + 1,
                            "chapter": page_map[p],
                            "source_pdf": pdf_path.name,
                        },
                    }
        book.close()
