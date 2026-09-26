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
    mean_faithfulness: float
    mean_answer_relevancy: float
    citation_accuracy: float
