"""The manager: decides which brain answers each message.

Auto mode  -> 1. my dataset (if a very similar question exists)
              2. Gemini API (for everything outside the dataset)
              3. my trained model (if Gemini fails)
Gemini     -> only Gemini.
My model   -> only my trained model.
"""

import logging

from .api_bot import GeminiBot
from .local_bot import LocalBot
from .rag_bot import DatasetBot

logger = logging.getLogger("minichatgpt")

MODE_AUTO = "Auto (Dataset → Gemini → My model)"
MODE_GEMINI = "Gemini only"
MODE_LOCAL = "My model only"
MODES = [MODE_AUTO, MODE_GEMINI, MODE_LOCAL]

SOURCE_DATASET = "dataset"
SOURCE_GEMINI = "gemini"
SOURCE_LOCAL = "local"
SOURCE_ERROR = "error"


def short_error(error):
    """Make API errors short and easy to read."""
    text = str(error)
    if "GEMINI_API_KEY is missing" in text:
        return "No Gemini API key"
    if "429" in text or "RESOURCE_EXHAUSTED" in text or "quota" in text.lower():
        return "Gemini free limit reached"
    if "503" in text or "UNAVAILABLE" in text:
        return "Gemini is busy right now"
    if "API key" in text or "API_KEY" in text or "401" in text or "403" in text:
        return "Gemini API key problem"
    if "404" in text or "NOT_FOUND" in text:
        return "Gemini model not found (check GEMINI_MODEL in .env)"
    return "Gemini not reachable"


class ChatRouter:
    def __init__(self):
        self.dataset = DatasetBot()
        self.gemini = GeminiBot()
        self.local = LocalBot()

    def status(self):
        """Simple status for the sidebar."""
        return {
            "dataset": self.dataset.is_available,
            "gemini": self.gemini.is_configured,
            "local": self.local.is_available,
        }

    def stream(self, message, history, mode):
        """Yield (reply_so_far, source, note) while the answer is being made."""
        # Step 1 (Auto only): answer from the dataset if a very similar question exists
        if mode == MODE_AUTO:
            answer, score, matched = self.dataset.search(message)
            if answer:
                logger.info("Dataset match %.2f: %r", score, matched)
                yield answer, SOURCE_DATASET, f"similarity {score:.2f}"
                return
            logger.info("No dataset match (best %.2f) -> asking Gemini", score)

        # Step 2: Gemini for everything outside the dataset
        if mode in (MODE_AUTO, MODE_GEMINI):
            reply = ""
            try:
                for piece in self.gemini.stream_reply(message, history):
                    reply += piece
                    yield reply, SOURCE_GEMINI, None
                if reply:
                    return
                raise RuntimeError("Gemini returned an empty answer.")
            except Exception as error:  # any API failure triggers the fallback
                logger.warning("Gemini failed: %s", error)
                if reply:
                    # Connection broke in the middle of an answer: keep what we got
                    yield reply + "\n\n_(The answer was cut off.)_", SOURCE_GEMINI, None
                    return
                if mode == MODE_GEMINI:
                    yield f"⚠️ {short_error(error)}. Please try again, or switch to Auto mode.", SOURCE_ERROR, None
                    return
                note = f"{short_error(error)} — switched to my model"
        else:
            note = None

        # Step 3: fallback / local mode: use my trained model
        try:
            yield self.local.reply(message), SOURCE_LOCAL, note
        except Exception as error:
            logger.warning("Local model failed: %s", error)
            yield f"⚠️ My model is not available: {error}", SOURCE_ERROR, note