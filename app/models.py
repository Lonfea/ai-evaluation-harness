from pydantic import BaseModel, Field


class GoldenCase(BaseModel):
    id: str
    category: str
    input: str
    expected_output: str
    retrieval_context: list[str]
    expected_citations: list[int] = Field(default_factory=list)
    should_refuse: bool = False


class TargetResult(BaseModel):
    answer: str
    retrieval_context: list[str] = Field(default_factory=list)
    citations: list[int] = Field(default_factory=list)


class AggregateResult(BaseModel):
    cases: int
    pass_rate: float
    citation_accuracy: float
    # LLM-judge metrics are None when the run used deterministic checks only.
    mean_faithfulness: float | None = None
    mean_answer_relevancy: float | None = None
    # Added in v0.2; defaults keep older approved baselines loadable.
    refusal_accuracy: float | None = None
    fact_accuracy: float | None = None
    category_pass_rates: dict[str, float] = Field(default_factory=dict)
