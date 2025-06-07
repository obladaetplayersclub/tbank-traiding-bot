import spacy
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline
from rapidfuzz import fuzz
from datasketch import MinHash, MinHashLSH
from sentence_transformers import SentenceTransformer
import numpy as np
from annoy import AnnoyIndex

class ClusteringUniqueChecker:
    """
    Проверщик уникальности новостей по кластеризации эмбеддингов и числовой тональности,
    основанной на prototype-сравнении.
    Новость считается дубликатом только если:
      - косинусная схожесть ≥ sim_threshold
      - разница тональности < sent_threshold
    """
    def __init__(self, ticker_list: list[str], sim_threshold: float = 0.8, sent_threshold: float = 0.2):
        # компактная модель для эмбеддингов
        self.embed_model = SentenceTransformer('all-MiniLM-L6-v2')
        # подготовка prototype embeddings для тональности
        pos_samples = ["купил акцию", "рост цены", "покупка активов"]
        neg_samples = ["продал акцию", "падение цены", "продажа активов"]
        pos_embs = self.embed_model.encode(pos_samples)
        neg_embs = self.embed_model.encode(neg_samples)
        # усреднённые прототипы
        self.pos_proto = pos_embs.mean(axis=0)
        self.neg_proto = neg_embs.mean(axis=0)
        # храним эмбеддинги и тональности по тикерам
        self.embeddings_by_ticker = {t: [] for t in ticker_list}
        self.sentiments_by_ticker = {t: [] for t in ticker_list}
        # пороги сравнения
        self.sim_threshold = sim_threshold
        self.sent_threshold = sent_threshold
        # накопленные уникальные новости
        self.unique_news = []  # каждый: {'text': str, 'tickers': list[str], 'sentiment': float}

    def _sentiment_score(self, emb: list[float]) -> float:
        """
        Числовая тональность на основе cosine_similarity к pos/neg prototype embeddings.
        возвращает значение в [-1,1]:
          +1 → очень положительное, -1 → очень отрицательное
        """
        sim_pos = cosine_similarity([emb], [self.pos_proto])[0][0]
        sim_neg = cosine_similarity([emb], [self.neg_proto])[0][0]
        # нормируем в диапазон [-1,1]
        return (sim_pos - sim_neg) / (sim_pos + sim_neg + 1e-8)

    def is_unique(self, emb: list[float], sentiment: float, ticker: str) -> bool:
        """
        Дубликатом считается, если найдена старая новость с:
          cosine ≥ sim_threshold и |sent_diff| < sent_threshold
        """
        ex_embs = self.embeddings_by_ticker[ticker]
        ex_sents = self.sentiments_by_ticker[ticker]
        if not ex_embs:
            return True
        sims = cosine_similarity([emb], ex_embs)[0]
        for score, old_sent in zip(sims, ex_sents):
            if score >= self.sim_threshold and abs(sentiment - old_sent) < self.sent_threshold:
                return False
        return True

    def add_news(self, text: str, tickers: list[str]) -> bool:
        """
        Добавляет новость, если она уникальна хотя бы для одного тикера.
        Возвращает True, если добавлена.
        """
        emb = self.embed_model.encode(text)
        sentiment = self._sentiment_score(emb)
        added = False
        for t in tickers:
            if self.is_unique(emb, sentiment, t):
                self.embeddings_by_ticker[t].append(emb)
                self.sentiments_by_ticker[t].append(sentiment)
                added = True
        if added:
            self.unique_news.append({'text': text, 'tickers': tickers, 'sentiment': sentiment})
        return added

    def get_unique(self) -> list[dict]:
        """Возвращает список уникальных новостей с их тональностью и тикерами."""
        return self.unique_news


class AdvancedUniqueChecker:
    """
    Проверщик уникальности новостей, использующий:
      1) Семантические роли (глагольная лемма)
      2) Антоним-лексикон для ключевых глаголов
      3) Двойной порог embedding-similarity
      4) Числовую тональность через prototype-метод
    """

    def __init__(self,
                 ticker_list: list[str],
                 low_thresh: float = 0.7,
                 high_thresh: float = 0.9,
                 sent_thresh: float = 0.2):
        # NLP и embedding модели
        self.nlp = spacy.load('ru_core_news_sm')
        self.embed_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Прототипы для тональности
        pos_samples = ["купил акцию", "рост цены", "увеличил капитал"]
        neg_samples = ["продал акцию", "падение цены", "уменьшил капитал"]
        pos_embs = self.embed_model.encode(pos_samples)
        neg_embs = self.embed_model.encode(neg_samples)
        self.pos_proto = pos_embs.mean(axis=0)
        self.neg_proto = neg_embs.mean(axis=0)

        # Пороги
        self.low_thresh = low_thresh
        self.high_thresh = high_thresh
        self.sent_thresh = sent_thresh

        # Антоним-лексикон для лемм
        self.antonyms = {
            'купить': 'продать', 'продать': 'купить',
            'расти': 'падать', 'падать': 'расти',
            'увеличить': 'уменьшить', 'уменьшить': 'увеличить'
        }

        # Храним по тикеру: список записей {'emb','sent','verb'}
        self.entries = {t: [] for t in ticker_list}
        self.unique_news = []

    def _extract_verb(self, text: str) -> str:
        """
        Находит первую глагольную лемму в тексте через spaCy.
        """
        doc = self.nlp(text)
        for token in doc:
            if token.pos_ == 'VERB':
                return token.lemma_
        return ''

    def _sentiment_score(self, emb: list[float]) -> float:
        """
        Числовая тональность [-1,1] через cosine similarity к прототипам.
        """
        sim_pos = cosine_similarity([emb], [self.pos_proto])[0][0]
        sim_neg = cosine_similarity([emb], [self.neg_proto])[0][0]
        return (sim_pos - sim_neg) / (sim_pos + sim_neg + 1e-8)

    def _are_antonyms(self, v1: str, v2: str) -> bool:
        """
        Проверка, являются ли две глагольные леммы антонимами.
        """
        return self.antonyms.get(v1) == v2 or self.antonyms.get(v2) == v1

    def is_unique_for_ticker(self,
                             emb: list[float],
                             sentiment: float,
                             verb: str,
                             ticker: str) -> bool:
        """
        Дубликат, если найдена старая запись, где:
          - cosine ≥ high_thresh и глагольные леммы совпадают
          - или low_thresh ≤ cosine < high_thresh и |sent_diff| < sent_thresh
        Антонимы и cosine < low_thresh всегда считаются уникальными.
        """
        for entry in self.entries[ticker]:
            old_emb, old_sent, old_verb = entry['emb'], entry['sent'], entry['verb']
            score = cosine_similarity([emb], [old_emb])[0][0]
            # 1) Антонимы → уникально
            if self._are_antonyms(verb, old_verb):
                continue
            # 2) явно разные по косинусу → уникально
            if score < self.low_thresh:
                continue
            # 3) явный дубликат по выс. порогу + одинаков. лемма
            if score >= self.high_thresh and verb == old_verb:
                return False
            # 4) среднее сходство → проверяем тональность
            if score >= self.low_thresh and score < self.high_thresh:
                if abs(sentiment - old_sent) < self.sent_thresh:
                    return False
        return True

    def add_news(self, text: str, tickers: list[str]) -> bool:
        """
        Проверяет и добавляет новость, если уникальна по хотя бы одному тикеру.
        """
        emb = self.embed_model.encode(text)
        sentiment = self._sentiment_score(emb)
        verb = self._extract_verb(text)
        added = False
        for t in tickers:
            if self.is_unique_for_ticker(emb, sentiment, verb, t):
                self.entries[t].append({'emb': emb, 'sent': sentiment, 'verb': verb})
                added = True
        if added:
            self.unique_news.append({'text': text, 'tickers': tickers,
                                     'sent': sentiment, 'verb': verb})
        return added

    def get_unique(self) -> list[dict]:
        """Возвращает список уникальных новостей с их метаданными."""
        return self.unique_news

class NLIUniqueChecker:
    """
    Проверка уникальности новостей с учётом:
      1) Семантического разбора (глагол, объект)
      2) Двойных порогов по embedding-сходству
      3) Числовой тональности prototype-методом
      4) NLI через компактную distilBART-MNLI модель
    """
    def __init__(self,
                 ticker_list: list[str],
                 low_thresh: float = 0.7,
                 high_thresh: float = 0.9,
                 sent_thresh: float = 0.2,
                 obj_thresh: float = 80):
        # NLP и embedding модели
        self.nlp = spacy.load('ru_core_news_sm')
        self.embed_model = SentenceTransformer('all-MiniLM-L6-v2')
        # Zero-shot NLI pipeline на базе компактного distilBART-MNLI
        self.nli = pipeline(
            "zero-shot-classification",
            model="valhalla/distilbart-mnli-12-6"
        )
        # Прототипы для тональности
        pos_samples = ["купил акцию", "рост цены", "увеличил капитал"]
        neg_samples = ["продал акцию", "падение цены", "уменьшил капитал"]
        pos_embs = self.embed_model.encode(pos_samples)
        neg_embs = self.embed_model.encode(neg_samples)
        self.pos_proto = pos_embs.mean(axis=0)
        self.neg_proto = neg_embs.mean(axis=0)
        # Пороги
        self.low_thresh = low_thresh
        self.high_thresh = high_thresh
        self.sent_thresh = sent_thresh
        self.obj_thresh = obj_thresh
        # Храним по тикеру: список записей {'text','emb','sent','verb','obj'}
        self.entries = {t: [] for t in ticker_list}
        self.unique_news = []

    def _extract_verb(self, text: str) -> str:
        doc = self.nlp(text)
        for token in doc:
            if token.pos_ == 'VERB':
                return token.lemma_.lower()
        return ''

    def _extract_object(self, text: str) -> str:
        doc = self.nlp(text)
        for token in doc:
            if token.dep_ in ('obj', 'iobj', 'obl') and token.pos_ in ('NOUN', 'PROPN'):
                return token.lemma_.lower()
        return ''

    def _sentiment_score(self, emb) -> float:
        sim_pos = cosine_similarity([emb], [self.pos_proto])[0][0]
        sim_neg = cosine_similarity([emb], [self.neg_proto])[0][0]
        return (sim_pos - sim_neg) / (sim_pos + sim_neg + 1e-8)

    def _run_nli(self, premise: str, hypothesis: str) -> str:
        out = self.nli(
            sequences=hypothesis,
            candidate_labels=["entailment", "neutral", "contradiction"],
            hypothesis_template="\"{hypothesis}\" следует из: \"{premise}\"?"
        )
        return out['labels'][0]

    def _are_same_object(self, o1: str, o2: str) -> bool:
        if not o1 or not o2:
            return o1 == o2
        return fuzz.ratio(o1, o2) >= self.obj_thresh

    def is_unique_for_ticker(self, new, old) -> bool:
        emb, sent, verb, obj, text = new['emb'], new['sent'], new['verb'], new['obj'], new['text']
        old_emb, old_sent, old_verb, old_obj, old_text = old['emb'], old['sent'], old['verb'], old['obj'], old['text']
        score = cosine_similarity([emb], [old_emb])[0][0]
        # 1) разные глаголы
        if verb and old_verb and verb != old_verb:
            return True
        # 2) разные объекты
        if obj and old_obj and not self._are_same_object(obj, old_obj):
            return True
        # 3) быстрые пороги
        if score < self.low_thresh:
            return True
        if score >= self.high_thresh and verb == old_verb and self._are_same_object(obj, old_obj):
            return False
        # 4) средняя зона: тональность
        if self.low_thresh <= score < self.high_thresh:
            if abs(sent - old_sent) >= self.sent_thresh:
                return True
            label = self._run_nli(old_text, text)
            if label == 'contradiction':
                return True
            if label == 'entailment':
                return False
            mid = (self.low_thresh + self.high_thresh) / 2
            return score < mid
        return True

    def add_news(self, text: str, tickers: list[str]) -> bool:
        emb = self.embed_model.encode(text)
        sent = self._sentiment_score(emb)
        verb = self._extract_verb(text)
        obj = self._extract_object(text)
        entry = {'text': text, 'emb': emb, 'sent': sent, 'verb': verb, 'obj': obj}
        added = False
        for t in tickers:
            if all(self.is_unique_for_ticker(entry, old) for old in self.entries[t]):
                self.entries[t].append(entry)
                added = True
        if added:
            self.unique_news.append(entry)
        return added

    def get_unique(self) -> list[dict]:
        return self.unique_news


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