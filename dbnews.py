import psycopg2
from pgvector.psycopg2 import register_vector
from pgvector import Vector
import numpy as np
from sentence_transformers import SentenceTransformer
from datasketch import MinHash
import pickle


class DBNewsDeduplicator:
    def __init__(self,
                 db_config,
                 shingle_size=4,
                 n_perm=256,
                 emb_model='all-MiniLM-L6-v2',
                 threshold_jaccard=0.05,
                 threshold_cosine=0.4,
                 alpha=0.5,
                 sentiment_diff_thresh=2):
        self.conn = psycopg2.connect(**db_config)
        register_vector(self.conn)
        self.shingle_size = shingle_size
        self.n_perm = n_perm
        self.model = SentenceTransformer(emb_model)
        self.threshold_j = threshold_jaccard
        self.threshold_c = threshold_cosine
        self.alpha = alpha
        self.sentiment_diff_thresh = sentiment_diff_thresh

    def _minhash(self, text: str) -> bytes:
        m = MinHash(num_perm=self.n_perm)
        for i in range(len(text) - self.shingle_size + 1):
            m.update(text[i:i + self.shingle_size].encode('utf-8'))
        return pickle.dumps(m)

    def _embed(self, text: str) -> np.ndarray:
        vec = self.model.encode([text], convert_to_numpy=True)[0]
        return vec / np.linalg.norm(vec)

    def _is_duplicate_for_ticker(self, text: str, ticker: str, new_pol: str, new_int: int) -> bool:
        cur = self.conn.cursor()
        vec_np = self._embed(text)
        vec_pg = Vector(vec_np.tolist())

        query = """
        SELECT id, text, ticker, polarity, intensity, minhash, embedding
        FROM news
        WHERE %s = ANY(ticker)
        ORDER BY embedding <-> %s
        LIMIT 20
        """
        cur.execute(query, (ticker, vec_pg))
        rows = cur.fetchall()
        cur.close()

        if not rows:
            return False

        m_new = pickle.loads(self._minhash(text))
        for row in rows:
            old_id, old_text, old_tickers, old_pol, old_int, mh_bytes, emb_vec = row

            if new_pol != old_pol or abs(new_int - old_int) > self.sentiment_diff_thresh:
                continue

            m_old = pickle.loads(bytes(mh_bytes))
            jaccard = m_new.jaccard(m_old)

            vec_old = np.array(emb_vec, dtype=np.float32)
            cosine = float(np.dot(vec_old, vec_np) / (np.linalg.norm(vec_old) * np.linalg.norm(vec_np)))

            if jaccard >= self.threshold_j and cosine >= self.threshold_c:
                return True

        return False

    def add_news(self, text: str, tickers: list[str], polarity: str, intensity: int) -> bool:
        unique_tickers = []
        for ticker in tickers:
            if not self._is_duplicate_for_ticker(text, ticker, polarity, intensity):
                unique_tickers.append(ticker)

        if not unique_tickers:
            return False

        cur = self.conn.cursor()
        minhash_bytes = self._minhash(text)
        embedding_vec = Vector(self._embed(text).tolist())

        cur.execute("""
            INSERT INTO news (text, ticker, polarity, intensity, minhash, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (text, tickers, polarity, intensity, memoryview(minhash_bytes), embedding_vec))

        self.conn.commit()
        cur.close()
        return True

    def get_unique(self) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT text, ticker FROM news")
        rows = cur.fetchall()
        cur.close()

        result = []
        for text, tickers in rows:
            result.append({
                'text': text,
                'tickers': tickers
            })
        return result

    def close(self):
        self.conn.close()