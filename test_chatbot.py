"""Phase 4 test: check both brains and the fallback, without the chat screen."""

from src.chatbot.router import ChatRouter, MODE_AUTO, MODE_GEMINI, MODE_LOCAL

router = ChatRouter()


def ask(message, mode, history=None):
    """Send one message and print the final reply, who answered, and why."""
    final = None
    for final in router.stream(message, history or [], mode):
        pass  # keep only the last (complete) reply
    reply, source, note = final
    print(f"[{mode}] Q: {message}")
    print(f"   A ({source}{' | ' + note if note else ''}): {reply}")
    print("-" * 60)


# Test 1: is everything found?
print("Status:", router.status())
print("-" * 60)

# Test 2: my trained model
ask("hi, how are you?", MODE_LOCAL)

# Test 3: Gemini
ask("What is machine learning? Answer in one sentence.", MODE_GEMINI)

# Test 4: chat memory (Gemini should remember the name)
history = [
    {"role": "user", "content": "My name is Ali."},
    {"role": "assistant", "content": "Nice to meet you, Ali!"},
]
ask("What is my name?", MODE_GEMINI, history)

# Test 5: fallback (pretend Gemini is down)
router.gemini.client = None
ask("i'm feeling tired today.", MODE_AUTO)