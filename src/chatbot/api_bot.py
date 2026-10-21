"""Main brain: gets answers from the free Google Gemini API."""

import logging
import time

from google import genai
from google.genai import types

from . import config

logger = logging.getLogger("minichatgpt")


def is_busy(error):
    """True when Google says the model is busy (error 503)."""
    text = str(error)
    return "503" in text or "UNAVAILABLE" in text


class GeminiBot:
    """Sends the chat (with memory) to Gemini and streams the reply back."""

    def __init__(self):
        self.client = None
        self.use_thinking_setting = True  # turned off if a model does not support it
        if config.GEMINI_API_KEY:
                        self.client = genai.Client(
                api_key=config.GEMINI_API_KEY,
                # Give up if Google does not answer in time (then the backup takes over)
                http_options=types.HttpOptions(timeout=config.GEMINI_TIMEOUT_SECONDS * 1000),
            )

    @property
    def is_configured(self):
        """True when an API key was found in the .env file."""
        return self.client is not None

    def _settings(self):
        """Gemini settings: personality, creativity, and how long it may 'think'."""
        thinking = None
        if self.use_thinking_setting and config.GEMINI_THINKING_LEVEL:
            # Less thinking = the answer starts much sooner
            thinking = types.ThinkingConfig(thinking_level=config.GEMINI_THINKING_LEVEL)
        return types.GenerateContentConfig(
            system_instruction=config.SYSTEM_PROMPT,
            temperature=0.7,
            thinking_config=thinking,
        )

    def stream_reply(self, message, history):
        """Yield the reply piece by piece, like ChatGPT typing.

        message: the new user message (text)
        history: earlier messages as a list of {"role": ..., "content": ...}
        """
        if not self.is_configured:
            raise RuntimeError("GEMINI_API_KEY is missing in the .env file.")

        # Turn the chat history into Gemini's format (keep only recent messages)
        contents = []
        for item in history[-config.MAX_HISTORY_MESSAGES:]:
            role = "user" if item["role"] == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=item["content"])])
            )
        contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

        # Try the main model first, then the backup Gemini model (if set in .env)
        models = [config.GEMINI_MODEL]
        if config.GEMINI_BACKUP_MODEL:
            models.append(config.GEMINI_BACKUP_MODEL)

        start = time.time()
        last_error = None
        for model_name in models:
            attempt = 0
            while attempt <= config.GEMINI_RETRIES:
                got_text = False
                try:
                    stream = self.client.models.generate_content_stream(
                        model=model_name,
                        contents=contents,
                        config=self._settings(),
                    )
                    for chunk in stream:
                        if chunk.text:
                            if not got_text:
                                logger.info("%s: first words after %.1f s", model_name, time.time() - start)
                            got_text = True
                            yield chunk.text
                    logger.info("%s: full answer after %.1f s", model_name, time.time() - start)
                    return  # success: the full answer was sent
                except Exception as error:
                    if got_text:
                        raise  # broke in the middle of an answer: let the router handle it
                    last_error = error
                    # This model does not accept the thinking setting: try again without it
                    if "thinking" in str(error).lower() and self.use_thinking_setting:
                        logger.info("Thinking setting not supported, retrying without it.")
                        self.use_thinking_setting = False
                        continue
                    logger.warning("%s failed after %.1f s: %s", model_name, time.time() - start, error)
                    if not is_busy(error):
                        break  # not a "busy" error: retrying won't help, try the next model
                    attempt += 1
                    if attempt <= config.GEMINI_RETRIES:
                        time.sleep(1)  # busy: wait 1 second, then try again

        raise last_error