"""How each kind of text is written before embedding.

gemini-embedding-2 has no task_type option. Instead the text gets a short prefix that
says what it is used for (from ai.google.dev/gemini-api/docs/embeddings).
"""


def complaint_text(title: str, description: str) -> str:
    # same prefix on both sides: we compare complaints with complaints
    return f"task: sentence similarity | query: {title.strip()}. {description.strip()}"


def policy_chunk_text(doc_title: str, chunk: str) -> str:
    return f"title: {doc_title} | text: {chunk}"


def question_text(question: str) -> str:
    return f"task: question answering | query: {question.strip()}"
