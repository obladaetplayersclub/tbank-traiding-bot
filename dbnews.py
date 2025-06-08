import psycopg2
from pgvector import Vector
from pgvector.psycopg2 import register_vector
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
                 threshold_jaccard=0.1,
                 threshold_cosine=0.4,
                 alpha=0.5,
                 sentiment_diff_thresh=2):
        self.conn = psycopg2.connect(**db_config)
        register_vector(self.conn)
        self.shingle_size = shingle_size
        self.n_perm = n_perm
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.threshold_j = threshold_jaccard
        self.threshold_c = threshold_cosine
        self.alpha = alpha
        self.sentiment_diff_thresh = sentiment_diff_thresh

    def _minhash(self, text: str) -> bytes:
        """Создаёт и сериализует MinHash подпись"""
        m = MinHash(num_perm=self.n_perm)
        for i in range(len(text) - self.shingle_size + 1):
            m.update(text[i:i + self.shingle_size].encode('utf-8'))
        return pickle.dumps(m)

    def _embed(self, text: str) -> np.ndarray:
        vec = self.model.encode([text], convert_to_numpy=True)[0]
        return vec / np.linalg.norm(vec)

    def _is_duplicate_for_ticker(self, text, ticker, new_pol, new_int):
        cur = self.conn.cursor()
        vec_np = self._embed(text)
        vec_pg = Vector(vec_np.tolist())

        query = """
        SELECT id, text, polarity, intensity, minhash, embedding
        FROM news
        WHERE ticker = %s
        ORDER BY embedding <-> %s
        LIMIT 20
        """
        cur.execute(query, (ticker, vec_pg))  # передаём Vector, не list
        rows = cur.fetchall()
        cur.close()

        if not rows:
            return False

        m_new = pickle.loads(self._minhash(text))
        for row in rows:
            old_id, old_text, old_pol, old_int, mh_bytes, emb_vec = row

            if new_pol != old_pol or abs(new_int - old_int) > self.sentiment_diff_thresh:
                continue

            m_old = pickle.loads(bytes(mh_bytes))
            jaccard = m_new.jaccard(m_old)

            vec_old = np.array(emb_vec, dtype=np.float32)
            vec_new = np.array(vec_np, dtype=np.float32)
            cosine = float(np.dot(vec_old, vec_new) / (np.linalg.norm(vec_old) * np.linalg.norm(vec_new)))

            if jaccard >= self.threshold_j and cosine >= self.threshold_c:
                return True

        return False

    def add_news(self, text: str, tickers: list[str], polarity: str, intensity: int) -> bool:
        """Добавляет новость, если она уникальна хотя бы для одного тикера"""
        unique_tickers = []
        for ticker in tickers:
            if not self._is_duplicate_for_ticker(text, ticker, polarity, intensity):
                unique_tickers.append(ticker)

        if not unique_tickers:
            return False

        cur = self.conn.cursor()
        minhash_bytes = self._minhash(text)
        embedding_list = self._embed(text)

        for ticker in unique_tickers:
            cur.execute("""
                INSERT INTO news (text, ticker, polarity, intensity, minhash, embedding)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (text, ticker, polarity, intensity, memoryview(minhash_bytes), embedding_list))

        self.conn.commit()
        cur.close()
        return True

    def get_unique(self) -> list[dict]:
        """Возвращает все уникальные новости с привязкой к тикерам"""
        cur = self.conn.cursor()
        cur.execute("SELECT DISTINCT text, ticker FROM news")
        rows = cur.fetchall()
        result = {}
        for text, ticker in rows:
            if text not in result:
                result[text] = {'text': text, 'tickers': []}
            result[text]['tickers'].append(ticker)
        cur.close()
        return list(result.values())

    def close(self):
        """Закрывает соединение с БД"""
        self.conn.close()