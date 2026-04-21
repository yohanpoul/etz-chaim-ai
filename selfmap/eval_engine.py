"""Moteur d'évaluation — Gevurah-de-Hod : tester la compétence réelle.

Évalue un modèle Ollama sur un domaine via des questions à réponse
vérifiable. Le feu de Shin consume les illusions de compétence.
"""

from __future__ import annotations

from typing import Any

from .models import DomainScore, EvalResult


# Questions d'évaluation par domaine — chaque Q a une réponse attendue
EVAL_SETS: dict[str, list[dict[str, str]]] = {
    "python": [
        {"q": "What does `list.append()` return in Python?", "a": "None"},
        {"q": "Is `dict` ordered in Python 3.7+?", "a": "yes"},
        {"q": "What is the time complexity of `in` for a Python set?", "a": "O(1)"},
        {"q": "What does `//` do in Python?", "a": "integer division"},
        {"q": "What is a generator in Python? Answer in one sentence.", "a": "lazy iterator"},
    ],
    "math": [
        {"q": "What is the derivative of x^3?", "a": "3x^2"},
        {"q": "Is 0 a natural number in the ISO 80000-2 standard?", "a": "yes"},
        {"q": "What is the integral of 1/x?", "a": "ln|x|"},
        {"q": "What is 7! (7 factorial)?", "a": "5040"},
        {"q": "Is the set of rational numbers countable?", "a": "yes"},
    ],
    "history": [
        {"q": "In what year did the French Revolution begin?", "a": "1789"},
        {"q": "Who was the first Emperor of Rome?", "a": "Augustus"},
        {"q": "What treaty ended World War I?", "a": "Treaty of Versailles"},
        {"q": "In which century did the Black Death devastate Europe?", "a": "14th"},
        {"q": "Who invented the printing press in Europe?", "a": "Gutenberg"},
    ],
    "kabbalah": [
        {"q": "How many Sephiroth are there on the Tree of Life?", "a": "10"},
        {"q": "What is the name of Luria's concept of divine contraction?", "a": "Tsimtsum"},
        {"q": "Who wrote the Etz Chaim?", "a": "Chaim Vital"},
        {"q": "What language is the Zohar written in?", "a": "Aramaic"},
        {"q": "What is the Qliphah associated with Tiferet?", "a": "Thagirion"},
    ],
    "medicine": [
        {"q": "What organ produces insulin?", "a": "pancreas"},
        {"q": "What does ECG stand for?", "a": "electrocardiogram"},
        {"q": "What is normal resting heart rate range for adults in bpm?", "a": "60-100"},
        {"q": "What vitamin is produced by sun exposure?", "a": "vitamin D"},
        {"q": "What is the largest organ of the human body?", "a": "skin"},
    ],
    "auto_improve": [
        {"q": "What is the explore-exploit tradeoff in reinforcement learning?", "a": "balancing new actions vs known rewards"},
        {"q": "What does 'novelty detection' mean in machine learning?", "a": "identifying new or unseen patterns"},
        {"q": "What is a hypothesis in the scientific method?", "a": "testable prediction"},
        {"q": "What is ablation study in ML research?", "a": "removing components to measure impact"},
        {"q": "What is the ratchet pattern in iterative improvement?", "a": "progress that cannot regress"},
    ],
    "general": [
        {"q": "What is the capital of France?", "a": "Paris"},
        {"q": "How many bits in a byte?", "a": "8"},
        {"q": "What is the chemical symbol for water?", "a": "H2O"},
        {"q": "What programming paradigm uses classes and objects?", "a": "object-oriented"},
        {"q": "What is the speed of light in vacuum approximately in km/s?", "a": "300000"},
    ],
}

JUDGE_PROMPT = """You are a strict evaluator. Given a question, expected answer, and actual answer, determine if the actual answer is correct.

Question: {question}
Expected answer: {expected}
Actual answer: {actual}

Reply with ONLY "correct" or "incorrect". Nothing else."""


def _default_judge_model() -> str:
    """Get default judge model from config."""
    from olamot import get_model
    return get_model("yetzirah")


def _ollama_generate(
    model: str, prompt: str, timeout: int = 30,
    domain: str | None = None,
    context_items: list[str] | None = None,
) -> tuple[str, float]:
    """Call Ollama via olamot — Hod (Yetzirah) avec model override."""
    from olamot import ollama_generate
    return ollama_generate(
        "yetzirah", prompt, timeout=timeout,
        model=model, temperature=0.1, num_predict=150,
        kavvanah={
            "intention": "Évaluer la qualité de la réponse du système dans ce domaine",
            "critere_succes": "Score calibré reflétant la justesse et la profondeur",
            "anti_pattern": "Ne pas sur-noter par complaisance ni sous-noter par excès de rigueur",
        },
        context_items=context_items,
        principles=["Évaluation stricte : correct ou incorrect, sans complaisance"],
        domain=domain,
    )


def _judge_answer(
    question: str, expected: str, actual: str, judge_model: str
) -> bool:
    """Use a judge model to evaluate correctness."""
    prompt = JUDGE_PROMPT.format(
        question=question, expected=expected, actual=actual
    )
    response, _ = _ollama_generate(
        judge_model, prompt, timeout=15,
        domain="evaluation",
        context_items=[f"Domaine évalué: {question[:80]}"],
    )
    return "correct" in response.lower()


def eval_domain(
    domain: str,
    model_id: str,
    judge_model: str | None = None,
    questions: list[dict[str, str]] | None = None,
) -> DomainScore:
    """Évaluer un modèle sur un domaine.

    Gevurah-de-Hod : le feu qui teste sans complaisance.

    Args:
        domain: Le domaine à évaluer.
        model_id: Le modèle Ollama à tester.
        judge_model: Le modèle qui juge les réponses.
        questions: Questions custom, sinon utilise EVAL_SETS.

    Returns:
        DomainScore avec résultats détaillés.
    """
    if judge_model is None:
        judge_model = _default_judge_model()
    if questions is None:
        questions = EVAL_SETS.get(domain, [])
    if not questions:
        return DomainScore(
            domain=domain, model_id=model_id, score=0.0,
            brier_score=1.0, n_evals=0,
        )

    results: list[EvalResult] = []

    for q_item in questions:
        question = q_item["q"]
        expected = q_item["a"]

        prompt = f"Answer concisely in one or two words if possible.\n\nQuestion: {question}\nAnswer:"
        try:
            actual, latency = _ollama_generate(
                model_id, prompt, timeout=60,
                domain=domain,
                context_items=[f"Évaluation domaine: {domain}"],
            )
        except Exception:
            actual = "[ERROR]"
            latency = 0.0

        correct = _judge_answer(question, expected, actual, judge_model)

        # Estimate confidence from response style (heuristic)
        confidence = 0.8  # default for terse answers
        if "I'm not sure" in actual or "I don't know" in actual:
            confidence = 0.3
        elif "?" in actual:
            confidence = 0.5

        results.append(EvalResult(
            question=question,
            expected=expected,
            actual=actual,
            correct=correct,
            confidence=confidence,
            latency_ms=latency,
        ))

    # Compute scores
    n = len(results)
    score = sum(1 for r in results if r.correct) / n

    # Brier score: mean of (confidence - outcome)^2
    brier = sum(
        (r.confidence - (1.0 if r.correct else 0.0)) ** 2
        for r in results
    ) / n

    return DomainScore(
        domain=domain,
        model_id=model_id,
        score=score,
        brier_score=brier,
        n_evals=n,
        eval_results=results,
    )
