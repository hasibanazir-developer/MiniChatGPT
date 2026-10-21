"""Dataset brain: finds the most similar question in my cleaned DailyDialog data.

How it works (retrieval):
  1. All dataset questions are turned into TF-IDF vectors (word importance scores).
  2. A new message is turned into a vector the same way.
  3. Cosine similarity finds the closest dataset question (0 = different, 1 = identical).
  4. If the similarity is high enough, the dataset's answer is used.
     Otherwise the router asks the Gemini API.
"""

import json
import logging
import re

from . import config

logger = logging.getLogger("minichatgpt")


def _normalize(text):
    """Same style as the cleaned data: lowercase, simple punctuation removed."""
    return re.sub(r"[^a-z0-9' ]", " ", text.lower())


def _is_messy(answer):
    """Skip dataset answers that only make sense in their original conversation."""
    return bool(
        re.search(r"x{3,}", answer)                 # "xxxxxxxx" placeholders
        or ":" in answer[:25]                         # "mr.: ..." speaker labels
        or len(answer.split()) > 14                   # long, story-like answers
        or re.search(r"\b(mr|mrs|ms|miss|dr|sir|madam)\b", answer)  # talks to a named person
    )


def _capitalize(text):
    """The dataset is lowercase: make 'i' -> 'I' and capitalize each sentence."""
    text = re.sub(r"\bi\b", "I", text)
    return re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)


class DatasetBot:
    """Answers from the dataset when a very similar question exists."""

    def __init__(self):
        self.questions = []
        self.answers = []
        self.vectorizer = None
        self.matrix = None
        self.answer_vectorizer = None
        self.answer_matrix = None
        self._build()

    @property
    def is_available(self):
        return self.matrix is not None

    def _build(self):
        """Read the dataset and build the search index (about 2 seconds)."""
        if not config.DATASET_FILE.exists():
            logger.warning("Dataset not found: %s (dataset answers are turned off)", config.DATASET_FILE)
            return

        from sklearn.feature_extraction.text import TfidfVectorizer

        with config.DATASET_FILE.open("r", encoding="utf-8") as file:
            for line in file:
                record = json.loads(line)
                if _is_messy(record["answer"]):
                    continue
                self.questions.append(record["question"])
                self.answers.append(record["answer"])

        # Single words and word pairs (e.g. "how are", "are you") both count
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True,
                                          preprocessor=_normalize)
        self.matrix = self.vectorizer.fit_transform(self.questions)
        # Answer vectors: used to pick the most typical answer when there are many
        self.answer_vectorizer = TfidfVectorizer(preprocessor=_normalize)
        self.answer_matrix = self.answer_vectorizer.fit_transform(self.answers)
        logger.info("Dataset search ready: %d questions", len(self.questions))

    def search(self, message):
        """Return (answer, score, matched_question), or (None, score, None) if no good match."""
        if not self.is_available or not message.strip():
            return None, 0.0, None

        from sklearn.metrics.pairwise import linear_kernel

        scores = linear_kernel(self.vectorizer.transform([message]), self.matrix).ravel()
        best = float(scores.max())
        if best < config.DATASET_MIN_SCORE:
            return None, best, None

        # Many questions (like "hello") appear many times with different answers.
        # Pick the most TYPICAL answer: the one most similar to all the other answers,
        # with a small preference for shorter answers.
        top = [i for i in scores.argsort()[::-1][:300] if scores[i] >= best - 0.02]
        if len(top) == 1:
            index = top[0]
        else:
            import numpy as np

            subset = self.answer_matrix[top]
            similarity = linear_kernel(subset, subset)
            np.fill_diagonal(similarity, 0)
            lengths = np.array([len(self.answers[i].split()) for i in top])
            typical = similarity.mean(axis=1) - 0.004 * lengths
            index = top[int(typical.argmax())]
        return _capitalize(self.answers[index]), best, self.questions[index]