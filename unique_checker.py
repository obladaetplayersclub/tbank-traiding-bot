from datasketch import MinHash, MinHashLSH
from sentence_transformers import SentenceTransformer
import numpy as np
from annoy import AnnoyIndex

class NewsDeduplicator:
    def __init__(self,
                 ticker_list: list[str],      # список тикеров для предсоздания индексов; новые тикеры будут добавляться автоматически
                 n_perm: int = 256,           # количество пермутаций для MinHash; больше → более точная оценка Jaccard, но медленнее
                 shingle_size: int = 4,       # размер шингла (количество символов) для разбивки текста; меньше → более тонкая детализация, но шумнее
                 emb_model: str = 'all-MiniLM-L6-v2',  # название Bi-Encoder модели для эмбеддингов (SBERT)
                 threshold_jaccard: float = 0.1,       # минимальный Jaccard для отметки «дубликат» при AND-проверке
                 threshold_cosine: float = 0.4,       # минимальный cosine similarity для отметки «дубликат» при AND-проверке
                 alpha: float = 0.5,           # вес cosine в комбинированном скоре: score = α·cosine + (1–α)·jaccard
                 annoy_trees: int = 30,        # число деревьев в Annoy-индексе; больше → точнее поиск, но дольше билд
                 sentiment_diff_thresh: int = 2  # допустимая разница интенсивности тональности (1–10); выше → менее строгая фильтрация по настроению
                 ):
        # Параметры MinHash + LSH
        self.n_perm = n_perm
        self.shingle_size = shingle_size
        self.threshold_j = threshold_jaccard

        # Параметры эмбеддингов и Annoy (Bi-Encoder)
        self.model = SentenceTransformer(emb_model)
        self.emb_dim = self.model.get_sentence_embedding_dimension()
        self.threshold_c = threshold_cosine
        self.alpha = alpha
        self.annoy_trees = annoy_trees

        # Параметр фильтрации по разнице тональности
        self.sentiment_diff_thresh = sentiment_diff_thresh

        # Инициализация по-тикерных индексов
        # Структура для каждого тикера:
        # {
        #   'lsh': MinHashLSH(...),
        #   'annoy': AnnoyIndex(...),
        #   'id_to_text': {},
        #   'id_to_sentiment': {},  # polarity + intensity
        #   'next_id': 0
        # }
        self.ticker_indices: dict[str, dict] = {}
        for t in ticker_list:
            self._init_indices_for_ticker(t)

        # Хранилище окончательно добавленных уникальных новостей
        self.unique_news: list[dict] = []

    def _init_indices_for_ticker(self, ticker: str):
        """Создает пустые LSH и Annoy индексы для нового тикера."""
        self.ticker_indices[ticker] = {
            'lsh': MinHashLSH(threshold=self.threshold_j, num_perm=self.n_perm),
            'annoy': AnnoyIndex(self.emb_dim, 'angular'),
            'id_to_text': {},
            'id_to_sentiment': {},  # key → (polarity, intensity)
            'next_id': 0
        }

    def _minhash(self, text: str) -> MinHash:
        """Строит MinHash-подпись по шинглам заданного размера."""
        m = MinHash(num_perm=self.n_perm)
        shingles = [text[i:i + self.shingle_size]
                    for i in range(len(text) - self.shingle_size + 1)]
        for sh in shingles:
            m.update(sh.encode('utf8'))
        return m

    def _embed(self, text: str) -> np.ndarray:
        """Возвращает L2-нормированный embedding для текста."""
        vec = self.model.encode([text], convert_to_numpy=True)
        return vec / np.linalg.norm(vec, axis=1, keepdims=True)

    def _is_duplicate_for_ticker(self,
                                 text: str,
                                 ticker: str,
                                 new_pol: str,
                                 new_int: int) -> bool:
        """
        Проверяет, является ли текст дубликатом внутри данного тикера.
        Сначала фильтр по тональности (polarity+intensity), затем по Jaccard и Cosine.
        """
        idx = self.ticker_indices[ticker]
        if idx['next_id'] == 0:
            return False

        # кандидаты по MinHashLSH
        m_new = self._minhash(text)
        cand_lsh = idx['lsh'].query(m_new)

        # кандидаты по Annoy (Bi-Encoder)
        vec_new = self._embed(text)[0]
        cand_annoy = idx['annoy'].get_nns_by_vector(vec_new, 20)

        for cid in set(cand_lsh) | set(cand_annoy):
            old = idx['id_to_text'][cid]
            old_pol, old_int = idx['id_to_sentiment'][cid]

            # жесткая фильтрация по тональности
            if new_pol != old_pol or abs(new_int - old_int) > self.sentiment_diff_thresh:
                continue

            # вычисляем метрики
            j = m_new.jaccard(self._minhash(old))
            vec_old = self._embed(old)[0]
            c = float(np.dot(vec_new, vec_old))
            score = self.alpha * c + (1 - self.alpha) * j

            # AND-логика: обе метрики должны быть ≥ своих порогов
            if j >= self.threshold_j and c >= self.threshold_c:
                return True
            # или комбинированный скор:
            #if score >= max(self.threshold_j, self.threshold_c):
             #   return True

        return False

    def _add_to_indices_for_ticker(self,
                                   text: str,
                                   ticker: str,
                                   pol: str,
                                   intensity: int):
        """
        Добавляет текст, его тональность и векторы в LSH и Annoy индексы для тикера.
        Перестраивает Annoy с нуля для корректности.
        """
        idx = self.ticker_indices[ticker]
        key = idx['next_id']
        idx['id_to_text'][key] = text
        idx['id_to_sentiment'][key] = (pol, intensity)
        idx['next_id'] += 1

        # LSH вставка
        idx['lsh'].insert(key, self._minhash(text))

        # пересборка Annoy
        new_annoy = AnnoyIndex(self.emb_dim, 'angular')
        for k, txt in idx['id_to_text'].items():
            vec = self._embed(txt)[0]
            new_annoy.add_item(k, vec)
        new_annoy.build(self.annoy_trees)
        idx['annoy'] = new_annoy

    def add_news(self,
                 text: str,
                 tickers: list[str],
                 polarity: str,
                 intensity: int) -> bool:
        """
        Основной метод.
        Принимает текст, список тикеров, а также заранее вычисленные
        polarity ('POSITIVE'/'NEGATIVE'/'NEUTRAL') и intensity (1–10).
        Возвращает True, если новость уникальна хотя бы для одного тикера,
        False — если дубликат для всех.
        """
        unique_tickers = []
        for t in tickers:
            if t not in self.ticker_indices:
                self._init_indices_for_ticker(t)
            if not self._is_duplicate_for_ticker(text, t, polarity, intensity):
                unique_tickers.append(t)

        if not unique_tickers:
            return False

        for t in unique_tickers:
            self._add_to_indices_for_ticker(text, t, polarity, intensity)

        self.unique_news.append({
            'text': text,
            'tickers': unique_tickers
        })
        return True

    def get_unique(self) -> list[dict]:
        """Возвращает список словарей {'text': ..., 'tickers': ...} для всех уникальных новостей."""
        return self.unique_news